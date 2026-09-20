"""Generic Statutory Policy Selection Service.

Selects the applicable time-bounded policy version for any scheme based on an
evaluation date. Contains zero scheme-specific business logic; queries PostgreSQL
strictly using statutory effective date intervals.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.ast.nodes import RuleASTNode
from app.engine.ast.validation import validate_ast
from app.models.scheme import PolicyVersion, RuleSet, Scheme
from app.services.policy_loader import SchemeNotFoundError


class PolicyVersionNotFoundError(Exception):
    """Raised when no effective policy version exists for a scheme on the specified date."""
    pass


async def select_policy_version(
    session: AsyncSession,
    scheme_code: str,
    evaluation_date: date,
) -> Optional[PolicyVersion]:
    """Select the active PolicyVersion for a scheme on a given evaluation date.
    
    Generic selection algorithm:
    1. Lookup Scheme by scheme_code (normalized uppercase).
    2. Filter PolicyVersion where:
       - scheme_id == scheme.id
       - effective_from <= evaluation_date
       - (effective_to IS NULL OR effective_to >= evaluation_date)
    3. Order by effective_from DESC to resolve latest applicable generation.
    4. Eagerly load the associated RuleSet.
    
    Returns:
        The matched PolicyVersion with its loaded RuleSet, or None if no version covers the date.
        
    Raises:
        SchemeNotFoundError: If the scheme_code is not registered.
    """
    normalized_code = scheme_code.strip().upper()

    scheme_stmt = select(Scheme).where(Scheme.scheme_code == normalized_code)
    scheme_res = await session.execute(scheme_stmt)
    scheme = scheme_res.scalar_one_or_none()

    if not scheme:
        raise SchemeNotFoundError(f"Scheme with code '{scheme_code}' was not found in database.")

    pv_stmt = (
        select(PolicyVersion)
        .options(selectinload(PolicyVersion.rule_set), selectinload(PolicyVersion.scheme))
        .where(
            PolicyVersion.scheme_id == scheme.id,
            PolicyVersion.effective_from <= evaluation_date,
            or_(
                PolicyVersion.effective_to.is_(None),
                PolicyVersion.effective_to >= evaluation_date,
            ),
        )
        .order_by(PolicyVersion.effective_from.desc())
        .limit(1)
    )

    pv_res = await session.execute(pv_stmt)
    return pv_res.scalar_one_or_none()


async def get_policy_version(
    session: AsyncSession,
    scheme_code: str,
    evaluation_date: date,
) -> PolicyVersion:
    """Select active PolicyVersion, raising PolicyVersionNotFoundError if none exists."""
    pv = await select_policy_version(session, scheme_code, evaluation_date)
    if not pv:
        raise PolicyVersionNotFoundError(
            f"No policy version found for scheme '{scheme_code}' effective on {evaluation_date.isoformat()}."
        )
    return pv


def get_policy_rule_ast(policy_version: PolicyVersion) -> RuleASTNode:
    """Extract and validate the RuleASTNode from a loaded PolicyVersion.
    
    Raises:
        ValueError: If the policy version lacks an associated RuleSet or definition_json.
        ASTValidationError: If the stored JSON fails AST validation.
    """
    if not policy_version.rule_set or not policy_version.rule_set.definition_json:
        raise ValueError(
            f"PolicyVersion '{policy_version.version_code}' has no associated RuleSet definition."
        )

    raw_ast = policy_version.rule_set.definition_json
    if "root_rule" in raw_ast and isinstance(raw_ast["root_rule"], dict):
        return validate_ast(raw_ast["root_rule"])
    return validate_ast(raw_ast)
