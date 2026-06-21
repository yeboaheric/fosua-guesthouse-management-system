# Cloud Deployment Guide

This project is now cloud-ready with:
- production-safe Django settings
- `gunicorn` app server
- `whitenoise` static file serving
- PostgreSQL support via `DATABASE_URL`
- `/healthz/` endpoint for load balancers
- Docker and Docker Compose setup

## Fastest Path (Render + GitHub)

This repository now includes [`render.yaml`](/Users/work/Documents/Fosua%20Guesthouse%20Management%20System/render.yaml), so you can deploy with Render Blueprint.

1. Push latest code to GitHub.
2. In Render dashboard, choose **New** -> **Blueprint**.
3. Connect your GitHub repo: `yeboaheric/fosua-guesthouse-management-system`.
4. Render reads `render.yaml` and creates:
   - web service: `fosua-guesthouse-web`
   - Postgres DB: `fosua-guesthouse-db`
5. During setup, provide:
   - `DJANGO_ALLOWED_HOSTS` = your Render hostname (for example `fosua-guesthouse-web.onrender.com`)
   - `DJANGO_CSRF_TRUSTED_ORIGINS` = `https://your-render-hostname`
6. Deploy.

After first successful deploy, open Render Shell and run:

```bash
python manage.py seed_roles
python manage.py seed_rooms
python manage.py createsuperuser
```

## 1) Required Environment Variables

Use these in your cloud platform:

```bash
DJANGO_ENV=production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=replace-with-long-random-secret
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
DJANGO_SECURE_SSL_REDIRECT=True
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
DB_SSL_REQUIRE=True
```

## 2) Run in Cloud Runtime

The start command is:

```bash
./scripts/start-cloud.sh
```

This command:
1. runs migrations,
2. collects static files,
3. starts `gunicorn`.

## 3) Health Check

Set your cloud health check path to:

```text
/healthz/
```

## 4) Docker Option

Build and run:

```bash
docker compose up --build
```

App URL:
- http://localhost:8000

## 5) Post-Deploy First Steps

Run once after first deployment:
```bash
python manage.py seed_roles
python manage.py seed_rooms
python manage.py createsuperuser
```

## 6) Security Notes

- Keep `DJANGO_DEBUG=False` in production.
- Use HTTPS in front of the app; production redirects HTTP and enables one-year HSTS.
- Rotate `DJANGO_SECRET_KEY` if exposed.
- Keep the generated `DJANGO_SECRET_KEY` stable between deploys so existing sessions and reset links remain valid.
- New passwords use Argon2; existing PBKDF2 passwords upgrade automatically after successful login.
- Sessions expire after 24 hours and authentication endpoints are rate limited.
- Use managed PostgreSQL backups.
