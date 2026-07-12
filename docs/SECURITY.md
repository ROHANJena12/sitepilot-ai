# Security

**Product:** SitePilot AI  
**Status:** Operational controls (Sprint 35) + ongoing hardening

---

## Reporting a vulnerability

Please report security issues privately. Do not file public GitHub issues for vulnerabilities.

Include:

- Description of the issue
- Impact assessment (if known)
- Steps to reproduce
- Affected component / version (if known)

Response targets (aspirational until a formal SLA exists):

- Acknowledgement within 3 business days
- Status update within 10 business days

---

## Current controls

| Control | Implementation |
|---------|----------------|
| Security headers | API middleware + Next.js `headers()` (CSP, Referrer-Policy, XCTO, XFO, Permissions-Policy; HSTS in production) |
| SSRF protection | URL Validation Engine on outbound audit fetches |
| Signed share links | HMAC tokens; invalid/tampered → 404; expired → 410 |
| Secrets | Environment variables / secret manager — never commit |
| Error envelopes | No stack traces in client responses |
| Rate limiting | IP sliding windows on audit create, AI generate, share create |
| Startup validation | Production fail-fast for insecure `SECRET_KEY`, `DEBUG`, DB URL, provider keys |
| Logging hygiene | No API keys / prompts in structured logs |

See also: [`docs/DEPLOYMENT.md`](./DEPLOYMENT.md), [`docs/API_SPEC.md`](./API_SPEC.md) §21–22.

---

## Planned / future

| Practice | Intent |
|----------|--------|
| AuthN / AuthZ | Tenant isolation for multi-user plans |
| Edge WAF / distributed rate limits | Multi-replica deployments |
| Dependency scanning | CI supply-chain checks (Dependabot / similar) |
| Asymmetric JWT | Production auth tokens |

---

## Responsible disclosure

Coordinate fixes before public disclosure. Credit will be given where appropriate and requested.
