"""Generic, structured information gap and blocker representation."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


from app.engine.explainability.constants import BLOCKER_SCHEMA_VERSION


class BlockerCategory(str, Enum):
    """Categorization for why an entitlement condition is unresolved or blocked."""
    MISSING_FIELD = "MISSING_FIELD"
    UNRESOLVED_EVIDENCE = "UNRESOLVED_EVIDENCE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class InformationGapBlocker(BaseModel):
    """Structured, machine-readable record of an information gap preventing eligibility."""

    blocker_schema_version: str = Field(
        default=BLOCKER_SCHEMA_VERSION, description="Schema version of blocker model"
    )
    code: str = Field(..., min_length=1, description="Stable identifier code e.g. BLOCKER_MISSING_CITIZEN_INCOME")
    category: BlockerCategory = Field(..., description="Category of blocker")
    field_path: Optional[str] = Field(None, description="Context field path that is missing or unverified")
    rule_id: Optional[str] = Field(None, description="Rule ID where information is required")
    message_en: str = Field(..., description="English plain-text explanation of the required gap")
    message_hi: str = Field(..., description="Hindi plain-text explanation of the required gap")
    evidence_reference: Optional[str] = Field(None, description="Optional link to related evidence record")
    verification_reference: Optional[str] = Field(None, description="Optional link to verification record")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary blocker metadata")

    model_config = ConfigDict(extra="ignore", frozen=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize blocker to Python dictionary."""
        return self.model_dump(mode="python")
