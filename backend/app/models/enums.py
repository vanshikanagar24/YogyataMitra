"""Canonical domain enumerations for YogyataMitra."""

from enum import Enum


class SchemeStatus(str, Enum):
    """Lifecycle status of a government welfare scheme."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class ClaimStatus(str, Enum):
    """Status of an asserted citizen claim."""
    CLAIMED = "CLAIMED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class EvidenceStatus(str, Enum):
    """Lifecycle and verification status of submitted evidence."""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(str, Enum):
    """Outcome status of a verification assessment."""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    UNKNOWN = "UNKNOWN"


class EligibilityResult(str, Enum):
    """Five-state deterministic eligibility decision outcome."""
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class JourneyState(str, Enum):
    """Lifecycle state of a citizen welfare eligibility evaluation journey."""
    DRAFT = "DRAFT"
    FACTS_COLLECTED = "FACTS_COLLECTED"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    VERIFICATION_IN_PROGRESS = "VERIFICATION_IN_PROGRESS"
    READY_FOR_EVALUATION = "READY_FOR_EVALUATION"
    EVALUATED = "EVALUATED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    COMPLETED = "COMPLETED"


class HumanReviewStatus(str, Enum):
    """Lifecycle status of an officer/human verification case review."""
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"


