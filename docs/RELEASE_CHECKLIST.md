# YogyataMitra Pre-Flight Release Checklist

This checklist must be executed and fully checked off prior to promoting any release of **YogyataMitra** to production, academic review, or public demonstration.

---

## 1. Repository Boundary & Isolation
- [x] Canonical working tree is strictly `D:\YogyataMitra`.
- [x] External directories (`D:\YogyataMitra-main`) are completely isolated: zero imports, zero comparisons, zero merges.
- [x] Clean working tree with no untracked secrets, `.env` files, or binary artifacts (`git status`).
- [x] Clean clone test passes cleanly without tracking or configuration errors (`verify_clean_clone.py`).

---

## 2. Statutory Policy & Mathematical Invariants
- [x] **Exactly 2 statutory schemes** exist in the system: `PM_KISAN` and `SSY`. No unauthorized or unapproved schemes exist.
- [x] **Exactly 6 authoritative policy versions** exist:
  - `PM_KISAN`: `v1.0-2018`, `v2.0-2019`, `v3.0-2023`
  - `SSY`: `v1.0-2016`, `v2.0-2019`, `v3.0-2024`
- [x] **All 6 canonical SHA-256 rule definition hashes** match the permanently frozen regression baseline:
  - `PM_KISAN v1.0-2018`: `facc14b3388802e3d0ef0c4134414459500dc9a9be7e0dc62ddecc082b47e9d2`
  - `PM_KISAN v2.0-2019`: `55fe76d5bd441cbe4a0ceddb45ddbf253f5f059683570bd29096bf9b972ad6d8`
  - `PM_KISAN v3.0-2023`: `7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6`
  - `SSY v1.0-2016`: `ffb3c2dae2cf283d3b0b41c8dfd87267cfff29e30fa898ee1ca93fde19419ae7`
  - `SSY v2.0-2019`: `3dbd7d9d1f87ae7ce5064143333bd8ac969b14e927ac6cb7e6206f1777288669`
  - `SSY v3.0-2024`: `5fa83b3d5b0177ca9d0983e46213d11e92883993f2f7a5abc9fe43fb25b9ff28`
- [x] **Rule engine neutrality**: Zero scheme-specific logic or hardcoded scheme rules exist in `app/engine/`.
- [x] **Draft policy quarantine**: All authored policy drafts remain strictly staged/quarantined in `policy_drafts`. No draft has been activated or published to authoritative statutory tables.

---

## 3. Database Schema & Migration Readiness
- [x] PostgreSQL 16 database running and healthy.
- [x] Alembic migration head verified at `6b2e477e42cb (head)`.
- [x] All 18 required domain tables present in public schema.
- [x] Fresh database creation and migration from scratch verified cleanly via `verify_fresh_db.py`.
- [x] Application-level append-only audit trail integrity preserved.

---

## 4. Security & Environment Configuration
- [x] `ENVIRONMENT` set to `production` for production deployments.
- [x] `SECRET_KEY` configured with high-entropy 256-bit secret (no dev/insecure fallbacks).
- [x] `ENABLE_DEMO_ACCOUNTS` disabled (`false`).
- [x] `CORS_ORIGINS` whitelisted to trusted production domains only; wildcard `*` rejected.
- [x] Production database credentials configured and secured (`chmod 600 .env`).
- [x] Nginx reverse proxy configured with TLS 1.2/1.3, rate limiting, and security headers.

---

## 5. Automated Verification & Quality Gates
- [x] **Backend Pytest Suite**: 244 passed, 0 failed, 0 skipped.
- [x] **Frontend Jest Suite**: 80 passed across 16 test suites, 0 failed.
- [x] **Playwright E2E Suite**: 23 passed across 8 test suites, 0 failed.
- [x] **Total Automated Tests**: 347 passed (100% pass rate).
- [x] **Frontend Production Build**: `npm run build` completed with exit code 0; all 14/14 static pages generated cleanly.

---

## 6. Static Media Assets & Fallback Verification
- [x] `docs/ASSET_PROVENANCE.md` created and committed.
- [x] `parliament_hero.jpg` verified: SHA-256 `9ec95cb8cdd3ae9126c8d075f967eaad0bdcd9d7055c3fa7d41f22e214544eca`.
- [x] `logo.png` verified: SHA-256 `5bb85cde33814e00c42e07769b2bbd0aba3c58f39f09422e188186df286f7bf7`.
- [x] CSS background fallback (`bg-primary-dark`) and descriptive `alt` attribute verified.
- [x] Scheme benefit strings explicitly labeled as descriptive presentation summaries in `SchemeCard.tsx` and i18n locales.

---

## 7. Sign-Off & Release Approval

| Role | Name / Identifier | Verification Status | Date |
| :--- | :--- | :--- | :--- |
| **Lead Architect** | Antigravity AI Systems | **APPROVED** | 2026-09-25 |
| **Statutory Policy Auditor** | Automated Hash Guard | **VERIFIED (6/6 HASHES)** | 2026-09-25 |
| **QA / Testing Lead** | Automated Test Runner | **VERIFIED (347/347 PASS)**| 2026-09-25 |
| **Release Verdict** | **READY FOR RELEASE** | **ALL CHECKS PASSED** | 2026-09-25 |
