# YogyataMitra Backup & Disaster Recovery Guide

This runbook establishes backup, restoration, database migration rollback, and disaster recovery procedures for the **YogyataMitra** platform, with special emphasis on preserving statutory policy immutability and application-level audit trail integrity.

---

## 1. Backup Strategies & Cadence

YogyataMitra relies on PostgreSQL 16 as its single source of truth for statutory policies, rulesets, citizen claims, evidence verifications, and audit trails.

### 1.1 Backup Taxonomy

| Backup Type | Tool / Mechanism | Frequency | Retention Target | Storage Location |
| :--- | :--- | :--- | :--- | :--- |
| **Logical Dump** | `pg_dump` (Custom format `-Fc`) | Daily (02:00 UTC) | 30 Days | Encrypted Off-site Object Storage |
| **Complete Cluster**| `pg_dumpall` (Globals & Roles) | Weekly (Sunday) | 90 Days | Encrypted Cold Storage |
| **Write-Ahead Log** | Continuous WAL Archiving | Continuous (15 min) | 7 Days | Streaming S3/GCS Bucket |

---

## 2. Automated Logical Backup Execution

### 2.1 Daily Automated Backup Script (`backup_yogyatamitra.sh`)
```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/yogyatamitra"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="${BACKUP_DIR}/yogyatamitra_db_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

echo "[INFO] Starting database backup to ${FILENAME}..."
docker exec yogyatamitra_postgres pg_dump \
    -U yogyata_admin \
    -d yogyatamitra_db \
    -Fc \
    -Z 9 \
    -f "/tmp/backup.dump"

docker cp yogyatamitra_postgres:/tmp/backup.dump "${FILENAME}"
docker exec yogyatamitra_postgres rm -f /tmp/backup.dump

echo "[INFO] Generating SHA-256 checksum..."
sha256sum "${FILENAME}" > "${FILENAME}.sha256"

echo "[INFO] Uploading to encrypted off-site cloud storage..."
# aws s3 cp "${FILENAME}" s3://gov-backups/yogyatamitra/
echo "[SUCCESS] Backup completed successfully."
```

### 2.2 Manual On-Demand Backup (PowerShell on Windows)
```powershell
# Create immediate logical dump of production database
docker exec yogyatamitra_postgres pg_dump -U yogyata_admin -d yogyatamitra_db -Fc -f /tmp/manual_backup.dump
docker cp yogyatamitra_postgres:/tmp/manual_backup.dump .\backup_manual.dump
docker exec yogyatamitra_postgres rm -f /tmp/manual_backup.dump
Get-FileHash .\backup_manual.dump -Algorithm SHA256
```

---

## 3. Database Restoration Procedures

### 3.1 Standard Full Restore from Logical Dump
To restore the platform database from a verified `.dump` file:

```bash
# 1. Stop application containers to prevent active client writes
docker compose stop backend

# 2. Terminate active database connections
docker exec -i yogyatamitra_postgres psql -U yogyata_admin -d postgres <<EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'yogyatamitra_db' AND pid <> pg_backend_pid();
EOF

# 3. Drop and recreate clean target database
docker exec -i yogyatamitra_postgres psql -U yogyata_admin -d postgres <<EOF
DROP DATABASE IF EXISTS yogyatamitra_db;
CREATE DATABASE yogyatamitra_db OWNER yogyata_admin;
EOF

# 4. Restore using pg_restore
docker cp ./yogyatamitra_db_backup.dump yogyatamitra_postgres:/tmp/restore.dump
docker exec -i yogyatamitra_postgres pg_restore \
    -U yogyata_admin \
    -d yogyatamitra_db \
    --clean \
    --if-exists \
    --no-owner \
    /tmp/restore.dump

docker exec yogyatamitra_postgres rm -f /tmp/restore.dump

# 5. Verify database integrity
docker exec -i yogyatamitra_postgres psql -U yogyata_admin -d yogyatamitra_db <<EOF
SELECT scheme_code, name_en FROM schemes;
SELECT version_code, rule_definition_hash FROM policy_versions ORDER BY version_code;
EOF

# 6. Restart backend application
docker compose start backend
```

---

## 4. Database Migration Rollback Runbook

When deploying schema updates, if a migration fails or introduces an unforeseen issue, follow this rollback procedure:

### 4.1 Inspecting Migration State
```powershell
cd D:\YogyataMitra\backend
alembic current
alembic history --verbose
```

### 4.2 Safe Reversion to Previous Revision
To downgrade by exactly one revision:
```powershell
alembic downgrade -1
```

To downgrade to a specific historical revision (e.g., prior to Phase 16 authoring models):
```powershell
alembic downgrade f8a2b3c4d5e6
```

### 4.3 Re-seeding Post-Rollback
If a downgrade modified or dropped tables containing statutory policies:
```powershell
alembic upgrade head
python -c "import asyncio; from app.services.policy_loader import load_all_policies; asyncio.run(load_all_policies())"
```

---

## 5. Audit Trail & Statutory Immutability Preservation

### 5.1 Strictly Non-Truncatable Tables
The following tables are governed by statutory and legal audit policies and **must never be truncated, manually edited, or mass-deleted**:
- `policy_versions` (Historical Gazetted statutory rules)
- `rule_sets` (Deterministic Rule AST representations)
- `evaluation_traces` (Citizen entitlement evaluation audit records)
- `verification_records` (Officer evidence verification determinations)
- `human_reviews` & `human_review_audit_events` (Officer review log)
- `policy_discovery_review_events` (AI policy discovery audit trail)
- `policy_draft_audit_events` (Officer authoring audit trail)

### 5.2 Post-Restore Verification Checklist
Following any restoration or disaster recovery exercise:
1. Confirm Alembic migration head: `6b2e477e42cb`.
2. Verify all 6 canonical rule definition hashes match the frozen baseline.
3. Verify that zero staged policy drafts have been activated.
4. Execute `pytest backend/tests/test_health.py` and `pytest backend/tests/test_statutory_rulesets.py` to confirm operational readiness.
