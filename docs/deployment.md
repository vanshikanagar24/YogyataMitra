# YogyataMitra Production Deployment Guide

This document defines the production architecture, security hardening standards, deployment procedures, operational runbooks, and monitoring baselines for the **YogyataMitra** platform.

---

## 1. System Architecture & Topology

In a production environment, YogyataMitra operates as a multi-tier, decoupled architecture designed for high availability, zero-trust boundary isolation, and deterministic reasoning integrity.

```
                              [ Internet / Public Clients ]
                                             │
                                             ▼ HTTPS (443)
                         ┌───────────────────────────────────────┐
                         │      Nginx Reverse Proxy / TLS        │
                         │    (SSL Termination, Rate Limiting)   │
                         └───────┬───────────────────────┬───────┘
                                 │                       │
                       /api/*    │                       │  /*
                                 ▼                       ▼
            ┌─────────────────────────────┐   ┌─────────────────────────────┐
            │   FastAPI Backend Cluster   │   │     Next.js Frontend SSR    │
            │  (Uvicorn / Gunicorn, :8000)│   │        (Node.js, :3000)     │
            └──────────────┬──────────────┘   └─────────────────────────────┘
                           │
                 SQLAlchemy (asyncpg)
                           │
                           ▼
            ┌─────────────────────────────┐
            │   PostgreSQL 16 Database    │
            │   (ACID, Append-Only Audit) │
            └─────────────────────────────┘
```

### Network Topology & Port Mappings
- **Public Ingress**: Ports `80` (HTTP redirect) and `443` (HTTPS TLS 1.3).
- **Frontend Service**: Port `3000` (Internal Docker network / localhost).
- **Backend API Service**: Port `8000` (Internal Docker network / localhost).
- **Database Engine**: Port `5432` (Internal isolated network, never exposed to public internet).

---

## 2. Production Security Hardening Checklist

Prior to launching in a production or publicly accessible environment, execute the following mandatory security controls:

### 2.1 Cryptographic Key Generation
A high-entropy secret key is **mandatory** in production. The backend application refuses to start if `SECRET_KEY` is omitted, uses the dev fallback, or contains `insecure` or `dev-`:

```bash
# Generate a cryptographically secure 256-bit secret key
openssl rand -hex 32
```

Configure this generated string into `.env`:
```ini
ENVIRONMENT=production
SECRET_KEY=e83a9f7...b942
```

### 2.2 Strict CORS Origin Configuration
In production, wildcard `*` CORS origins are forbidden by system validation:
```ini
# Explicitly whitelist production hostnames
CORS_ORIGINS=https://yogyatamitra.gov.in,https://www.yogyatamitra.gov.in
```

### 2.3 Disabling Insecure Demo Accounts
Demo accounts for quick evaluation are strictly prohibited in production mode. The system automatically enforces `ENABLE_DEMO_ACCOUNTS=false` via Pydantic validators:
```ini
ENABLE_DEMO_ACCOUNTS=false
```

### 2.4 Production Database Credentials
Replace all development defaults with unique high-entropy credentials:
```ini
POSTGRES_USER=yogyata_prod_user
POSTGRES_PASSWORD=your_super_secret_db_password
POSTGRES_DB=yogyatamitra_db
POSTGRES_SERVER=db.internal.cluster
POSTGRES_PORT=5432
```

---

## 3. Step-by-Step Production Deployment

### Step 1: Clone Canonical Repository
```bash
git clone https://github.com/vanshikanagar24/YogyataMitra.git /opt/yogyatamitra
cd /opt/yogyatamitra
```

### Step 2: Configure Production Environment Variables
```bash
cp .env.example .env
chmod 600 .env
nano .env
```
Ensure `ENVIRONMENT=production`, a valid `SECRET_KEY`, restricted `CORS_ORIGINS`, and production `POSTGRES_*` credentials are set.

### Step 3: Start PostgreSQL 16
```bash
docker compose up -d postgres
```
Verify PostgreSQL health:
```bash
docker compose ps postgres
```

### Step 4: Run Database Migrations
Execute Alembic migrations to apply all schema revisions through `6b2e477e42cb (head)`:
```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

### Step 5: Materialize Authoritative Statutory Policies
Materialize the 6 authoritative policy versions into PostgreSQL:
```bash
python -c "import asyncio; from app.services.policy_loader import load_all_policies; asyncio.run(load_all_policies())"
```
Verify that exactly 2 schemes (`PM_KISAN`, `SSY`) and 6 policy versions are loaded with matching SHA-256 rule hashes.

### Step 6: Build & Start Frontend
```bash
cd ../frontend
npm ci
npm run build
npm run start -- -p 3000
```

### Step 7: Launch FastAPI Backend
Launch the backend using multiple Uvicorn workers behind a production supervisor (systemd or Gunicorn):
```bash
cd ../backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers
```

---

## 4. Nginx Reverse Proxy Configuration

Below is a hardened production Nginx server block with TLS termination and security headers:

```nginx
server {
    listen 80;
    server_name yogyatamitra.gov.in www.yogyatamitra.gov.in;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yogyatamitra.gov.in www.yogyatamitra.gov.in;

    ssl_certificate /etc/letsencrypt/live/yogyatamitra.gov.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yogyatamitra.gov.in/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # API Backend Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Healthcheck Proxy
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
    }

    # Frontend SSR Proxy
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 5. Health Monitoring & Readiness Probes

YogyataMitra exposes standard HTTP health and readiness endpoints for container orchestrators (Kubernetes, Docker Swarm) and load balancers:

- **Liveness Probe**: `GET /health`
  - Returns `200 OK` with JSON: `{"status": "ok", "service": "YogyataMitra"}`
  - Tests process availability and HTTP server event loop.

- **Readiness Probe**: `GET /health/db`
  - Returns `200 OK` with JSON: `{"status": "ok", "database": "connected", "service": "YogyataMitra"}`
  - Executes active `SELECT 1` ping against PostgreSQL connection pool.

---

## 6. Sizing & Resource Guidelines

| Component | Minimum Sizing (Dev / Staging) | Recommended Production (10,000 req/hr) |
| :--- | :--- | :--- |
| **Backend CPU** | 1 vCPU | 2 - 4 vCPUs |
| **Backend RAM** | 1 GB RAM | 2 - 4 GB RAM |
| **Frontend CPU** | 1 vCPU | 2 vCPUs |
| **Frontend RAM** | 512 MB RAM | 1 - 2 GB RAM |
| **PostgreSQL** | 1 vCPU, 2 GB RAM, 20 GB SSD | 2 - 4 vCPUs, 8 GB RAM, 100 GB SSD (NVMe) |
| **DB Connections**| `pool_size=10`, `max_overflow=20` | `pool_size=30`, `max_overflow=50` |
