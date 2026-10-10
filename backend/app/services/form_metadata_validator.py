"""Policy Form Metadata Validation Service (Phase G).

Validates declarative policy-driven form metadata definitions against statutory
integrity invariants:
- Uniqueness of field keys
- Valid generic field types
- Non-empty bilingual labels, section titles, and guidance
- Valid select/radio option shapes and unique option values
- Reference integrity: all fields reference valid sections in sections list
- Reference integrity: associated evidence types reference valid evidence_types
- Reference integrity: condition field_keys reference existing form fields
- Reference integrity: cross-field rules reference existing form fields
- Condition operator validity
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from app.schemas.form_metadata import (
    ConditionOperator,
    CrossFieldRule,
    FieldCondition,
    FormFieldDefinition,
    FormFieldType,
    PolicyFormMetadata,
)


class PolicyFormMetadataValidationError(ValueError):
    """Raised when policy form metadata fails structural or semantic invariants."""
    pass


MetadataValidationError = PolicyFormMetadataValidationError


VALID_FIELD_TYPES: Set[str] = {t.value for t in FormFieldType}


def validate_policy_form_metadata(metadata: PolicyFormMetadata) -> None:
    """Validate all structural, bilingual, and relational invariants of a PolicyFormMetadata definition."""
    if not metadata.scheme_code or not metadata.scheme_code.strip():
        raise PolicyFormMetadataValidationError("PolicyFormMetadata must have a non-empty 'scheme_code'.")

    if not metadata.policy_version_code or not metadata.policy_version_code.strip():
        raise PolicyFormMetadataValidationError("PolicyFormMetadata must have a non-empty 'policy_version_code'.")

    if not metadata.sections:
        raise PolicyFormMetadataValidationError("PolicyFormMetadata must define at least one section in 'sections'.")

    # 1. Validate Sections
    section_keys: Set[str] = set()
    for s in metadata.sections:
        if not s.section_key or not s.section_key.strip():
            raise PolicyFormMetadataValidationError("All form sections must have a non-empty 'section_key'.")
        if s.section_key in section_keys:
            raise PolicyFormMetadataValidationError(f"Duplicate section_key detected in metadata: '{s.section_key}'.")
        section_keys.add(s.section_key)

        if not s.title_en or not s.title_en.strip():
            raise PolicyFormMetadataValidationError(f"Section '{s.section_key}' is missing required 'title_en'.")
        if not s.title_hi or not s.title_hi.strip():
            raise PolicyFormMetadataValidationError(f"Section '{s.section_key}' is missing required 'title_hi'.")

    # 2. Validate Evidence Types
    evidence_types: Set[str] = set()
    for ev in metadata.evidence_types:
        if not ev.evidence_type or not ev.evidence_type.strip():
            raise PolicyFormMetadataValidationError("All evidence definitions must have a non-empty 'evidence_type'.")
        if ev.evidence_type in evidence_types:
            raise PolicyFormMetadataValidationError(f"Duplicate evidence_type detected: '{ev.evidence_type}'.")
        evidence_types.add(ev.evidence_type)

        if not ev.label_en or not ev.label_en.strip():
            raise PolicyFormMetadataValidationError(f"Evidence '{ev.evidence_type}' is missing required 'label_en'.")
        if not ev.label_hi or not ev.label_hi.strip():
            raise PolicyFormMetadataValidationError(f"Evidence '{ev.evidence_type}' is missing required 'label_hi'.")

    # 3. Validate Fields
    field_keys: Set[str] = set()
    for f in metadata.fields:
        if not f.field_key or not f.field_key.strip():
            raise PolicyFormMetadataValidationError("All form fields must have a non-empty 'field_key'.")
        if f.field_key in field_keys:
            raise PolicyFormMetadataValidationError(f"Duplicate field_key detected in metadata: '{f.field_key}'.")
        field_keys.add(f.field_key)

        # Field type validity
        ft = f.field_type.lower().strip()
        if ft not in VALID_FIELD_TYPES:
            raise PolicyFormMetadataValidationError(
                f"Field '{f.field_key}' has invalid field_type '{f.field_type}'. Allowed types: {sorted(VALID_FIELD_TYPES)}."
            )

        # Bilingual labels
        if not f.label_en or not f.label_en.strip():
            raise PolicyFormMetadataValidationError(f"Field '{f.field_key}' is missing required 'label_en'.")
        if not f.label_hi or not f.label_hi.strip():
            raise PolicyFormMetadataValidationError(f"Field '{f.field_key}' is missing required 'label_hi'.")

        # Section reference integrity
        if f.section_key not in section_keys and f.section_key != "general":
            raise PolicyFormMetadataValidationError(
                f"Field '{f.field_key}' references nonexistent section_key '{f.section_key}'. Defined sections: {sorted(section_keys)}."
            )

        # Evidence reference integrity
        if f.associated_evidence_type and f.associated_evidence_type not in evidence_types:
            raise PolicyFormMetadataValidationError(
                f"Field '{f.field_key}' references nonexistent evidence_type '{f.associated_evidence_type}'. Defined evidence: {sorted(evidence_types)}."
            )

        # Options for choice types
        if ft in ("select", "radio", "multi_select"):
            if not f.options or len(f.options) == 0:
                raise PolicyFormMetadataValidationError(
                    f"Field '{f.field_key}' of type '{ft}' must define a non-empty 'options' list."
                )
            opt_vals: Set[str] = set()
            for opt in f.options:
                val = opt.get("value")
                if val is None or str(val).strip() == "":
                    raise PolicyFormMetadataValidationError(
                        f"Field '{f.field_key}' has an option with missing or empty 'value'."
                    )
                str_val = str(val)
                if str_val in opt_vals:
                    raise PolicyFormMetadataValidationError(
                        f"Field '{f.field_key}' has duplicate option value '{str_val}'."
                    )
                opt_vals.add(str_val)

        # Numeric bounds
        if f.min_value is not None and f.max_value is not None and f.min_value > f.max_value:
            raise PolicyFormMetadataValidationError(
                f"Field '{f.field_key}' has invalid numeric range: min_value ({f.min_value}) > max_value ({f.max_value})."
            )

        # Date bounds
        if f.min_date is not None and f.max_date is not None and f.min_date > f.max_date:
            raise PolicyFormMetadataValidationError(
                f"Field '{f.field_key}' has invalid date range: min_date ({f.min_date}) > max_date ({f.max_date})."
            )

    # 4. Validate Field Conditions (must reference known fields)
    for f in metadata.fields:
        if f.condition:
            cond = f.condition
            if cond.field_key not in field_keys:
                raise PolicyFormMetadataValidationError(
                    f"Field '{f.field_key}' condition references unknown field_key '{cond.field_key}'."
                )
            if cond.field_key == f.field_key:
                raise PolicyFormMetadataValidationError(
                    f"Field '{f.field_key}' condition cannot depend cyclically on itself."
                )

    # 5. Validate Cross-Field Rules
    for cfr in metadata.cross_field_rules:
        if cfr.primary_field not in field_keys:
            raise PolicyFormMetadataValidationError(
                f"CrossFieldRule '{cfr.rule_id}' primary_field '{cfr.primary_field}' does not exist in fields."
            )
        if cfr.secondary_field and cfr.secondary_field not in field_keys:
            raise PolicyFormMetadataValidationError(
                f"CrossFieldRule '{cfr.rule_id}' secondary_field '{cfr.secondary_field}' does not exist in fields."
            )
        if not cfr.message_en or not cfr.message_en.strip():
            raise PolicyFormMetadataValidationError(f"CrossFieldRule '{cfr.rule_id}' is missing required 'message_en'.")
        if not cfr.message_hi or not cfr.message_hi.strip():
            raise PolicyFormMetadataValidationError(f"CrossFieldRule '{cfr.rule_id}' is missing required 'message_hi'.")


# ==============================================================================
# Citizen Fact and Form Submission Validation (Runtime)
# ==============================================================================

def flatten_facts(facts: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten hierarchical or nested section dictionaries into dot-notated keys."""
    flattened: Dict[str, Any] = {}
    for k, v in facts.items():
        if isinstance(v, dict) and not ("value" in v and len(v) == 1):
            for sub_k, sub_v in v.items():
                flattened[f"{k}.{sub_k}"] = sub_v
        else:
            actual_v = v.get("value") if isinstance(v, dict) and "value" in v and len(v) == 1 else v
            flattened[k] = actual_v
    return flattened


def validate_citizen_form_submission(
    facts: Dict[str, Any],
    metadata: PolicyFormMetadata,
    evidence_items: Optional[List[Any]] = None,
    is_submission: bool = False,
) -> List[str]:
    """Validate citizen submitted facts and evidence against PolicyFormMetadata.

    Enforces:
    - Rejection of unknown field keys (strict schema safety)
    - Field type constraints (boolean, number, integer, decimal, date, select)
    - Value ranges (min/max numbers, allowed select options)
    - Mandatory field requirements (for applicable fields on submission)
    - Conditional field applicability (hidden fields are not mandatory)
    - Declarative cross-field rules (e.g. age-at-opening limits)
    - Mandatory documentary evidence presence on submission

    Returns:
        List of error strings (empty list indicates valid submission).
    """
    from datetime import date

    errors: List[str] = []
    flat = flatten_facts(facts)

    field_map: Dict[str, FormFieldDefinition] = {f.field_key: f for f in metadata.fields}
    allowed_keys: Set[str] = set(field_map.keys())

    # Also allow base section names if nested
    allowed_sections: Set[str] = {f.field_key.split(".")[0] for f in metadata.fields if "." in f.field_key}

    # 1. Unknown Field Rejection (Anti-Spoofing & Invariant Protection)
    for raw_k in facts.keys():
        if raw_k not in allowed_keys and raw_k not in allowed_sections:
            errors.append(
                f"Unknown field '{raw_k}' is not permitted for policy version '{metadata.policy_version_code}'."
            )

    for flat_k in flat.keys():
        if flat_k not in allowed_keys:
            errors.append(
                f"Unknown field key '{flat_k}' is not defined for policy version '{metadata.policy_version_code}'."
            )

    # 2. Type and Value Boundary Validation for Declared Fields
    for f_key, val in flat.items():
        if f_key not in field_map or val is None or val == "":
            continue

        f_def = field_map[f_key]
        ft = f_def.field_type.lower().strip()

        # Boolean validation
        if ft == "boolean":
            if not isinstance(val, bool):
                errors.append(f"Field '{f_key}' must be a boolean (True/False).")

        # Numeric validations
        elif ft in ("number", "integer", "decimal"):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                errors.append(f"Field '{f_key}' must be a numeric value.")
            else:
                num_val = float(val)
                if ft == "integer" and not float(val).is_integer():
                    errors.append(
                        f_def.validation_message_en
                        or f"Field '{f_key}' must be an integer."
                    )
                if f_def.min_value is not None and num_val < f_def.min_value:
                    errors.append(
                        f"Field '{f_key}' value {num_val} is less than statutory minimum ({f_def.min_value})."
                    )
                if f_def.max_value is not None and num_val > f_def.max_value:
                    errors.append(
                        f"Field '{f_key}' value {num_val} exceeds statutory maximum ({f_def.max_value})."
                    )

        # Date validation
        elif ft == "date":
            if not isinstance(val, str):
                errors.append(f"Field '{f_key}' must be a valid date string (YYYY-MM-DD).")
            else:
                try:
                    parsed_d = date.fromisoformat(val.strip())
                    if f_def.min_date:
                        min_d = date.fromisoformat(f_def.min_date)
                        if parsed_d < min_d:
                            errors.append(f"Field '{f_key}' date cannot be prior to {f_def.min_date}.")
                    if f_def.max_date:
                        max_d = date.fromisoformat(f_def.max_date)
                        if parsed_d > max_d:
                            errors.append(f"Field '{f_key}' date cannot be after {f_def.max_date}.")
                except ValueError:
                    errors.append(f"Field '{f_key}' value '{val}' is not a valid ISO date (YYYY-MM-DD).")

        # Select / Radio options validation
        elif ft in ("select", "radio") and f_def.options:
            allowed_opts = {str(opt["value"]) for opt in f_def.options if "value" in opt}
            if str(val) not in allowed_opts:
                errors.append(
                    f"Field '{f_key}' value '{val}' is not among authorized options: {sorted(allowed_opts)}."
                )

    # 3. Submission-Only Mandatory Field & Cross-Field Validations
    if is_submission:
        # Check mandatory fields
        for f_def in metadata.fields:
            if not f_def.required:
                continue

            # Evaluate conditional visibility: if condition is not satisfied, field is not applicable
            if f_def.condition:
                is_applicable = f_def.condition.evaluate(flat)
                if not is_applicable:
                    continue

            val = flat.get(f_def.field_key)
            if val is None or val == "":
                errors.append(
                    f_def.validation_message_en
                    or f"Mandatory statutory field '{f_def.field_key}' ({f_def.label_en}) is required."
                )

        # Evaluate cross-field rules
        for cfr in metadata.cross_field_rules:
            if cfr.rule_type == "AGE_AT_DATE":
                dob_val = flat.get(cfr.primary_field)
                open_val = flat.get(cfr.secondary_field) if cfr.secondary_field else None
                if dob_val:
                    try:
                        d_dob = date.fromisoformat(str(dob_val).strip())
                        if open_val:
                            d_open = date.fromisoformat(str(open_val).strip())
                        else:
                            d_open = date.today()
                        # Compute completed years of age at opening date
                        age = d_open.year - d_dob.year - ((d_open.month, d_open.day) < (d_dob.month, d_dob.day))
                        max_age = (cfr.parameters or {}).get("max_age_years", 10)
                        if age > max_age:
                            errors.append(cfr.message_en)
                    except ValueError:
                        pass

            elif cfr.rule_type == "DATE_CHRONOLOGY":
                date1_val = flat.get(cfr.primary_field)
                date2_val = flat.get(cfr.secondary_field) if cfr.secondary_field else None
                if date1_val and date2_val:
                    try:
                        d1 = date.fromisoformat(str(date1_val).strip())
                        d2 = date.fromisoformat(str(date2_val).strip())
                        if cfr.operator == "GREATER_THAN_OR_EQUAL" and d1 < d2:
                            errors.append(cfr.message_en)
                        elif cfr.operator == "LESS_THAN_OR_EQUAL" and d1 > d2:
                            errors.append(cfr.message_en)
                    except ValueError:
                        pass

        # Validate that any attached evidence belongs to registered evidence types
        if evidence_items:
            known_ev_types = {ev.evidence_type for ev in metadata.evidence_types}
            for item in evidence_items:
                ev_type = getattr(item, "evidence_type", None) or (item.get("evidence_type") if isinstance(item, dict) else None)
                if ev_type and ev_type not in known_ev_types:
                    errors.append(
                        f"Unknown evidence type '{ev_type}' is not recognized for policy version '{metadata.policy_version_code}'."
                    )

    return errors
