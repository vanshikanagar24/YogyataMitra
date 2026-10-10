# YogyataMitra Release Manifest (v1.0.0-phase18)

This release manifest provides a cryptographic, immutable record of build artifacts, statutory policy hashes, database schema revisions, API surface definitions, and automated verification metrics for the **YogyataMitra** platform.

---

## 1. Release Metadata

| Field | Value |
| :--- | :--- |
| **Platform Name** | YogyataMitra (योग्यता मित्र) |
| **Release Tag** | `v1.0.0-phase18` |
| **Release Date** | September 25, 2026 |
| **Release Title** | Phase 18 Final Product Acceptance & Production Readiness |
| **Canonical Repository Root** | `D:\YogyataMitra` |
| **Git Branch** | `main` |
| **Git Baseline Commit SHA** | `258971c4de6b2d84886140f21090641a5c7f8c06` |
| **Target Runtime** | Node.js 20+ / Python 3.12+ / PostgreSQL 16 |
| **Alembic Migration Head** | `6b2e477e42cb` |
| **Production Readiness Status** | **READY FOR RELEASE** |

---

## 2. Statutory Policy & Cryptographic Hash Manifest

YogyataMitra strictly enforces **exactly two statutory welfare schemes** and **exactly six authoritative policy versions**. All rule definitions are represented as AST structures and cryptographically bound via canonical SHA-256 hashes.

| Scheme Code | Scheme Title | Version Code | Effective Period | Canonical SHA-256 Rule Definition Hash |
| :--- | :--- | :--- | :--- | :--- |
| `PM_KISAN` | Pradhan Mantri Kisan Samman Nidhi | `v1.0-2018` | 2018-12-01 → 2019-03-31 | `facc14b3388802e3d0ef0c4134414459500dc9a9be7e0dc62ddecc082b47e9d2` |
| `PM_KISAN` | Pradhan Mantri Kisan Samman Nidhi | `v2.0-2019` | 2019-04-01 → 2023-01-31 | `55fe76d5bd441cbe4a0ceddb45ddbf253f5f059683570bd29096bf9b972ad6d8` |
| `PM_KISAN` | Pradhan Mantri Kisan Samman Nidhi | `v3.0-2023` | 2023-02-01 → Open | `7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6` |
| `SSY` | Sukanya Samriddhi Account Scheme | `v1.0-2016` | 2016-03-18 → 2019-12-11 | `ffb3c2dae2cf283d3b0b41c8dfd87267cfff29e30fa898ee1ca93fde19419ae7` |
| `SSY` | Sukanya Samriddhi Account Scheme | `v2.0-2019` | 2019-12-12 → 2024-02-29 | `3dbd7d9d1f87ae7ce5064143333bd8ac969b14e927ac6cb7e6206f1777288669` |
| `SSY` | Sukanya Samriddhi Account Scheme | `v3.0-2024` | 2024-03-01 → Open | `5fa83b3d5b0177ca9d0983e46213d11e92883993f2f7a5abc9fe43fb25b9ff28` |

---

## 3. Database Schema Revisions

Database migrations are executed via Alembic and maintained across 7 sequential revision files resulting in 18 public domain tables:

| Revision ID | Description |
| :--- | :--- |
| `5cc3457b7818` | Initial core domain models (`schemes`, `policy_versions`, `rule_sets`, `citizens`, `claims`, `evidence`, `verification_records`) |
| `c5128b89cf97` | Add cryptographic rule hash and policy version bindings to `evaluation_traces` |
| `9bc038aebd36` | Add evaluation journey models (`evaluation_journeys`, `journey_transition_records`) |
| `d4e9f1a2b3c5` | Add officer human review and audit models (`human_reviews`, `human_review_audit_events`) |
| `e7f1a2b3c4d5` | Add AI policy discovery models (`policy_discovery_candidates`, `policy_discovery_review_events`) |
| `f8a2b3c4d5e6` | Strengthen policy discovery provenance bindings |
| `6b2e477e42cb` | Add policy authoring and staging models (`policy_drafts`, `policy_draft_audit_events`, `policy_draft_revisions`, `policy_draft_tests`) **[HEAD]** |

---

## 4. Automated Test Suite Metrics

| Test Suite Layer | Runner / Framework | Tests Executed | Passed | Failed | Skipped | Pass Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Unit & Integration** | Pytest 8.3 + `pytest-asyncio` | 244 | 244 | 0 | 0 | **100%** |
| **Frontend Unit & Component** | Jest 29.7 + Testing Library | 80 (16 suites) | 80 | 0 | 0 | **100%** |
| **Browser End-to-End** | Playwright (Chromium/Firefox) | 23 (8 specs) | 23 | 0 | 0 | **100%** |
| **Total Test Suite** | Combined | **347** | **347** | **0** | **0** | **100%** |

---

## 5. Static Assets & Provenance Checksums

| Asset Path | Format | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `frontend/public/images/parliament_hero.jpg` | JPEG | 930,522 B | `9ec95cb8cdd3ae9126c8d075f967eaad0bdcd9d7055c3fa7d41f22e214544eca` |
| `frontend/public/images/logo.png` | PNG | 176,789 B | `5bb85cde33814e00c42e07769b2bbd0aba3c58f39f09422e188186df286f7bf7` |

---

## 6. API Endpoint Inventory

### System & Health
- `GET /health`: Liveness probe.
- `GET /health/db`: Readiness probe (PostgreSQL ping).

### Schemes & Policies
- `GET /api/v1/schemes`: List all active schemes with bilingual metadata.
- `GET /api/v1/schemes/{scheme_code}`: Retrieve scheme details and policy version history.
- `GET /api/v1/schemes/{scheme_code}/policies/{version_code}`: Retrieve specific policy AST and metadata.

### Deterministic Eligibility Evaluation
- `POST /api/v1/evaluations`: Execute deterministic evaluation using Rule AST and Kleene tri-state logic.
- `GET /api/v1/evaluations/{evaluation_id}`: Retrieve evaluation result and bilingual explainability trace.
- `GET /api/v1/evaluations/{evaluation_id}/audit`: Retrieve tamper-evident audit record with cryptographic hash bindings.

### Citizen Journeys & Evidence
- `POST /api/v1/journeys`: Initiate citizen eligibility journey.
- `GET /api/v1/journeys/{journey_id}`: Retrieve journey state, missing facts, and required evidence.
- `POST /api/v1/journeys/{journey_id}/transitions`: Execute state machine transition.
- `POST /api/v1/journeys/{journey_id}/evidence`: Upload and register evidence metadata.

### Officer Portal & Human Review
- `POST /api/v1/officer/auth/login`: Officer JWT authentication.
- `GET /api/v1/officer/auth/me`: Retrieve authenticated officer profile and role (`OFFICER`, `SUPERVISOR`).
- `GET /api/v1/officer/reviews`: List assigned citizen claim reviews.
- `POST /api/v1/officer/reviews/{review_id}/decide`: Record officer verification decision (APPROVE/REJECT/REQUEST_INFO).
- `GET /api/v1/officer/audit/events`: Retrieve application-level append-only officer audit trail.

### AI Policy Discovery (Bounded Quarantine)
- `POST /api/v1/policy-discovery/candidates/discover`: Ingest and analyze unstructured policy text into candidate dossier.
- `GET /api/v1/policy-discovery/candidates`: List discovery candidates in review lifecycle.
- `POST /api/v1/policy-discovery/candidates/{candidate_id}/review`: Record human officer review of AI discovery candidate.

### Policy Authoring & Staging
- `GET /api/v1/policy-authoring/drafts`: List policy drafts in authoring workbench.
- `POST /api/v1/policy-authoring/drafts`: Create new policy draft.
- `GET /api/v1/policy-authoring/drafts/{draft_id}`: Retrieve draft details and revisions.
- `POST /api/v1/policy-authoring/drafts/{draft_id}/revisions`: Save new AST revision with semantic validation.
- `POST /api/v1/policy-authoring/drafts/{draft_id}/test`: Execute dry-run test suite against policy draft.
- `POST /api/v1/policy-authoring/drafts/{draft_id}/stage`: Move draft to `STAGED` quarantine status.
