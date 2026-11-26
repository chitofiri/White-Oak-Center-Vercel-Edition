#Client Portal

## Important
This is a deployment-adapted development build, **not certified or ready for real children's, court or safeguarding records**. Before live use, complete a UK GDPR/DPA 2018 DPIA and lawful-basis review, safeguarding/access policy approval, independent security testing, MFA/session hardening, retention and deletion workflows, malware scanning, backups and restore tests.

## Architecture
- FastAPI exposed as a Vercel Python Function at `api/index.py`.
- Static frontend served from `web/`.
- External persistent PostgreSQL database (Neon, Supabase Postgres, or another managed PostgreSQL provider).
- Private S3-compatible object storage for PDF files (for example Cloudflare R2 or AWS S3). Vercel function filesystems are ephemeral; local disk storage is disabled for production.
- SQLAlchemy creates missing tables automatically at cold start. `create_all` does not modify existing tables; use reviewed Alembic migrations for future schema changes.

## Deploy to Vercel
1. Upload the **contents** of this folder to a GitHub repository root. Keep `api/`, `app/`, and `web/` folders.
2. In Vercel choose **Add New → Project**, import the GitHub repository, and leave the Root Directory as the repository root.
3. Framework preset: **Other**. Build command: leave blank. Output directory: leave blank. Vercel uses `vercel.json`.
4. Provision a managed PostgreSQL database. Copy its connection string. It must be reachable from Vercel and should include TLS (`sslmode=require` where supported).
5. Provision a private S3-compatible bucket. Do not make the bucket public. Create a bucket access key with only the permissions required for this bucket.
6. Add these variables in Vercel → Project → Settings → Environment Variables (Production and Preview only if needed):
   - `ENVIRONMENT=production`
   - `DATABASE_URL` = PostgreSQL connection string
   - `JWT_SECRET` = output of `python -c "import secrets; print(secrets.token_urlsafe(48))"` (never commit/share)
   - `ACCESS_TOKEN_MINUTES=20`
   - `MAX_PDF_MB=3` (Vercel request payload limit means this server-mediated upload is deliberately limited)
   - `S3_BUCKET` = private bucket name
   - `S3_ENDPOINT_URL` = provider's S3 endpoint (for AWS S3 this may be blank)
   - `S3_REGION` = provider region
   - `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY`
   - `BOOTSTRAP_ADMIN_EMAIL` = first administrator email
   - `BOOTSTRAP_ADMIN_PASSWORD` = unique password of at least 14 characters
7. Deploy. On first cold start, the app tests the database, creates missing tables and creates the first administrator if that email does not already exist.
8. Confirm `/api/health` returns `{"status":"ok","database":"connected","environment":"production"}`.
9. Test login, create a fictional test client/case, grant case access, upload/download a small test PDF, and verify that the client can only see explicitly shared documents.
10. After confirming the administrator account exists, remove `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` from Vercel variables and redeploy.

## Required configuration notes
- **Do not use SQLite or a local Vercel file path in production.** Vercel instances are ephemeral.
- **Do not omit S3 settings.** Production startup refuses to run without the private object storage bucket and credentials.
- Use a private bucket with encryption at rest, restricted access, versioning/backups and appropriate UK data residency and processor terms. Provider configuration alone does not establish legal compliance.
- The current API uploads files through the function and is capped at 3 MB to stay below Vercel's request body limit. Larger files need a separate presigned direct-to-object-storage upload workflow.
- Vercel functions can cold start and scale horizontally. The SQLAlchemy connection pool is intentionally small. Use a serverless/pooled PostgreSQL connection URL where the database provider offers one.
- `create_all` handles missing tables only, not schema upgrades. Add Alembic migrations before evolving the database schema.
- First-admin bootstrap is idempotent; remove the bootstrap variables after account creation.
- Railway-specific configuration is retained only as an optional file and is not used by Vercel.

## Local development
Set `ENVIRONMENT=development`, a strong `JWT_SECRET`, and a local or managed PostgreSQL URL in `.env`. For local-only development, S3 can be omitted and PDFs are stored in `PRIVATE_UPLOAD_DIR`. Install dependencies with `pip install -r requirements.txt`, then run `uvicorn app.main:app --reload`. Open `http://127.0.0.1:8000`.

## Current feature boundaries
This build retains case management, explicit per-client case permissions, document sharing, contact sessions, referral submissions, restricted safeguarding notes and audit events. It does not yet implement email delivery, MFA, approved secure-cookie sessions/CSRF, malware scanning, complete safeguarding break-glass workflows, immutable audit storage, final approved referral forms, scheduling conflict management or full UK GDPR rights/retention automation.
