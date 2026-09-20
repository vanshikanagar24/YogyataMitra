# YogyataMitra — Architectural Boundary: Citizen Layer vs Authorized Auditor Layer

**Document Version:** 1.0.0  
**Phase:** Phase 13 (Policy Transparency, Provenance & Audit UX Separation)  
**Status:** Approved Architectural Standard  
**Project:** YogyataMitra Platform (`D:\YogyataMitra`)  

---

## 1. Executive Summary

YogyataMitra provides deterministic entitlement evaluation and policy verification for Government of India welfare schemes. To uphold both **citizen usability** and **rigorous administrative auditability**, the platform enforces a strict architectural boundary separating the **Citizen Layer** from the **Authorized Auditor Layer**.

- The **Citizen Layer** is designed for respectful, plain-language, bilingual (English/Hindi) transparency. It presents authoritative scheme rules, historical timelines, plain explainability, and official Gazette citations without exposing internal technical artifacts, cryptographic hashes, or database keys.
- The **Authorized Auditor Layer** is designed for administrative oversight, statutory compliance verification, and forensic reproducibility. It records immutable canonical SHA-256 rule hashes, AST execution traces, frozen fact snapshots, and evaluation timestamps.

---

## 2. The Architectural Boundary

```
+-----------------------------------------------------------------------------------+
|                                  CITIZEN LAYER                                    |
|  - Plain-Language Explanations (Bilingual English & Hindi)                        |
|  - Official Ministry Gazette Titles & Authoritative Links                         |
|  - Chronological Policy Version Timelines (Current, Previous, Earlier)            |
|  - Respectful Five-Outcome Determination & Next Actions Guidance                  |
|  - Session-Based Recent Evaluation History (Zero Mandatory UUIDs)                |
+-----------------------------------------+-----------------------------------------+
                                          |
                        ARCHITECTURAL FIREWALL & VIEW MODELS
                     (Strict Anti-Leakage Serialization Boundary)
                                          |
+-----------------------------------------v-----------------------------------------+
|                             AUTHORIZED AUDITOR LAYER                              |
|  - Canonical Rule Definition Cryptographic Hashes (SHA-256)                       |
|  - Exact Abstract Syntax Tree (AST) Ruleset Nodes & Schemas                       |
|  - Disaggregated Rule Execution Traces & Node Truth Values                        |
|  - Evaluation Date (Statutory Enactment) vs Execution Timestamp (Runtime)         |
|  - Frozen JSON Fact Snapshots & Verification Event Timestamps                    |
|  - Database Internal Primary Keys (UUIDv4)                                        |
+-----------------------------------------------------------------------------------+
```

---

## 3. Data Separation Invariants & Non-Leakage Matrix

The following table defines the mandatory data separation invariants between layers:

| Data Field / Concept | Citizen Layer (`CitizenPolicySummary` / `CitizenEvaluationExplanation`) | Auditor Layer (`AuditPolicyDetails` / `AuditEvaluationDetails`) | Enforcing Mechanism |
| :--- | :--- | :--- | :--- |
| **Canonical Rule Hash** | **STRICTLY PROHIBITED** (Zero SHA-256 displayed) | **MANDATORY** (64-character hex SHA-256) | Sanitized View Models, Frontend regex tests |
| **Internal Database IDs** | **STRICTLY PROHIBITED** (No UUIDs in normal citizen flow) | **MANDATORY** (`id`, `evaluation_id`, `journey_id`) | UI masking, session-based recent history |
| **AST Node Structure** | **STRICTLY PROHIBITED** (No `node_type`, `predicate`, `root_rule`) | **MANDATORY** (Full JSON AST tree) | DTO separation, `rulePresentation.ts` |
| **Field Names** | Plain-language labels (e.g., "Cultivable Land Ownership") | Raw dot-notation (e.g., `family.owns_cultivable_land`) | `claimPresentation.ts`, `rulePresentation.ts` |
| **Rule Identifiers** | Plain titles (e.g., "Income Tax Payer Exclusion") | Statutory codes (e.g., `PMKISAN-EXCL-INCOME-TAX`) | `RULE_PRESENTATION_MAP` in `rulePresentation.ts` |
| **Policy Provenance** | Ministry guidelines title, gazette citation, public URL | Schema version, ruleset version, raw source identifier | `PolicyVersionDetailResponse` |
| **Assessment Date** | Displayed as statutory effective date for eligibility | Displayed alongside calculation execution timestamp | `ExplainabilityView`, `AuditHistoryPage` |

---

## 4. Evaluation Date vs Execution Timestamp

A critical architectural distinction maintained across YogyataMitra is the separation between:

1. **Statutory Assessment Date (`evaluation_date`)**:
   - The date against which eligibility is determined (format `YYYY-MM-DD`).
   - Determines **which statutory policy version** and ruleset were legally effective in the Gazette of India on that date.
   - For example, an assessment conducted for a date in 2018 evaluates against PM-KISAN `v1.0-2018` (2.0 hectare ceiling), whereas an assessment for a date in 2024 evaluates against `v3.0-2023` (universal landholding).

2. **Calculation Execution Timestamp (`created_at`)**:
   - The ISO 8601 UTC timestamp recording exactly when the deterministic evaluation engine executed the computation in software.
   - Used for administrative audit logging, system performance monitoring, and forensic immutability.

Citizens are provided with the clear notice:
> *"Eligibility is assessed using the scheme rules applicable to the assessment date. When assessing eligibility for a past date, the specific statutory rules, ceilings, and guidelines effective during that period are automatically applied."*

---

## 5. Cryptographic Policy Integrity (SHA-256)

Every statutory ruleset version is materialized with an immutable SHA-256 canonical hash computed over the normalized AST definition:

| Scheme | Version Code | Effective Period | Canonical Rule Hash (SHA-256) |
| :--- | :--- | :--- | :--- |
| **PM-KISAN** | `v1.0-2018` | 2018-12-01 → 2019-03-31 | `facc14b3388802e3d0ef0c4134414459500dc9a9be7e0dc62ddecc082b47e9d2` |
| **PM-KISAN** | `v2.0-2019` | 2019-04-01 → 2022-12-31 | `55fe76d5bd441cbe4a0ceddb45ddbf253f5f059683570bd29096bf9b972ad6d8` |
| **PM-KISAN** | `v3.0-2023` | 2023-01-01 → Present | `7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6` |
| **SSY** | `v1.0-2016` | 2016-03-18 → 2019-12-11 | `ffb3c2dae2cf283d3b0b41c8dfd87267cfff29e30fa898ee1ca93fde19419ae7` |
| **SSY** | `v2.0-2019` | 2019-12-12 → 2024-03-31 | `3dbd7d9d1f87ae7ce5064143333bd8ac969b14e927ac6cb7e6206f1777288669` |
| **SSY** | `v3.0-2024` | 2024-04-01 → Present | `5fa83b3d5b0177ca9d0983e46213d11e92883993f2f7a5abc9fe43fb25b9ff28` |

These hashes are verified byte-for-byte during server startup and unit testing. In the Citizen Layer, they are omitted to prevent cognitive overload; in the Auditor Layer (`AuditPolicyView`), they are prominently verified.

---

## 6. Type Definitions & Software Interfaces

The contract between layers is formalized in `frontend/src/types/audit.ts`:

- `CitizenPolicySummary`: Plain-language policy version summary with timeline status (`CURRENT`, `PREVIOUS`, `EARLIER`), statutory descriptions, and official links.
- `CitizenEvaluationExplanation`: Five-outcome plain-language explanation without raw rule codes or field paths.
- `AuditPolicyDetails`: Technical metadata including canonical hash, ruleset schema version, and database IDs.
- `AuditEvaluationDetails`: Execution timestamp vs assessment date, input snapshot, and AST execution trace.
- `AuditEvidenceDetails`: Artifact verification audit pointers and verification officer IDs.
- `AuditTraceDetails`: Cryptographic trace reproducibility and AST node evaluations.

---

## 7. Future Implementation Scope Boundary

In strict accordance with Phase 13 specifications:
- **Phase 13 establishes**: The architectural foundation, view models, centralized plain-language rule presentation, citizen assessment history, and isolated `AuditPolicyView` / `CitizenPolicyView` components.
- **Reserved for Future Phases**: Officer authentication (e.g. MeriPehchan / Jan Parichay), role-based access control (RBAC), administrative workflow approvals, and official departmental sanction management.
