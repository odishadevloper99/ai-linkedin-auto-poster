# 24/7 AI Career + LinkedIn Automation

Production-oriented Flask service designed for a Render Web Service plus GitHub Actions scheduler. It uses Firebase Realtime Database for persistent state; no Render Cron or PostgreSQL resource is required.

## Architecture

GitHub Actions runs every 30 minutes and calls the protected Render endpoints. Firebase stores job fingerprints, job status, agent runs, locks, LinkedIn post history, settings and usage state.

## Required Render environment variables

Set the Firebase credentials/database URL, `CRON_SECRET`, AI/provider credentials, Telegram credentials, LinkedIn credentials, and career profile variables listed in `.env.example`.

`LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` are retained for configuration compatibility, while the current publishing flow uses the official LinkedIn REST APIs with `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_USER_URN`.

## Required GitHub Actions secrets

Only these two secrets are needed by the scheduler:

- `RENDER_BASE_URL`
- `CRON_SECRET`

Provider secrets stay on Render and are never copied into GitHub Actions.

## Firebase

Create a Firebase project, enable Realtime Database, create a service account, and store the complete service-account JSON as the `FIREBASE_SERVICE_ACCOUNT_JSON` Render secret. Set `FIREBASE_DATABASE_URL` to the Realtime Database URL.

Use Firebase Security Rules appropriate for the project. The service account is server-side only and must never be exposed to browser/client code.

## Deployment

1. Create a Render Blueprint from this repository.
2. Render creates only the Web Service from `render.yaml`.
3. Add the required secret environment variables.
4. Deploy and verify `/health` and `/status`.
5. Add `RENDER_BASE_URL` and the same `CRON_SECRET` to GitHub repository Actions secrets.
6. Run the workflow manually once with `both` to verify the end-to-end path.

## Scheduler behavior

GitHub Actions provides the 30-minute scheduler. Render only hosts the API. Each protected endpoint is independently lock-protected in Firebase so overlapping executions do not duplicate work.

## Security

Secrets are environment variables only. The internal endpoints require `X-Cron-Secret`. Telegram administrative commands require the configured admin user ID. LinkedIn publishing uses official REST APIs only.
