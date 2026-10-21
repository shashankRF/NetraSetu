# Troubleshooting email configuration

Troubleshooting reports are stored as JSON Lines in `Backend/support/reports/reports.jsonl` and accepted attachments are stored below the same directory. Reports contain the submitter's account name and the report content; do not include credentials or secrets.

Email is optional. Without all of `NETRASETU_SUPPORT_EMAIL`, `NETRASETU_SMTP_HOST`, and `NETRASETU_SMTP_FROM`, submissions are retained locally and the UI reports that delivery is not configured. Configure the following server-side environment variables to enable delivery:

- `NETRASETU_SUPPORT_EMAIL`: maintainer-configured recipient address (no default is supplied).
- `NETRASETU_SMTP_HOST`, `NETRASETU_SMTP_PORT` (default 587), `NETRASETU_SMTP_FROM`.
- `NETRASETU_SMTP_USERNAME`, `NETRASETU_SMTP_PASSWORD` when the relay requires authentication.
- `NETRASETU_SMTP_USE_SSL` (`true` for implicit TLS; otherwise STARTTLS), `NETRASETU_SMTP_TIMEOUT` (default 10 seconds).

Authentication is server enforced. Local development retains the demo account `admin` / `admin123`; do not expose development mode publicly. Production requires `NETRASETU_ENV=production`, `NETRASETU_ADMIN_USERNAME`, and an Argon2id hash in `NETRASETU_ADMIN_PASSWORD_HASH` (never set `NETRASETU_ADMIN_PASSWORD` in production). Session expiry, CSRF and TLS deployment setup are documented in [SECURITY_DEPLOYMENT.md](../SECURITY_DEPLOYMENT.md). Reports remain local JSONL files unless SMTP is configured; protect the report directory and backups as sensitive data.
