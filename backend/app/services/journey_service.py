"""Citizen Evaluation Journey & Evidence Workflow Service.

Orchestrates the stateful lifecycle of a citizen's welfare entitlement journey:
1. Journey Creation & Lifecycle State Transitions (DRAFT -> FACTS_COLLECTED -> ... -> COMPLETED)
2. Claim Registration & Association to Journeys
3. Evidence Submission & Multi-Source Verification
4. Strict Separation of Concerns: Evidence verification status NEVER mutates factual claims.
5. Integration with Stateless Deterministic Evaluator & Audit Persistence.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.citizen import Citizen, Claim, Evidence, VerificationRecord
from app.models.enums import (
    ClaimStatus,
    EligibilityResult,
    EvidenceStatus,
    JourneyState,
    VerificationStatus,
)
from app.models.journey import EvaluationJourney, JourneyTransitionRecord
from app.models.scheme import Scheme
from app.schemas.api import (
    AccountFacts,
    BeneficiaryFacts,
    EvaluationFacts,
    EvaluationRequest,
    EvaluationResponse,
    FamilyFacts,
    GuardianFacts,
    LandFacts,
)
from app.schemas.journey import (
    EvidenceVerificationRequest,
    JourneyClaimCreateRequest,
    JourneyCreateRequest,
    JourneyEvaluateRequest,
    JourneyEvaluationResponse,
    JourneyEvidenceCreateRequest,
    JourneyTransitionRequest,
)
from app.services.evaluation_service import EvaluationService
from app.services.policy_loader import SchemeNotFoundError

logger = logging.getLogger("yogyatamitra.services.journey_service")


# ==============================================================================
# Domain Exceptions
# ==============================================================================

class JourneyError(Exception):
    """Base exception for journey workflow failures."""
    pass


class JourneyNotFoundError(JourneyError):
    """Raised when a requested evaluation journey ID does not exist."""
    pass


class InvalidJourneyTransitionError(JourneyError):
    """Raised when an illegal lifecycle state transition is requested."""
    pass


class ClaimNotFoundError(JourneyError):
    """Raised when a requested claim ID is not found or does not belong to the journey."""
    pass


class EvidenceNotFoundError(JourneyError):
    """Raised when a requested evidence ID is not found or does not belong to the journey."""
    pass


class InvalidEvidenceTransitionError(JourneyError):
    """Raised when an invalid evidence status or transition is attempted."""
    pass


# ==============================================================================
# State Transition Matrix
# ==============================================================================

ALLOWED_JOURNEY_TRANSITIONS: Dict[JourneyState, Set[JourneyState]] = {
    JourneyState.DRAFT: {
        JourneyState.FACTS_COLLECTED,
    },
    JourneyState.FACTS_COLLECTED: {
        JourneyState.EVIDENCE_PENDING,
        JourneyState.READY_FOR_EVALUATION,
    },
    JourneyState.EVIDENCE_PENDING: {
        JourneyState.VERIFICATION_IN_PROGRESS,
        JourneyState.READY_FOR_EVALUATION,
    },
    JourneyState.VERIFICATION_IN_PROGRESS: {
        JourneyState.READY_FOR_EVALUATION,
        JourneyState.EVIDENCE_PENDING,
    },
    JourneyState.READY_FOR_EVALUATION: {
        JourneyState.EVALUATED,
    },
    JourneyState.EVALUATED: {
        JourneyState.ACTION_REQUIRED,
        JourneyState.COMPLETED,
        JourneyState.READY_FOR_EVALUATION,  # For re-evaluation
    },
    JourneyState.ACTION_REQUIRED: {
        JourneyState.EVIDENCE_PENDING,
        JourneyState.FACTS_COLLECTED,
        JourneyState.READY_FOR_EVALUATION,
    },
    JourneyState.COMPLETED: set(),  # Terminal state
}


# ==============================================================================
# Fact Assembly Utilities
# ==============================================================================

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively deep-merge two nested dictionaries."""
    merged = dict(base)
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


VALID_FACT_FIELDS: Dict[str, Set[str]] = {
    "family": set(FamilyFacts.model_fields.keys()),
    "land": set(LandFacts.model_fields.keys()),
    "beneficiary": set(BeneficiaryFacts.model_fields.keys()),
    "guardian": set(GuardianFacts.model_fields.keys()),
    "account": set(AccountFacts.model_fields.keys()),
}


def claims_to_facts_dict(claims: List[Claim]) -> Dict[str, Any]:
    """Reconstruct a hierarchical facts payload from a list of citizen claims.
    
    Filters out operational claims (e.g. document proofs, status markers)
    that do not correspond to statutory facts schema.
    """
    facts: Dict[str, Any] = {}
    for claim in claims:
        if "." in claim.claim_type:
            parts = claim.claim_type.split(".", 1)
            section, field = parts[0], parts[1]
            if section in VALID_FACT_FIELDS and field in VALID_FACT_FIELDS[section]:
                if section not in facts:
                    facts[section] = {}
                val = claim.value_json
                if isinstance(val, dict) and "value" in val and len(val) == 1:
                    val = val["value"]
                facts[section][field] = val
        else:
            section = claim.claim_type
            if section in VALID_FACT_FIELDS:
                if isinstance(claim.value_json, dict):
                    if section not in facts:
                        facts[section] = {}
                    filtered_data = {
                        k: v for k, v in claim.value_json.items()
                        if k in VALID_FACT_FIELDS[section]
                    }
                    facts[section].update(filtered_data)
    return facts


# ==============================================================================
# Service Implementation
# ==============================================================================

class JourneyService:
    """Service managing the lifecycle, claims, evidence, and evaluation of citizen journeys."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _resolve_or_create_citizen(self, citizen_ref: str) -> Citizen:
        """Resolve an existing Citizen by synthetic_reference or create a minimal record."""
        stmt = select(Citizen).where(Citizen.synthetic_reference == citizen_ref)
        result = await self.session.execute(stmt)
        citizen = result.scalar_one_or_none()
        if citizen is None:
            citizen = Citizen(
                id=uuid.uuid4(),
                synthetic_reference=citizen_ref,
                display_name=None,
                date_of_birth=None,
                gender=None,
                state=None,
                district=None,
            )
            self.session.add(citizen)
            await self.session.flush()
        return citizen

    async def _get_journey_entity(
        self,
        journey_id: uuid.UUID,
        load_relations: bool = False,
    ) -> EvaluationJourney:
        """Retrieve an EvaluationJourney by UUID with optional deep relationship loading."""
        stmt = select(EvaluationJourney).where(EvaluationJourney.id == journey_id)
        if load_relations:
            stmt = stmt.options(
                selectinload(EvaluationJourney.citizen),
                selectinload(EvaluationJourney.scheme),
                selectinload(EvaluationJourney.claims)
                .selectinload(Claim.evidence_items)
                .selectinload(Evidence.verification_records),
                selectinload(EvaluationJourney.transitions),
            )
        result = await self.session.execute(stmt)
        journey = result.scalar_one_or_none()
        if journey is None:
            raise JourneyNotFoundError(f"Evaluation journey with ID '{journey_id}' not found.")
        return journey

    async def create_journey(self, request: JourneyCreateRequest) -> EvaluationJourney:
        """Create a new citizen evaluation journey."""
        # 1. Resolve Scheme
        scheme_stmt = select(Scheme).where(Scheme.scheme_code == request.scheme_code)
        scheme_result = await self.session.execute(scheme_stmt)
        scheme = scheme_result.scalar_one_or_none()
        if scheme is None:
            raise SchemeNotFoundError(f"Scheme with code '{request.scheme_code}' not found.")

        # 2. Resolve or create minimal synthetic Citizen
        citizen = await self._resolve_or_create_citizen(request.citizen_ref)

        # 3. Create Journey
        journey = EvaluationJourney(
            id=uuid.uuid4(),
            citizen_id=citizen.id,
            scheme_id=scheme.id,
            state=JourneyState.DRAFT,
            latest_evaluation_id=None,
        )
        self.session.add(journey)
        await self.session.flush()

        # 4. Handle initial facts if provided
        if request.initial_facts:
            # Create claims from initial facts
            for section_key, section_val in request.initial_facts.items():
                if isinstance(section_val, dict):
                    claim = Claim(
                        id=uuid.uuid4(),
                        citizen_id=citizen.id,
                        journey_id=journey.id,
                        claim_type=section_key,
                        value_json=section_val,
                        source="INITIAL_FACTS",
                        status=ClaimStatus.CLAIMED,
                    )
                    self.session.add(claim)
                else:
                    claim = Claim(
                        id=uuid.uuid4(),
                        citizen_id=citizen.id,
                        journey_id=journey.id,
                        claim_type=section_key,
                        value_json={"value": section_val},
                        source="INITIAL_FACTS",
                        status=ClaimStatus.CLAIMED,
                    )
                    self.session.add(claim)

            # Record transition DRAFT -> FACTS_COLLECTED
            transition = JourneyTransitionRecord(
                id=uuid.uuid4(),
                journey_id=journey.id,
                from_state=JourneyState.DRAFT,
                to_state=JourneyState.FACTS_COLLECTED,
                actor="SYSTEM",
                reason="Initial facts provided at journey creation",
            )
            self.session.add(transition)
            journey.state = JourneyState.FACTS_COLLECTED

        await self.session.commit()
        return await self._get_journey_entity(journey.id, load_relations=True)

    async def get_journey(self, journey_id: uuid.UUID) -> EvaluationJourney:
        """Retrieve an evaluation journey with all claims and transition history."""
        return await self._get_journey_entity(journey_id, load_relations=True)

    async def transition_journey(
        self,
        journey_id: uuid.UUID,
        request: JourneyTransitionRequest,
    ) -> EvaluationJourney:
        """Advance or move the lifecycle state of a journey adhering to allowed transitions."""
        journey = await self._get_journey_entity(journey_id, load_relations=True)

        current_state = journey.state
        target_state = request.target_state

        allowed = ALLOWED_JOURNEY_TRANSITIONS.get(current_state, set())
        if target_state not in allowed:
            raise InvalidJourneyTransitionError(
                f"Illegal state transition from '{current_state.value}' to '{target_state.value}'. "
                f"Allowed target states: {[s.value for s in allowed]}"
            )

        # Record transition
        transition = JourneyTransitionRecord(
            id=uuid.uuid4(),
            journey_id=journey.id,
            from_state=current_state,
            to_state=target_state,
            actor=request.actor,
            reason=request.reason,
        )
        self.session.add(transition)
        journey.state = target_state

        await self.session.commit()
        return await self._get_journey_entity(journey.id, load_relations=True)

    async def get_journey_history(
        self,
        journey_id: uuid.UUID,
    ) -> List[JourneyTransitionRecord]:
        """Retrieve the ordered chronological transition audit log for a journey."""
        # Verify journey exists
        await self._get_journey_entity(journey_id, load_relations=False)

        stmt = (
            select(JourneyTransitionRecord)
            .where(JourneyTransitionRecord.journey_id == journey_id)
            .order_by(JourneyTransitionRecord.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_claim(
        self,
        journey_id: uuid.UUID,
        request: JourneyClaimCreateRequest,
    ) -> Claim:
        """Register an asserted factual claim under an active journey."""
        journey = await self._get_journey_entity(journey_id, load_relations=True)

        if journey.state == JourneyState.COMPLETED:
            raise InvalidJourneyTransitionError("Cannot add claims to a COMPLETED journey.")

        claim = Claim(
            id=uuid.uuid4(),
            citizen_id=journey.citizen_id,
            journey_id=journey.id,
            claim_type=request.claim_type,
            value_json=request.value_json,
            source=request.source,
            status=ClaimStatus.CLAIMED,
        )
        self.session.add(claim)

        # If currently in DRAFT, advance to FACTS_COLLECTED
        if journey.state == JourneyState.DRAFT:
            transition = JourneyTransitionRecord(
                id=uuid.uuid4(),
                journey_id=journey.id,
                from_state=JourneyState.DRAFT,
                to_state=JourneyState.FACTS_COLLECTED,
                actor="SYSTEM",
                reason="First claim registered in journey",
            )
            self.session.add(transition)
            journey.state = JourneyState.FACTS_COLLECTED

        await self.session.commit()

        # Reload claim with evidence items
        stmt = (
            select(Claim)
            .where(Claim.id == claim.id)
            .options(
                selectinload(Claim.evidence_items)
                .selectinload(Evidence.verification_records)
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one()

    async def get_claims(self, journey_id: uuid.UUID) -> List[Claim]:
        """List all claims attached to a journey with nested evidence and verifications."""
        await self._get_journey_entity(journey_id, load_relations=False)
        stmt = (
            select(Claim)
            .where(Claim.journey_id == journey_id)
            .options(
                selectinload(Claim.evidence_items)
                .selectinload(Evidence.verification_records)
            )
            .order_by(Claim.claimed_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_evidence(
        self,
        journey_id: uuid.UUID,
        claim_id: uuid.UUID,
        request: JourneyEvidenceCreateRequest,
    ) -> Evidence:
        """Submit evidence supporting an existing claim under a journey."""
        journey = await self._get_journey_entity(journey_id, load_relations=False)

        if journey.state == JourneyState.COMPLETED:
            raise InvalidJourneyTransitionError("Cannot submit evidence for a COMPLETED journey.")

        claim_stmt = select(Claim).where(
            Claim.id == claim_id,
            Claim.journey_id == journey_id,
        )
        claim_res = await self.session.execute(claim_stmt)
        claim = claim_res.scalar_one_or_none()
        if claim is None:
            raise ClaimNotFoundError(f"Claim with ID '{claim_id}' not found in journey '{journey_id}'.")

        evidence = Evidence(
            id=uuid.uuid4(),
            claim_id=claim.id,
            evidence_type=request.evidence_type,
            storage_reference=request.storage_reference,
            metadata_json=request.metadata_json,
            status=EvidenceStatus.PENDING,
        )
        self.session.add(evidence)

        await self.session.commit()

        stmt = (
            select(Evidence)
            .where(Evidence.id == evidence.id)
            .options(selectinload(Evidence.verification_records))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one()

    async def verify_evidence(
        self,
        journey_id: uuid.UUID,
        evidence_id: uuid.UUID,
        request: EvidenceVerificationRequest,
    ) -> Evidence:
        """Verify or reject an evidence item with full verification audit log.
        
        CRITICAL ARCHITECTURAL INVARIANT:
        Evidence verification status NEVER mutates factual claims or forces eligibility.
        Facts represent citizen claims; evidence represents procedural proof.
        """
        # 1. Fetch evidence ensuring it belongs to a claim in this journey
        stmt = (
            select(Evidence)
            .join(Claim, Evidence.claim_id == Claim.id)
            .where(
                Evidence.id == evidence_id,
                Claim.journey_id == journey_id,
            )
            .options(selectinload(Evidence.verification_records))
        )
        res = await self.session.execute(stmt)
        evidence = res.scalar_one_or_none()
        if evidence is None:
            raise EvidenceNotFoundError(
                f"Evidence with ID '{evidence_id}' not found in journey '{journey_id}'."
            )

        # 2. Validate requested status
        if request.status not in (EvidenceStatus.VERIFIED, EvidenceStatus.REJECTED):
            raise InvalidEvidenceTransitionError(
                f"Target evidence status must be VERIFIED or REJECTED, got '{request.status.value}'."
            )

        if request.status == EvidenceStatus.REJECTED and not request.rejection_reason:
            raise InvalidEvidenceTransitionError(
                "rejection_reason is mandatory when rejecting evidence."
            )

        now = datetime.now(timezone.utc)
        evidence.status = request.status

        if request.status == EvidenceStatus.VERIFIED:
            evidence.verified_at = now
            evidence.rejected_at = None
            evidence.rejection_reason = None
            v_status = VerificationStatus.VERIFIED
        else:
            evidence.rejected_at = now
            evidence.verified_at = None
            evidence.rejection_reason = request.rejection_reason
            v_status = VerificationStatus.REJECTED

        # 3. Create VerificationRecord audit
        record = VerificationRecord(
            id=uuid.uuid4(),
            evidence_id=evidence.id,
            claim_id=evidence.claim_id,
            verification_method=request.verification_method,
            status=v_status,
            verified_by=request.verified_by,
            verified_at=now,
            details_json=request.details_json,
        )
        self.session.add(record)
        if evidence.verification_records is None:
            evidence.verification_records = []
        evidence.verification_records.append(record)

        await self.session.commit()
        await self.session.refresh(evidence, ["verification_records"])
        return evidence

    async def evaluate_journey(
        self,
        journey_id: uuid.UUID,
        request: JourneyEvaluateRequest,
    ) -> JourneyEvaluationResponse:
        """Execute deterministic eligibility evaluation for an active journey."""
        journey = await self._get_journey_entity(journey_id, load_relations=True)

        if journey.state == JourneyState.COMPLETED:
            raise InvalidJourneyTransitionError("Cannot evaluate a COMPLETED journey.")

        # 1. State advance to READY_FOR_EVALUATION if not already evaluated / ready
        current_state = journey.state
        if current_state == JourneyState.DRAFT:
            # DRAFT -> FACTS_COLLECTED -> READY_FOR_EVALUATION
            t1 = JourneyTransitionRecord(
                id=uuid.uuid4(),
                journey_id=journey.id,
                from_state=JourneyState.DRAFT,
                to_state=JourneyState.FACTS_COLLECTED,
                actor="EVALUATION_SERVICE",
                reason="Automatic progression before evaluation",
            )
            t2 = JourneyTransitionRecord(
                id=uuid.uuid4(),
                journey_id=journey.id,
                from_state=JourneyState.FACTS_COLLECTED,
                to_state=JourneyState.READY_FOR_EVALUATION,
                actor="EVALUATION_SERVICE",
                reason="Automatic progression to evaluation",
            )
            self.session.add_all([t1, t2])
            journey.state = JourneyState.READY_FOR_EVALUATION
        elif current_state == JourneyState.FACTS_COLLECTED:
            t = JourneyTransitionRecord(
                id=uuid.uuid4(),
                journey_id=journey.id,
                from_state=JourneyState.FACTS_COLLECTED,
                to_state=JourneyState.READY_FOR_EVALUATION,
                actor="EVALUATION_SERVICE",
                reason="Transitioning to ready for evaluation",
            )
            self.session.add(t)
            journey.state = JourneyState.READY_FOR_EVALUATION
        elif current_state in (JourneyState.EVIDENCE_PENDING, JourneyState.VERIFICATION_IN_PROGRESS):
            t = JourneyTransitionRecord(
                id=uuid.uuid4(),
                journey_id=journey.id,
                from_state=current_state,
                to_state=JourneyState.READY_FOR_EVALUATION,
                actor="EVALUATION_SERVICE",
                reason="Advancing to ready for evaluation",
            )
            self.session.add(t)
            journey.state = JourneyState.READY_FOR_EVALUATION
        elif current_state in (JourneyState.EVALUATED, JourneyState.ACTION_REQUIRED):
            # Allow re-evaluation: transition back to READY_FOR_EVALUATION
            t = JourneyTransitionRecord(
                id=uuid.uuid4(),
                journey_id=journey.id,
                from_state=current_state,
                to_state=JourneyState.READY_FOR_EVALUATION,
                actor="EVALUATION_SERVICE",
                reason="Triggering re-evaluation",
            )
            self.session.add(t)
            journey.state = JourneyState.READY_FOR_EVALUATION

        # Transition READY_FOR_EVALUATION -> EVALUATED
        t_eval = JourneyTransitionRecord(
            id=uuid.uuid4(),
            journey_id=journey.id,
            from_state=JourneyState.READY_FOR_EVALUATION,
            to_state=JourneyState.EVALUATED,
            actor="DETERMINISTIC_ENGINE",
            reason="Statutory rule engine evaluation executed",
        )
        self.session.add(t_eval)
        journey.state = JourneyState.EVALUATED

        # 2. Build hierarchical facts dictionary
        facts_dict = claims_to_facts_dict(journey.claims)
        if request.facts_override:
            facts_dict = deep_merge(facts_dict, request.facts_override)

        evaluation_facts = EvaluationFacts(**facts_dict)
        eval_date = request.evaluation_date or date.today()

        eval_request = EvaluationRequest(
            scheme_code=journey.scheme.scheme_code,
            evaluation_date=eval_date,
            facts=evaluation_facts,
            policy_version_code=request.policy_version_code,
            citizen_ref=journey.citizen.synthetic_reference,
        )

        # 3. Execute stateless deterministic evaluation
        eval_service = EvaluationService(self.session)
        eval_response = await eval_service.evaluate(eval_request)

        # 4. Link persisted evaluation trace to journey
        journey.latest_evaluation_id = eval_response.evaluation_id

        # 5. Count evidence status across journey
        all_evidence: List[Evidence] = []
        for c in journey.claims:
            all_evidence.extend(c.evidence_items)

        pending_evidence_count = sum(1 for e in all_evidence if e.status == EvidenceStatus.PENDING)
        unverified_evidence_count = sum(1 for e in all_evidence if e.status != EvidenceStatus.VERIFIED)

        # 6. Determine action items & post-evaluation state
        action_items: List[str] = []
        disqualifying_factors: List[Dict[str, Any]] = []
        if eval_response.overall_result == EligibilityResult.ELIGIBLE:
            missing_facts: List[str] = []
        else:
            missing_facts: List[str] = list(eval_response.missing_fields)
            for b in eval_response.blockers:
                if b.field_path and b.field_path not in missing_facts:
                    missing_facts.append(b.field_path)

        # Missing facts action items
        for mf in missing_facts:
            action_items.append(f"Provide missing required fact: {mf}")

        # Extract disqualifying factors if ineligible
        if eval_response.overall_result == EligibilityResult.INELIGIBLE:
            trace_nodes = (eval_response.trace or {}).get("ordered_nodes", [])
            for node in trace_nodes:
                if node.get("truth_value") == "FALSE" and node.get("rule_id"):
                    meta = node.get("metadata") or {}
                    field_path = meta.get("field_path")
                    if not field_path and "explanation_en" in node:
                        m = re.search(r"Field '([^']+)'", node["explanation_en"])
                        if m:
                            field_path = m.group(1)

                    disqualifying_factors.append({
                        "code": node["rule_id"],
                        "message_en": node.get("explanation_en") or f"Disqualified under {node['rule_id']}",
                        "message_hi": node.get("explanation_hi") or f"नियम {node['rule_id']} के तहत अपात्र",
                        "field_path": field_path,
                    })
                    action_items.append(
                        f"Disqualifying statutory condition: {node.get('explanation_en') or node['rule_id']}"
                    )

        if pending_evidence_count > 0:
            action_items.append(
                f"{pending_evidence_count} evidence item(s) pending verification."
            )

        # Post-evaluation journey state resolution:
        # If blockers exist or pending evidence exists, move to ACTION_REQUIRED
        if (
            eval_response.overall_result != EligibilityResult.ELIGIBLE
            or pending_evidence_count > 0
        ):
            t_act = JourneyTransitionRecord(
                id=uuid.uuid4(),
                journey_id=journey.id,
                from_state=JourneyState.EVALUATED,
                to_state=JourneyState.ACTION_REQUIRED,
                actor="SYSTEM",
                reason="Evaluation produced blockers or outstanding evidence actions required",
            )
            self.session.add(t_act)
            journey.state = JourneyState.ACTION_REQUIRED
        else:
            action_items.append("All statutory criteria satisfied and verified.")

        await self.session.commit()

        if eval_response.overall_result == EligibilityResult.ELIGIBLE:
            is_eligible_bool = True
        elif eval_response.overall_result == EligibilityResult.INELIGIBLE:
            is_eligible_bool = False
        else:
            is_eligible_bool = None

        return JourneyEvaluationResponse(
            journey_id=journey.id,
            journey_state=journey.state,
            evaluation_id=eval_response.evaluation_id,
            result_state=eval_response.overall_result,
            is_eligible=is_eligible_bool,
            scheme_code=eval_response.scheme_code,
            policy_version_code=eval_response.policy_version_code,
            evaluation_date=eval_response.evaluation_date,
            missing_facts=missing_facts,
            disqualifying_factors=disqualifying_factors,
            pending_evidence_count=pending_evidence_count,
            unverified_evidence_count=unverified_evidence_count,
            action_items=action_items,
        )
