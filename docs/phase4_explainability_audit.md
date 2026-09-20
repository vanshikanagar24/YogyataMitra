# YogyataMitra — Phase 4 Specification: Explainability, Provenance & Auditability

## 1. Executive Summary & Core Invariants

The YogyataMitra Explainability, Provenance, and Auditability subsystem bridges the deterministic Rule AST evaluation engine with transparent, legally defensible, and privacy-preserving decision traces. It translates low-level multi-valued logic evaluations into ordered, bilingual human explanations and cryptographically-sealed audit records.

### Core Invariants

1. **Stateless & Deterministic**: The explainability pipeline does not mutate the evaluator's output or introduce stochastic variation. Given an `EvaluationResult`, `PolicyProvenance`, and `InputSnapshot`, trace generation and audit serialization are 100% deterministic and reproducible.
2. **Provider-Neutral & Scheme-Agnostic**: All explainability templates, blocker definitions, and audit structures are completely agnostic to specific government programs. No hardcoded scheme identifiers, farmer terms, landholding rules, or girl child conditions exist within the engine or explainability layers.
3. **Strict Separation of Eligibility from Evidence**: The eligibility truth value (`TRUE`, `FALSE`, `UNKNOWN`) is logically orthogonal to evidence verification status (`PENDING`, `VERIFIED`, `REJECTED`, `EXPIRED`). The engine determines legal entitlement based on asserted facts; the audit layer links verification state to trace nodes without mutating deterministic logic.
4. **Zero-PII & Privacy by Design**: Real personal identifiers (e.g. national identity numbers, account numbers, biometric data, phone numbers) are never embedded into explanation strings or audit trace nodes. Entity references use synthetic pseudonymous tokens (e.g., `cit-syn-8f3a12d9`, `member_alias`).
5. **Cryptographic Sealing & Historical Reproducibility**: Every rule set and input snapshot is hashed using canonicalized SHA-256. Any historical decision can be audited, replayed, and verified against the exact policy version and facts active at the time of evaluation.
6. **Bilingual Fidelity**: Every evaluated node produces synchronized, faithful English (`en`) and Hindi (`hi`) explanations that convey identical factual meaning (including actual values, expected values, missing fields, operator, and outcome).

---

## 2. Architecture & Data Flow Pipeline

```
+-------------------------------------------------------------+
|                      Citizen Input Data                     |
|            (Synthetic Profile Facts & Claim State)          |
+-------------------------------------------------------------+
                               |
                               v
                     +-------------------+
                     |   InputSnapshot   |  ---> SHA-256 Hash
                     | (Deepcopy+Frozen) |
                     +-------------------+
                               |
                               v
+-------------------------------------------------------------+
|                   Deterministic Engine                      |
|            (Stateless AST Evaluation, Kleene K3)            |
+-------------------------------------------------------------+
                               |
                               v
                     +-------------------+
                     | EvaluationResult  |
                     +-------------------+
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
+-----------------------+              +----------------------+
|   PolicyProvenance    |              | Explainability Trace |
| (Statutory References |              |   (Pre-Order DFS,    |
|  & Canonical Hash)    |              | Bilingual Messages,  |
+-----------------------+              | Actionable Blockers) |
            \                                     /
             \                                   /
              v                                 v
+-------------------------------------------------------------+
|                    AuditEvaluationRecord                    |
|             (Sealed Immutable Audit Document)               |
|         - schema_version: "1.0.0"                           |
|         - canonical JSON serialization                      |
|         - frozen Pydantic model                             |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|               SQLAlchemy: EvaluationTrace                   |
|              (PostgreSQL Persistence Layer)                 |
|         - rule_definition_hash: String(64)                  |
|         - trace_schema_version: String(16)                  |
|         - input_snapshot_json: JSONB                        |
|         - trace_json: JSONB                                 |
+-------------------------------------------------------------+
```

---

## 3. Canonical Rule Hashing

Statutory rulesets must be tamper-evident. Two structurally identical rule definitions must yield the identical hash regardless of dictionary key ordering or Python representation (Pydantic model vs raw dictionary). Conversely, structurally or semantically distinct definitions must never collide.

### 3.1 Normalization Algorithm

1. If the input is a dictionary containing a `node_type` field, it is parsed and validated into a canonical `RuleASTNode` via `validate_ast()`. This aligns schema defaults across raw dictionaries and AST model objects.
2. If the input is a Pydantic `BaseRuleNode`, serialize it via `.model_dump(mode="json")`.
3. Recursively canonicalize the dictionary:
   - **Retain all structural elements**: Empty dictionaries `{}`, empty lists `[]`, empty strings `""`, and `None` (JSON `null`) are strictly preserved. They are never removed for cosmetic reasons, preventing structural collisions.
   - **Sort keys**: Dictionary keys at every hierarchy level are sorted lexicographically.
   - **Normalize types**: Dates and datetimes are formatted as ISO-8601 strings; floating-point numbers are formatted with consistent precision; UUIDs are converted to strings.
4. Serialize the canonical structure to compact UTF-8 JSON with delimiters `(",", ":")` and `sort_keys=True`.
5. Compute standard SHA-256 over the resulting UTF-8 byte stream.

### 3.2 Invariance & Collision-Free Guarantees

$$\text{hash}(\text{RuleNode}) = \text{SHA-256}(\text{CanonicalJSON}(\text{RuleNode}))$$

- **Key Order Immunity**: `{"rule_id": "R1", "operator": "EQ"}` and `{"operator": "EQ", "rule_id": "R1"}` yield the identical 64-character hex string.
- **Model vs Dict Identity**: A parsed `ComparisonNode` and an equivalent dictionary representation produce the exact same hash.
- **Collision Resistance Across Types**:
  - `{"x": {}}` $\neq$ `{}`
  - `{"x": []}` $\neq$ `{}`
  - `{"x": ""}` $\neq$ `{}`
  - `{"x": None}` $\neq$ `{}`
  - `{"a": {"b": {}}}` $\neq$ `{"a": {}}`

---

## 4. Ordered Explainability Trace

The explainability trace represents the execution graph as both a hierarchical tree and a flattened, 1-based sequentially indexed list.

### 4.1 Traversal Order

The evaluation tree is flattened using **strict depth-first pre-order traversal**:
1. The root node is visited first (`evaluation_order: 1`, `parent_trace_id: None`).
2. Child nodes are visited recursively from left to right.
3. Each node receives a synthetic sequential identifier (e.g. `trc-0001`, `trc-0002`).
4. Each child node explicitly references its direct enclosing parent via `parent_trace_id`.

```
        AND (Order 1, trc-0001)
       /   \
      /     \
     A (2)   OR (3, trc-0003)
            /  \
           B(4) C(5)
```

Pre-order: `[AND, A, OR, B, C]`

### 4.2 Trace Node Attributes

| Field | Type | Description |
|---|---|---|
| `trace_id` | `str` | Unique sequential trace identifier (`trc-0001`) |
| `parent_trace_id` | `Optional[str]` | Direct parent trace node identifier |
| `rule_id` | `Optional[str]` | Declarative statutory rule identifier |
| `evaluation_order` | `int` | 1-based sequential evaluation index |
| `node_type` | `str` | AST node type (`logical`, `comparison`, etc.) |
| `operator` | `str` | Operator applied (`AND`, `GTE`, `EQ`, etc.) |
| `field_path` | `Optional[str]` | Context field evaluated |
| `truth_value` | `RuleTruthValue` | Tri-state outcome (`TRUE`, `FALSE`, `UNKNOWN`) |
| `actual_value` | `Any` | Resolved value from citizen facts |
| `expected_value` | `Any` | Policy benchmark value |
| `missing_fields` | `List[str]` | Required fields missing from context |
| `explanation_en` | `str` | Faithful English explanation |
| `explanation_hi` | `str` | Faithful Hindi explanation |
| `source_clause` | `Optional[str]` | Statutory clause citation |
| `evidence_reference`| `Optional[str]` | Associated document/claim evidence ID |
| `evidence_status` | `Optional[str]` | Evidence state (`PENDING`, `VERIFIED`, etc.) |
| `family_member_context`| `Optional[dict]` | Contextual scope attributes (e.g. role, index) |

---

## 5. Information Gap Blockers

When an evaluation cannot proceed to a definitive `ELIGIBLE` or `INELIGIBLE` state due to missing facts or unverified evidence, the engine emits structured, actionable blockers.

### 5.1 Blocker Taxonomy

| Category | Enum Value | Description | Action Required |
|---|---|---|---|
| Missing Field | `MISSING_FIELD` | Mandatory context attribute is absent or null | Prompt citizen to provide fact |
| Unresolved Evidence | `UNRESOLVED_EVIDENCE` | Required supporting document is missing | Upload certified document |
| Verification Required | `VERIFICATION_REQUIRED` | Document uploaded but pending official verification | Administrative verification |
| Insufficient Info | `INSUFFICIENT_INFORMATION` | Ambiguous aggregate or collection predicate | Clarify multi-entity attributes |
| Manual Review | `MANUAL_REVIEW_REQUIRED` | Exceptional statutory condition requires officer review | Caseworker assignment |

### 5.2 Deterministic Blocker Construction

Blockers are extracted systematically from AST nodes that evaluated to `UNKNOWN`:
- `blocker_schema_version`: Schema version of the blocker model (`"1.0.0"`)
- `code`: Deterministic identifier (e.g., `BLOCKER_MISSING_LAND_AREA_HECTARES`)
- `field_path`: Fully qualified dot-notation fact path
- `category`: Categorical blocker type
- `message_en`: Actionable user-facing guidance in English
- `message_hi`: Actionable user-facing guidance in Hindi
- `evidence_reference`: Optional link to related evidence record

---

## 6. Bilingual Explanation Strategy

Rule explanations convey identical factual meaning in both English and Hindi without revealing private information.

### 6.1 Semantic Fidelity Matrix

| Truth Value | English Detail Pattern | Hindi Detail Pattern | Factual Information Preserved |
|---|---|---|---|
| `TRUE` | "Evaluated operator '{op}' successfully on '{field_path}'. Found: {actual}." | "फ़ील्ड '{field_path}' पर ऑपरेटर '{op}' सफलतापूर्वक पूरा हुआ। प्राप्त मान: {actual}।" | Field path, operator, actual value |
| `FALSE` | "Failed condition for '{field_path}' using operator '{op}'. Found: {actual}, Expected: {expected}." | "फ़ील्ड '{field_path}' पर ऑपरेटर '{op}' की शर्त पूरी नहीं हुई। प्राप्त मान: {actual}, अपेक्षित: {expected}।" | Field path, operator, actual value, expected value |
| `UNKNOWN` | "Cannot determine condition because required information is missing or unresolved: {missing_fields}." | "शर्त का निर्धारण नहीं हो सका क्योंकि आवश्यक जानकारी अनुपलब्ध या अनिर्धारित है: {missing_fields}।" | Missing field names |

Explanations are strictly informational and generated after deterministic evaluation; they never feed back into or alter the engine's logical decision.

---

## 7. Separation of Eligibility Logic and Evidence Verification

A foundational principle of YogyataMitra is that **Eligibility Logic** and **Evidence Verification** are independent, orthogonal dimensions:

1. **Eligibility Evaluation Dimension**:
   - Assesses statutory rule satisfaction against asserted facts.
   - States: `ELIGIBLE`, `INELIGIBLE`, `INSUFFICIENT_INFORMATION`, `VERIFICATION_REQUIRED`, `MANUAL_REVIEW_REQUIRED`.
   - Independent of document authentication, file uploads, or OCR confidence.

2. **Evidence Verification Dimension**:
   - Assesses the procedural validity and authenticity of submitted proof.
   - States: `PENDING`, `VERIFIED`, `REJECTED`, `EXPIRED`.
   - Carried as metadata on trace nodes (`evidence_reference`, `evidence_status`, `verification_reference`).

### Cross-Dimension Independence Matrix

| Statutory Facts | Evidence Status | Resulting Eligibility | Resulting Evidence State | Meaning |
|---|---|---|---|---|
| Qualifies (`age >= 18` $\rightarrow$ `TRUE`) | `PENDING` | `ELIGIBLE` | `PENDING` | Statutorily qualified; awaiting administrative document verification. |
| Qualifies (`age >= 18` $\rightarrow$ `TRUE`) | `VERIFIED` | `ELIGIBLE` | `VERIFIED` | Fully entitled with verified proof. |
| Qualifies (`age >= 18` $\rightarrow$ `TRUE`) | `REJECTED` | `ELIGIBLE` | `REJECTED` | Statutorily meets condition, but uploaded document failed authentication. |
| Disqualified (`age < 18` $\rightarrow$ `FALSE`) | `VERIFIED` | `INELIGIBLE` | `VERIFIED` | Authenticated proof confirms applicant is statutorily ineligible. |
| Missing fact | `PENDING` | `INSUFFICIENT_INFORMATION` | `PENDING` | Cannot evaluate condition; document not yet verified. |

---

## 8. Audit Evaluation Record & Immutability Architecture

The platform implements multi-tiered immutability guarantees.

### 8.1 In-Memory Immutability Guarantees

1. **Frozen Record Container**: `AuditEvaluationRecord` is configured with `ConfigDict(frozen=True)`. Attempting to modify attributes (e.g. `record.final_result = ...`) raises a validation error.
2. **Deep Input Isolation**: When `create_audit_evaluation_record` is invoked, `input_data` is deep-copied (`copy.deepcopy`). Subsequent mutations to the caller's input dictionary cannot alter the snapshot.
3. **Frozen Snapshot Data**: `InputSnapshot.data` is recursively converted into `FrozenSnapshotDict` and immutable tuples. Any attempt to modify top-level or nested dictionary keys (`snapshot.data["key"] = val`) raises `TypeError: Cannot mutate immutable audit snapshot data`.

### 8.2 Application-Level Append-Only Guarantee

- The application layer exposes no update or deletion endpoints or methods for evaluation traces.
- The `EvaluationTrace` model has no modification methods; once created, it is treated as append-only history.

### 8.3 Database-Level Mutability Distinction

> [!NOTE]
> **Database Immutability Scope**:
> Currently, the PostgreSQL `evaluation_traces` table is physically mutable at the SQL database layer if direct SQL `UPDATE` or `DELETE` commands are executed with database administrative credentials. The system does not currently enforce a database trigger or role-level `REVOKE UPDATE, DELETE ON evaluation_traces`. Immutability is currently guaranteed at the in-memory object and application service layers. Future infrastructure hardening may apply database-level permissions or triggers.

---

## 9. Historical Reproducibility Protocol

To audit or dispute any past welfare entitlement determination:

1. **Fetch Audit Record**: Retrieve the stored `EvaluationTrace` row from PostgreSQL.
2. **Verify Input Integrity**: Recompute `compute_input_snapshot_hash(input_snapshot_json["data"], evaluation_date)`. Assert equality with `input_snapshot_json["snapshot_hash"]`.
3. **Verify Policy Integrity**: Lookup the statutory `RuleSet` associated with `policy_version_id`. Recompute `compute_canonical_rule_hash(ruleset.rule_definition)`. Assert equality with `evaluation_traces.rule_definition_hash`.
4. **Re-Execute Evaluator**: Execute `DeterministicEvaluator().evaluate(ruleset.rule_definition, EvaluationContext(data=snapshot.data, evaluation_date=record.evaluation_date))`.
5. **Bit-for-Bit Verification**: Assert that re-evaluated `overall_result`, `root_truth_value`, and individual node truth values match the historical record exactly.

---

## 10. Security & Privacy Audit Findings

- **Zero Insecure Code Execution**: Verified zero occurrences of `eval()`, `exec()`, `compile()`, `__import__()`, `subprocess`, `os.system`, `requests`, `urllib`, `httpx`, or `socket` in engine and explainability modules.
- **Zero Scheme Coupling**: Verified zero references to `PM-KISAN`, `Sukanya`, `SSY`, `farmer`, `girl child`, or `landholding` in engine or services layers.
- **PII Sanitation**: All citizen context fields are treated as abstract dictionary paths. Explanations do not print sensitive government IDs or personal contact details.
- **Schema Version Persistence**: All 6 schema version constants (`TRACE_SCHEMA_VERSION`, `EXPLANATION_SCHEMA_VERSION`, `AUDIT_SCHEMA_VERSION`, `BLOCKER_SCHEMA_VERSION`, `PROVENANCE_SCHEMA_VERSION`, `EVALUATOR_VERSION`) are explicitly persisted inside the database record.
