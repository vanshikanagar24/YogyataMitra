"""Explainability, Provenance, and Audit layer for YogyataMitra."""

from app.engine.explainability.audit import (
    AuditEvaluationRecord,
    InputSnapshot,
    compute_input_snapshot_hash,
    create_audit_evaluation_record,
)
from app.engine.explainability.blockers import (
    BlockerCategory,
    InformationGapBlocker,
)
from app.engine.explainability.constants import (
    AUDIT_SCHEMA_VERSION,
    BLOCKER_SCHEMA_VERSION,
    EVALUATOR_VERSION,
    EXPLANATION_SCHEMA_VERSION,
    PROVENANCE_SCHEMA_VERSION,
    TRACE_SCHEMA_VERSION,
)
from app.engine.explainability.explanation import (
    RuleExplanation,
    generate_rule_explanation,
)
from app.engine.explainability.provenance import (
    PolicyProvenance,
    compute_canonical_rule_hash,
)
from app.engine.explainability.trace import (
    ExplainabilityTrace,
    ExplainableTraceNode,
)
from app.engine.explainability.trace_builder import (
    TraceBuilder,
    build_explainability_trace,
)

__all__ = [
    # Constants
    "TRACE_SCHEMA_VERSION",
    "EXPLANATION_SCHEMA_VERSION",
    "AUDIT_SCHEMA_VERSION",
    "BLOCKER_SCHEMA_VERSION",
    "PROVENANCE_SCHEMA_VERSION",
    "EVALUATOR_VERSION",
    # Blockers
    "BlockerCategory",
    "InformationGapBlocker",
    # Provenance
    "PolicyProvenance",
    "compute_canonical_rule_hash",
    # Explanation
    "RuleExplanation",
    "generate_rule_explanation",
    # Trace
    "ExplainableTraceNode",
    "ExplainabilityTrace",
    "TraceBuilder",
    "build_explainability_trace",
    # Audit
    "InputSnapshot",
    "AuditEvaluationRecord",
    "compute_input_snapshot_hash",
    "create_audit_evaluation_record",
]
