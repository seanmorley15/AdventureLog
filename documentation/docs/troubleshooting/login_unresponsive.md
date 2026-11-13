# Login and Registration Unresponsive

**Symptom:** the login or sign-up button does nothing, or the request fails with an error such as `403` or `ERR_CONNECTION_REFUSED`.

**Cause:** almost always a URL setting that doesn't match the address you open in the browser, so the backend rejects the request as cross-site (CSRF), or the frontend can't reach the backend.

## Fix on Standard Deployment

1. Set `SITE_URL` in `.env` to the exact address in your browser's address bar, including `http://` or `https://` and any port. For example `https://adventurelog.example.com` or `http://192.168.1.20:8015`.
2. Open AdventureLog only at that address. Forms are accepted from the `SITE_URL` origin, so signing in at `http://localhost:8015` fails when `SITE_URL` is your domain.
3. Restart: `docker compose --env-file .env up -d`.

## Fix on Advanced Deployment

1. Open your browser's developer tools, go to the **Network** tab, and try to sign in.
2. If a request fails with `ERR_CONNECTION_REFUSED`, the frontend can't reach the backend. Check that `PUBLIC_SERVER_URL` is `http://server:8000` (the internal Docker address), and that the backend container is running.
3. If it fails with `403`, check the URL settings in `.env.advanced`:
   - `ORIGIN` is the address you use to open the frontend.
   - `CSRF_TRUSTED_ORIGINS` lists both the frontend and backend addresses, and one of them matches `ORIGIN`.
   - Behind a reverse proxy on one domain, set `SITE_URL` instead and delete the four URL settings above, which otherwise take precedence.
4. Restart the containers.

See [URLs](../install/docker.md#urls) for what each setting does. `bash scripts/validate-env.sh .env.advanced` catches common mistakes.

## Still not working

Check the backend log for errors. See [Common Issues](common_issues.md#first-read-the-log).
