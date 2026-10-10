"""Provenance Ingestion and Seeding Service.

Populates official government sources, official documents, document versions,
policy-version bindings, and rule-level provenances for all 10 statutory schemes
and 14 policy versions in YogyataMitra.
"""

from __future__ import annotations

from datetime import date, datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    DocumentVersionStatus,
    OfficialDocumentType,
    OfficialSourceType,
    PolicySourceBindingType,
    ProvenanceCompleteness,
)
from app.models.scheme import PolicyVersion, RuleSet, Scheme
from app.services.provenance_service import ProvenanceService

logger = logging.getLogger("yogyatamitra.services.provenance_loader")

# Canonical ministry, domain, and document registry mapping for the 10 statutory schemes
OFFICIAL_SCHEME_METADATA = {
    "PM_KISAN": {
        "publisher_name": "Department of Agriculture and Farmers Welfare, Ministry of Agriculture & Farmers Welfare",
        "publisher_type": OfficialSourceType.DEPARTMENT,
        "official_domain": "pmkisan.gov.in",
        "canonical_url": "https://pmkisan.gov.in",
        "source_type": OfficialSourceType.MINISTRY,
        "document_title": "Operational Guidelines for Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "document_type": OfficialDocumentType.OPERATIONAL_GUIDELINE,
        "issuing_authority": "Department of Agriculture and Farmers Welfare, Government of India",
        "reference_number": "F.No. 1-1/2019-Credit-II",
    },
    "SSY": {
        "publisher_name": "Department of Economic Affairs, Ministry of Finance",
        "publisher_type": OfficialSourceType.DEPARTMENT,
        "official_domain": "dea.gov.in",
        "canonical_url": "https://dea.gov.in",
        "source_type": OfficialSourceType.MINISTRY,
        "document_title": "Sukanya Samriddhi Account Scheme (Statutory Rules & Amendments)",
        "document_type": OfficialDocumentType.GAZETTE_NOTIFICATION,
        "issuing_authority": "Department of Economic Affairs, Ministry of Finance, Government of India",
        "reference_number": "G.S.R. 914(E)",
    },
    "PM_KMY": {
        "publisher_name": "Ministry of Agriculture and Farmers Welfare",
        "publisher_type": OfficialSourceType.MINISTRY,
        "official_domain": "maandhan.in",
        "canonical_url": "https://maandhan.in",
        "source_type": OfficialSourceType.MINISTRY,
        "document_title": "Pradhan Mantri Kisan Maan-Dhan Yojana (PM-KMY) Scheme Guidelines",
        "document_type": OfficialDocumentType.SCHEME_GUIDELINE,
        "issuing_authority": "Department of Agriculture, Cooperation & Farmers Welfare, GoI",
        "reference_number": "PMKMY-GUIDELINES-2019",
    },
    "PMUY": {
        "publisher_name": "Ministry of Petroleum and Natural Gas",
        "publisher_type": OfficialSourceType.MINISTRY,
        "official_domain": "pmuy.gov.in",
        "canonical_url": "https://pmuy.gov.in",
        "source_type": OfficialSourceType.MINISTRY,
        "document_title": "Pradhan Mantri Ujjwala Yojana (PMUY) 2.0 Guidelines",
        "document_type": OfficialDocumentType.SCHEME_GUIDELINE,
        "issuing_authority": "Ministry of Petroleum and Natural Gas, Government of India",
        "reference_number": "PMUY-2.0-GUIDELINES-2021",
    },
    "PM_VISHWAKARMA": {
        "publisher_name": "Ministry of Micro, Small and Medium Enterprises",
        "publisher_type": OfficialSourceType.MINISTRY,
        "official_domain": "pmvishwakarma.gov.in",
        "canonical_url": "https://pmvishwakarma.gov.in",
        "source_type": OfficialSourceType.MINISTRY,
        "document_title": "PM Vishwakarma Scheme Operational Guidelines",
        "document_type": OfficialDocumentType.OPERATIONAL_GUIDELINE,
        "issuing_authority": "Ministry of Micro, Small and Medium Enterprises, Government of India",
        "reference_number": "PM-VISHWAKARMA-2023",
    },
    "PMAY_G": {
        "publisher_name": "Ministry of Rural Development",
        "publisher_type": OfficialSourceType.MINISTRY,
        "official_domain": "pmayg.nic.in",
        "canonical_url": "https://pmayg.nic.in",
        "source_type": OfficialSourceType.MINISTRY,
        "document_title": "Framework for Implementation of Pradhan Mantri Awaas Yojana - Gramin",
        "document_type": OfficialDocumentType.FRAMEWORK,
        "issuing_authority": "Department of Rural Development, Ministry of Rural Development, GoI",
        "reference_number": "PMAYG-FRAMEWORK-2016",
    },
    "PMAY_U_2_0": {
        "publisher_name": "Ministry of Housing and Urban Affairs",
        "publisher_type": OfficialSourceType.MINISTRY,
        "official_domain": "pmay-urban.gov.in",
        "canonical_url": "https://pmay-urban.gov.in",
        "source_type": OfficialSourceType.MINISTRY,
        "document_title": "Pradhan Mantri Awas Yojana - Urban 2.0 (PMAY-U 2.0) Guidelines",
        "document_type": OfficialDocumentType.SCHEME_GUIDELINE,
        "issuing_authority": "Ministry of Housing and Urban Affairs, Government of India",
        "reference_number": "PMAYU-2.0-GUIDELINES-2024",
    },
    "PM_SVANIDHI": {
        "publisher_name": "Ministry of Housing and Urban Affairs",
        "publisher_type": OfficialSourceType.MINISTRY,
        "official_domain": "pmsvanidhi.mohua.gov.in",
        "canonical_url": "https://pmsvanidhi.mohua.gov.in",
        "source_type": OfficialSourceType.MINISTRY,
        "document_title": "Scheme Guidelines for PM Street Vendor's AtmaNirbhar Nidhi (PM SVANidhi)",
        "document_type": OfficialDocumentType.SCHEME_GUIDELINE,
        "issuing_authority": "Ministry of Housing and Urban Affairs, Government of India",
        "reference_number": "PMSVANIDHI-GUIDELINES-2020",
    },
    "PMMVY": {
        "publisher_name": "Ministry of Women and Child Development",
        "publisher_type": OfficialSourceType.MINISTRY,
        "official_domain": "wcd.nic.in",
        "canonical_url": "https://wcd.nic.in",
        "source_type": OfficialSourceType.MINISTRY,
        "document_title": "Mission Shakti — Guidelines for Implementation of Pradhan Mantri Matru Vandana Yojana",
        "document_type": OfficialDocumentType.SCHEME_GUIDELINE,
        "issuing_authority": "Ministry of Women and Child Development, Government of India",
        "reference_number": "PMMVY-MISSION-SHAKTI-2022",
    },
    "IGNOAPS": {
        "publisher_name": "Ministry of Rural Development (National Social Assistance Programme)",
        "publisher_type": OfficialSourceType.MINISTRY,
        "official_domain": "nsap.nic.in",
        "canonical_url": "https://nsap.nic.in",
        "source_type": OfficialSourceType.MINISTRY,
        "document_title": "National Social Assistance Programme (NSAP) Operational Guidelines",
        "document_type": OfficialDocumentType.OPERATIONAL_GUIDELINE,
        "issuing_authority": "Department of Rural Development, Ministry of Rural Development, GoI",
        "reference_number": "NSAP-GUIDELINES-2014",
    },
}


def _extract_rule_clauses(node: Any, accumulator: List[Tuple[str, Optional[str], Optional[str]]]) -> None:
    """Traverse an AST definition tree to extract (rule_id, source_clause, description)."""
    if isinstance(node, dict):
        rule_id = node.get("rule_id")
        source_clause = node.get("source_clause")
        desc = node.get("description_en") or node.get("description")
        if rule_id:
            accumulator.append((rule_id, source_clause, desc))

        for k, v in node.items():
            if isinstance(v, list):
                for item in v:
                    _extract_rule_clauses(item, accumulator)
            elif isinstance(v, dict):
                _extract_rule_clauses(v, accumulator)


async def seed_all_provenance(session: AsyncSession) -> Dict[str, Any]:
    """Populate official government sources, documents, versions, bindings, and rule provenances.
    
    Idempotent: preserves existing records, avoids duplicate bindings, and records audit trail events.
    """
    service = ProvenanceService(session)

    # Resolve schemes_data folder
    backend_dir = Path(__file__).resolve().parent.parent.parent
    schemes_dir = backend_dir.parent / "schemes_data"
    if not schemes_dir.exists():
        schemes_dir = Path("schemes_data").resolve()

    results = {
        "sources_registered": 0,
        "documents_registered": 0,
        "document_versions_registered": 0,
        "policy_bindings_registered": 0,
        "rules_bound": 0,
    }

    # Fetch all Schemes and PolicyVersions from DB
    stmt = (
        select(Scheme)
        .options(
            selectinload(Scheme.policy_versions).selectinload(PolicyVersion.rule_set)
        )
        .order_by(Scheme.scheme_code)
    )
    res = await session.execute(stmt)
    schemes = res.scalars().all()

    for scheme in schemes:
        meta = OFFICIAL_SCHEME_METADATA.get(scheme.scheme_code)
        if not meta:
            logger.warning("No official provenance metadata registered for scheme %s", scheme.scheme_code)
            continue

        # 1. Register OfficialSource
        source = await service.register_official_source(
            publisher_name=meta["publisher_name"],
            publisher_type=meta["publisher_type"],
            official_domain=meta["official_domain"],
            canonical_url=meta["canonical_url"],
            source_type=meta["source_type"],
            scheme_code=scheme.scheme_code,
            description=f"Official publishing authority for {scheme.name_en}",
        )
        results["sources_registered"] += 1

        # 2. Register OfficialDocument
        doc = await service.register_official_document(
            official_source_id=source.id,
            scheme_code=scheme.scheme_code,
            document_title=meta["document_title"],
            document_type=meta["document_type"],
            issuing_authority=meta["issuing_authority"],
            official_url=meta["canonical_url"],
            reference_number=meta["reference_number"],
        )
        results["documents_registered"] += 1

        # 3. For each PolicyVersion, register OfficialDocumentVersion and bindings
        prev_dv_id = None
        for pv in sorted(scheme.policy_versions, key=lambda v: v.effective_from):
            doc_url = pv.source_url if pv.source_url.startswith("https://") else f"{meta['canonical_url']}/guidelines"

            dv = await service.add_document_version(
                document_id=doc.id,
                version_label=pv.version_code,
                official_url=doc_url,
                published_at=pv.effective_from,
                effective_from=pv.effective_from,
                effective_to=pv.effective_to,
                supersedes_version_id=prev_dv_id,
                status=DocumentVersionStatus.ACTIVE if pv.effective_to is None or pv.effective_to >= date.today() else DocumentVersionStatus.SUPERSEDED,
                # Metadata-only entry: document_hash is None because raw PDF binary is not stored locally.
                # Phase J: Use SOURCE_METADATA_VERIFIED for metadata-only entries (no physical artifact).
                provenance_completeness=ProvenanceCompleteness.SOURCE_METADATA_VERIFIED if not pv.source_document_identifier else ProvenanceCompleteness.COMPLETE,
            )
            prev_dv_id = dv.id
            results["document_versions_registered"] += 1

            # 4. Bind PolicyVersion to OfficialDocumentVersion
            citation_text = pv.source_title
            await service.bind_policy_to_document(
                policy_version_id=pv.id,
                document_version_id=dv.id,
                binding_type=PolicySourceBindingType.PRIMARY_SOURCE,
                citation=citation_text[:255] if citation_text else None,
                notes=f"Statutory foundation for {scheme.scheme_code} version {pv.version_code}.",
            )
            results["policy_bindings_registered"] += 1

            # 5. Extract and bind rule-level provenance from RuleSet AST
            if pv.rule_set and pv.rule_set.definition_json:
                rule_clauses: List[Tuple[str, Optional[str], Optional[str]]] = []
                _extract_rule_clauses(pv.rule_set.definition_json, rule_clauses)

                for r_id, r_clause, r_desc in rule_clauses:
                    locator = r_clause or "General Provisions"
                    rule_cit = f"{doc.document_title}, {locator}"
                    await service.bind_rule_provenance(
                        rule_id=r_id,
                        policy_version_id=pv.id,
                        document_version_id=dv.id,
                        citation=rule_cit[:255],
                        source_locator=locator[:128],
                        provenance_type="STATUTORY_RULE",
                        notes=r_desc,
                    )
                    results["rules_bound"] += 1

    await session.commit()
    logger.info("Provenance seeding completed: %s", results)
    return results
