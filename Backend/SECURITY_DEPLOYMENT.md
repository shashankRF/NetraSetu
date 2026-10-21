# NetraSetu security setup

The local `development` mode intentionally exposes demo credentials (`admin` / `admin123`). It is for a local prototype only and is not a secure production deployment.

## Production setup

1. Install `Backend/requirements-security.txt` in the same Python environment as the app.
2. Generate an Argon2id password hash without putting the password in shell history:

   ```powershell
   python -c "from getpass import getpass; from argon2 import PasswordHasher; print(PasswordHasher().hash(getpass()))"
   ```

3. Configure `NETRASETU_ENV=production`, `NETRASETU_ADMIN_USERNAME`, and `NETRASETU_ADMIN_PASSWORD_HASH` in the deployment secret store. Do not set `NETRASETU_ADMIN_PASSWORD` in production. The service fails closed if the production username/hash is missing.
4. Terminate TLS 1.3 at a trusted reverse proxy/load balancer and forward the HTTPS scheme to Uvicorn using trusted proxy settings. The app rejects HTTP in production and emits HSTS on HTTPS responses. Do not expose the Uvicorn port directly to the internet.

The app uses server-side, in-memory sessions with a 30-minute expiry, HttpOnly/Secure (in production)/SameSite=Strict cookies, CSRF tokens on authenticated state-changing requests, and an eight-failure/15-minute per-client-and-account login lockout. Sessions are lost on server restart and are not shared across multiple workers; use a shared session store before scaling horizontally. TOTP/passkeys, CAPTCHA, persistent encrypted sensitive fields, and production TLS termination are not implemented. This prototype should not be described as independently audited or production-certified.
