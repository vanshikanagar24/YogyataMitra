import copy
from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.engine.explainability.blockers import InformationGapBlocker
from app.engine.explainability.constants import AUDIT_SCHEMA_VERSION
from app.engine.explainability.provenance import PolicyProvenance, _canonicalize_object
from app.engine.explainability.trace import ExplainabilityTrace
from app.engine.types import RuleTruthValue
from app.models.enums import EligibilityResult
from app.models.evaluation import EvaluationTrace


class FrozenSnapshotDict(dict):
    """Immutable dictionary subclass that rejects all item modifications and mutator methods."""

    def __setitem__(self, key: Any, value: Any) -> None:
        raise TypeError("Cannot mutate immutable audit snapshot data")

    def __delitem__(self, key: Any) -> None:
        raise TypeError("Cannot mutate immutable audit snapshot data")

    def clear(self) -> None:
        raise TypeError("Cannot mutate immutable audit snapshot data")

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError("Cannot mutate immutable audit snapshot data")

    def popitem(self) -> Any:
        raise TypeError("Cannot mutate immutable audit snapshot data")

    def setdefault(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError("Cannot mutate immutable audit snapshot data")

    def update(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("Cannot mutate immutable audit snapshot data")


def _freeze_snapshot_data(val: Any) -> Any:
    """Recursively freeze dictionary and list containers to enforce deep immutability."""
    if isinstance(val, dict):
        return FrozenSnapshotDict({k: _freeze_snapshot_data(v) for k, v in val.items()})
    elif isinstance(val, (list, tuple)):
        return tuple(_freeze_snapshot_data(x) for x in val)
    return val


def compute_input_snapshot_hash(data: Dict[str, Any], evaluation_date: date) -> str:
    """Compute a deterministic SHA-256 hash of the input snapshot facts."""
    payload = {
        "evaluation_date": evaluation_date.isoformat(),
        "facts": _canonicalize_object(data),
    }
    canonical_bytes = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


class InputSnapshot(BaseModel):
    """Immutable, frozen input fact record evaluated at a specific historical moment."""

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    citizen_ref: str = Field(..., description="Synthetic non-sensitive citizen reference")
    evaluation_date: date = Field(..., description="As-of evaluation reference date")
    data: Dict[str, Any] = Field(..., description="Complete frozen citizen facts and claims")
    snapshot_hash: str = Field(..., description="Cryptographic SHA-256 hash of input data")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when snapshot was sealed",
    )

    model_config = ConfigDict(extra="ignore", frozen=True, arbitrary_types_allowed=True)

    @field_validator("data", mode="after")
    @classmethod
    def _enforce_frozen_data(cls, v: Any) -> Any:
        return _freeze_snapshot_data(v)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize snapshot to Python dictionary."""
        return self.model_dump(mode="python")


class AuditEvaluationRecord(BaseModel):
    """Authoritative, audit-ready record capturing full policy, trace, inputs, and decision."""

    audit_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique audit record identifier")
    evaluation_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique evaluation identifier")
    schema_version: str = Field(default=AUDIT_SCHEMA_VERSION, description="Audit schema version")
    citizen_ref: str = Field(..., description="Synthetic, non-sensitive citizen identifier")
    scheme_code: str = Field(..., description="Unique statutory scheme code")
    policy_version_code: str = Field(..., description="Policy version code e.g. v2019.1")
    evaluation_date: date = Field(..., description="Date of evaluation")
    final_result: EligibilityResult = Field(..., description="Final eligibility decision")
    root_truth_value: RuleTruthValue = Field(..., description="Root AST truth value")
    input_snapshot: InputSnapshot = Field(..., description="Immutable snapshot of inputs evaluated")
    provenance: PolicyProvenance = Field(..., description="Policy provenance and statutory sources")
    explainability_trace: ExplainabilityTrace = Field(..., description="Ordered explainability trace")
    blockers: List[InformationGapBlocker] = Field(
        default_factory=list, description="Structured blockers preventing entitlement"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when audit record was created",
    )

    model_config = ConfigDict(extra="ignore", frozen=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize audit record to Python dictionary."""
        return self.model_dump(mode="python")

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize audit record to canonical formatted JSON with sorted keys."""
        data = self.model_dump(mode="json")
        return json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False)

    def to_db_model(
        self,
        citizen_id: uuid.UUID,
        scheme_id: uuid.UUID,
        policy_version_id: uuid.UUID,
    ) -> EvaluationTrace:
        """Bridge into persistent SQLAlchemy EvaluationTrace model."""
        return EvaluationTrace(
            id=self.evaluation_id,
            citizen_id=citizen_id,
            scheme_id=scheme_id,
            policy_version_id=policy_version_id,
            evaluation_date=self.evaluation_date,
            input_snapshot_json=self.input_snapshot.model_dump(mode="json"),
            result_state=self.final_result,
            trace_json=self.explainability_trace.model_dump(mode="json"),
            rule_definition_hash=self.provenance.canonical_rule_hash,
            trace_schema_version=self.explainability_trace.trace_version,
            created_at=self.created_at,
        )


def create_audit_evaluation_record(
    citizen_ref: str,
    input_data: Dict[str, Any],
    provenance: PolicyProvenance,
    explainability_trace: ExplainabilityTrace,
    evaluation_id: Optional[uuid.UUID] = None,
) -> AuditEvaluationRecord:
    """Create a complete, sealed AuditEvaluationRecord."""
    eval_id = evaluation_id or uuid.uuid4()
    eval_date = provenance.evaluation_date

    deep_copied_data = copy.deepcopy(input_data)
    snapshot_hash = compute_input_snapshot_hash(deep_copied_data, eval_date)
    frozen_data = _freeze_snapshot_data(deep_copied_data)

    snapshot = InputSnapshot(
        snapshot_id=f"snp-{snapshot_hash[:12]}",
        citizen_ref=citizen_ref,
        evaluation_date=eval_date,
        data=frozen_data,
        snapshot_hash=snapshot_hash,
    )

    return AuditEvaluationRecord(
        evaluation_id=eval_id,
        citizen_ref=citizen_ref,
        scheme_code=provenance.scheme_code,
        policy_version_code=provenance.policy_version_code,
        evaluation_date=eval_date,
        final_result=explainability_trace.overall_result,
        root_truth_value=explainability_trace.root_truth_value,
        input_snapshot=snapshot,
        provenance=provenance,
        explainability_trace=explainability_trace,
        blockers=list(explainability_trace.blockers),
    )
