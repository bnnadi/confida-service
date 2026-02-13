# Production Deployment Checklist

Use this checklist before deploying confida-service to production. Run the automated validation script first, then complete manual verification steps.

**Related:** [PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md) | [Rollback Procedures](#rollback-procedures)

---

## Quick Start

```bash
# 1. Run automated validation (local or remote)
python scripts/validate_production_readiness.py --url http://localhost:8000

# 2. Quick monitoring check
./scripts/check_monitoring.sh http://localhost:8000

# 3. Complete manual checklist below
```

---

## 1. Privacy Requirements

- [ ] **Consent endpoints live** — `GET /api/v1/consent/` and `PUT /api/v1/consent/` return expected responses
  - Verify: `curl -s -o /dev/null -w "%{http_code}" https://your-api/api/v1/consent/` returns `401` (unauthenticated)
- [ ] **Data export works** — `GET /api/v1/data-rights/export` returns user data when authenticated
  - Verify: Authenticated request returns JSON with `user`, `sessions`, `consents`, etc.
- [ ] **Account deletion works** — `POST /api/v1/data-rights/delete-account` with password confirmation
  - Verify: Endpoint requires `password` in body and removes all user data
- [ ] **Consent history tracked** — `GET /api/v1/consent/history` returns audit trail
  - Verify: Consent changes are logged with timestamps

**Dependencies:** INT-30 (Privacy Policy & Consent) — Done

---

## 2. Security Measures

- [ ] **SECRET_KEY not default** — Must not be `your-secret-key-change-this-in-production`
  - Verify: `echo $SECRET_KEY | grep -v "your-secret-key"` (should not match)
- [ ] **HTTPS enforced** — Production served over HTTPS; HSTS headers enabled
  - Verify: `curl -sI https://your-api/health | grep -i strict-transport`
- [ ] **Security headers on** — `SECURITY_HEADERS_ENABLED=true`
  - Verify: Response includes `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`
- [ ] **Rate limiting enabled** — `RATE_LIMIT_ENABLED=true`
  - Verify: `RATE_LIMIT_ENABLED` is set in environment
- [ ] **Debug/admin routes** — `ENABLE_DEBUG_ROUTES=false`, `ENABLE_SECURITY_ROUTES=false` in production

**Verification command:**
```bash
curl -sI https://your-api/health | grep -E "X-Content-Type-Options|X-Frame-Options"
```

---

## 3. Compliance Verification

- [ ] **GDPR data rights** — Export and delete endpoints functional (see Privacy section)
- [ ] **Audit logging (INT-32)** — Status: In Progress. Document current state before deploy.
- [ ] **Encryption (INT-31)** — `ENCRYPTION_ENABLED=true` and `ENCRYPTION_MASTER_KEY` set when required
  - Verify: Sensitive data encrypted at rest when encryption is enabled
- [ ] **Data retention** — Cleanup/maintenance (INT-34) configured if applicable

**Dependencies:** INT-30 Done, INT-31 Done, INT-32 In Progress

---

## 4. Performance

- [ ] **Health checks pass** — `GET /health` returns 200 with `status: healthy` or `degraded` (not `unhealthy` for critical services)
  - Verify: `curl -s https://your-api/health | jq '.status'`
- [ ] **Response time** — `/health` responds in < 500ms under normal load
- [ ] **DB pool configured** — `DATABASE_POOL_SIZE`, `ASYNC_DATABASE_POOL_SIZE` set for production load
- [ ] **Migrations applied** — `alembic current` matches `alembic heads`

**Verification:**
```bash
curl -s -w "\nTime: %{time_total}s\n" -o /dev/null https://your-api/health
alembic current
alembic heads
```

---

## 5. Accessibility (API)

- [ ] **Error formats** — API returns structured JSON errors (`detail`, `status_code`) for frontend consumption
- [ ] **CORS configured** — `CORS_ORIGINS` includes production frontend domain(s)
  - Verify: `curl -sI -X OPTIONS -H "Origin: https://your-frontend.com" https://your-api/health` returns CORS headers

---

## 6. Cross-Browser (API)

- [ ] **API contract stable** — No browser-specific assumptions; standard HTTP/JSON
- [ ] **Content-Type** — Responses use `application/json` where appropriate

---

## 7. Staging Validation

- [ ] **Staging env deployed** — Railway preview or separate staging project
- [ ] **Env vars set** — `ENVIRONMENT=staging` or similar to distinguish from prod
- [ ] **Validation script passes** — `python scripts/validate_production_readiness.py --url https://staging-url`
- [ ] **Smoke test** — Auth, create session, consent endpoints, data export work end-to-end
- [ ] **Health endpoints** — `/health`, `/ready` return 200

**Smoke test commands:**
```bash
# Health
curl -s https://staging-url/health | jq '.status'

# Readiness
curl -s https://staging-url/ready | jq '.ready'

# Consent (unauthenticated should return 401)
curl -s -o /dev/null -w "%{http_code}" https://staging-url/api/v1/consent/
```

---

## 8. Rollback Procedures

### Railway

1. Open Railway dashboard → Project → confida-service
2. Go to **Deployments** tab
3. Find the last known good deployment
4. Click **Redeploy** or **Rollback** to redeploy that commit
5. Verify: `curl -s https://your-api/health | jq '.status'`

### Docker

```bash
# Stop current deployment
docker-compose -f docker-compose.prod.yml down

# Restore previous image (if using tagged images)
# docker pull your-registry/confida:previous-tag

# Start previous version
docker-compose -f docker-compose.prod.yml up -d

# Verify
curl -f http://localhost:8000/health || exit 1
```

### Database Migrations

```bash
# Roll back one revision
alembic downgrade -1

# Roll back to specific revision
alembic downgrade <revision_id>

# Check current revision
alembic current
```

**Note:** Not all migrations are reversible. Review `alembic/versions/` for `downgrade()` implementations before rolling back.

### Post-Rollback Verification

- [ ] Health check returns 200
- [ ] Critical endpoints respond (auth, sessions, consent)
- [ ] No new errors in logs

---

## 9. Monitoring Setup

- [ ] **Healthcheck path** — Railway/Docker uses `/health` (see `railway.json`, `docker-compose.prod.yml`)
- [ ] **Prometheus scraping** — If `MONITORING_ENABLED=true`, `/api/v1/health/metrics` is scraped
- [ ] **Alerting** — Alerts configured for health check failures, high error rate
- [ ] **Logs** — Production logs aggregated and searchable

**Verification:**
```bash
./scripts/check_monitoring.sh https://your-api
```

---

## Dependencies Status

| Ticket | Description | Status |
|--------|-------------|--------|
| INT-30 (T-28) | Privacy Policy & Consent | Done |
| INT-31 (T-29) | Data Encryption | Done |
| INT-32 (T-30) | Audit Logging | In Progress |
| T-18 | Session persistence | Exists (sessions API) |
| Security audit | Full security audit | Document as pending/completed |

---

## Pre-Deployment Summary

Before deploying, ensure:

1. Automated script passes: `python scripts/validate_production_readiness.py --url <target-url>`
2. All checklist sections above completed
3. Rollback procedure reviewed and tested in staging
4. Monitoring and alerting verified
