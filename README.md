# Fosua Guesthouse Management System

A practical hotel management system built for **Fosua Guesthouse - Aduman**.

This project helps the team run daily guesthouse operations from one place: reservations, rooms, guests, staff, housekeeping, POS sales, payments, finance, reports, analytics, and role-based access control.

It is intentionally built with Django templates instead of a heavy frontend stack, so it stays easy to host, easy to maintain, and friendly for a small hotel team.

## What It Does

- Manage room reservations, check-ins, check-outs, cancellations, and guest records
- Track room status, maintenance, cleaning, availability, and occupancy
- Run POS sales, receipts, payment tracking, and sales reports
- Manage staff records, leave, attendance, duty roster, users, roles, and permissions
- Log housekeeping item usage, stock levels, and low-stock alerts
- Generate Excel reports across bookings, revenue, rooms, housekeeping, POS, staff, and finance
- Track expenses and produce finance summaries such as revenue, expenses, and profit/loss
- Protect sensitive actions with admin/receptionist role permissions

## Tech Stack

- **Backend:** Django 5.2
- **Frontend:** Django Templates, Bootstrap, custom CSS
- **Database:** SQLite for local development, PostgreSQL for production
- **Auth:** Django authentication, groups, permissions, django-axes lockout protection
- **Exports:** openpyxl for Excel reports
- **Receipts/PDF:** ReportLab
- **Deployment:** Render, Gunicorn, WhiteNoise

## Project Structure

```text
accounts/      Users, roles, staff, finance, reports, analytics, permissions
bookings/      Room bookings, event reservations, payments
guests/        Guest records and guest history
inventory/     POS, inventory items, sales, stock, sales reports
rooms/         Rooms, housekeeping, maintenance, operations overview
shifts/        Duty roster and staff scheduling
templates/     Django HTML templates
static/        CSS, JavaScript, images, and UI assets
scripts/       Deployment/startup scripts
config/        Django settings and project URLs
```

## Local Setup

Clone the project and move into the folder:

```bash
cd "Fosua Guesthouse Management System"
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

If an `.env.example` file exists, use it as your starting point:

```bash
cp .env.example .env
```

If there is no `.env.example`, create `.env` manually and add the values you need. For local development, SQLite works out of the box if `DATABASE_URL` is not set, so you can also run the app locally without a database URL.

Run migrations:

```bash
python manage.py migrate
```

Create an admin user:

```bash
python manage.py createsuperuser
```

Start the app:

```bash
python manage.py runserver 127.0.0.1:8000
```

Then open:

```text
http://127.0.0.1:8000/
```

## Useful Commands

Run system checks:

```bash
python manage.py check
```

Create new migrations:

```bash
python manage.py makemigrations
```

Apply migrations:

```bash
python manage.py migrate
```

Run tests:

```bash
python manage.py test
```

Collect static files:

```bash
python manage.py collectstatic
```

## Environment Variables

Common production variables:

```text
DJANGO_ENV=production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=your-secure-secret-key
DATABASE_URL=your-postgres-database-url
DB_SSL_REQUIRE=True
DJANGO_ALLOWED_HOSTS=your-domain.onrender.com,yourdomain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.onrender.com,https://yourdomain.com
```

Important note: `DJANGO_CSRF_TRUSTED_ORIGINS` must include `https://` or `http://`.

## Deployment

This project is ready for Render.

Render uses:

```text
Build command: pip install -r requirements.txt
Start command: ./scripts/start-cloud.sh
```

The startup script runs migrations, collects static files, and starts Gunicorn:

```bash
./scripts/start-cloud.sh
```

Make sure your Render service has a PostgreSQL database connected through `DATABASE_URL`.

## Security Notes

The system includes several production-minded safeguards:

- Argon2 password hashing
- Strong password validation
- Login lockout protection with django-axes
- CSRF protection on forms
- Role-based access checks for sensitive pages and actions
- Secure HTTP headers middleware
- Audit logging for important activity
- Environment-based secrets instead of hardcoded credentials

Still, before going live, always double-check production environment variables, database backups, HTTPS, and user permissions.

## Reports and Exports

Many parts of the system export Excel files, including:

- Bookings and reservations
- Revenue and payments
- POS sales
- Inventory stock
- Housekeeping usage
- Duty roster
- Staff and leave records
- Finance reports

Exports are designed for day-to-day hotel operations, management review, and accounting support.

## A Small Note

This system was built around the real workflow of a guesthouse, not as a generic demo app. The goal is simple: make daily operations calmer, clearer, and easier for the team using it.
