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
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    UNKNOWN = "UNKNOWN"


class ClarificationStatus(str, Enum):
    """Lifecycle status of an evidence or claim clarification request."""
    OPEN = "OPEN"
    RESPONDED = "RESPONDED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class VerificationCompleteness(str, Enum):
    """Backend-derived operational readiness of case evidence verification."""
    VERIFICATION_IN_PROGRESS = "VERIFICATION_IN_PROGRESS"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    VERIFICATION_COMPLETE = "VERIFICATION_COMPLETE"
    VERIFICATION_BLOCKED = "VERIFICATION_BLOCKED"


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


class AssignmentStatus(str, Enum):
    """Operational lifecycle status of an officer case assignment."""
    UNASSIGNED = "UNASSIGNED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    REASSIGNED = "REASSIGNED"
    COMPLETED = "COMPLETED"


class SLAStatus(str, Enum):
    """Operational SLA compliance status for verification assignments."""
    NOT_DUE = "NOT_DUE"
    DUE_SOON = "DUE_SOON"
    OVERDUE = "OVERDUE"
    COMPLETED = "COMPLETED"


class OfficialSourceType(str, Enum):
    """Controlled classification of official government publishers/sources."""
    MINISTRY = "MINISTRY"
    DEPARTMENT = "DEPARTMENT"
    OFFICIAL_PORTAL = "OFFICIAL_PORTAL"
    GAZETTE = "GAZETTE"
    OFFICIAL_GUIDELINE = "OFFICIAL_GUIDELINE"
    OFFICIAL_NOTIFICATION = "OFFICIAL_NOTIFICATION"
    OTHER_OFFICIAL_SOURCE = "OTHER_OFFICIAL_SOURCE"


class OfficialDocumentType(str, Enum):
    """Controlled classification of official government policy documents."""
    GAZETTE_NOTIFICATION = "GAZETTE_NOTIFICATION"
    SCHEME_GUIDELINE = "SCHEME_GUIDELINE"
    OPERATIONAL_GUIDELINE = "OPERATIONAL_GUIDELINE"
    FRAMEWORK = "FRAMEWORK"
    MINISTRY_CIRCULAR = "MINISTRY_CIRCULAR"
    OFFICIAL_MANUAL = "OFFICIAL_MANUAL"
    OFFICIAL_PORTAL_DOCUMENT = "OFFICIAL_PORTAL_DOCUMENT"
    OTHER_OFFICIAL_DOCUMENT = "OTHER_OFFICIAL_DOCUMENT"


class DocumentVersionStatus(str, Enum):
    """Lifecycle status of a specific official document version."""
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"
    CANDIDATE = "CANDIDATE"


class ProvenanceCompleteness(str, Enum):
    """Auditable state of official source document provenance completeness."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
    UNDER_REVIEW = "UNDER_REVIEW"
    SOURCE_METADATA_VERIFIED = "SOURCE_METADATA_VERIFIED"
    PHYSICAL_ARTIFACT_VERIFIED = "PHYSICAL_ARTIFACT_VERIFIED"


class PolicySourceBindingType(str, Enum):
    """Role and relationship of an official document version to a PolicyVersion."""
    PRIMARY_SOURCE = "PRIMARY_SOURCE"
    SUPPLEMENTARY_SOURCE = "SUPPLEMENTARY_SOURCE"
    AMENDMENT = "AMENDMENT"
    CLARIFICATION = "CLARIFICATION"
    IMPLEMENTATION_GUIDANCE = "IMPLEMENTATION_GUIDANCE"


class ProvenanceEventType(str, Enum):
    """Audit event classifications for official document and provenance lifecycle changes."""
    DOCUMENT_REGISTERED = "DOCUMENT_REGISTERED"
    DOCUMENT_VERSION_ADDED = "DOCUMENT_VERSION_ADDED"
    DOCUMENT_SUPERSEDED = "DOCUMENT_SUPERSEDED"
    POLICY_SOURCE_BOUND = "POLICY_SOURCE_BOUND"
    RULE_PROVENANCE_BOUND = "RULE_PROVENANCE_BOUND"
    PROVENANCE_CORRECTED = "PROVENANCE_CORRECTED"
    DOCUMENT_HASH_VERIFIED = "DOCUMENT_HASH_VERIFIED"
