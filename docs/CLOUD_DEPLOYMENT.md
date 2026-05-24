# Cloud Deployment Guide

This project is now cloud-ready with:
- production-safe Django settings
- `gunicorn` app server
- `whitenoise` static file serving
- PostgreSQL support via `DATABASE_URL`
- `/healthz/` endpoint for load balancers
- Docker and Docker Compose setup

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
- Use HTTPS in front of the app.
- Rotate `DJANGO_SECRET_KEY` if exposed.
- Use managed PostgreSQL backups.
