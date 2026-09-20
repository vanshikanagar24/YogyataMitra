"""Deterministic Policy Compiler and Static Analysis Service.

CRITICAL INVARIANTS:
- Deterministic compilation and validation: Same input produces the exact same output.
- Strictly NO network calls and NO AI calls during compilation or validation.
- Validates AST using the official engine validate_ast() validator.
- Computes canonical SHA-256 hash via compute_canonical_rule_hash().
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.ast.nodes import BaseRuleNode, RuleASTNode
from app.engine.ast.validation import validate_ast
from app.engine.explainability.provenance import compute_canonical_rule_hash
from app.models.policy_draft import (
    PolicyDraft,
    PolicyDraftValidationStatus,
)
from app.models.scheme import PolicyVersion, Scheme
from app.schemas.policy_authoring import (
    CompilationResponse,
    ValidationFinding,
    ValidationReportResponse,
)


# ==============================================================================
# Helper to extract all rule IDs and check duplicates
# ==============================================================================

def _collect_ast_nodes(
    node: Any,
    rule_ids: List[str],
    fields: List[str],
    findings: List[ValidationFinding],
) -> None:
    """Recursively collect rule IDs, field paths, and detect obvious issues."""
    if not isinstance(node, dict):
        return

    rule_id = node.get("rule_id")
    if rule_id:
        if rule_id in rule_ids:
            findings.append(
                ValidationFinding(
                    code="DUPLICATE_RULE_ID",
                    message=f"Duplicate rule_id detected: '{rule_id}'. Rule IDs must be unique within ruleset.",
                    rule_id=rule_id,
                )
            )
        rule_ids.append(rule_id)

    # Check field path
    field_path = node.get("field_path") or node.get("dob_field") or node.get("collection_path")
    if field_path:
        fields.append(str(field_path))

    # Check for dangerous code injection patterns
    dangerous_patterns = ["__import__", "eval(", "exec(", "os.system", "subprocess", "import os", "import sys"]
    for val_str in [str(field_path or ""), str(node.get("expected_value", "")), str(node.get("rule_id", ""))]:
        if any(pat in val_str for pat in dangerous_patterns):
            findings.append(
                ValidationFinding(
                    code="UNSUPPORTED_CODE_INJECTION",
                    message=f"Potentially executable or malicious code payload detected in AST: {val_str}",
                    rule_id=rule_id,
                )
            )

    # Check for empty children in logical node
    if node.get("node_type") == "logical":
        children = node.get("children")
        if children is not None and len(children) == 0:
            findings.append(
                ValidationFinding(
                    code="EMPTY_LOGICAL_CHILDREN",
                    message="Logical node has empty children array.",
                    rule_id=rule_id,
                )
            )

    # Traverse children
    if "children" in node and isinstance(node["children"], list):
        for child in node["children"]:
            _collect_ast_nodes(child, rule_ids, fields, findings)

    if "child" in node and isinstance(node["child"], dict):
        _collect_ast_nodes(node["child"], rule_ids, fields, findings)

    if "predicate" in node and isinstance(node["predicate"], dict):
        _collect_ast_nodes(node["predicate"], rule_ids, fields, findings)

    if "rule" in node and isinstance(node["rule"], dict):
        _collect_ast_nodes(node["rule"], rule_ids, fields, findings)


# ==============================================================================
# Static Policy Analysis & Invariant Inspection
# ==============================================================================

async def validate_draft_static_invariants(
    session: AsyncSession,
    draft: PolicyDraft,
) -> ValidationReportResponse:
    """Perform deterministic static policy analysis and structural AST validation."""
    now = datetime.now(timezone.utc)
    errors: List[ValidationFinding] = []
    warnings: List[ValidationFinding] = []
    info: List[ValidationFinding] = []

    # 1. Rule Definition Presence
    rules_json = draft.authored_rules_json or {}
    if not rules_json or not isinstance(rules_json, dict) or not rules_json.get("node_type"):
        errors.append(
            ValidationFinding(
                code="EMPTY_RULESET",
                message="Authored ruleset is empty. A valid root AST rule node is required.",
            )
        )
        return ValidationReportResponse(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            info=info,
            rule_count=0,
            validated_at=now,
        )

    # 2. Engine AST Schema Validation
    try:
        validated_ast_node = validate_ast(rules_json)
        info.append(
            ValidationFinding(
                code="AST_VALID_SCHEMA",
                message=f"Root AST passed strict schema validation ({validated_ast_node.node_type}).",
            )
        )
    except Exception as exc:
        errors.append(
            ValidationFinding(
                code="INVALID_AST_SCHEMA",
                message=f"AST validation failure: {str(exc)}",
            )
        )

    # 3. Rule ID Uniqueness & Structural Consistency
    rule_ids: List[str] = []
    field_paths: List[str] = []
    structural_findings: List[ValidationFinding] = []
    _collect_ast_nodes(rules_json, rule_ids, field_paths, structural_findings)
    errors.extend(structural_findings)

    if not rule_ids:
        warnings.append(
            ValidationFinding(
                code="NO_EXPLICIT_RULE_IDS",
                message="AST contains no explicit rule_ids. Adding unique rule_ids is strongly advised.",
            )
        )
    else:
        info.append(
            ValidationFinding(
                code="RULE_IDS_COLLECTED",
                message=f"Identified {len(rule_ids)} distinct rule nodes.",
            )
        )

    # 4. Temporal and Chronological Sequence Validation
    if draft.effective_from and draft.effective_to:
        if draft.effective_from > draft.effective_to:
            errors.append(
                ValidationFinding(
                    code="INVALID_DATE_RANGE",
                    message=f"Effective start date ({draft.effective_from}) is after end date ({draft.effective_to}).",
                )
            )

    # 5. Overlap and Precedence Risk Analysis against existing PolicyVersion records
    stmt = (
        select(PolicyVersion)
        .where(PolicyVersion.scheme_id == draft.scheme_id)
        .order_by(PolicyVersion.effective_from.asc())
    )
    res = await session.execute(stmt)
    existing_versions = res.scalars().all()

    if draft.effective_from:
        for pv in existing_versions:
            if pv.effective_to and pv.effective_from <= draft.effective_from <= pv.effective_to:
                warnings.append(
                    ValidationFinding(
                        code="POLICY_VERSION_OVERLAP_RISK",
                        message=(
                            f"Proposed effective_from ({draft.effective_from}) falls within existing authoritative "
                            f"version '{pv.version_code}' ({pv.effective_from} to {pv.effective_to}). "
                            "Ensure this draft is intended as an amendment or supersede."
                        ),
                    )
                )

    # 6. Source Provenance Inspection
    if not draft.source_url:
        warnings.append(
            ValidationFinding(
                code="MISSING_SOURCE_PROVENANCE",
                message="Draft has no official source URL attached. Policy authoring should cite statutory sources.",
            )
        )

    if draft.adversarial_flag_detected:
        warnings.append(
            ValidationFinding(
                code="ADVERSARIAL_CONTENT_FLAGGED",
                message="Imported source excerpt was flagged for potential prompt injection. Inspect carefully.",
            )
        )

    # 7. Unverified Source Warning
    if draft.provenance_status in ("UNVERIFIED", "UNVERIFIED_SOURCE"):
        warnings.append(
            ValidationFinding(
                code="UNVERIFIED_SOURCE_NOTICE",
                message="Source provenance is unverified. Substantive statutory documentation required prior to review.",
            )
        )

    is_valid = len(errors) == 0
    return ValidationReportResponse(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        info=info,
        rule_count=len(rule_ids),
        validated_at=now,
    )


# ==============================================================================
# Deterministic Compilation and Hashing
# ==============================================================================

def compile_draft_ruleset(draft: PolicyDraft) -> CompilationResponse:
    """Compile authored AST into canonical representation and calculate SHA-256 hash.
    
    Guarantees:
    - Deterministic: Identical rule AST produces the exact same hash regardless of key order.
    - Zero network calls.
    - Zero AI calls.
    """
    now = datetime.now(timezone.utc)
    rules_json = draft.authored_rules_json or {}

    if not rules_json or not isinstance(rules_json, dict) or not rules_json.get("node_type"):
        raise ValueError("Cannot compile draft: authored ruleset is empty or lacks 'node_type'.")

    # Validate AST first
    validated = validate_ast(rules_json)
    canonical_dict = validated.model_dump(mode="json")

    # Compute hash
    rule_hash = compute_canonical_rule_hash(validated)

    return CompilationResponse(
        is_compiled=True,
        rule_hash=rule_hash,
        canonical_rules_json=canonical_dict,
        compiled_at=now,
    )
