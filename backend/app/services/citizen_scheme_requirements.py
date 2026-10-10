"""Generic Statutory Scheme Requirements Service (Phase C & G).

Extracts and structures policy-driven form fields, grouping sections, and documentary evidence
specifications for statutory schemes (PM_KISAN, SSY) bound to active PolicyVersions.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.scheme import PolicyVersion, Scheme
from app.schemas.citizen_application import (
    SchemeRequirementEvidence,
    SchemeRequirementField,
    SchemeRequirementsResponse,
)
from app.services.form_metadata_service import (
    SchemeFormNotSupportedError,
    get_policy_form_metadata,
)
from app.services.policy_loader import SchemeNotFoundError
from app.services.policy_selector import PolicyVersionNotFoundError, select_policy_version


async def get_scheme_requirements(
    session: AsyncSession,
    scheme_code: str,
    evaluation_date: Optional[date] = None,
    policy_version_id: Optional[uuid.UUID] = None,
) -> SchemeRequirementsResponse:
    """Retrieve structured data-entry field and evidence specifications for a scheme."""
    eval_date = evaluation_date or date.today()
    normalized_code = scheme_code.strip().upper()

    scheme_stmt = select(Scheme).where(Scheme.scheme_code == normalized_code)
    scheme_res = await session.execute(scheme_stmt)
    scheme = scheme_res.scalar_one_or_none()

    if not scheme:
        raise SchemeNotFoundError(f"Scheme with code '{scheme_code}' was not found in the database.")

    if policy_version_id:
        pv_stmt = select(PolicyVersion).where(
            PolicyVersion.id == policy_version_id,
            PolicyVersion.scheme_id == scheme.id,
        )
        pv_res = await session.execute(pv_stmt)
        policy_version = pv_res.scalar_one_or_none()
        if not policy_version:
            raise PolicyVersionNotFoundError(
                f"Policy version '{policy_version_id}' not found for scheme '{scheme_code}'."
            )
    else:
        policy_version = await select_policy_version(session, normalized_code, eval_date)
        if not policy_version:
            raise PolicyVersionNotFoundError(
                f"No policy version found for scheme '{scheme_code}' effective on {eval_date.isoformat()}."
            )

    try:
        form_meta = get_policy_form_metadata(normalized_code, policy_version.version_code)
    except SchemeFormNotSupportedError as exc:
        raise SchemeNotFoundError(str(exc))

    fields = [
        SchemeRequirementField(
            field_key=f.field_key,
            field_type=f.field_type,
            label_en=f.label_en,
            label_hi=f.label_hi,
            help_text_en=f.help_text_en,
            help_text_hi=f.help_text_hi,
            required=f.required,
            options=f.options,
            default_value=f.default_value,
            claim_type=f.claim_type,
            section_key=f.section_key,
            display_order=f.display_order,
            min_value=f.min_value,
            max_value=f.max_value,
            min_date=f.min_date,
            max_date=f.max_date,
            step=f.step,
            validation_message_en=f.validation_message_en,
            validation_message_hi=f.validation_message_hi,
            associated_evidence_type=f.associated_evidence_type,
            condition=f.condition.model_dump() if f.condition else None,
            is_active=f.is_active,
        )
        for f in form_meta.fields
    ]

    evidence_types = [
        SchemeRequirementEvidence(
            evidence_type=ev.evidence_type,
            label_en=ev.label_en,
            label_hi=ev.label_hi,
            description_en=ev.description_en,
            description_hi=ev.description_hi,
            mandatory=ev.mandatory,
            allowed_extensions=ev.allowed_extensions,
            max_size_mb=ev.max_size_mb,
            associated_field_keys=ev.associated_field_keys,
        )
        for ev in form_meta.evidence_types
    ]

    return SchemeRequirementsResponse(
        scheme_code=scheme.scheme_code,
        scheme_name_en=scheme.name_en,
        scheme_name_hi=scheme.name_hi,
        ministry=scheme.ministry,
        official_url=scheme.official_url,
        policy_version_id=policy_version.id,
        policy_version_code=policy_version.version_code,
        effective_from=str(policy_version.effective_from),
        rule_definition_hash=policy_version.rule_definition_hash,
        sections=form_meta.sections,
        fields=fields,
        evidence_types=evidence_types,
        cross_field_rules=form_meta.cross_field_rules,
    )
