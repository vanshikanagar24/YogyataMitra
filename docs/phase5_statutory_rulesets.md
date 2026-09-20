# YogyataMitra — Phase 5 Specification: Statutory Welfare Rulesets (PM-KISAN & SSY)

## 1. Executive Summary & Statutory Authority

Phase 5 transitions YogyataMitra from generic abstract evaluation into authoritative statutory welfare entitlement reasoning by materializing the formal rulesets of two flagship Indian Central Sector welfare schemes:

1. **Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)** — Ministry of Agriculture and Farmers Welfare (MoAFW)
2. **Sukanya Samriddhi Account Scheme (SSY)** — Ministry of Finance (MoF), Department of Economic Affairs (DEA)

### Strict Architectural Boundaries

- **Zero Scheme-Specific Code in Engine**: The core rule engine (`backend/app/engine/`) remains 100% provider-neutral and generic. No scheme names, agrarian terms, or account concepts are hardcoded in engine logic.
- **Declarative AST Representation**: All statutory criteria, exclusions, age limits, and exceptions are authored as strict declarative AST JSON structures under `schemes_data/`.
- **Statutory Provenance**: Every rule node directly cites its legal source instrument, gazette notification, and statutory clause.
- **Dual-Language Statutory Explanations**: Every rule contains legally faithful English (`description_en`) and Hindi (`description_hi`) descriptions.
- **Canonical SHA-256 Hashing**: Rulesets are cryptographically sealed. Any mutation alters the 64-character hash, preventing silent tampering.
- **Strictly Two Schemes**: Only PM-KISAN and SSY are materialized in Phase 5. No third scheme is created.

---

## 2. Statutory Instruments & Chronological Policy Versions

### A. PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)

| Version Code | Effective From | Effective To | Statutory Source Document | Reference / Gazette | Core Policy Delta |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **v1.0-2018** | 2018-12-01 | 2019-03-31 | PM-KISAN Operational Guidelines (Feb 2019) | MoAFW 1-1/2019-Credit-I | Small & Marginal Farmers (SMF) only: strict **<= 2.0 hectare** cultivable landholding ceiling. 7 statutory exclusion categories. |
| **v2.0-2019** | 2019-04-01 | 2022-12-31 | Revised PM-KISAN Guidelines (Cabinet Decision May 2019) | MoAFW Extension Order | Land ceiling **removed** (all landholding farmer families eligible). Introduced **01.02.2019 cut-off date** for land transfer, with exception for succession on death. |
| **v3.0-2023** | 2023-01-01 | *Present* | PM-KISAN Operational Guidelines & e-KYC Mandates 2023 | MoAFW Operative Manual | Retains universal landholding and 01.02.2019 cut-off/succession rule; incorporates statutory exclusion enforcement with operational e-KYC metadata. |

### B. SSY (Sukanya Samriddhi Account)

| Version Code | Effective From | Effective To | Statutory Source Document | Reference / Gazette | Core Policy Delta |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **v1.0-2016** | 2016-03-18 | 2019-12-11 | Sukanya Samriddhi Account Rules, 2016 | GSR 323(E), Min. of Finance | Girl child <= 10 years, Indian resident, natural/legal guardian, max 2 accounts per family (triplet/twin exception). Min deposit ₹1,000. |
| **v2.0-2019** | 2019-12-12 | 2024-03-31 | Sukanya Samriddhi Account Scheme, 2019 | GSR 914(E), Min. of Finance | Re-enacted under Government Savings Promotion Act. Retains core eligibility; min deposit reduced to ₹250 (stored in operational metadata). |
| **v3.0-2024** | 2024-04-01 | *Present* | Consolidated Post Office Savings Guidelines 2024 | MOF-DEA-SSY-2024 | Consolidated operational norms; re-affirmed strict natural/court guardian verification and twin exception affidavit norms. |

---

## 3. Statutory Policy Traceability Matrix

| Scheme | Policy Version | Rule ID | Source Document | Statutory Clause | Operator / Node Type | Target Field / Condition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PM_KISAN** | `v1.0-2018` | `PMKISAN-V1-ROOT` | Guidelines 2018 | Paras 2 & 3 | `AND` (Logical) | Conjunction of land, ceiling & non-exclusion |
| PM_KISAN | `v1.0-2018` | `PMKISAN-LAND-OWNERSHIP` | Guidelines 2018 | Para 2.1 | `EQ` (Comparison) | `family.owns_cultivable_land == True` |
| PM_KISAN | `v1.0-2018` | `PMKISAN-HIST-LAND-CEILING-2HA` | Guidelines 2018 | Para 2.1 | `LTE` (Comparison) | `family.total_land_area_hectares <= 2.0` |
| PM_KISAN | `v1.0-2018` | `PMKISAN-NON-INSTITUTIONAL` | Guidelines 2018 | Para 3.1 | `EQ` (Comparison) | `family.is_institutional_landholder == False` |
| PM_KISAN | `v1.0-2018` | `PMKISAN-EXCL-CONSTITUTIONAL` | Guidelines 2018 | Para 3.2(a) | `EQ` (Comparison) | `family.has_constitutional_post_holder == False` |
| PM_KISAN | `v1.0-2018` | `PMKISAN-EXCL-REPRESENTATIVE` | Guidelines 2018 | Para 3.2(b) | `EQ` (Comparison) | `family.has_public_representative == False` |
| PM_KISAN | `v1.0-2018` | `PMKISAN-EXCL-GOVT-EMPLOYEE` | Guidelines 2018 | Para 3.2(c) | `EQ` (Comparison) | `family.has_disqualified_government_employee == False` |
| PM_KISAN | `v1.0-2018` | `PMKISAN-EXCL-PENSIONER-10K` | Guidelines 2018 | Para 3.2(d) | `EQ` (Comparison) | `family.has_pensioner_above_ten_thousand == False` |
| PM_KISAN | `v1.0-2018` | `PMKISAN-EXCL-INCOME-TAX` | Guidelines 2018 | Para 3.2(e) | `EQ` (Comparison) | `family.has_income_tax_payer == False` |
| PM_KISAN | `v1.0-2018` | `PMKISAN-EXCL-PROFESSIONAL` | Guidelines 2018 | Para 3.2(f) | `EQ` (Comparison) | `family.has_registered_practicing_professional == False` |
| **PM_KISAN** | `v2.0-2019` | `PMKISAN-V2-ROOT` | Guidelines 2019 | Paras 2 & 3 | `AND` (Logical) | Conjunction of land, cut-off & non-exclusion (no ceiling) |
| PM_KISAN | `v2.0-2019` | `PMKISAN-LAND-OWNERSHIP` | Guidelines 2019 | Para 2 | `EQ` (Comparison) | `family.owns_cultivable_land == True` |
| PM_KISAN | `v2.0-2019` | `PMKISAN-LAND-CUTOFF-2019` | Guidelines 2019 | Para 2.2 | `OR` (Logical) | Land pre-cutoff OR bona-fide succession |
| PM_KISAN | `v2.0-2019` | `PMKISAN-LAND-PRE-CUTOFF` | Guidelines 2019 | Para 2.2 | `EQ` (Comparison) | `land.transferred_after_cutoff == False` |
| PM_KISAN | `v2.0-2019` | `PMKISAN-LAND-SUCCESSION-ON-DEATH` | Guidelines 2019 | Para 2.2 Proviso | `AND` (Logical) | Acquisition via succession AND previous owner deceased |
| PM_KISAN | `v2.0-2019` | `PMKISAN-EXCL-CONSTITUTIONAL..PROF` | Guidelines 2019 | Para 3.2 | `EQ` (Comparison) | All 7 statutory exclusions enforced |
| PM_KISAN | `v2.0-2019` | `PMKISAN-EXCL-NRI` | DA&FW Guidelines 2020 | Operative Guidelines (29.03.2020) | `EQ` (Comparison) | `family.is_nri == False` |
| **PM_KISAN** | `v3.0-2023` | `PMKISAN-V3-ROOT` | Guidelines 2023 | Operational Norms | `AND` (Logical) | Conjunction of land, cut-off, non-exclusion (incl. NRI) + e-KYC metadata |
| PM_KISAN | `v3.0-2023` | `PMKISAN-EXCL-NRI` | DA&FW Guidelines 2020 | Operative Guidelines (29.03.2020) | `EQ` (Comparison) | `family.is_nri == False` |
| **SSY** | `v1.0-2016` | `SSY-V1-ROOT` | GSR 323(E) | Rules 3 & 4 | `AND` (Logical) | Conjunction of gender, residency, age, guardian & limit |
| SSY | `v1.0-2016` | `SSY-BENEFICIARY-GENDER` | GSR 323(E) | Rule 3 | `EQ` (Comparison) | `beneficiary.gender == "FEMALE"` |
| SSY | `v1.0-2016` | `SSY-BENEFICIARY-RESIDENT` | GSR 323(E) | Rule 3 | `EQ` (Comparison) | `beneficiary.is_indian_resident == True` |
| SSY | `v1.0-2016` | `SSY-AGE-LIMIT-10` | GSR 323(E) | Rule 4(1) | `HAS_NOT_ATTAINED_AGE` (Temporal) | `beneficiary.date_of_birth` as of `account.opening_date` (< 10 yrs) |
| SSY | `v1.0-2016` | `SSY-ONE-ACCOUNT-PER-CHILD` | GSR 323(E) | Rule 4(2) | `EQ` (Comparison) | `account.is_first_account_for_child == True` |
| SSY | `v1.0-2016` | `SSY-GUARDIAN-ELIGIBILITY` | GSR 323(E) | Rule 2(d) & 4(1) | `OR` (Logical) | `guardian.is_natural_guardian` OR `guardian.is_court_appointed_legal_guardian` |
| SSY | `v1.0-2016` | `SSY-FAMILY-ACCOUNT-LIMIT` | GSR 323(E) | Rule 4(3) | `OR` (Logical) | Active accounts < 2 OR multiple birth exception |
| **SSY** | `v2.0-2019` | `SSY-V2-ROOT` | GSR 914(E) | Paras 3 & 4 | `AND` (Logical) | Re-enacted statutory criteria under 2019 Rules |
| **SSY** | `v3.0-2024` | `SSY-V3-ROOT` | GSR 914(E) as amended; MoF Order F.No. 1/3/2024-NS | Paras 3 & 4 | `AND` (Logical) | Consolidated 2019 criteria as amended under 2024 MoF Guidelines |

---

## 4. Canonical Cryptographic Rule Hashing

Policy definitions are cryptographically sealed using deterministic canonical SHA-256 digests (`compute_canonical_rule_hash`):

1. **Structural Invariant Preservation**: Normalization retains `None`, empty lists `[]`, empty dictionaries `{}`, and empty strings `""`.
2. **Key Ordering Neutrality**: Dictionary keys are recursively sorted (`sort_keys=True`), ensuring formatting variations do not alter the hash.
3. **Pydantic Validation Alignment**: Raw AST dictionaries are parsed through strict Pydantic AST models so that schema defaults align across environments.
4. **Collision Resistance**: Adversarial structures with identical key lengths or nested empties produce strictly distinct hashes.

### Canonical Hashes for Phase 5 Policies

| Scheme Code | Version Code | Canonical SHA-256 Rule Hash |
| :--- | :--- | :--- |
| `PM_KISAN` | `v1.0-2018` | `facc14b3388802e3d0ef0c4134414459500dc9a9be7e0dc62ddecc082b47e9d2` |
| `PM_KISAN` | `v2.0-2019` | `55fe76d5bd441cbe4a0ceddb45ddbf253f5f059683570bd29096bf9b972ad6d8` |
| `PM_KISAN` | `v3.0-2023` | `7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6` |
| `SSY` | `v1.0-2016` | `ffb3c2dae2cf283d3b0b41c8dfd87267cfff29e30fa898ee1ca93fde19419ae7` |
| `SSY` | `v2.0-2019` | `3dbd7d9d1f87ae7ce5064143333bd8ac969b14e927ac6cb7e6206f1777288669` |
| `SSY` | `v3.0-2024` | `5fa83b3d5b0177ca9d0983e46213d11e92883993f2f7a5abc9fe43fb25b9ff28` |

---

## 5. Ingestion & Materialization Services

### `policy_loader.py`

- **Filesystem Discovery**: Scans `schemes_data/<scheme_code>/scheme.json` and `schemes_data/<scheme_code>/policies/*.json`.
- **AST Validation**: Validates every rule through `validate_ast()` prior to database interaction.
- **Idempotent Loading**: If a `PolicyVersion` with the exact `version_code` and matching `rule_definition_hash` exists, the entity is retained without re-inserting.
- **Strict Immutability**: If an existing version code is encountered with a conflicting hash, `PolicyHashConflictError` is raised. Policies are historical records and cannot be overwritten in place.

### `policy_selector.py`

- **Date-Bounded Generic Selection**: Queries `PolicyVersion` where `effective_from <= evaluation_date` and `(effective_to IS NULL OR effective_to >= evaluation_date)`.
- **Precedence Ordering**: Resolves latest applicable generation by ordering by `effective_from DESC`.
- **Zero Scheme Coupling**: The selector relies purely on database date intervals and scheme codes.

---

## 6. Strong Kleene UNKNOWN Semantics

Statutory welfare evaluations strictly abide by 3-valued Kleene logic ($K_3$):

- **Missing Facts**: If a statutory fact is not supplied (e.g. `beneficiary.date_of_birth` or `land.transferred_after_cutoff`), the evaluating node yields `UNKNOWN`.
- **Dominance Rules**:
  - `FALSE AND UNKNOWN` $\rightarrow$ `FALSE` (disqualification dominates missing information).
  - `TRUE AND UNKNOWN` $\rightarrow$ `UNKNOWN` (cannot confirm entitlement without required evidence).
  - `TRUE OR UNKNOWN` $\rightarrow$ `TRUE` (qualifying alternative confirms entitlement).
- **Blocker Generation**: Every `UNKNOWN` node is collected into actionable `InformationGapBlocker` records with specific field paths and plain-language guidance in English and Hindi.

---

## 7. Separation of Eligibility Logic from Operational Rules

Statutory schemes specify operational and administrative requirements that do not govern baseline entitlement:

- **SSY Minimum Initial Deposit**: ₹1,000 under 2016 rules; ₹250 under 2019/2024 rules.
- **PM-KISAN e-KYC Verification & Land Seeding**: Required for operational disbursement.
- **SSY Maturity Period**: 21 years from account opening or marriage after age 18.

**Architectural Placement**: These operational requirements are partitioned into `metadata.operational_rules` inside the policy version files. They are available for downstream workflow orchestration (Phase 6/7) without polluting the pure eligibility AST with banking or disbursement logic.

---

## 8. Verification & Quality Gate Results

### Live Test Collection Breakdown (Verified by Pytest)

The live test suite was verified using `pytest --collect-only -q` and `pytest -q`. Pytest collected and passed exactly **111** tests across all modules in the baseline audit:

| Test Suite | Collected Tests | Status |
| :--- | :---: | :---: |
| `test_database_config.py` | 4 | PASSED |
| `test_domain_models.py` | 8 | PASSED |
| `test_engine_ast.py` | 15 | PASSED |
| `test_engine_evaluator.py` | 20 | PASSED |
| `test_explainability_audit.py` | 19 | PASSED |
| `test_health.py` | 3 | PASSED |
| `test_migrations.py` | 2 | PASSED |
| `test_statutory_rulesets.py` | 40 | PASSED |
| **TOTAL (Baseline Audit)** | **111** | **ALL PASSED** |

Following the approved remediation of DEF-01 (adding dedicated test `test_ak_pm_kisan_nri_exclusion_semantics`), the test suite collects and passes **112** tests (`test_statutory_rulesets.py` = 41).

- **Alembic Database State**: Schema synchronized at `c5128b89cf97 (head)`, verified with `alembic check` (zero schema drift).
- **Policy Loader Idempotency**: Materialization creates 0 duplicates and retains all 6 versions.
- **Conflicting Hash Protection**: Fails loudly with `PolicyHashConflictError` upon hash mutation.
- **Evaluator Neutrality**: Grep audit across `backend/app/engine/` confirms zero occurrences of scheme-specific terms.
