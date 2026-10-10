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

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Set
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.evaluator.context import EvaluationContext
from app.engine.evaluator.evaluator import DeterministicEvaluator
from app.engine.explainability.audit import create_audit_evaluation_record
from app.engine.explainability.provenance import PolicyProvenance
from app.engine.explainability.trace_builder import build_explainability_trace
from app.engine.types import RuleTruthValue
from app.models.citizen import Citizen, Claim, Evidence, VerificationRecord
from app.models.enums import (
    ClaimStatus,
    EligibilityResult,
    EvidenceStatus,
    HumanReviewStatus,
    JourneyState,
    VerificationStatus,
)
from app.models.evaluation import EvaluationTrace
from app.models.human_review import HumanReview, HumanReviewAuditEvent
from app.models.journey import EvaluationJourney, JourneyTransitionRecord
from app.models.scheme import PolicyVersion, RuleSet, Scheme
from app.schemas.api import (
    AccountFacts,
    ApplicantFacts,
    BeneficiaryFacts,
    BlockerResponse,
    EvaluationFacts,
    EvaluationRequest,
    EvaluationResponse,
    ExclusionFacts,
    FamilyFacts,
    GuardianFacts,
    HouseholdFacts,
    HousingFacts,
    LandFacts,
    LocationFacts,
    MaternityFacts,
    PersistedEvaluationResponse,
    TradeFacts,
    VendorFacts,
)
from app.schemas.citizen_application import CitizenDecisionResponse
from app.schemas.officer import (
    OfficerAssessmentResponse,
    OfficerAssessmentRuleResponse,
)
from app.services.policy_loader import SchemeNotFoundError
from app.services.policy_selector import (
    PolicyVersionNotFoundError,
    get_policy_rule_ast,
    select_policy_version,
)
from app.services.verification_service import (
    compute_verification_status,
    get_or_create_human_review,
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

    def _extract_facts_from_claims(self, claims: List[Claim]) -> Dict[str, Any]:
        """Extract and categorize verified facts from journey claims into hierarchical sections.

        Strict Verified Fact Provenance Invariant (Phase F):
        Only claims with status == ClaimStatus.VERIFIED may enter the evaluation fact snapshot.
        Unverified declarations (CLAIMED, PENDING, REJECTED, UNKNOWN) MUST NOT become evaluation facts.
        """
        field_to_section: Dict[str, str] = {}
        for sec, flds in VALID_FACT_FIELDS.items():
            for f in flds:
                field_to_section[f] = sec

        facts: Dict[str, Any] = {}

        for claim in claims:
            # Enforce strict verified fact provenance: unverified claims are never evaluation facts
            if claim.status != ClaimStatus.VERIFIED:
                continue

            # 1. Dot notation e.g. "family.owns_cultivable_land"
            if "." in claim.claim_type:
                parts = claim.claim_type.split(".", 1)
                section, field = parts[0], parts[1]
                if section in VALID_FACT_FIELDS and field in VALID_FACT_FIELDS[section]:
                    facts.setdefault(section, {})
                    val = claim.value_json
                    if isinstance(val, dict) and "value" in val and len(val) == 1:
                        val = val["value"]
                    facts[section][field] = val

            # 2. Section name directly e.g. "family"
            elif claim.claim_type in VALID_FACT_FIELDS:
                section = claim.claim_type
                if isinstance(claim.value_json, dict):
                    facts.setdefault(section, {})
                    for k, v in claim.value_json.items():
                        if k in VALID_FACT_FIELDS[section]:
                            facts[section][k] = v

            # 3. Flat field directly e.g. "owns_cultivable_land"
            elif claim.claim_type in field_to_section:
                section = field_to_section[claim.claim_type]
                facts.setdefault(section, {})
                val = claim.value_json
                if isinstance(val, dict) and "value" in val and len(val) == 1:
                    val = val["value"]
                facts[section][claim.claim_type] = val

        return facts


    def _build_trace_json(
        self,
        eval_result,
        explainability_trace,
        pv: PolicyVersion,
    ) -> Dict[str, Any]:
        rules_evaluated: List[Dict[str, Any]] = []
        passed_conditions: List[str] = []
        failed_conditions: List[str] = []

        for node in explainability_trace.ordered_nodes:
            if node.truth_value == RuleTruthValue.TRUE:
                res_str = "PASS"
                if node.explanation_en:
                    passed_conditions.append(f"{node.rule_id or 'Criterion'}: {node.explanation_en}")
            elif node.truth_value == RuleTruthValue.FALSE:
                res_str = "FAIL"
                if node.explanation_en:
                    failed_conditions.append(f"{node.rule_id or 'Criterion'}: {node.explanation_en}")
            else:
                res_str = "UNKNOWN"

            op_str = (
                node.operator.value
                if hasattr(node.operator, "value")
                else (str(node.operator) if node.operator else None)
            )
            rules_evaluated.append({
                "rule_id": node.rule_id or node.node_id,
                "rule_name": node.rule_id or "Statutory Criterion",
                "description": node.explanation_en or "",
                "result": res_str,
                "details": node.explanation_en,
                "operator": op_str,
                "expected_value": str(node.expected_value) if node.expected_value is not None else None,
                "actual_value": str(node.actual_value) if node.actual_value is not None else None,
            })

        reasons_en, reasons_hi = self._extract_reasons(explainability_trace)

        missing_facts = list(eval_result.all_missing_fields)
        disqualifiers = [
            node.explanation_en
            for node in explainability_trace.ordered_nodes
            if node.truth_value == RuleTruthValue.FALSE and node.explanation_en
        ]
        blockers = [
            {
                "code": b.code,
                "category": b.category.value if hasattr(b.category, "value") else str(b.category),
                "field_path": b.field_path,
                "rule_id": b.rule_id,
                "message_en": b.message_en,
                "message_hi": b.message_hi,
            }
            for b in explainability_trace.blockers
        ]

        return {
            "outcome": eval_result.overall_result.value,
            "policy_version_code": pv.version_code,
            "rule_definition_hash": pv.rule_definition_hash,
            "rules_evaluated": rules_evaluated,
            "missing_facts": missing_facts,
            "disqualifiers": disqualifiers,
            "reasons_en": list(dict.fromkeys(reasons_en)),
            "reasons_hi": list(dict.fromkeys(reasons_hi)),
            "passed_conditions": list(dict.fromkeys(passed_conditions)),
            "failed_conditions": list(dict.fromkeys(failed_conditions)),
            "unverified_requirements": [],
            "blockers": blockers,
        }

    def _trace_to_assessment_response(self, trace: EvaluationTrace) -> OfficerAssessmentResponse:
        trace_json = trace.trace_json or {}
        rules_evaluated: List[OfficerAssessmentRuleResponse] = []
        for r in trace_json.get("rules_evaluated", []):
            rules_evaluated.append(
                OfficerAssessmentRuleResponse(
                    rule_id=r.get("rule_id", "UNKNOWN"),
                    rule_name=r.get("rule_name", r.get("rule_id", "Statutory Rule")),
                    description=r.get("description", ""),
                    result=r.get("result", "UNKNOWN"),
                    details=r.get("details") or r.get("reason"),
                    operator=r.get("operator"),
                    expected_value=str(r.get("expected_value")) if r.get("expected_value") is not None else None,
                    actual_value=str(r.get("actual_value")) if r.get("actual_value") is not None else None,
                )
            )

        raw_missing = trace_json.get("missing_facts", [])
        missing_facts = [
            item.get("fact_key", item.get("name", str(item))) if isinstance(item, dict) else str(item)
            for item in raw_missing
        ]

        raw_disqualifiers = trace_json.get("disqualifiers", trace_json.get("blockers", []))
        disqualifiers = [
            item.get("message", item.get("description", item.get("code", str(item))))
            if isinstance(item, dict) else str(item)
            for item in raw_disqualifiers
        ]

        pv_code = "1.0"
        if trace.policy_version:
            pv_code = trace.policy_version.version_code
        elif "policy_version_code" in trace_json:
            pv_code = trace_json["policy_version_code"]

        return OfficerAssessmentResponse(
            evaluation_id=trace.id,
            determination=trace.result_state.value,
            evaluated_at=trace.created_at,
            ruleset_version=pv_code,
            ruleset_hash=trace.rule_definition_hash,
            rules_evaluated=rules_evaluated,
            missing_facts=missing_facts,
            disqualifiers=disqualifiers,
            reasons_en=trace_json.get("reasons_en", []),
            reasons_hi=trace_json.get("reasons_hi", []),
        )

    async def evaluate_case(
        self,
        journey_id: uuid.UUID,
        actor_identity: str,
        actor_role: str,
        notes: Optional[str] = None,
    ) -> OfficerAssessmentResponse:
        """Execute deterministic eligibility evaluation for a case.

        Server-side gate enforcement:
        - If mandatory requirements are missing: returns INSUFFICIENT_INFORMATION.
        - If verification is pending/unverified/rejected: returns VERIFICATION_REQUIRED.
        - When all mandatory requirements and evidence are verified: runs DeterministicEvaluator
          against the application's bound policy_version_id and returns ELIGIBLE / INELIGIBLE.
        """
        # 0. Serialize concurrent evaluation attempts with exclusive row lock
        await self.session.execute(
            select(EvaluationJourney.id).where(EvaluationJourney.id == journey_id).with_for_update()
        )

        # 1. Fetch journey with bound policy version and relations
        stmt = (
            select(EvaluationJourney)
            .options(
                selectinload(EvaluationJourney.scheme),
                selectinload(EvaluationJourney.citizen),
                selectinload(EvaluationJourney.policy_version).selectinload(PolicyVersion.rule_set),
                selectinload(EvaluationJourney.claims).selectinload(Claim.evidence_items).selectinload(Evidence.verification_records),
                selectinload(EvaluationJourney.clarification_requests),
                selectinload(EvaluationJourney.evaluation_traces),
                selectinload(EvaluationJourney.latest_evaluation),
            )
            .where(EvaluationJourney.id == journey_id)
        )
        res = await self.session.execute(stmt)
        journey = res.scalars().first()
        if not journey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification case with ID '{journey_id}' was not found",
            )

        # Statutory Immutability: Verify case has bound statutory policy version and structured ruleset
        if not journey.policy_version_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case has no bound statutory policy version.",
            )
        if not journey.policy_version or not journey.policy_version.rule_set:
            pv_stmt = (
                select(PolicyVersion)
                .options(selectinload(PolicyVersion.rule_set))
                .where(PolicyVersion.id == journey.policy_version_id)
            )
            journey.policy_version = (await self.session.execute(pv_stmt)).scalar_one_or_none()

        pv = journey.policy_version
        if not pv or not pv.rule_set or not pv.rule_set.definition_json:
            scheme_code = journey.scheme.scheme_code if journey.scheme else "UNKNOWN"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scheme '{scheme_code}' does not have a structured deterministic ruleset.",
            )

        review = await get_or_create_human_review(self.session, journey.id, actor_identity)
        now = datetime.now(timezone.utc)
        eval_date = journey.submitted_at.date() if journey.submitted_at else date.today()

        # 2. Check Idempotency / Double-click protection (Section 27)
        if journey.latest_evaluation and journey.latest_evaluation.evaluated_by == actor_identity:
            age_seconds = (now - journey.latest_evaluation.created_at).total_seconds()
            if age_seconds < 2.0:
                return self._trace_to_assessment_response(journey.latest_evaluation)

        # 3. Server-side verification gate (Section 8)
        v_status = await compute_verification_status(self.session, journey_id)
        missing_mandatory = v_status.get("missing_mandatory_requirements", [])

        # GATE CASE 1: Missing mandatory evidence / information -> INSUFFICIENT_INFORMATION
        if len(missing_mandatory) > 0:
            outcome = EligibilityResult.INSUFFICIENT_INFORMATION
            reasons_en = [f"Missing mandatory statutory requirement: {req}" for req in missing_mandatory]
            reasons_hi = [f"अनिवार्य वैधानिक आवश्यकता अनुपलब्ध है: {req}" for req in missing_mandatory]
            blockers = [{"code": req, "message": f"Missing mandatory document: {req}"} for req in missing_mandatory]

            trace_json = {
                "outcome": outcome.value,
                "policy_version_code": journey.policy_version.version_code if journey.policy_version else None,
                "rules_evaluated": [],
                "missing_facts": missing_mandatory,
                "disqualifiers": [],
                "reasons_en": reasons_en,
                "reasons_hi": reasons_hi,
                "passed_conditions": [],
                "failed_conditions": [],
                "unverified_requirements": [],
                "blockers": blockers,
            }

            trace = EvaluationTrace(
                id=uuid.uuid4(),
                citizen_id=journey.citizen_id,
                scheme_id=journey.scheme_id,
                policy_version_id=journey.policy_version_id,
                journey_id=journey.id,
                evaluated_by=actor_identity,
                evaluation_date=eval_date,
                input_snapshot_json={"missing_mandatory_requirements": missing_mandatory},
                result_state=outcome,
                trace_json=trace_json,
                rule_definition_hash=journey.policy_version.rule_definition_hash if journey.policy_version else None,
                created_at=now,
            )
            self.session.add(trace)
            journey.latest_evaluation_id = trace.id
            journey.updated_at = now

            prev_state = journey.state
            journey.state = JourneyState.ACTION_REQUIRED
            t_record = JourneyTransitionRecord(
                journey_id=journey.id,
                from_state=prev_state,
                to_state=JourneyState.ACTION_REQUIRED,
                actor=actor_identity,
                reason=f"Evaluation halted: mandatory evidence missing ({', '.join(missing_mandatory)})",
            )
            self.session.add(t_record)

            review.evaluation_id = trace.id
            audit_event = HumanReviewAuditEvent(
                review_id=review.id,
                journey_id=journey.id,
                actor_identity=actor_identity,
                actor_role=actor_role,
                action="EVALUATION_COMPLETED",
                previous_status=review.status.value,
                new_status=review.status.value,
                reason="Evaluation executed: INSUFFICIENT_INFORMATION",
                details_json={
                    "evaluation_id": str(trace.id),
                    "outcome": outcome.value,
                    "missing_mandatory": missing_mandatory,
                    "notes": notes,
                },
            )
            self.session.add(audit_event)
            await self.session.commit()
            return self._trace_to_assessment_response(trace)

        # GATE CASE 2: Verification Incomplete / Blocked -> VERIFICATION_REQUIRED
        if not v_status.get("is_ready_for_evaluation"):
            outcome = EligibilityResult.VERIFICATION_REQUIRED
            unverified: List[str] = []
            if v_status.get("pending_mandatory_requirements"):
                unverified.extend([f"{r} (PENDING)" for r in v_status["pending_mandatory_requirements"]])
            if v_status.get("rejected_mandatory_requirements"):
                unverified.extend([f"{r} (REJECTED)" for r in v_status["rejected_mandatory_requirements"]])
            if v_status.get("clarification_mandatory_requirements"):
                unverified.extend([f"{r} (CLARIFICATION_REQUIRED)" for r in v_status["clarification_mandatory_requirements"]])

            if not unverified:
                if v_status.get("open_clarification_count", 0) > 0:
                    unverified.append("Open clarification request awaiting response/resolution")
                if v_status.get("pending_evidence_count", 0) > 0:
                    unverified.append(f"{v_status['pending_evidence_count']} evidence item(s) pending officer verification")
                if v_status.get("rejected_evidence_count", 0) > 0:
                    unverified.append(f"{v_status['rejected_evidence_count']} evidence item(s) rejected")
                if v_status.get("clarification_required_count", 0) > 0:
                    unverified.append(f"{v_status['clarification_required_count']} evidence item(s) requiring clarification")

            reasons_en = [f"Statutory evidence verification incomplete: {item}" for item in unverified]
            reasons_hi = [f"वैधानिक साक्ष्य सत्यापन अपूर्ण है: {item}" for item in unverified]
            blockers = [{"code": "VERIFICATION_PENDING", "message": f"Verification incomplete: {item}"} for item in unverified]

            trace_json = {
                "outcome": outcome.value,
                "policy_version_code": journey.policy_version.version_code if journey.policy_version else None,
                "rules_evaluated": [],
                "missing_facts": [],
                "disqualifiers": [],
                "reasons_en": reasons_en,
                "reasons_hi": reasons_hi,
                "passed_conditions": [],
                "failed_conditions": [],
                "unverified_requirements": unverified,
                "blockers": blockers,
            }

            trace = EvaluationTrace(
                id=uuid.uuid4(),
                citizen_id=journey.citizen_id,
                scheme_id=journey.scheme_id,
                policy_version_id=journey.policy_version_id,
                journey_id=journey.id,
                evaluated_by=actor_identity,
                evaluation_date=eval_date,
                input_snapshot_json={"unverified_requirements": unverified},
                result_state=outcome,
                trace_json=trace_json,
                rule_definition_hash=journey.policy_version.rule_definition_hash if journey.policy_version else None,
                created_at=now,
            )
            self.session.add(trace)
            journey.latest_evaluation_id = trace.id
            journey.updated_at = now

            prev_state = journey.state
            journey.state = JourneyState.ACTION_REQUIRED
            t_record = JourneyTransitionRecord(
                journey_id=journey.id,
                from_state=prev_state,
                to_state=JourneyState.ACTION_REQUIRED,
                actor=actor_identity,
                reason="Evaluation halted: verification required",
            )
            self.session.add(t_record)

            review.evaluation_id = trace.id
            audit_event = HumanReviewAuditEvent(
                review_id=review.id,
                journey_id=journey.id,
                actor_identity=actor_identity,
                actor_role=actor_role,
                action="EVALUATION_COMPLETED",
                previous_status=review.status.value,
                new_status=review.status.value,
                reason="Evaluation executed: VERIFICATION_REQUIRED",
                details_json={
                    "evaluation_id": str(trace.id),
                    "outcome": outcome.value,
                    "unverified_requirements": unverified,
                    "notes": notes,
                },
            )
            self.session.add(audit_event)
            await self.session.commit()
            return self._trace_to_assessment_response(trace)

        # GATE CASE 3: Verification Complete -> Execute Deterministic Rule Engine
        # 1. Extract AST Node
        ast_node = get_policy_rule_ast(pv)

        # 2. Extract Verified Facts from Claims
        facts_raw = self._extract_facts_from_claims(journey.claims)
        evaluation_facts = EvaluationFacts(**facts_raw)
        facts_dict = evaluation_facts.to_engine_dict()

        # 3. Context & Stateless Evaluation
        ctx = EvaluationContext(
            data=facts_dict,
            evaluation_date=eval_date,
            policy_metadata=dict(pv.rule_set.definition_json.get("metadata", {}))
            if pv.rule_set and isinstance(pv.rule_set.definition_json, dict)
            else {},
        )
        eval_result = self.evaluator.evaluate(ast_node, ctx)

        # 4. Build Provenance & Explainability Trace
        eval_id = uuid.uuid4()
        provenance = PolicyProvenance(
            scheme_id=journey.scheme.id,
            scheme_code=journey.scheme.scheme_code,
            policy_version_id=pv.id,
            policy_version_code=pv.version_code,
            rule_set_id=pv.rule_set.id if pv.rule_set else None,
            rule_set_version=pv.rule_set.rule_set_version if pv.rule_set else "1.0",
            canonical_rule_hash=pv.rule_definition_hash or "",
            evaluation_date=eval_date,
            effective_from=pv.effective_from,
            effective_to=pv.effective_to,
            source_url=pv.source_url,
            source_title=pv.source_title,
            source_clause=None,
        )
        explainability_trace = build_explainability_trace(
            eval_result=eval_result,
            provenance=provenance,
            evaluation_id=eval_id,
        )

        # 5. Build Trace JSON
        trace_json = self._build_trace_json(eval_result, explainability_trace, pv)

        # 6. Persist EvaluationTrace
        trace = EvaluationTrace(
            id=eval_id,
            citizen_id=journey.citizen_id,
            scheme_id=journey.scheme_id,
            policy_version_id=pv.id,
            journey_id=journey.id,
            evaluated_by=actor_identity,
            evaluation_date=eval_date,
            input_snapshot_json=evaluation_facts.model_dump(mode="json", exclude_unset=True),
            result_state=eval_result.overall_result,
            trace_json=trace_json,
            rule_definition_hash=pv.rule_definition_hash,
            created_at=now,
        )
        self.session.add(trace)
        journey.latest_evaluation_id = trace.id
        journey.updated_at = now

        # 8. Journey Transition
        prev_state = journey.state
        new_journey_state = (
            JourneyState.EVALUATED
            if eval_result.overall_result == EligibilityResult.ELIGIBLE
            else JourneyState.ACTION_REQUIRED
        )
        journey.state = new_journey_state
        t_record = JourneyTransitionRecord(
            journey_id=journey.id,
            from_state=prev_state,
            to_state=new_journey_state,
            actor=actor_identity,
            reason=f"Deterministic statutory evaluation executed: outcome={eval_result.overall_result.value}",
        )
        self.session.add(t_record)

        # 9. Audit Event
        review.evaluation_id = trace.id
        audit_event = HumanReviewAuditEvent(
            review_id=review.id,
            journey_id=journey.id,
            actor_identity=actor_identity,
            actor_role=actor_role,
            action="EVALUATION_COMPLETED",
            previous_status=review.status.value,
            new_status=review.status.value,
            reason=f"Evaluation executed: {eval_result.overall_result.value}",
            details_json={
                "evaluation_id": str(trace.id),
                "outcome": eval_result.overall_result.value,
                "policy_version": pv.version_code,
                "notes": notes,
            },
        )
        self.session.add(audit_event)
        await self.session.commit()
        return self._trace_to_assessment_response(trace)

    async def get_case_evaluation(self, journey_id: uuid.UUID) -> OfficerAssessmentResponse:
        """Retrieve the latest statutory evaluation for a case."""
        stmt = (
            select(EvaluationTrace)
            .options(selectinload(EvaluationTrace.policy_version))
            .where(EvaluationTrace.journey_id == journey_id)
            .order_by(EvaluationTrace.created_at.desc())
        )
        res = await self.session.execute(stmt)
        trace = res.scalars().first()
        if not trace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No statutory evaluation has been executed for case '{journey_id}'.",
            )
        return self._trace_to_assessment_response(trace)

    async def get_case_evaluation_history(self, journey_id: uuid.UUID) -> List[OfficerAssessmentResponse]:
        """Retrieve complete historical audit log of statutory evaluations for a case."""
        stmt = (
            select(EvaluationTrace)
            .options(selectinload(EvaluationTrace.policy_version))
            .where(EvaluationTrace.journey_id == journey_id)
            .order_by(EvaluationTrace.created_at.desc())
        )
        res = await self.session.execute(stmt)
        traces = res.scalars().all()
        return [self._trace_to_assessment_response(t) for t in traces]

    async def get_citizen_decision(
        self,
        journey_id: uuid.UUID,
        citizen_id: uuid.UUID,
    ) -> CitizenDecisionResponse:
        """Retrieve the citizen-facing statutory eligibility decision and plain-language explanation."""
        stmt = (
            select(EvaluationJourney)
            .options(
                selectinload(EvaluationJourney.scheme),
                selectinload(EvaluationJourney.policy_version),
                selectinload(EvaluationJourney.latest_evaluation).selectinload(EvaluationTrace.policy_version),
            )
            .where(EvaluationJourney.id == journey_id, EvaluationJourney.citizen_id == citizen_id)
        )
        res = await self.session.execute(stmt)
        journey = res.scalars().first()
        if not journey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or does not belong to your account",
            )

        year = journey.created_at.year if journey.created_at else 2026
        hex_id = str(journey.id).replace("-", "")[:8].upper()
        app_ref = f"APP-{year}-{hex_id}"

        if not journey.latest_evaluation:
            return CitizenDecisionResponse(
                application_id=journey.id,
                application_ref=app_ref,
                scheme_code=journey.scheme.scheme_code if journey.scheme else "UNKNOWN",
                scheme_name_en=journey.scheme.name_en if journey.scheme else "Welfare Scheme",
                scheme_name_hi=journey.scheme.name_hi if journey.scheme else "कल्याणकारी योजना",
                is_evaluated=False,
                outcome="PENDING_EVALUATION",
                policy_version_code=journey.policy_version.version_code if journey.policy_version else None,
                evaluated_at=None,
                reasons_en=["Application is awaiting statutory eligibility evaluation."],
                reasons_hi=["आवेदन वैधानिक पात्रता मूल्यांकन की प्रतीक्षा में है।"],
                passed_conditions=[],
                failed_conditions=[],
                missing_information=[],
                unverified_requirements=[],
            )

        trace = journey.latest_evaluation
        trace_json = trace.trace_json or {}

        pv_code = None
        if trace.policy_version:
            pv_code = trace.policy_version.version_code
        elif journey.policy_version:
            pv_code = journey.policy_version.version_code

        return CitizenDecisionResponse(
            application_id=journey.id,
            application_ref=app_ref,
            scheme_code=journey.scheme.scheme_code if journey.scheme else "UNKNOWN",
            scheme_name_en=journey.scheme.name_en if journey.scheme else "Welfare Scheme",
            scheme_name_hi=journey.scheme.name_hi if journey.scheme else "कल्याणकारी योजना",
            is_evaluated=True,
            outcome=trace.result_state.value,
            policy_version_code=pv_code,
            evaluated_at=trace.created_at,
            reasons_en=trace_json.get("reasons_en", []),
            reasons_hi=trace_json.get("reasons_hi", []),
            passed_conditions=trace_json.get("passed_conditions", []),
            failed_conditions=trace_json.get("failed_conditions", []),
            missing_information=trace_json.get("missing_facts", []),
            unverified_requirements=trace_json.get("unverified_requirements", []),
        )


VALID_FACT_FIELDS: Dict[str, Set[str]] = {
    "family": set(FamilyFacts.model_fields.keys()),
    "land": set(LandFacts.model_fields.keys()),
    "beneficiary": set(BeneficiaryFacts.model_fields.keys()),
    "guardian": set(GuardianFacts.model_fields.keys()),
    "account": set(AccountFacts.model_fields.keys()),
    "applicant": set(ApplicantFacts.model_fields.keys()),
    "household": set(HouseholdFacts.model_fields.keys()),
    "trade": set(TradeFacts.model_fields.keys()),
    "housing": set(HousingFacts.model_fields.keys()),
    "location": set(LocationFacts.model_fields.keys()),
    "vendor": set(VendorFacts.model_fields.keys()),
    "maternity": set(MaternityFacts.model_fields.keys()),
    "exclusions": set(ExclusionFacts.model_fields.keys()),
}
