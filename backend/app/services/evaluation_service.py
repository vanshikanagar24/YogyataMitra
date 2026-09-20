"""Evaluation Service.

Orchestrates the lifecycle of an eligibility evaluation request:
1. Resolves Scheme by code from PostgreSQL.
2. Selects PolicyVersion by scheme + evaluation_date using date-bounded logic.
3. Enforces optional policy version matching (historical audit requests).
4. Extracts and validates the declarative Rule AST.
5. Resolves or generates a synthetic non-sensitive Citizen identity.
6. Builds an immutable EvaluationContext preserving Strong Kleene semantics.
7. Executes evaluation using the stateless DeterministicEvaluator.
8. Constructs ExplainabilityTrace and sealed AuditEvaluationRecord.
9. Persists EvaluationTrace into PostgreSQL for immutable historical audit.
10. Formulates the structured EvaluationResponse.

Zero scheme-specific policy branching in this service.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.evaluator.context import EvaluationContext
from app.engine.evaluator.evaluator import DeterministicEvaluator
from app.engine.explainability.audit import create_audit_evaluation_record
from app.engine.explainability.provenance import PolicyProvenance
from app.engine.explainability.trace_builder import build_explainability_trace
from app.engine.types import RuleTruthValue
from app.models.citizen import Citizen
from app.models.enums import EligibilityResult
from app.models.evaluation import EvaluationTrace
from app.models.scheme import PolicyVersion, Scheme
from app.schemas.api import (
    BlockerResponse,
    EvaluationRequest,
    EvaluationResponse,
    PersistedEvaluationResponse,
)
from app.services.policy_loader import SchemeNotFoundError
from app.services.policy_selector import (
    PolicyVersionNotFoundError,
    get_policy_rule_ast,
    select_policy_version,
)


# ==============================================================================
# Domain Exceptions
# ==============================================================================

class EvaluationServiceError(Exception):
    """Base exception for evaluation service failures."""
    pass


class CitizenNotFoundError(EvaluationServiceError):
    """Raised when an explicitly requested citizen_id does not exist."""
    pass


class EvaluationNotFoundError(EvaluationServiceError):
    """Raised when a requested evaluation trace ID is not found in the database."""
    pass


class PolicyVersionConflictError(EvaluationServiceError):
    """Raised when caller requests a policy version conflicting with the effective version."""
    pass


# ==============================================================================
# Service Implementation
# ==============================================================================

class EvaluationService:
    """Service coordinating statutory eligibility evaluation and audit persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.evaluator = DeterministicEvaluator()

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        """Execute a full statutory evaluation and persist audit trace.
        
        Args:
            request: Validated EvaluationRequest with scheme_code, evaluation_date, and facts.
            
        Returns:
            EvaluationResponse with decision, explanations, blockers, and trace.
            
        Raises:
            SchemeNotFoundError: If scheme does not exist.
            PolicyVersionNotFoundError: If no policy covers the evaluation_date.
            PolicyVersionConflictError: If explicit policy_version_code does not match effective version.
            CitizenNotFoundError: If explicit citizen_id does not exist.
        """
        normalized_scheme_code = request.scheme_code.strip().upper()

        # 1. Resolve Scheme
        scheme_stmt = select(Scheme).where(Scheme.scheme_code == normalized_scheme_code)
        scheme_res = await self.session.execute(scheme_stmt)
        scheme = scheme_res.scalar_one_or_none()
        if not scheme:
            raise SchemeNotFoundError(
                f"Statutory scheme with code '{request.scheme_code}' was not found in database."
            )

        # 2. Select PolicyVersion by date
        pv = await select_policy_version(self.session, normalized_scheme_code, request.evaluation_date)
        if not pv:
            raise PolicyVersionNotFoundError(
                f"No statutory policy version found for scheme '{request.scheme_code}' effective on {request.evaluation_date.isoformat()}."
            )

        # 3. Verify explicit policy version if requested (historical audit request)
        if request.policy_version_code:
            requested_code = request.policy_version_code.strip()
            if pv.version_code != requested_code:
                raise PolicyVersionConflictError(
                    f"Requested policy version '{requested_code}' conflicts with statutory policy version '{pv.version_code}' "
                    f"governing {normalized_scheme_code} as of {request.evaluation_date.isoformat()}."
                )

        # 4. Extract validated RuleASTNode
        ast_node = get_policy_rule_ast(pv)

        # 5. Resolve or create synthetic Citizen profile
        citizen = await self._resolve_or_create_citizen(request)

        # 6. Build EvaluationContext
        facts_dict = request.facts.to_engine_dict()
        ctx = EvaluationContext(
            data=facts_dict,
            evaluation_date=request.evaluation_date,
            policy_metadata=dict(pv.rule_set.definition_json.get("metadata", {})) if pv.rule_set and isinstance(pv.rule_set.definition_json, dict) else {},
        )

        # 7. Execute evaluation with generic engine
        eval_result = self.evaluator.evaluate(ast_node, ctx)

        # 8. Build statutory PolicyProvenance
        provenance = PolicyProvenance(
            scheme_id=scheme.id,
            scheme_code=scheme.scheme_code,
            policy_version_id=pv.id,
            policy_version_code=pv.version_code,
            rule_set_id=pv.rule_set.id if pv.rule_set else None,
            rule_set_version=pv.rule_set.rule_set_version if pv.rule_set else "1.0",
            canonical_rule_hash=pv.rule_definition_hash or "",
            evaluation_date=request.evaluation_date,
            effective_from=pv.effective_from,
            effective_to=pv.effective_to,
            source_url=pv.source_url,
            source_title=pv.source_title,
            source_clause=None,
        )

        # 9. Build ExplainabilityTrace
        eval_id = uuid.uuid4()
        explainability_trace = build_explainability_trace(
            eval_result=eval_result,
            provenance=provenance,
            evaluation_id=eval_id,
        )

        # 10. Persist immutable AuditEvaluationRecord -> EvaluationTrace
        audit_record = create_audit_evaluation_record(
            citizen_ref=citizen.synthetic_reference,
            input_data=facts_dict,
            provenance=provenance,
            explainability_trace=explainability_trace,
            evaluation_id=eval_id,
        )
        db_trace_model = audit_record.to_db_model(
            citizen_id=citizen.id,
            scheme_id=scheme.id,
            policy_version_id=pv.id,
        )
        self.session.add(db_trace_model)
        await self.session.commit()

        # 11. Extract natural-language reasons from trace nodes
        reasons_en, reasons_hi = self._extract_reasons(explainability_trace)

        # 12. Format Blocker responses
        blockers = [
            BlockerResponse(
                code=b.code,
                category=b.category.value if hasattr(b.category, "value") else str(b.category),
                field_path=b.field_path,
                rule_id=b.rule_id,
                message_en=b.message_en,
                message_hi=b.message_hi,
            )
            for b in explainability_trace.blockers
        ]

        return EvaluationResponse(
            evaluation_id=eval_id,
            scheme_code=scheme.scheme_code,
            policy_version_code=pv.version_code,
            rule_definition_hash=pv.rule_definition_hash or "",
            evaluation_date=request.evaluation_date,
            effective_from=pv.effective_from,
            effective_to=pv.effective_to,
            overall_result=eval_result.overall_result,
            root_truth_value=eval_result.root_truth_value.value,
            reasons_en=reasons_en,
            reasons_hi=reasons_hi,
            missing_fields=list(eval_result.all_missing_fields),
            satisfied_rules=list(eval_result.satisfied_rules),
            failed_rules=list(eval_result.failed_rules),
            unknown_rules=list(eval_result.unknown_rules),
            blockers=blockers,
            audit_persisted=True,
            created_at=datetime.now(timezone.utc),
            trace=explainability_trace.model_dump(mode="json"),
        )

    async def get_evaluation_by_id(self, evaluation_id: uuid.UUID) -> PersistedEvaluationResponse:
        """Retrieve a persisted evaluation trace and audit snapshot by ID.
        
        Args:
            evaluation_id: UUID of the persisted evaluation.
            
        Returns:
            PersistedEvaluationResponse with snapshot and trace data.
            
        Raises:
            EvaluationNotFoundError: If the evaluation does not exist.
        """
        stmt = (
            select(EvaluationTrace)
            .options(
                selectinload(EvaluationTrace.scheme),
                selectinload(EvaluationTrace.policy_version),
            )
            .where(EvaluationTrace.id == evaluation_id)
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            raise EvaluationNotFoundError(
                f"Evaluation record with identifier '{evaluation_id}' was not found in audit logs."
            )

        return PersistedEvaluationResponse(
            id=record.id,
            citizen_id=record.citizen_id,
            scheme_id=record.scheme_id,
            scheme_code=record.scheme.scheme_code,
            policy_version_id=record.policy_version_id,
            policy_version_code=record.policy_version.version_code,
            evaluation_date=record.evaluation_date,
            result_state=record.result_state,
            rule_definition_hash=record.rule_definition_hash,
            trace_schema_version=record.trace_schema_version,
            input_snapshot_json=record.input_snapshot_json,
            trace_json=record.trace_json,
            created_at=record.created_at,
        )

    async def _resolve_or_create_citizen(self, request: EvaluationRequest) -> Citizen:
        """Resolve an existing Citizen or link to a minimal statutory reference entity.
        
        Preserves domain model foreign key invariant (evaluation_traces.citizen_id NOT NULL)
        without silently inventing fake citizen identities or introducing unnecessary PII:
        1. If explicit citizen_id is supplied, validates existence or raises CitizenNotFoundError.
        2. If citizen_ref is supplied, looks up existing record or creates a minimal record with
           only synthetic_reference (no PII, no fake names, all demographic fields None).
           Repeated evaluations for the same citizen_ref link to the same Citizen row.
        3. If no citizen identifier is provided, links the evaluation to a single canonical
           system entity ('SYSTEM_ANONYMOUS_CITIZEN') rather than generating fake identities.
        """
        if request.citizen_id:
            citizen = await self.session.get(Citizen, request.citizen_id)
            if not citizen:
                raise CitizenNotFoundError(f"Citizen with identifier '{request.citizen_id}' was not found.")
            return citizen

        if request.citizen_ref:
            target_ref = request.citizen_ref.strip()
            stmt = select(Citizen).where(Citizen.synthetic_reference == target_ref)
            res = await self.session.execute(stmt)
            citizen = res.scalar_one_or_none()
            if citizen:
                return citizen
            # Minimal representation: only the provided reference, zero invented PII
            new_citizen = Citizen(
                synthetic_reference=target_ref,
                display_name=None,
                date_of_birth=None,
                gender=None,
                state=None,
                district=None,
            )
            self.session.add(new_citizen)
            await self.session.flush()
            return new_citizen

        # When caller provides no citizen identity, link to a single canonical system entity
        canonical_anonymous_ref = "SYSTEM_ANONYMOUS_CITIZEN"
        stmt = select(Citizen).where(Citizen.synthetic_reference == canonical_anonymous_ref)
        res = await self.session.execute(stmt)
        anon_citizen = res.scalar_one_or_none()
        if anon_citizen:
            return anon_citizen

        anon_citizen = Citizen(
            synthetic_reference=canonical_anonymous_ref,
            display_name=None,
            date_of_birth=None,
            gender=None,
            state=None,
            district=None,
        )
        self.session.add(anon_citizen)
        await self.session.flush()
        return anon_citizen

    def _extract_reasons(self, trace) -> tuple[List[str], List[str]]:
        """Extract bilingual explanations ordered logically for user-facing feedback."""
        reasons_en: List[str] = []
        reasons_hi: List[str] = []

        # If overall is INELIGIBLE, prioritize failed rule explanations
        if trace.overall_result == EligibilityResult.INELIGIBLE:
            for node in trace.ordered_nodes:
                if node.truth_value == RuleTruthValue.FALSE and node.explanation_en:
                    if node.explanation_en not in reasons_en:
                        reasons_en.append(node.explanation_en)
                        reasons_hi.append(node.explanation_hi)
        elif trace.overall_result == EligibilityResult.ELIGIBLE:
            # If ELIGIBLE, collect root or satisfied rule explanations
            if trace.root_node.explanation_en:
                reasons_en.append(trace.root_node.explanation_en)
                reasons_hi.append(trace.root_node.explanation_hi)
        elif trace.overall_result == EligibilityResult.INSUFFICIENT_INFORMATION:
            for blocker in trace.blockers:
                if blocker.message_en and blocker.message_en not in reasons_en:
                    reasons_en.append(blocker.message_en)
                    reasons_hi.append(blocker.message_hi)

        return reasons_en, reasons_hi
