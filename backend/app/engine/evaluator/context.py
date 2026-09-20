"""Evaluation Context for deterministic, read-only data resolution."""

from datetime import date
from types import MappingProxyType
from typing import Any, Dict, Optional, Tuple

from app.engine.errors import FieldPathResolutionError


class EvaluationContext:
    """Immutable evaluation context encapsulating citizen facts, reference dates, and scoped data."""

    def __init__(
        self,
        data: Dict[str, Any],
        evaluation_date: date,
        policy_metadata: Optional[Dict[str, Any]] = None,
        scoped_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not isinstance(evaluation_date, date):
            raise TypeError(f"evaluation_date must be an instance of datetime.date, got {type(evaluation_date).__name__}")

        self._data = MappingProxyType(dict(data))
        self._evaluation_date = evaluation_date
        self._policy_metadata = MappingProxyType(dict(policy_metadata or {}))
        self._scoped_data = MappingProxyType(dict(scoped_data or {}))

    @property
    def data(self) -> MappingProxyType:
        return self._data

    @property
    def evaluation_date(self) -> date:
        return self._evaluation_date

    @property
    def policy_metadata(self) -> MappingProxyType:
        return self._policy_metadata

    @property
    def scoped_data(self) -> MappingProxyType:
        return self._scoped_data

    def with_scope(self, scope_dict: Dict[str, Any]) -> "EvaluationContext":
        """Create a new EvaluationContext inheriting base data with extended scoped definitions."""
        merged_scopes = dict(self._scoped_data)
        merged_scopes.update(scope_dict)
        return EvaluationContext(
            data=dict(self._data),
            evaluation_date=self._evaluation_date,
            policy_metadata=dict(self._policy_metadata),
            scoped_data=merged_scopes,
        )

    def resolve_path(self, path: str) -> Tuple[Any, bool]:
        """Safely resolve a dot-delimited field path against scoped and primary data.
        
        Returns:
            Tuple[value, exists]: Where exists indicates whether the path was present
            (distinguishing an explicitly null field from a non-existent field).
        """
        if not path or not isinstance(path, str):
            raise FieldPathResolutionError("Field path must be a non-empty string.")

        clean_path = path.strip()

        # Built-in context dates
        if clean_path == "evaluation_date":
            return self._evaluation_date, True

        parts = clean_path.split(".")

        # 1. Check scoped data first (for aliases like 'member' or 'item')
        if parts[0] in self._scoped_data:
            current = self._scoped_data[parts[0]]
            parts = parts[1:]
            if not parts:
                return current, True
        elif parts[0] in self._data:
            current = self._data[parts[0]]
            parts = parts[1:]
            if not parts:
                return current, True
        else:
            return None, False

        # Traverse remaining parts
        for part in parts:
            if current is None:
                return None, False

            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return None, False
            elif isinstance(current, (list, tuple)):
                if part.isdigit():
                    idx = int(part)
                    if 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return None, False
                else:
                    return None, False
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None, False

        return current, True
