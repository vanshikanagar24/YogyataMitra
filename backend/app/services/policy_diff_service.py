"""Deterministic Policy Diff Engine.

Compares authored draft policy rules and metadata against the baseline
authoritative PolicyVersion (or active scheme policy) to generate a
human-readable, rule-level structural diff.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.ast.nodes import BaseRuleNode, RuleASTNode
from app.engine.ast.validation import validate_ast
from app.engine.explainability.provenance import compute_canonical_rule_hash
from app.models.policy_draft import PolicyDraft
from app.models.scheme import PolicyVersion, RuleSet
from app.schemas.policy_authoring import (
    PolicyDiffResponse,
    PolicyRuleDiffItem,
)


def _index_rules_by_id(node: Any, rule_map: Dict[str, Dict[str, Any]]) -> None:
    """Recursively index all rule nodes by rule_id."""
    if not isinstance(node, dict):
        return

    rule_id = node.get("rule_id")
    if rule_id:
        rule_map[rule_id] = node

    if "children" in node and isinstance(node["children"], list):
        for child in node["children"]:
            _index_rules_by_id(child, rule_map)
    if "child" in node and isinstance(node["child"], dict):
        _index_rules_by_id(node["child"], rule_map)
    if "predicate" in node and isinstance(node["predicate"], dict):
        _index_rules_by_id(node["predicate"], rule_map)
    if "rule" in node and isinstance(node["rule"], dict):
        _index_rules_by_id(node["rule"], rule_map)


async def compute_policy_diff(
    session: AsyncSession,
    draft: PolicyDraft,
) -> PolicyDiffResponse:
    """Compare a draft's authored rules and metadata against baseline PolicyVersion."""
    # 1. Resolve parent PolicyVersion
    parent_version: Optional[PolicyVersion] = None
    if draft.parent_policy_version_id:
        stmt = (
            select(PolicyVersion)
            .options(selectinload(PolicyVersion.rule_set))
            .where(PolicyVersion.id == draft.parent_policy_version_id)
        )
        res = await session.execute(stmt)
        parent_version = res.scalar_one_or_none()

    if not parent_version:
        # Fallback to latest active version for the scheme
        stmt = (
            select(PolicyVersion)
            .options(selectinload(PolicyVersion.rule_set))
            .where(PolicyVersion.scheme_id == draft.scheme_id)
            .order_by(PolicyVersion.effective_from.desc())
            .limit(1)
        )
        res = await session.execute(stmt)
        parent_version = res.scalars().first()

    parent_rules: Dict[str, Any] = {}
    parent_version_code = None
    parent_rule_hash = None

    if parent_version and parent_version.rule_set:
        parent_version_code = parent_version.version_code
        parent_rules = parent_version.rule_set.definition_json or {}
        parent_rule_hash = parent_version.rule_definition_hash or compute_canonical_rule_hash(parent_rules)

    draft_rules = draft.authored_rules_json or {}
    draft_rule_hash = draft.rule_hash
    if not draft_rule_hash and draft_rules:
        try:
            draft_rule_hash = compute_canonical_rule_hash(draft_rules)
        except Exception:
            draft_rule_hash = None

    # Index rules by ID
    parent_rule_map: Dict[str, Dict[str, Any]] = {}
    draft_rule_map: Dict[str, Dict[str, Any]] = {}
    _index_rules_by_id(parent_rules, parent_rule_map)
    _index_rules_by_id(draft_rules, draft_rule_map)

    added_rules: List[PolicyRuleDiffItem] = []
    removed_rules: List[PolicyRuleDiffItem] = []
    modified_rules: List[PolicyRuleDiffItem] = []
    metadata_changes: List[Dict[str, Any]] = []

    # Check Added Rules
    for r_id, node in draft_rule_map.items():
        if r_id not in parent_rule_map:
            desc_en = node.get("description_en") or f"Rule {r_id}"
            desc_hi = node.get("description_hi")
            nt = node.get("node_type", "rule")
            op = node.get("operator", "")
            added_rules.append(
                PolicyRuleDiffItem(
                    rule_id=r_id,
                    diff_type="ADDED",
                    description_en=desc_en,
                    description_hi=desc_hi,
                    old_value=None,
                    new_value=node,
                    human_explanation=f"New {nt} rule '{desc_en}' added with operator {op}.",
                )
            )

    # Check Removed Rules
    for r_id, node in parent_rule_map.items():
        if r_id not in draft_rule_map:
            desc_en = node.get("description_en") or f"Rule {r_id}"
            desc_hi = node.get("description_hi")
            removed_rules.append(
                PolicyRuleDiffItem(
                    rule_id=r_id,
                    diff_type="REMOVED",
                    description_en=desc_en,
                    description_hi=desc_hi,
                    old_value=node,
                    new_value=None,
                    human_explanation=f"Existing rule '{desc_en}' removed from policy.",
                )
            )

    # Check Modified Rules
    for r_id in set(parent_rule_map.keys()).intersection(draft_rule_map.keys()):
        p_node = parent_rule_map[r_id]
        d_node = draft_rule_map[r_id]

        p_hash = compute_canonical_rule_hash(p_node)
        d_hash = compute_canonical_rule_hash(d_node)

        if p_hash != d_hash:
            changes = []
            if p_node.get("operator") != d_node.get("operator"):
                changes.append(f"operator changed from {p_node.get('operator')} to {d_node.get('operator')}")
            if p_node.get("expected_value") != d_node.get("expected_value"):
                changes.append(f"threshold value changed from {p_node.get('expected_value')} to {d_node.get('expected_value')}")
            if p_node.get("age_limit") != d_node.get("age_limit"):
                changes.append(f"age limit changed from {p_node.get('age_limit')} to {d_node.get('age_limit')}")
            if p_node.get("field_path") != d_node.get("field_path"):
                changes.append(f"field path changed from {p_node.get('field_path')} to {d_node.get('field_path')}")

            explanation = (
                f"Rule {r_id} modified: {', '.join(changes)}"
                if changes
                else f"Rule {r_id} logic or parameters altered."
            )

            modified_rules.append(
                PolicyRuleDiffItem(
                    rule_id=r_id,
                    diff_type="MODIFIED",
                    description_en=d_node.get("description_en") or p_node.get("description_en"),
                    description_hi=d_node.get("description_hi") or p_node.get("description_hi"),
                    old_value=p_node,
                    new_value=d_node,
                    human_explanation=explanation,
                )
            )

    # Metadata Changes
    if parent_version:
        if parent_version.effective_from != draft.effective_from:
            metadata_changes.append({
                "field": "effective_from",
                "old": str(parent_version.effective_from),
                "new": str(draft.effective_from) if draft.effective_from else None,
                "label": "Effective Start Date",
            })
        if parent_version.effective_to != draft.effective_to:
            metadata_changes.append({
                "field": "effective_to",
                "old": str(parent_version.effective_to) if parent_version.effective_to else None,
                "new": str(draft.effective_to) if draft.effective_to else None,
                "label": "Effective End Date",
            })
        if parent_version.source_title != draft.source_title and draft.source_title:
            metadata_changes.append({
                "field": "source_title",
                "old": parent_version.source_title,
                "new": draft.source_title,
                "label": "Source Title",
            })

    # Summary
    summary_parts = []
    if parent_version_code:
        summary_parts.append(f"Comparing against authoritative version '{parent_version_code}'.")
    else:
        summary_parts.append("Initial draft without existing baseline version.")

    summary_parts.append(
        f"Diff highlights: {len(added_rules)} rule(s) added, {len(removed_rules)} rule(s) removed, "
        f"{len(modified_rules)} rule(s) modified, {len(metadata_changes)} metadata field(s) changed."
    )

    return PolicyDiffResponse(
        parent_version_code=parent_version_code,
        parent_rule_hash=parent_rule_hash,
        draft_rule_hash=draft_rule_hash,
        added_rules=added_rules,
        removed_rules=removed_rules,
        modified_rules=modified_rules,
        metadata_changes=metadata_changes,
        human_summary=" ".join(summary_parts),
    )
