# YOGYATAMITRA — FINAL PHASE A–J ACADEMIC & DEMONSTRATION READINESS REPORT

**Platform**: YogyataMitra — Deterministic Welfare Entitlement Reasoning & Verification Engine  
**Repository**: `D:\YogyataMitra`  
**Current Milestone**: Phases A–J Complete & Frozen  
**Independent Audit Verdict**: `PHASE J COMPLETE & FROZEN` (0 Critical, 0 High Findings)  
**Next Phase**: Phase K (NOT STARTED)  
**Scope**: Academic Readiness, Defense/Viva Documentation, Demonstration Architecture & Reproducibility Review  

---

## 1. Executive Summary

YogyataMitra is an academic research platform engineered to investigate and demonstrate deterministic statutory welfare entitlement reasoning and structured evidence verification. In contemporary digital public administration, delivery of social welfare often encounters challenges arising from manual discretionary administrative delays on one hand, and experimental, probabilistic artificial intelligence (LLM/GenAI) approaches on the other, which can introduce unverified assertions, inconsistent outcomes, and lack of auditable traceability.

YogyataMitra investigates a structured, symbolic computing paradigm: **Deterministic Symbolic Entitlement Reasoning with Structured Evidence Verification**. The design invariant of the system is formulated as:

$$\text{Verified Facts} + \text{Bound Policy Version} + \text{Deterministic AST Rule Engine} = \text{Evaluation Result}$$

Under this architectural constraint, **YogyataMitra does not use a Large Language Model (LLM) or generative artificial intelligence model as the final entitlement evaluator**. No dynamic heuristic, `eval()`, or `exec()` call is used to compute eligibility results in the live evaluation path. The engine deterministically evaluates the encoded policy rules using Abstract Syntax Tree (AST) representations operating over Strong Kleene 3-valued propositional logic ($\text{TRUE}$, $\text{FALSE}$, $\text{UNKNOWN}$).

### Legal & Institutional Boundary
> [!IMPORTANT]
> **YogyataMitra is an academic research implementation that evaluates encoded policy rules deterministically. It does not replace statutory interpretation, administrative decision-making, or judicial review.**
>
> The system does not possess delegated statutory authority, does not establish legal entitlement under any Central or State enactment, and is not an officially certified or approved deployment of the Government of India. Independent audit findings reported in this document are project audit results and do not constitute government certification or legal certification.

### Evidentiary Classification of Claims
To ensure academic integrity, this report explicitly distinguishes between:
1. **Directly Verified Repository Facts**: Properties verified directly from the current repository codebase, schema definitions, migration history, policy files, and local test executions (e.g., migration head `d4e5f6a7b8c9`, linear chain of 14 migrations, 14 database policy versions with SHA-256 rule definition hashes, 212 passing A–J regression tests, 458 total collected backend tests, 137 passing frontend Jest tests).
2. **Independent Phase J Audit Results**: Outcomes recorded during the independent Phase J freeze audit (verdict `PHASE J COMPLETE & FROZEN`, 0 Critical, 0 High findings, and audit observations F-J-01, F-J-02, F-J-03).
3. **Project Design Claims**: Architectural hypotheses and engineering models evaluated during Phases A–J (e.g., pure AST traversal, claim/evidence separation, verification gate mechanics, Strong Kleene truth-value propagation).
4. **Limitations & Research Non-Claims**: Explicit academic boundaries confirming that YogyataMitra is not a government production platform, does not connect to live government databases, and produces system evaluation outcomes rather than legally binding orders.

### Project Milestone & Frozen Baseline

Phases A through J have completed implementation, testing, and independent freeze auditing:
- **Phase A**: Authentication & Role-Based Access Control (RBAC)
- **Phase B**: Citizen Workspace & Journey Lifecycle
- **Phase C**: Application Creation & Evidence Attachment
- **Phase D**: Officer Assignment, Workload Pools & SLA Engine
- **Phase E**: Evidence Verification & Clarification Cycle
- **Phase F**: Deterministic Evaluation & Decision Engine
- **Phase G**: Generic Policy-Driven Forms & Schema Registry
- **Phase H**: Ten Government Schemes & 40 Canonical Scenarios
- **Phase I**: Official Documents & Statutory Provenance Hardening
- **Phase J**: Production Hardening, Concurrency, Immutability & Demonstration Readiness

### Verified Final System Quality Metrics

| Subsystem | Metric | Verified Evidence (Repository & Audit) | Status |
| :--- | :--- | :--- | :--- |
| **Backend A–J Regression** | Pytest Execution | 212 passed / 212 tests across 10 files (117.2s) | **PASS** |
| **Backend Total Suite** | Pytest Collection | 458 passed / 458 tests (including core engine & authoring) | **PASS** |
| **Frontend Unit & Integration** | Jest Test Suites | 137 passed / 137 tests across 24 suites | **PASS** |
| **Frontend Type Safety** | TypeScript Compiler | 0 errors (`tsc --noEmit`) | **PASS** |
| **Frontend Code Quality** | ESLint Linter | 0 errors, 0 warnings (`next lint`) | **PASS** |
| **Production Build** | Next.js Engine | 33 routes compiled & statically optimized | **PASS** |
| **Database Migrations** | Alembic Migration Graph | Linear chain of 14 migrations, single head `d4e5f6a7b8c9` | **PASS** |
| **Scheme Coverage** | Government Schemes | 10 Central Welfare Schemes | **FROZEN** |
| **Policy Versions** | Statutory Policies | 14 Authoritative Versions in Database & Policy Registry | **FROZEN** |
| **Scenario Verification** | Canonical Scenarios | 40 / 40 Canonical Policy Scenarios Passed | **PASS** |
| **Phase J Dedicated E2E** | End-to-End Suite | 32 / 32 Passed (`test_phase_j_end_to_end.py`) | **PASS** |
| **Security Audit Findings** | Critical / High | 0 Critical, 0 High (Project Audit Results) | **VERIFIED** |

---

## 2. Final Architecture

The YogyataMitra architecture is structured across ten modular subsystems operating under role separation and statutory provenance. The system evaluates encoded policy rules and does not replace statutory, administrative, or judicial authority.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CITIZEN / OFFICER UI                            │
│                 Next.js 14 App Router (Bilingual En/Hi, Tailwind)           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS / JSON / JWT
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI BACKEND                                │
│  ┌────────────────────────┐  ┌───────────────────────┐  ┌────────────────┐  │
│  │   Auth / RBAC Filter   │  │ Citizen & Officer API │  │ Provenance API │  │
│  │ (JWT Bearer, 2 Roles)  │  │ (Journeys, Evidence)  │  │ (Audit, Sources│  │
│  └───────────┬────────────┘  └───────────┬───────────┘  └───────┬────────┘  │
│              │                           │                      │           │
│  ┌───────────▼───────────────────────────▼──────────────────────▼────────┐  │
│  │                  POLICY FORM & DISCOVERY REGISTRY                     │  │
│  │       (Generic Form Schemas, Ministry Metadata, Policy Binding)       │  │
│  └───────────────────────────────────────┬───────────────────────────────┘  │
│                                          │                                  │
│  ┌───────────────────────────────────────▼───────────────────────────────┐  │
│  │                       VERIFICATION GATE SERVICE                       │  │
│  │   (Filters unverified claims; verifies officer sign-off before eval)  │  │
│  └───────────────────────────────────────┬───────────────────────────────┘  │
│                                          │ Verified Facts Only              │
│  ┌───────────────────────────────────────▼───────────────────────────────┐  │
│  │                  DETERMINISTIC EVALUATION ENGINE                      │  │
│  │        (Pure AST Traverser, Strong Kleene 3-Valued Propositional      │  │
│  │         Logic, Rule Hash Invariant, Zero Evaluator Side-Effects)      │  │
│  └───────────────────────────────────────┬───────────────────────────────┘  │
│                                          │ EvaluationTrace                  │
│  ┌───────────────────────────────────────▼───────────────────────────────┐  │
│  │                 EXPLAINABILITY & AUDIT TRAIL SERVICE                  │  │
│  │     (Synthesizes human-readable bilingual explanations from AST;      │  │
│  │      Records append-only provenance events & immutable traces)        │  │
│  └───────────────────────────────────────┬───────────────────────────────┘  │
└──────────────────────────────────────┬───┴──────────────────────────────────┘
                                       │ Async SQLAlchemy 2.0
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            POSTGRESQL DATABASE                              │
│  - Journeys, Claims, Evidence, Officers, Assignments, Clarification Cycles   │
│  - Policy Versions, AST Rules, Official Sources, Documents, Provenance       │
│  - DB Trigger: trg_provenance_audit_events_immutable (Blocks UPDATE/DELETE)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1. Frontend Architecture
- **Framework**: Next.js 14 App Router with React Server and Client Components.
- **Language**: TypeScript (strict mode, zero build warnings).
- **Styling**: Tailwind CSS adhering to the Indian Government Web Guidelines tokens.
- **Internationalization (i18n)**: Bilingual interface supporting English (`en`) and Hindi (`hi`) across static navigation, dynamic form labels, help tooltips, and evaluation explanation cards.
- **Form Generation**: Dynamic schema-driven forms driven by backend `/api/v1/schemes/{code}/requirements` specifications. No hardcoded bypass forms exist in the citizen UI.

### 2.2. Backend Architecture
- **Framework**: FastAPI (Python 3.12) running asynchronous ASGI workers.
- **API Design**: Versioned RESTful endpoints (`/api/v1/`) with strict Pydantic v2 validation for all request payloads and response envelopes.
- **Dependency Injection**: Modular dependency trees (`get_db`, `get_current_user`, `get_current_officer`, `get_evaluation_service`) decoupling network transport, authorization, and business logic.

### 2.3. Database & Persistence Layer
- **Database Engine**: PostgreSQL with `asyncpg` asynchronous drivers (and SQLite compatibility for isolated in-memory unit tests).
- **ORM & Migrations**: SQLAlchemy 2.0 async sessions with Alembic versioning.
- **Migration Graph**: Single linear migration head (`d4e5f6a7b8c9`) spanning exactly 14 revisions without squashing, branching, or historical rewrite.
- **Database Triggers**: Native PostgreSQL triggers (`trg_provenance_audit_events_immutable`) enforcing database-level immutability on audit records.

### 2.4. Authentication & Role-Based Access Control (RBAC)
- **Token Format**: Stateless JSON Web Tokens (JWT) signed with HMAC-SHA256 (`HS256`).
- **User-Facing Roles**: Exactly two strictly segregated roles:
  1. `CITIZEN`: Can register, create applications, submit claims, upload evidence, view own journey status, and respond to clarifications.
  2. `OFFICER`: Can accept case assignments, inspect evidence artifacts, verify or reject claims, request clarifications, initiate evaluation, and view department-wide SLA metrics.
- **Zero Third Role**: No administrative or supervisor role can bypass statutory evaluation or inject unverified facts into the engine.

### 2.5. Citizen Application Workflow
The citizen application journey is managed by an explicit finite state machine with strictly validated transitions:

$$\text{DRAFT} \longrightarrow \text{SUBMITTED} \longrightarrow \text{UNDER\_REVIEW} \longrightarrow \text{READY\_FOR\_EVALUATION} \longrightarrow \text{EVALUATED} \longrightarrow \text{DECIDED}$$

An auxiliary clarification sub-cycle permits non-destructive remediation:
$$\text{UNDER\_REVIEW} \longleftrightarrow \text{CLARIFICATION\_REQUESTED}$$

### 2.6. Officer Workflow & SLA Management
- **Workload Routing**: Automatically routes submitted applications to scheme-specific officer pools or designated caseworkers based on availability and active load.
- **SLA Tracking**: Dynamic calculation of statutory processing deadlines with automatic escalation flags for breached service-level agreements.
- **Review Protocol**: Officers review individual claims against uploaded documentary evidence, attaching structured verification notes.

### 2.7. Deterministic Policy Engine
- **Engine Purity**: The rule evaluator (`backend/app/engine/evaluator/evaluator.py`) is side-effect-free and stateless.
- **Logic System**: Strong Kleene 3-valued propositional logic is used as an engineering mechanism for representing $\text{TRUE}$, $\text{FALSE}$, and $\text{UNKNOWN}$ when required factual information is incomplete. Missing or unverified attributes evaluate to `UNKNOWN` without raising unhandled exceptions or defaulting to false positives.
- **AST Nodes**: Expressive, composable nodes (`AndNode`, `OrNode`, `NotNode`, `ComparisonNode`) evaluating compound statutory conditions, threshold boundaries, and explicit exclusion criteria.

### 2.8. Evidence Verification & Verification Gate
- **Claim vs. Evidence Separation**: A *Claim* is an assertion of fact made by a citizen (e.g., `annual_income = 120000`). An *Evidence* is a verifiable artifact supporting that claim (e.g., `Income_Certificate_2024.pdf`).
- **Verification Gate**: The deterministic rule engine evaluates *only* claims that hold the status `ClaimStatus.VERIFIED`. Any claim in `CLAIMED`, `PENDING`, `REJECTED`, or `CLARIFICATION_REQUIRED` state is withheld from the facts context. If an essential statutory rule depends on an unverified claim, the evaluator resolves the condition to `UNKNOWN`, triggering `VERIFICATION_REQUIRED`.

### 2.9. Policy & Statutory Provenance
- Every statutory rule in the AST is cryptographically bound to an issuing ministry (`OfficialSource`), an official publication (`OfficialDocument`), an exact legal version (`DocumentVersion`), and a section/sub-clause citation (`RuleProvenance`).

### 2.10. Audit Trail & Immutability
- Every lifecycle transition, officer review action, verification status change, clarification message, and AST evaluation execution writes an append-only event record.
- PostgreSQL database triggers prevent any modification (`UPDATE`) or removal (`DELETE`) of audit log entries.

---

## 3. Final Requirement-to-Implementation Matrix

| Phase | Requirement Description | Implementing Component | API / Service / Module | Test Coverage | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A** | JWT Authentication & RBAC (Citizen & Officer roles) | `app.core.security`, `app.api.v1.auth` | `POST /api/v1/auth/login`, `POST /api/v1/auth/register` | `test_auth_phase_a.py` (10 tests) | **FROZEN** |
| **B** | Citizen Workspace & Application Lifecycle Management | `app.services.citizen_service`, `app.api.v1.citizen_applications` | `GET /api/v1/citizen/applications`, `POST /api/v1/citizen/applications` | `test_citizen_applications_phase_b.py` (8 tests) | **FROZEN** |
| **C** | Application Creation, Claim Submission & Evidence Upload | `app.models.journey`, `app.api.v1.journeys` | `POST /api/v1/journeys/{id}/claims`, `POST /api/v1/journeys/{id}/evidence` | `test_citizen_phase_c.py` (10 tests) | **FROZEN** |
| **D** | Officer Assignment, Pool Routing & SLA Tracking | `app.services.assignment_service`, `app.api.v1.officer` | `GET /api/v1/officer/queue`, `POST /api/v1/officer/assign` | `test_officer_assignment_phase_d.py` (10 tests) | **FROZEN** |
| **E** | Evidence Verification, Rejection & Clarification Workflow | `app.services.verification_service`, `app.api.v1.evidence` | `POST /api/v1/evidence/{id}/verify`, `POST /api/v1/clarifications` | `test_evidence_clarification_phase_e.py` (20 tests) | **FROZEN** |
| **F** | Deterministic AST Evaluation & Explainability Engine | `app.engine.evaluator`, `app.services.evaluation_service` | `POST /api/v1/evaluation/{journey_id}/evaluate` | `test_deterministic_evaluation_phase_f.py` (31 tests) | **FROZEN** |
| **G** | Generic Policy-Driven Forms & Field Validation Registry | `app.services.policy_form_registry`, `app.api.v1.schemes` | `GET /api/v1/schemes/{code}/requirements` | `test_generic_policy_forms_phase_g.py` (17 tests) | **FROZEN** |
| **H** | Ten Welfare Schemes & 40 Canonical Scenarios Verification | `schemes_data/*`, `app.services.policy_loader` | Full statutory evaluation across 10 schemes | `test_generic_policy_forms_phase_h.py` (49 tests) | **FROZEN** |
| **I** | Official Document Provenance & Immutability Trigger | `app.models.provenance`, `app.services.provenance_service` | `GET /api/v1/provenance/policy/{version_id}` | `test_provenance_phase_i.py` (25 tests) | **FROZEN** |
| **J** | End-to-End Verification, Demo Readiness & Hardening | `scripts.demo_seed_reset`, `test_phase_j_end_to_end` | Complete multi-role simulation & concurrency tests | `test_phase_j_end_to_end.py` (32 tests) | **FROZEN** |

---

## 4. Ten-Scheme Matrix & Authoritative 14 Policy-Version Inventory

### 4.1. Authoritative 14 Policy-Version Inventory Table (Directly Verified from Database & Policy Files)

The following table documents the exact, authoritative inventory of all 14 policy versions queried directly from the active PostgreSQL database (`policy_versions` table joined with `schemes`) and cross-checked against `schemes_data/*/policies/*.json`.

| Scheme Code | Scheme Name | Policy Version | Status | Rule Definition Hash (SHA-256) | Source / Provenance Reference |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `IGNOAPS` | Indira Gandhi National Old Age Pension Scheme | `v1.0-2011` | Active | `f8f5d40016b2136cb9f17cc0697a0fd73d0ef6673299af75e165800df56a8698` | `MORD-NSAP-IGNOAPS-GUIDELINES-2011` (National Social Assistance Programme (NSAP) Guidelines – IGNOAPS) |
| `PM_KISAN` | Pradhan Mantri Kisan Samman Nidhi | `v1.0-2018` | Historical | `facc14b3388802e3d0ef0c4134414459500dc9a9be7e0dc62ddecc082b47e9d2` | `PMKISAN-GUIDELINES-2018-SMF` (PM-KISAN Operational Guidelines (Original - Small & Marginal Farmers)) |
| `PM_KISAN` | Pradhan Mantri Kisan Samman Nidhi | `v2.0-2019` | Historical | `55fe76d5bd441cbe4a0ceddb45ddbf253f5f059683570bd29096bf9b972ad6d8` | `PMKISAN-REVISED-GUIDELINES-2019` (Revised Operational Guidelines for PM-KISAN 2019) |
| `PM_KISAN` | Pradhan Mantri Kisan Samman Nidhi | `v3.0-2023` | Active | `7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6` | `PMKISAN-OPERATIONAL-GUIDELINES-2023` (Operational Guidelines for PM-KISAN 2023) |
| `SSY` | Sukanya Samriddhi Account Scheme | `v1.0-2016` | Historical | `ffb3c2dae2cf283d3b0b41c8dfd87267cfff29e30fa898ee1ca93fde19419ae7` | `GSR-323E-2016` (Sukanya Samriddhi Account Rules, 2016) |
| `SSY` | Sukanya Samriddhi Account Scheme | `v2.0-2019` | Historical | `3dbd7d9d1f87ae7ce5064143333bd8ac969b14e927ac6cb7e6206f1777288669` | `GSR-914E-2019` (Sukanya Samriddhi Account Scheme, 2019) |
| `SSY` | Sukanya Samriddhi Account Scheme | `v3.0-2024` | Active | `5fa83b3d5b0177ca9d0983e46213d11e92883993f2f7a5abc9fe43fb25b9ff28` | `GSR-914E-2019-MOF-2024-NS` (Sukanya Samriddhi Account Scheme, 2019 as amended) |
| `PM_VISHWAKARMA` | PM Vishwakarma Scheme | `v1.0-2023` | Active | `1495c595a73b045c6d709591ad6e98efe676e8322148568553ff4c103597ba75` | `MSME-PM-VISHWAKARMA-GUIDELINES-2023` (PM Vishwakarma Scheme Operational Guidelines 2023) |
| `PMMVY` | Pradhan Mantri Matru Vandana Yojana | `v2.0-2022` | Active | `d33e0f6835a3901176c67aee6b8bc4df5892c64dc7220ae0ade96746713fd133` | `MWCD-PMMVY-MISSION-SHAKTI-2022` (Mission Shakti Guidelines for PMMVY) |
| `PM_KMY` | Pradhan Mantri Kisan Maandhan Yojana | `v1.0-2019` | Active | `73c5014917ef9f20e1aa9ec09cfbd2741a695dc3ad1ae47cb1ccde8550a2be93` | `DACFW-PMKMY-GUIDELINES-2019` (PM-KMY Operational Guidelines 2019) |
| `PMUY` | Pradhan Mantri Ujjwala Yojana (Ujjwala 2.0) | `v2.0-2021` | Active | `ce008cc4f3182d150f01c6c8de28810916065afee3827f58bf5f2cc36d62d46f` | `MOPNG-PMUY-2.0-GUIDELINES-2021` (PMUY 2.0 Operational Guidelines) |
| `PM_SVANIDHI` | PM Street Vendor's AtmaNirbhar Nidhi | `v1.0-2020` | Active | `eafcf7a942d156e55bb044e886b528d6250f5b7f1c635fd7ef127402e5739e77` | `MOHUA-PMSVANIDHI-GUIDELINES-2020` (Scheme Guidelines for PM SVANidhi) |
| `PMAY_U_2_0` | Pradhan Mantri Awas Yojana - Urban 2.0 | `v1.0-2024` | Active | `a43ecc26d3fdb9b43f28aa8759aee4d0ab54d1397001a563e729fdfe198f3130` | `MOHUA-PMAY-U-2.0-GUIDELINES-2024` (PMAY-U 2.0 Scheme Guidelines 2024) |
| `PMAY_G` | Pradhan Mantri Awaas Yojana - Gramin | `v1.0-2016` | Active | `9b1a19bce28cc2005ac5120c3411cdcafdc0bec9f531df0fab3fdb5148fa30bb` | `MORD-PMAYG-FRAMEWORK-2016` (Framework for Implementation of PMAY-G) |

### 4.2. Scheme Statutory Rule & Evidence Matrix

| Scheme Code | Ministry | Form Metadata Key | Statutory Rule Summary | Mandatory Facts | Mandatory Evidence | Canonical Scenarios | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PM_KISAN` | MoA&FW | `pm_kisan_v3_form` | Landholding, 7 Exclusions (Institutional, Pension, Tax, Constitutional) | `landholding_hectares`, `is_institutional_holder`, `monthly_pension`, `is_income_tax_payer` | Land Record (ROR), Aadhaar, Bank Passbook | 4 / 4 Passed | **FROZEN** |
| `SSY` | MoF / DoP | `ssy_v3_form` | Girl child citizenship, Age $\le 10$, Maximum 2 accounts per family | `child_gender`, `child_age_years`, `family_existing_ssy_accounts`, `is_indian_citizen` | Child Birth Certificate, Guardian Identity Proof | 4 / 4 Passed | **FROZEN** |
| `PM_KMY` | MoA&FW | `pm_kmy_v1_form` | Small/Marginal Farmer, Age 18–40, Exclusion from NPS/ESIC/PM-SYM | `age_years`, `cultivable_land_hectares`, `covered_under_nps_esic_epfo`, `is_smf` | Land Possession Certificate, Aadhaar Card | 4 / 4 Passed | **FROZEN** |
| `PMUY` | MoPNG | `pmuy_v2_form` | Adult woman ($\ge 18$), BPL/Deprived category, No existing LPG connection | `applicant_gender`, `applicant_age`, `household_has_lpg_connection`, `bpl_category_status` | Ration Card / BPL Proof, Aadhaar, Bank Details | 4 / 4 Passed | **FROZEN** |
| `PM_VISHWAKARMA` | MoMSME | `pm_vishwakarma_v1_form` | Traditional artisan trade, Age $\ge 18$, Self-employment, 1 member/family | `artisan_trade_type`, `applicant_age`, `family_member_availed_benefit`, `existing_pmegp_mudra_outstanding` | Artisan Registration Proof, Aadhaar, Self-Declaration | 4 / 4 Passed | **FROZEN** |
| `PMAY_G` | MoRD | `pmay_g_v1_form` | Houseless or kutcha house (0-2 rooms), 13 SECC exclusion filters | `house_wall_roof_type`, `household_owns_motorized_vehicle`, `has_kcc_limit_ge_50k`, `monthly_income` | SECC 2011 Verification List, Gram Sabha Resolution | 4 / 4 Passed | **FROZEN** |
| `PMAY_U_2_0` | MoHUA | `pmay_u_2_0_v1_form` | EWS/LIG/MIG income ceilings, No pucca house in India, Urban resident | `annual_household_income`, `owns_pucca_house_anywhere_in_india`, `urban_resident_status` | Income Certificate, Domicile/Residence Proof, Affidavit | 4 / 4 Passed | **FROZEN** |
| `PM_SVANIDHI` | MoHUA | `pm_svanidhi_v1_form` | Urban street vendor with Vending Certificate / LOR, Cutoff date | `has_vending_certificate_or_lor`, `vending_prior_to_cutoff`, `urban_local_body_jurisdiction` | Certificate of Vending / Letter of Recommendation (LOR) | 4 / 4 Passed | **FROZEN** |
| `PMMVY` | MoWCD | `pmmvy_v2_form` | Pregnant & Lactating Mothers, Age $\ge 19$, 1st child or 2nd (girl), PSU exclusion | `mother_age`, `live_birth_order`, `second_child_gender`, `is_regular_govt_psu_employee` | Mother-Child Protection (MCP) Card, Child Birth Certificate | 4 / 4 Passed | **FROZEN** |
| `IGNOAPS` | MoRD | `ignoaps_v1_form` | Age $\ge 60$ years, BPL household certification | `applicant_age`, `bpl_household_status` | Age Proof (Birth Certificate / Voter ID), Valid BPL Card | 4 / 4 Passed | **FROZEN** |

---

## 5. Security Evidence Matrix

The audited implementation includes and tests the following security controls across authentication, authorization, data integrity, and API boundaries.

| Security Control | Threat Model / Vulnerability Addressed | Implementation Mechanism | Verification Test Reference | Status |
| :--- | :--- | :--- | :--- | :--- |
| **JWT Authentication** | Session hijacking, forged identities, anonymous API access | Signed HMAC-SHA256 tokens with mandatory expiration, user ID, role, and issuer claims | `test_auth_phase_a.py::test_jwt_validation_and_expiration` | **VERIFIED** |
| **Citizen IDOR Protection** | Insecure Direct Object Reference (Citizen A accessing Citizen B's journey) | Database queries strictly bind `EvaluationJourney.citizen_id == current_user.id`. Cross-user access returns HTTP 404 (Not Found) | `test_phase_j_end_to_end.py::test_citizen_idor_isolation` | **VERIFIED** |
| **Officer Role Isolation** | Privilege escalation by citizen calling caseworker evaluation endpoints | Route decorators enforce `Depends(require_role(UserRole.OFFICER))`. Citizen access yields HTTP 403 (Forbidden) | `test_generic_policy_forms_phase_h.py::test_citizen_cannot_invoke_officer_evaluation` | **VERIFIED** |
| **Peer-Case Protection** | Officer tampering with another officer's locked or assigned case | Journey update endpoints verify caseworker assignment ownership; unassigned or peer-assigned journeys reject unauthorized transitions | `test_officer_assignment_phase_d.py::test_peer_officer_case_isolation` | **VERIFIED** |
| **Self-Escalation Resistance** | Citizen attempting to directly patch claim status or evidence to `VERIFIED` | Pydantic schema stripping on citizen endpoints; citizen payloads cannot mutate `Claim.status` or `Evidence.status` | `test_generic_policy_forms_phase_h.py::test_citizen_cannot_self_escalate_claims_or_evidence_to_verified` | **VERIFIED** |
| **Policy-Version Tampering** | Client attempting to bind application to non-existent or inactive policy version | Server-side validation against `PolicyVersion` registry; binds active version during journey creation | `test_provenance_phase_i.py::test_policy_version_immutability` | **VERIFIED** |
| **Verification Gate Enforcement** | Bypassing evidence verification to trigger premature eligibility evaluation | `VerificationGateService` validates that all mandatory claims have corresponding `VERIFIED` evidence prior to AST execution | `test_phase_j_end_to_end.py::test_verification_gate_halts_unverified_evaluation` | **VERIFIED** |
| **Audit Log Immutability** | Database administrator or compromised officer modifying historical audit logs | PostgreSQL trigger `trg_provenance_audit_events_immutable` raises an exception on any `UPDATE` or `DELETE` attempt | `test_provenance_phase_i.py::test_provenance_audit_events_immutable_trigger` | **VERIFIED** |
| **Provenance URL Sanitization** | Server-Side Request Forgery (SSRF) and phishing via malicious official source links | Source creation validates domains against approved Indian government domains (`.gov.in`, `.nic.in`) | `test_provenance_phase_i.py::test_official_url_validation` | **VERIFIED** |
| **Two-Role Boundary** | Introduction of unauthorized administrative super-users bypassing validation rules | System strictly restricts roles to `CITIZEN` and `OFFICER`; no administrative role exists that can override AST outcomes | `test_auth_phase_a.py::test_strict_two_role_model` | **VERIFIED** |

---

## 6. Deterministic Decision Evidence

### 6.1. Engineering Formulation & Strong Kleene Logic
Statutory rules frequently encounter incomplete information during an application process (e.g., pending documents or optional declarations). Conventional 2-valued Boolean logic collapses missing data into arbitrary falsehood, which in an administrative context can result in premature or wrongful denials.

Strong Kleene 3-valued logic is used as an engineering mechanism for representing $\text{TRUE}$, $\text{FALSE}$, and $\text{UNKNOWN}$ when required factual information is incomplete:

$$\begin{array}{c|ccc}
\land & \text{T} & \text{F} & \text{U} \\
\hline
\text{T} & \text{T} & \text{F} & \text{U} \\
\text{F} & \text{F} & \text{F} & \text{F} \\
\text{U} & \text{U} & \text{F} & \text{U}
\end{array}
\qquad
\begin{array}{c|ccc}
\lor & \text{T} & \text{T} & \text{T} \\
\hline
\text{T} & \text{T} & \text{T} & \text{T} \\
\text{F} & \text{T} & \text{F} & \text{U} \\
\text{U} & \text{T} & \text{U} & \text{U}
\end{array}
\qquad
\begin{array}{c|c}
\neg & \\
\hline
\text{T} & \text{F} \\
\text{F} & \text{T} \\
\text{U} & \text{U}
\end{array}$$

Under this logic:
- If a citizen record contains a verified fact that triggers an exclusion condition (e.g., `is_income_tax_payer == TRUE`), that exclusion sub-rule evaluates to `FALSE` immediately, even if other facts remain `UNKNOWN`.
- If an eligibility prerequisite is missing, the sub-tree evaluates to `UNKNOWN`. The engine produces one of the configured evaluation outcomes based on verified facts and the bound policy version (`INSUFFICIENT_INFORMATION` or `VERIFICATION_REQUIRED`), avoiding an unjustified negative determination.

### 6.2. Explainability without Generative AI
The `DecisionExplainer` service traverses the `EvaluationTrace` generated by the AST engine:
1. It isolates every evaluated node that resolved to `FALSE` or triggered an exclusion.
2. It extracts the pre-authored, bilingual statutory description strings associated with that specific rule node.
3. It appends the exact Gazette Notification section, clause, and sub-clause reference stored in `RuleProvenance`.
This ensures close adherence to the encoded statutory rules, predictable non-generative trace output, and structured traceability to official source clauses to assist administrative review.

---

## 7. Historical Reproducibility

YogyataMitra preserves the policy version selected for the application so that the system can reproduce the evaluation under the same encoded policy context:

1. **Immutable Policy Versioning**: When an `EvaluationJourney` is submitted, it is bound to the specific `policy_version_id` active at submission time.
2. **Rule Definition Hashing**: Every policy version computes a canonical SHA-256 hash of its serialized AST rule structure. This hash is permanently recorded on the `EvaluationTrace`.
3. **Non-Destructive Evolution**: Introducing a new policy version (e.g., `PM_KISAN v2.0-2019` removing the 2-hectare land ceiling) creates a distinct database record. Existing applications bound to `v1.0-2018` continue to execute against the v1.0 ruleset, enabling the system to reproduce the evaluation outcome for that case under the same encoded policy context.

Whether an amendment applies retrospectively is a legal/policy governance decision outside the evaluation engine.

---

## 8. Provenance Chain & Official Document Verification

$$\text{OfficialSource} \longrightarrow \text{OfficialDocument} \longrightarrow \text{DocumentVersion} \longrightarrow \text{PolicySourceBinding} \longrightarrow \text{RuleProvenance} \longrightarrow \text{EvaluationTrace}$$

### Distinction: Source Metadata vs. Physical Artifact Verification
- **`SOURCE_METADATA_VERIFIED`**:
  - `SOURCE_METADATA_VERIFIED` means the registered source/document metadata (issuing ministry, gazette notification number, publication date, circular reference, and official portal URL) has been verified according to the project's provenance process.
  - In this state, `document_hash` is recorded as `NULL` because the physical PDF artifact is referenced at its sovereign location rather than stored cryptographically inside the repository.
- **`PHYSICAL_ARTIFACT_VERIFIED`**:
  - `PHYSICAL_ARTIFACT_VERIFIED` requires an actual stored artifact and a recorded SHA-256 hash.
  - The physical binary artifact (PDF file) is locally archived in repository storage, and runtime checks verify that the stored file's byte hash matches the registered hash.

*No claim of physical artifact verification is made where `document_hash` is NULL.*

---

## 9. Demonstration Plan

Automated demo data initialization is handled by `backend/scripts/demo_seed_reset.py`. Demo records are synthetic and are intended to avoid unnecessary processing of real personal information.

### 9.1. Synthetic Demonstration Profiles
- `SYN-CIT-DEMO0001`: Ramesh Kumar (Demo), 39y Male, Varanasi, Uttar Pradesh (`PM_KISAN`)
- `SYN-CIT-DEMO0002`: Sunita Devi (Demo), 34y Female, Pune, Maharashtra (`SSY`)
- `SYN-CIT-DEMO0003`: Priya Sharma (Demo), 26y Female, Jaipur, Rajasthan (`PMMVY`)

### 9.2. Demonstration Scenarios & Flows
All demonstration outcomes represent system evaluation outcomes in synthetic test scenarios:
- **FLOW A (Positive Eligibility Scenario)**: Apply $\to$ Submit facts/evidence $\to$ Officer verifies $\to$ `READY_FOR_EVALUATION` $\to$ Evaluate $\to$ Outcome: `ELIGIBLE` $\to$ Bilingual explanation & provenance citation.
- **FLOW B (Statutory Ineligibility Scenario)**: Submit disqualifying fact ($\ge ₹10,000$ pension) $\to$ Officer verifies $\to$ Deterministic evaluation $\to$ Outcome: `INELIGIBLE` $\to$ Section 4.1(e) citation.
- **FLOW C (Verification Gate Enforcement Scenario)**: Submit application $\to$ Officer leaves mandatory evidence pending $\to$ Evaluation attempt $\to$ Outcome: `VERIFICATION_REQUIRED`.
- **FLOW D (Clarification Cycle Scenario)**: Blurred evidence $\to$ Officer triggers `CLARIFICATION_REQUESTED` $\to$ Citizen uploads replacement $\to$ Officer verifies $\to$ `READY_FOR_EVALUATION` $\to$ Evaluated.
- **FLOW E (Historical Policy Context Scenario)**: Application bound to historical policy version $D_1$ (e.g., PM-KISAN v1.0 2-ha ceiling) $\to$ Re-evaluated in presence of active $D_2$ $\to$ Evaluator preserves original $D_1$ decision outcome.

---

## 10. Viva / Academic Defense Questions & Answers

#### Q1: Why use deterministic AST rules instead of an LLM for eligibility decisions?
**Answer**: Public welfare administration requires predictable, auditable adherence to encoded administrative guidelines and statutory rules. Large Language Models are probabilistic and stochastic, meaning identical inputs can yield divergent outputs, and they may generate synthetic facts (hallucinations) or be influenced by prompt phrasing. YogyataMitra is an academic research implementation that evaluates encoded policy rules deterministically using Abstract Syntax Trees (AST) and formal propositional logic. This architecture ensures reproducible execution over identical input facts and bound policy versions, eliminates generative model hallucination in eligibility computation, and provides direct traceability to encoded rule clauses without replacing administrative or legal authority.

#### Q2: Why is policy versioning necessary?
**Answer**: Welfare schemes undergo frequent administrative and legislative amendments (e.g., the expansion of PM-KISAN in 2019 to remove the 2-hectare land ceiling, or changes in SSY deposit rules in 2024). If policy rules are stored as mutable database rows or hardcoded logic, modifying a rule silently alters the policy context of historical applications. Policy versioning decouples scheme definitions across time, allowing the system to evaluate an application against the exact policy version bound at submission time.

#### Q3: Why is Evidence Verification separated from Claims?
**Answer**: In administrative processes, an assertion of fact is distinct from verified evidence. A citizen asserts a fact (e.g., "My annual income is ₹45,000"), which represents a *Claim*. That claim is not admitted into the evaluation facts context until an authorized officer has examined the supporting documentary evidence (e.g., an Income Certificate) and updated its verification status. Separating claims from evidence prevents self-declared entries from directly influencing automated rule evaluation.

#### Q4: Why is Strong Kleene 3-valued logic used instead of Boolean logic?
**Answer**: Strong Kleene 3-valued logic is used as an engineering mechanism for representing TRUE, FALSE, and UNKNOWN when required factual information is incomplete. Standard Boolean logic requires every variable to be either `TRUE` or `FALSE`. Forcing missing data into `FALSE` can cause premature negative outcomes, while defaulting to `TRUE` risks unauthorized eligibility. Under Strong Kleene logic, an unverified prerequisite evaluates to `UNKNOWN`, allowing the engine to classify the outcome as `INSUFFICIENT_INFORMATION` or `VERIFICATION_REQUIRED`.

#### Q5: What is an EvaluationTrace and why is it stored?
**Answer**: An `EvaluationTrace` is an execution graph capturing every AST node evaluated during an eligibility check, including the resolved truth value, sub-expression outcomes, missing facts, and triggered exclusion clauses. It is stored permanently to enable administrative inspection, auditable record-keeping, and citizen explainability without re-running the engine.

#### Q6: How does YogyataMitra support historical reproducibility of evaluation outcomes?
**Answer**: When an application is created, it is bound to a specific `policy_version_id`. Each policy version computes a canonical SHA-256 hash of its normalized AST rule structure. When the application is evaluated, the `EvaluationTrace` records the rule definition hash. If subsequent policy amendments occur, historical journeys remain bound to their original policy version and hash, enabling the system to reproduce the evaluation outcome for that case under the same encoded policy context.

#### Q7: How does the system prevent Insecure Direct Object References (IDOR)?
**Answer**: All citizen-facing endpoints enforce authorization boundaries at the database query level. The citizen identity is extracted exclusively from the validated JWT token (`current_user.id`), and all SQL queries filter explicitly by `EvaluationJourney.citizen_id == current_user.id`. If a citizen attempts to view or mutate another citizen's journey ID, the system returns HTTP 404 (Not Found), preventing disclosure of other records.

#### Q8: How are officers authorized and how are peer conflicts prevented?
**Answer**: Officers authenticate via distinct credentials and receive JWTs with the `OFFICER` role claim. Caseworker endpoints enforce role validation via dependency injection. To prevent peer conflicts, submitted applications enter an assignment pool. Once an officer claims or is assigned a journey, write operations are locked to that assigned officer, preventing peer caseworkers from making conflicting modifications.

#### Q9: How are statutory policy amendments handled without system downtime?
**Answer**: Policy definitions are stored as versioned, declarative JSON/AST artifacts in `schemes_data/`. Adding an amendment involves registering a new `PolicyVersion` (e.g., `v2.0-2024`) with its own effective date and rule graph. The `PolicySelector` routes new applications to the updated version while preserving historical bindings for existing journeys. No database migrations, code modifications, or server restarts are required.

#### Q10: How is provenance established from an AST rule back to a Gazette Notification?
**Answer**: Provenance is modeled as a multi-tier relational hierarchy: an AST Rule references a `RuleProvenance` entity, which specifies the section, clause, and sub-clause of an `OfficialDocument`. The document is linked via `PolicySourceBinding` to the `PolicyVersion` and issued by an `OfficialSource` (Ministry). The `EvaluationTrace` cites these provenance IDs directly, linking the system outcome back to the recorded official source reference.

#### Q11: What happens when mandatory evidence is missing from an application?
**Answer**: The `VerificationGateService` intercepts the application before AST execution. It inspects the scheme's requirements; if a mandatory evidence category lacks an uploaded document, the journey is halted with the outcome `INSUFFICIENT_INFORMATION`. The citizen is prompted to upload the required artifact, and no evaluation occurs until the gap is resolved.

#### Q12: What happens when an officer rejects an uploaded evidence artifact?
**Answer**: When an officer marks an evidence artifact as `REJECTED`, the associated claim is marked `REJECTED`. The journey cannot proceed to `READY_FOR_EVALUATION`. The officer records a rejection reason, which triggers a clarification cycle or formal notification to the citizen, permitting them to submit a replacement artifact.

#### Q13: What happens if a policy amendment occurs while an application is under review?
**Answer**: The system binds an application to its selected policy version. Treatment of retrospective amendments remains a policy/legal governance decision outside the software engine. Within the platform, binding the policy version at journey submission ensures that subsequent amendments do not automatically alter the evaluation rules for existing applications unless explicitly re-bound by administrative action.

#### Q14: Why are all demonstration identities explicitly synthetic?
**Answer**: The demonstration environment uses synthetic identities and data to avoid unnecessary processing of real personal information and reduce privacy and data-governance risk during academic evaluation. All demonstration records use synthetic references (`SYN-CIT-DEMO...`), fabricated names, and mock documents.

#### Q15: What are the primary system limitations of YogyataMitra?
**Answer**: YogyataMitra is an academic research platform, not a certified production deployment of the Government of India. It does not integrate with live government backends (e.g., UIDAI Aadhaar e-KYC, state Bhulekh land databases, PFMS). Document verification is performed administratively within the workflow rather than via direct API interoperability.

#### Q16: What is the difference between Policy Discovery and Policy Activation?
**Answer**: Policy Discovery is an upstream research/observability tool that scans official circulars and identifies potential statutory amendments, structuring them as unapproved candidate proposals. Policy Activation is an administrative action: an approved candidate is converted into a frozen `PolicyVersion` with verified cryptographic hashes, registered in the database, and bound to the deterministic evaluator.

#### Q17: Why can artificial intelligence NOT be allowed to make the final entitlement decision?
**Answer**: In public administration, statutory eligibility decisions must strictly reflect authorized administrative guidelines and policy criteria. Probabilistic AI models exhibit variability, cannot be formally verified against statutory logic, and risk introducing unvetted bias or generative errors. YogyataMitra establishes a firm boundary where AI components may be explored for upstream policy discovery or text digitization, but the core eligibility evaluation engine remains strictly deterministic and based on symbolic rule evaluation over verified facts.

#### Q18: What is the distinction between metadata-verified documents and physical-artifact-verified documents?
**Answer**: `SOURCE_METADATA_VERIFIED` means the registered source/document metadata has been verified according to the project's provenance process (document_hash is recorded as NULL). `PHYSICAL_ARTIFACT_VERIFIED` requires an actual stored artifact and a recorded SHA-256 hash.

---

## 11. Known Limitations & Research Non-Claims

In accordance with academic integrity and ethical GovTech engineering, the following limitations are formally recorded:

1. **Academic Research Platform**: YogyataMitra is an academic research implementation developed to demonstrate deterministic statutory reasoning and evidence verification architectures. It is **not** an officially certified system of the Government of India, nor does it hold delegated legal authority under any Central or State statute.
2. **Absence of Live Government Interoperability**: The platform does not maintain direct API connections to live statutory registries (e.g., UIDAI Aadhaar authentication servers, PFMS payment gateways, State Revenue Bhulekh portals, or DigiLocker national repositories). Evidence artifacts are verified by caseworkers through the application workflow.
3. **Document Hash Boundary**: Official documents referenced in `schemes_data/` with `document_hash IS NULL` are verified at the source metadata level (`SOURCE_METADATA_VERIFIED`) against official publications. Cryptographic byte verification (`PHYSICAL_ARTIFACT_VERIFIED`) is restricted to artifacts locally stored with calculated SHA-256 digests.
4. **Advisory Scope**: The evaluation outcomes generated by YogyataMitra evaluate encoded policy rules and do not replace statutory, administrative, or judicial authority. They do not constitute legally binding administrative orders, nor do they replace statutory appellate processes under Indian administrative law.
5. **No Autonomous Policy Activation**: AI-assisted policy discovery tools cannot activate policy versions; activation requires manual administrative confirmation.
6. **Synthetic Demonstration Data**: All demo identities and uploaded artifacts are synthetic test records.
7. **Concurrency-Test Scope**: The concurrency tests in the test suite verify data consistency in memory and via local database transactions; they do not simulate multi-node distributed network load.
8. **Operating System Concurrency**: On Windows host operating systems, running multi-threaded Jest test execution concurrently may encounter port binding latencies; all test executions are verified using serial execution flags (`--runInBand`).

---

## 12. Test & Audit Evidence

### 12.1. Backend Test Suite Breakdown
- **Phase A–J Regression Suite**: Exactly 212 tests across 10 files, all passing in 117.20s:
  - `test_auth_phase_a.py`: 10 passed
  - `test_citizen_applications_phase_b.py`: 8 passed
  - `test_citizen_phase_c.py`: 10 passed
  - `test_officer_assignment_phase_d.py`: 10 passed
  - `test_evidence_clarification_phase_e.py`: 20 passed
  - `test_deterministic_evaluation_phase_f.py`: 31 passed
  - `test_generic_policy_forms_phase_g.py`: 17 passed
  - `test_generic_policy_forms_phase_h.py`: 49 passed (6 structural + 40 canonical scenarios across 10 schemes + 3 security tests)
  - `test_provenance_phase_i.py`: 25 passed
  - `test_phase_j_end_to_end.py`: 32 passed
- **Total Backend Test Collection**: 458 items collected and passed across all repository backend test suites (including policy authoring, policy discovery, statutory rulesets, and AST evaluator unit suites).

### 12.2. Frontend Test Suite Breakdown
- **Jest Test Suite**: 137 passed across 24 test suites (`npm test -- --runInBand`).
- **TypeScript**: 0 errors (`npx tsc --noEmit`).
- **ESLint**: 0 errors, 0 warnings (`npm run lint`).
- **Next.js Production Build**: 33 routes compiled and statically optimized (`npm run build`).

### 12.3. Database Migrations
- **Linear Revision Chain**: Exactly 14 migrations (`5cc3457b7818` through `d4e5f6a7b8c9`).
- **Current Head**: `d4e5f6a7b8c9 (head)`.

### 12.4. Independent Audit Findings
The independent freeze audit evaluated the implementation against production hardening criteria and confirmed:
- **Finding F-J-01 (LOW)**: Windows Jest concurrency behavior requiring `--runInBand` documented and verified.
- **Finding F-J-02 (LOW)**: In-memory concurrency testing accepted for academic research scope.
- **Finding F-J-03 (INFO)**: 212 Phase A–J regression tests reconciled against full 458 backend test suite.
- **Audit Verdict**: `PHASE J COMPLETE & FROZEN` (0 Critical, 0 High findings).
- **Audit Qualification**: Independent audit findings reported in this document are project audit results and do not constitute government certification or legal certification.

---

## 13. Final Project Status Block

```
YOGYATAMITRA

PHASES A–J:
COMPLETE & FROZEN

10 GOVERNMENT SCHEMES
14 POLICY VERSIONS
40 CANONICAL SCENARIOS

BACKEND:
212/212 A–J REGRESSION PASS

FRONTEND:
137/137 PASS

TYPESCRIPT:
0 ERRORS

LINT:
0 ERRORS

PRODUCTION BUILD:
PASS

ALEMBIC:
d4e5f6a7b8c9 — SINGLE HEAD

PHASE J:
INDEPENDENTLY AUDITED

CRITICAL FINDINGS:
0

HIGH FINDINGS:
0

PHASE K:
NOT STARTED
```

---

```
PHASES A–J COMPLETE & FROZEN
PHASE K NOT STARTED
FINAL ACADEMIC & DEMONSTRATION READINESS REVIEW COMPLETE
```
