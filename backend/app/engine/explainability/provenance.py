"""Policy provenance and canonical cryptographic rule hashing."""

from datetime import date
import hashlib
import json
from typing import Any, Dict, List, Optional, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.engine.ast.nodes import BaseRuleNode
from app.engine.explainability.constants import PROVENANCE_SCHEMA_VERSION


def _canonicalize_object(obj: Any) -> Any:
    """Recursively normalize data structures for deterministic hashing.
    
    Invariants:
    - Retains all structural elements (empty dicts, empty lists, empty strings, None).
    - Recursively sorts dictionary keys.
    - Dates and datetimes are normalized to ISO-8601 strings.
    - Floating point values are formatted deterministically.
    - UUIDs are converted to strings.
    """
    if isinstance(obj, BaseRuleNode):
        return _canonicalize_object(obj.model_dump(mode="json"))
    elif isinstance(obj, dict):
        return {
            k: _canonicalize_object(v)
            for k, v in sorted(obj.items())
        }
    elif isinstance(obj, (list, tuple)):
        return [_canonicalize_object(item) for item in obj]
    elif isinstance(obj, (date,)):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, float):
        # Format float consistently avoiding platform-specific variations
        return f"{obj:.8f}".rstrip("0").rstrip(".")
    else:
        return obj


def compute_canonical_rule_hash(rule_def: Union[Dict[str, Any], BaseRuleNode, List[Any]]) -> str:
    """Compute a cryptographically secure, deterministic SHA-256 hash of a rule definition.
    
    Guarantees:
    - Preserves all structural and semantic distinctions without dropping empty containers or None.
    - Identical rule structures produce the exact same 64-character hex hash regardless of
      dictionary insertion order.
    - Raw AST dictionaries are validated into canonical AST nodes so schema defaults align.
    - Any alteration to node type, operator, expected value, field path, or logic changes the hash.
    """
    if isinstance(rule_def, BaseRuleNode):
        raw_data = rule_def.model_dump(mode="json")
    elif isinstance(rule_def, dict):
        if "node_type" in rule_def:
            try:
                from app.engine.ast.validation import validate_ast
                validated = validate_ast(rule_def)
                raw_data = validated.model_dump(mode="json")
            except Exception:
                raw_data = dict(rule_def)
        else:
            raw_data = dict(rule_def)
    elif isinstance(rule_def, list):
        raw_data = list(rule_def)
    else:
        raise TypeError(
            f"Expected dict, BaseRuleNode, or list for rule definition, got {type(rule_def).__name__}"
        )

    canonical_data = _canonicalize_object(raw_data)
    canonical_json_bytes = json.dumps(
        canonical_data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(canonical_json_bytes).hexdigest()


class PolicyProvenance(BaseModel):
    """Immutable provenance record binding an evaluation to its statutory source and policy version."""

    provenance_schema_version: str = Field(
        default=PROVENANCE_SCHEMA_VERSION, description="Schema version of provenance metadata"
    )
    scheme_id: Optional[uuid.UUID] = Field(None, description="Database UUID of scheme if persisted")
    scheme_code: str = Field(..., min_length=1, description="Unique statutory code of scheme")
    policy_version_id: Optional[uuid.UUID] = Field(None, description="Database UUID of policy version if persisted")
    policy_version_code: str = Field(..., min_length=1, description="Policy version label e.g. v2019.1")
    rule_set_id: Optional[uuid.UUID] = Field(None, description="Database UUID of ruleset if persisted")
    rule_set_version: str = Field(..., min_length=1, description="Semantic version of ruleset e.g. 1.0.0")
    canonical_rule_hash: str = Field(
        ..., min_length=64, max_length=64, description="Cryptographic SHA-256 hex digest of canonical rule AST"
    )
    evaluation_date: date = Field(..., description="As-of reference date for policy evaluation")
    effective_from: date = Field(..., description="Date this policy version came into official effect")
    effective_to: Optional[date] = Field(None, description="Date this policy version was superseded if any")
    source_url: Optional[str] = Field(None, description="Authoritative statutory source URL or gazette link")
    source_title: Optional[str] = Field(None, description="Formal title of statutory guideline or order")
    source_clause: Optional[str] = Field(None, description="Specific statutory section or clause reference")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional provenance attributes")

    model_config = ConfigDict(extra="ignore", frozen=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize provenance to Python dictionary."""
        return self.model_dump(mode="python")

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize provenance to canonical formatted JSON string."""
        data = self.model_dump(mode="json")
        return json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False)
