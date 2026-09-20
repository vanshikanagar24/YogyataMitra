# YogyataMitra — Phase 3 Engine Specification: Rule AST & Deterministic Evaluator

## 1. Executive Summary & Design Principles

The YogyataMitra Rule AST and Deterministic Evaluation Engine constitutes the core reasoning layer of the platform. It evaluates declarative statutory welfare policy rules against citizen-asserted and administratively-verified facts without coupling to any specific welfare scheme, relational database, LLM/AI model, or external service.

### Core Architectural Invariants
1. **Stateless & Deterministic**: Given an AST representation and an immutable evaluation context, the engine always produces the exact same evaluation outcome and trace.
2. **Provider-Neutral & Scheme-Agnostic**: Contains zero hardcoded rules for PM-KISAN, SSY, or any specific scheme. All rules are expressed as declarative AST data.
3. **Database-Independent**: Pure in-memory computation. Accepts plain Python dictionaries, Pydantic objects, and an explicit reference date (`evaluation_date`).
4. **Kleene Strong Tri-State Logic**: Implements true multi-valued logic (`TRUE`, `FALSE`, `UNKNOWN`). Missing, null, or unverified facts evaluate to `UNKNOWN` rather than being falsely collapsed into `FALSE`.
5. **No Code Execution / Zero-Eval Security**: Rules are evaluated strictly via explicit AST visitor routines. No `eval()`, `exec()`, or dynamic code compilation is permitted.

---

## 2. AST Grammar & Node Specifications

All rule nodes inherit from `BaseRuleNode` and are discriminated by the `node_type` field using Pydantic v2 discriminated unions (`RuleASTNode`).

### 2.1 Common Node Metadata
All AST nodes support statutory provenance and bilingual human descriptions:
- `rule_id`: Optional unique rule identifier (e.g. `PMKISAN_LAND_CUTOFF_2019`)
- `description_en`: English plain-text description
- `description_hi`: Hindi plain-text description (हिंदी विवरण)
- `source_clause`: Statutory or guideline section reference (e.g. `Clause 4.1(a)`)
- `metadata`: Arbitrary policy metadata dictionary

### 2.2 Node Types & Operator Matrix

| Node Type (`node_type`) | Operator (`operator`) | Operands & Fields | Evaluation Semantics |
|---|---|---|---|
| `logical` | `AND` | `children: List[RuleASTNode]` | Kleene strong conjunction: `FALSE` dominates `UNKNOWN`, `UNKNOWN` dominates `TRUE`. |
| `logical` | `OR` | `children: List[RuleASTNode]` | Kleene strong disjunction: `TRUE` dominates `UNKNOWN`, `UNKNOWN` dominates `FALSE`. |
| `logical` | `NOT` | `child: RuleASTNode` | Negation: `TRUE` $\leftrightarrow$ `FALSE`, `UNKNOWN` $\leftrightarrow$ `UNKNOWN`. |
| `comparison` | `EQ`, `NEQ`, `GT`, `GTE`, `LT`, `LTE` | `field_path: str`, `expected_value: Any` | Evaluates field against expected target. If field is missing or None $\rightarrow$ `UNKNOWN`. |
| `comparison` | `IN`, `NOT_IN` | `field_path: str`, `expected_value: Sequence` | Container membership. If field is missing $\rightarrow$ `UNKNOWN`. |
| `existence` | `EXISTS` | `field_path: str` | `TRUE` if present and non-null, else `FALSE`. |
| `existence` | `IS_MISSING` | `field_path: str` | `TRUE` if absent or null, else `FALSE`. |
| `temporal` | `HAS_NOT_ATTAINED_AGE` | `dob_field: str`, `as_of_field: str`, `age_limit: int` | Exact calendar age. On the $N$-th birthday, age is $N$, meaning the person *has attained* $N$, evaluating to `FALSE`. |
| `temporal` | `AGE_AT` | `dob_field: str`, `as_of_field: str`, `comparison_operator`, `expected_years` | Exact calendar age comparison against threshold. |
| `collection` | `COUNT` | `collection_path: str`, `comparison_operator`, `expected_count: int`, `predicate?: RuleASTNode` | Counts total elements or elements matching optional `predicate`. |
| `collection` | `FOR_ALL` | `collection_path: str`, `item_alias: str`, `predicate: RuleASTNode` | Universal quantifier $\forall x \in C$. Empty collection is vacuously `TRUE`. Conjoins items under Kleene logic. |
| `collection` | `EXISTS_IN` | `collection_path: str`, `item_alias: str`, `predicate: RuleASTNode` | Existential quantifier $\exists x \in C$. Empty collection is `FALSE`. Disjoins items under Kleene logic. |
| `aggregation` | `AGGREGATE_SUM` | `collection_path: str`, `value_field: str`, `comparison_operator`, `expected_value: num` | Sums numeric property over items and tests against threshold. |
| `context` | `EVALUATE_FAMILY_MEMBER` | `collection_path: str`, `selector_field: str`, `selector_value: Any`, `member_alias: str`, `rule: RuleASTNode` | Scopes evaluation to a specific entity matching a selector within a collection. |

---

## 3. Kleene Strong Tri-State Logic (Truth Tables)

The engine implements Kleene's 3-valued logic of indeterminacy ($K_3$). This distinguishes conditions that definitively hold from those that definitively fail and those that are unknown due to absent facts.

### Conjunction (`kleene_and`)
$$\begin{array}{c|ccc}
\land & \mathbf{T} & \mathbf{U} & \mathbf{F} \\
\hline
\mathbf{T} & \mathbf{T} & \mathbf{U} & \mathbf{F} \\
\mathbf{U} & \mathbf{U} & \mathbf{U} & \mathbf{F} \\
\mathbf{F} & \mathbf{F} & \mathbf{F} & \mathbf{F}
\end{array}$$
*Key rule*: A single `FALSE` short-circuits to definitive failure (`FALSE`), even if other fields are `UNKNOWN`.

### Disjunction (`kleene_or`)
$$\begin{array}{c|ccc}
\lor & \mathbf{T} & \mathbf{U} & \mathbf{F} \\
\hline
\mathbf{T} & \mathbf{T} & \mathbf{T} & \mathbf{T} \\
\mathbf{U} & \mathbf{T} & \mathbf{U} & \mathbf{U} \\
\mathbf{F} & \mathbf{T} & \mathbf{U} & \mathbf{F}
\end{array}$$
*Key rule*: A single `TRUE` short-circuits to definitive satisfaction (`TRUE`), even if other fields are `UNKNOWN`.

### Negation (`kleene_not`)
$$\begin{array}{c|c}
\neg & \\
\hline
\mathbf{T} & \mathbf{F} \\
\mathbf{U} & \mathbf{U} \\
\mathbf{F} & \mathbf{T}
\end{array}$$

---

## 4. Evaluation Context & Resolution Semantics

### 4.1 Immutability
`EvaluationContext` encapsulates input facts as read-only `MappingProxyType` instances. Mutating input data after or during evaluation is strictly prohibited.

### 4.2 Dot-Path Traversal
Paths such as `family.members.0.monthly_income` or `land_records.ownership_transfer_history.acquisition_mode` are resolved safely:
- Distinguishes **missing keys** (`exists=False`) from **explicit nulls** (`exists=True, val=None`).
- Supports dictionary keys, list integer indices, and object attributes.
- Built-in `evaluation_date` returns the evaluation context reference date.
- `with_scope(scope_dict)` allows temporary variable binding for iterative collection predicates and member evaluations.

---

## 5. Decision Mapping & Audit Trace Structure

### 5.1 Final Eligibility Decision Mapping
| Root AST Truth Value (`RuleTruthValue`) | Final Outcome (`EligibilityResult`) | Description |
|---|---|---|
| `TRUE` | `ELIGIBLE` | Citizen meets all statutory requirements for entitlement. |
| `FALSE` | `INELIGIBLE` | Citizen definitively violates one or more statutory criteria. |
| `UNKNOWN` | `INSUFFICIENT_INFORMATION` | One or more mandatory fields are missing; further input or document upload required. |

### 5.2 Audit Trace Models
`EvaluationResult` provides complete, serializable visibility into every rule evaluation:
- `overall_result`: 5-state `EligibilityResult` enum.
- `root_truth_value`: Tri-state `RuleTruthValue`.
- `root_node_result`: Full tree of `NodeEvaluationResult` instances, each containing:
  - `truth_value`, `operator`, `actual_value`, `expected_value`
  - `missing_fields`: Specific field names missing at this node
  - `reason_en` & `reason_hi`: Bilingual plain-language explanations
- `all_missing_fields`: Deduplicated, order-preserving list of missing fields.
- `failed_rules`: Rule IDs of conditions that evaluated to `FALSE`.
- `satisfied_rules`: Rule IDs of conditions that evaluated to `TRUE`.
- `unknown_rules`: Rule IDs of conditions that evaluated to `UNKNOWN`.
- `.to_dict()` and `.to_json()`: Standard serialization helpers.

---

## 6. Verification Status
All 48 unit and integration tests are passing in `backend/tests/`:
- `test_engine_ast.py`: 15 tests verifying AST validation, discriminator handling, schema errors.
- `test_engine_evaluator.py`: 16 tests verifying Kleene logic, temporal boundary edge cases (SSY 10th birthday, leap years), collections, aggregations, context scoping, determinism, and zero-eval code injection safety.
- `test_database_config.py`, `test_domain_models.py`, `test_health.py`, `test_migrations.py`: 17 baseline tests verified without regressions.
