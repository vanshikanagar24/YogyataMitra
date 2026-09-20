"""Policy Ingestion and Materialization Service.

Discovers declarative scheme manifests and policy versions from disk, validates
syntactic and structural AST invariants, computes canonical SHA-256 cryptographic hashes,
and idempotently materializes them into PostgreSQL.

Enforces strict policy immutability: fails loudly with PolicyHashConflictError
if an incoming definition has a conflicting hash for an existing version code.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.engine.ast.nodes import BaseRuleNode, LogicalNode, RuleASTNode
from app.engine.ast.validation import validate_ast
from app.engine.explainability.provenance import compute_canonical_rule_hash
from app.models.enums import SchemeStatus
from app.models.scheme import PolicyVersion, RuleSet, Scheme

logger = logging.getLogger("yogyatamitra.services.policy_loader")


# ==============================================================================
# Domain Exceptions
# ==============================================================================

class PolicyLoaderError(Exception):
    """Base exception for policy loading and materialization failures."""
    pass


class PolicyValidationError(PolicyLoaderError):
    """Raised when policy metadata or AST fails statutory structural invariants."""
    pass


class PolicyHashConflictError(PolicyLoaderError):
    """Raised when an existing persisted policy version has a conflicting hash.
    
    Statutory policy versions are immutable once enacted. Any modification requires
    a new version code rather than overwriting historical records.
    """
    pass


class SchemeNotFoundError(PolicyLoaderError):
    """Raised when a referenced scheme does not exist in the database or filesystem."""
    pass


# ==============================================================================
# Ingestion File Schemas
# ==============================================================================

class SourceMetadata(BaseModel):
    """Authoritative statutory source reference."""
    title: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    reference: Optional[str] = None
    document_identifier: Optional[str] = None


class SchemeManifest(BaseModel):
    """Declarative scheme manifest schema."""
    scheme_code: str = Field(..., min_length=1, max_length=64)
    name_en: str = Field(..., min_length=1, max_length=255)
    name_hi: str = Field(..., min_length=1, max_length=255)
    description_en: str = Field(..., min_length=1)
    description_hi: str = Field(..., min_length=1)
    ministry: Optional[str] = None
    official_url: str = Field(..., min_length=1, max_length=512)
    status: str = Field(default="ACTIVE")


class PolicyVersionFile(BaseModel):
    """Declarative policy version file schema."""
    scheme_code: str = Field(..., min_length=1, max_length=64)
    policy_version_code: str = Field(..., min_length=1, max_length=64)
    effective_from: date
    effective_to: Optional[date] = None
    source: SourceMetadata
    ruleset_version: str = Field(default="1.0.0")
    root_rule: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


# ==============================================================================
# Structural AST and Invariant Validation
# ==============================================================================

def _collect_rule_ids_from_ast(node_data: Dict[str, Any], seen: Optional[Set[str]] = None) -> Set[str]:
    """Recursively collect and verify uniqueness of all rule_ids in an AST dictionary."""
    if seen is None:
        seen = set()

    rule_id = node_data.get("rule_id")
    if not rule_id:
        raise PolicyValidationError(f"AST node of type '{node_data.get('node_type')}' is missing mandatory 'rule_id'.")

    if rule_id in seen:
        raise PolicyValidationError(f"Duplicate rule_id detected within ruleset: '{rule_id}'. Rule IDs must be globally unique within a version.")
    seen.add(rule_id)

    # Inspect children if logical node
    if "children" in node_data and isinstance(node_data["children"], list):
        for child in node_data["children"]:
            if isinstance(child, dict):
                _collect_rule_ids_from_ast(child, seen)

    # Inspect single child (e.g. NOT or CONTEXT_SCOPE)
    if "child" in node_data and isinstance(node_data["child"], dict):
        _collect_rule_ids_from_ast(node_data["child"], seen)

    # Inspect predicate if collection node
    if "predicate" in node_data and isinstance(node_data["predicate"], dict):
        _collect_rule_ids_from_ast(node_data["predicate"], seen)

    return seen


def validate_policy_file_structure(policy_file: PolicyVersionFile, manifest: SchemeManifest) -> RuleASTNode:
    """Validate all structural, semantic, and relational invariants of a policy version file."""
    if policy_file.scheme_code.upper() != manifest.scheme_code.upper():
        raise PolicyValidationError(
            f"Policy file scheme_code '{policy_file.scheme_code}' does not match manifest scheme_code '{manifest.scheme_code}'."
        )

    if policy_file.effective_to is not None and policy_file.effective_from > policy_file.effective_to:
        raise PolicyValidationError(
            f"Policy version '{policy_file.policy_version_code}' has invalid date range: "
            f"effective_from ({policy_file.effective_from}) > effective_to ({policy_file.effective_to})."
        )

    # Collect rule IDs and verify uniqueness
    rule_ids = _collect_rule_ids_from_ast(policy_file.root_rule)
    if not rule_ids:
        raise PolicyValidationError(f"Policy version '{policy_file.policy_version_code}' contains no rule IDs.")

    # Validate the full AST structure using generic engine validator
    try:
        validated_root = validate_ast(policy_file.root_rule)
    except Exception as exc:
        raise PolicyValidationError(
            f"Policy version '{policy_file.policy_version_code}' failed AST validation: {exc}"
        ) from exc

    return validated_root


def validate_policy_sequence(policies: List[PolicyVersionFile]) -> None:
    """Validate chronological ordering and non-overlapping sequence across versions of a scheme."""
    sorted_policies = sorted(policies, key=lambda p: p.effective_from)
    version_codes = set()

    for idx, p in enumerate(sorted_policies):
        if p.policy_version_code in version_codes:
            raise PolicyValidationError(f"Duplicate policy_version_code '{p.policy_version_code}' found.")
        version_codes.add(p.policy_version_code)

        if idx > 0:
            prev = sorted_policies[idx - 1]
            if prev.effective_to is None:
                raise PolicyValidationError(
                    f"Policy version '{prev.policy_version_code}' is open-ended (effective_to is null) "
                    f"but subsequent version '{p.policy_version_code}' begins at {p.effective_from}."
                )
            if prev.effective_to >= p.effective_from:
                raise PolicyValidationError(
                    f"Policy version dates overlap between '{prev.policy_version_code}' (to {prev.effective_to}) "
                    f"and '{p.policy_version_code}' (from {p.effective_from})."
                )


# ==============================================================================
# Discovery and Reading
# ==============================================================================

def get_default_schemes_data_dir() -> Path:
    """Resolve default schemes_data directory from project root."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    schemes_dir = backend_dir.parent / "schemes_data"
    if not schemes_dir.exists():
        # Fallback to local schemes_data if running from another directory
        schemes_dir = Path("schemes_data").resolve()
    return schemes_dir


def discover_schemes_and_policies(base_dir: Optional[Path] = None) -> Dict[str, Tuple[SchemeManifest, List[PolicyVersionFile]]]:
    """Discover and parse all scheme manifests and policy version files.
    
    Returns:
        Mapping of scheme_code -> (SchemeManifest, List[PolicyVersionFile])
    """
    schemes_path = base_dir or get_default_schemes_data_dir()
    if not schemes_path.exists():
        raise PolicyLoaderError(f"Schemes data directory not found: {schemes_path}")

    discovered: Dict[str, Tuple[SchemeManifest, List[PolicyVersionFile]]] = {}

    for scheme_folder in sorted(schemes_path.iterdir()):
        if not scheme_folder.is_dir() or scheme_folder.name.startswith("."):
            continue

        manifest_file = scheme_folder / "scheme.json"
        if not manifest_file.exists():
            manifest_file = scheme_folder / "manifest.json"
        if not manifest_file.exists():
            continue

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        manifest = SchemeManifest.model_validate(manifest_data)

        policies_dir = scheme_folder / "policies"
        if not policies_dir.exists() or not policies_dir.is_dir():
            # Support policies directly in folder if no 'policies' subfolder
            policy_files = list(scheme_folder.glob("v*.json"))
        else:
            policy_files = list(policies_dir.glob("*.json"))

        policies: List[PolicyVersionFile] = []
        for pfile in sorted(policy_files):
            with open(pfile, "r", encoding="utf-8") as f:
                pdata = json.load(f)
            policy = PolicyVersionFile.model_validate(pdata)
            validate_policy_file_structure(policy, manifest)
            policies.append(policy)

        if not policies:
            raise PolicyValidationError(f"Scheme '{manifest.scheme_code}' has no policy versions in {scheme_folder}.")

        validate_policy_sequence(policies)
        discovered[manifest.scheme_code] = (manifest, policies)

    return discovered


# ==============================================================================
# Database Materialization Service
# ==============================================================================

async def load_scheme(session: AsyncSession, manifest: SchemeManifest) -> Scheme:
    """Idempotently load or update a Scheme domain entity."""
    stmt = select(Scheme).where(Scheme.scheme_code == manifest.scheme_code)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    status_enum = SchemeStatus[manifest.status.upper()] if manifest.status.upper() in SchemeStatus.__members__ else SchemeStatus.ACTIVE

    if existing:
        existing.name_en = manifest.name_en
        existing.name_hi = manifest.name_hi
        existing.description_en = manifest.description_en
        existing.description_hi = manifest.description_hi
        existing.ministry = manifest.ministry
        existing.official_url = manifest.official_url
        existing.status = status_enum
        await session.flush()
        return existing

    new_scheme = Scheme(
        id=uuid.uuid4(),
        scheme_code=manifest.scheme_code,
        name_en=manifest.name_en,
        name_hi=manifest.name_hi,
        description_en=manifest.description_en,
        description_hi=manifest.description_hi,
        ministry=manifest.ministry,
        official_url=manifest.official_url,
        status=status_enum,
    )
    session.add(new_scheme)
    await session.flush()
    return new_scheme


async def load_policy_version(
    session: AsyncSession,
    scheme: Scheme,
    policy_data: PolicyVersionFile,
) -> Tuple[PolicyVersion, RuleSet, bool]:
    """Idempotently load a PolicyVersion and its RuleSet with strict conflict detection.
    
    Returns:
        (policy_version, rule_set, created: bool)
    
    Raises:
        PolicyHashConflictError: If the policy version already exists with a different hash.
    """
    # Compute canonical hash from root rule AST
    canonical_hash = compute_canonical_rule_hash(policy_data.root_rule)

    stmt = (
        select(PolicyVersion)
        .options(selectinload(PolicyVersion.rule_set))
        .where(
            PolicyVersion.scheme_id == scheme.id,
            PolicyVersion.version_code == policy_data.policy_version_code,
        )
    )
    result = await session.execute(stmt)
    existing_pv = result.scalar_one_or_none()

    if existing_pv:
        # Enforce strict immutability check
        if existing_pv.rule_definition_hash and existing_pv.rule_definition_hash != canonical_hash:
            raise PolicyHashConflictError(
                f"Policy version '{policy_data.policy_version_code}' for scheme '{scheme.scheme_code}' "
                f"already exists with hash '{existing_pv.rule_definition_hash}', but incoming definition has "
                f"conflicting hash '{canonical_hash}'. Statutory policies are immutable once enacted. "
                f"Increment or change the policy version code to enact amended rules."
            )
        # Update metadata if needed while preserving immutability
        existing_pv.source_url = policy_data.source.url
        existing_pv.source_title = policy_data.source.title
        existing_pv.source_document_identifier = policy_data.source.document_identifier
        existing_pv.rule_definition_hash = canonical_hash
        await session.flush()
        return existing_pv, existing_pv.rule_set, False

    # Create new PolicyVersion
    new_pv = PolicyVersion(
        id=uuid.uuid4(),
        scheme_id=scheme.id,
        version_code=policy_data.policy_version_code,
        effective_from=policy_data.effective_from,
        effective_to=policy_data.effective_to,
        source_url=policy_data.source.url,
        source_title=policy_data.source.title,
        source_document_identifier=policy_data.source.document_identifier,
        rule_definition_hash=canonical_hash,
    )
    session.add(new_pv)
    await session.flush()

    # RuleSet definition JSON stores root_rule and metadata
    new_rs = RuleSet(
        id=uuid.uuid4(),
        policy_version_id=new_pv.id,
        definition_json=policy_data.root_rule,
        schema_version="1.0",
        rule_set_version=policy_data.ruleset_version,
    )
    session.add(new_rs)
    await session.flush()

    return new_pv, new_rs, True


async def load_all_policies(
    schemes_dir: Optional[Path] = None,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Discover, validate, and materialize all policy manifests and versions.
    
    Guarantees:
    - Pre-flight validation occurs in memory before any DB writes.
    - Idempotent execution: existing records with matching hashes are preserved.
    - Fails loudly on hash conflicts.
    """
    discovered = discover_schemes_and_policies(schemes_dir)

    results: Dict[str, Any] = {
        "schemes_processed": len(discovered),
        "schemes": {},
        "total_versions_loaded": 0,
        "total_versions_created": 0,
        "total_versions_retained": 0,
    }

    async def _execute_with_session(s: AsyncSession) -> Dict[str, Any]:
        for scheme_code, (manifest, policies) in discovered.items():
            scheme_entity = await load_scheme(s, manifest)
            scheme_summary = {
                "scheme_code": scheme_code,
                "scheme_id": str(scheme_entity.id),
                "versions": [],
            }

            for pdata in policies:
                pv, rs, created = await load_policy_version(s, scheme_entity, pdata)
                status_str = "CREATED" if created else "RETAINED"
                if created:
                    results["total_versions_created"] += 1
                else:
                    results["total_versions_retained"] += 1
                results["total_versions_loaded"] += 1

                scheme_summary["versions"].append({
                    "version_code": pv.version_code,
                    "policy_version_id": str(pv.id),
                    "rule_set_id": str(rs.id) if rs else None,
                    "effective_from": pv.effective_from.isoformat(),
                    "effective_to": pv.effective_to.isoformat() if pv.effective_to else None,
                    "canonical_hash": pv.rule_definition_hash,
                    "status": status_str,
                })

            results["schemes"][scheme_code] = scheme_summary

        await s.commit()
        return results

    if session is not None:
        return await _execute_with_session(session)
    else:
        async with AsyncSessionLocal() as s:
            return await _execute_with_session(s)


# ==============================================================================
# CLI Entrypoint
# ==============================================================================

async def main() -> None:
    """CLI runner for policy ingestion."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("\n============================================================")
    print("YogyataMitra — Policy Ingestion & Materialization")
    print("============================================================\n")

    try:
        summary = await load_all_policies()
        print(f"Ingestion successful! Schemes: {summary['schemes_processed']}, "
              f"Versions Loaded: {summary['total_versions_loaded']} "
              f"(Created: {summary['total_versions_created']}, Retained: {summary['total_versions_retained']})")
        for sc, sdata in summary["schemes"].items():
            print(f"\nScheme: {sc} (ID: {sdata['scheme_id']})")
            for v in sdata["versions"]:
                print(f"  Version: {v['version_code']} [{v['effective_from']} to {v['effective_to'] or 'PRESENT'}] "
                      f"Status: {v['status']} Hash: {v['canonical_hash'][:16]}...")
        print("\nPolicy materialization completed successfully.\n")
    except PolicyHashConflictError as pce:
        print(f"\n[FATAL HASH CONFLICT] {pce}\n")
        raise SystemExit(1)
    except PolicyValidationError as pve:
        print(f"\n[VALIDATION ERROR] {pve}\n")
        raise SystemExit(1)
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {exc}\n")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
