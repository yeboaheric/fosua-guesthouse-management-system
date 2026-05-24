# Fosua Guesthouse Management System

This is the software system for **Fosua Guesthouse - Aduman** (12 rooms).

Goal: a secure, beginner-friendly hotel management system with:
- room availability tracking
- guest booking and guest records
- receptionist and admin logins (role-based access)
- printable booking receipts

## 1) Recommended Stack (Beginner-Friendly + Secure)

As of **May 23, 2026**, we should use currently supported versions:
- **Backend + Frontend:** Django 5.2 (LTS)
- **Database:** PostgreSQL 16+
- **UI:** Django templates + Bootstrap 5
- **Authentication:** Django auth + groups (Admin, Receptionist)
- **Receipt PDF:** ReportLab
- **Server (production):** Nginx + Gunicorn + Ubuntu LTS

Why this stack:
- One language (Python) across the whole app.
- Django includes strong security defaults.
- Easy to learn and maintain for a single business.
- Scales comfortably for a 12-room guesthouse and beyond.

## 2) Security-First Rules from Day 1

1. Never store plain passwords.
2. Use role-based permissions for every page/action.
3. Use environment variables for secrets (`.env`), never hardcode keys.
4. Use PostgreSQL in production, not SQLite.
5. Use HTTPS in production.
6. Log critical actions (check-in, check-out, booking edits, cancellations).
7. Keep dependencies updated.
8. Daily database backup.

## 3) Local Setup (Mac) - Step by Step

### A. Install Python 3.12 and PostgreSQL

If Homebrew is not installed:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install Python and PostgreSQL:
```bash
brew install python@3.12 postgresql@16
brew services start postgresql@16
```

Confirm:
```bash
python3.12 --version
psql --version
```

If you do not have Administrator (`sudo`) access on your Mac, use a local Python install:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
UV_CACHE_DIR=/private/tmp/uv-cache UV_PYTHON_INSTALL_DIR="$PWD/.uv-python" /Users/work/.local/bin/uv python install 3.12
```

Then use this Python path:
```bash
./.uv-python/cpython-3.12.13-macos-aarch64-none/bin/python3.12 --version
```

### B. Create project virtual environment

From this project folder:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

If you used local `uv` Python above:
```bash
./.uv-python/cpython-3.12.13-macos-aarch64-none/bin/python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### C. Install core dependencies
```bash
pip install "Django>=5.2,<5.3" psycopg[binary] django-environ reportlab
```

### D. Start Django project
```bash
django-admin startproject config .
python manage.py startapp accounts
python manage.py startapp rooms
python manage.py startapp bookings
python manage.py startapp guests
python manage.py startapp receipts
```

If this repository is already scaffolded, skip this step.

### E. Create PostgreSQL database
```bash
createdb fosua_guesthouse
```

Then configure `.env` with DB credentials and Django secrets.

If PostgreSQL is not yet available locally, use SQLite temporarily for local development and switch to PostgreSQL before production.

### F. Run migrations and seed roles
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_roles
python manage.py seed_rooms
```

### G. Create the first admin user
```bash
python manage.py createsuperuser
```

Assign a role to any user:
```bash
python manage.py assign_role <username> Admin
python manage.py assign_role <username> Receptionist
```

### H. Run the development server
```bash
python manage.py runserver 127.0.0.1:8000
```

## 4) System Modules

- `accounts`: login/logout, user roles, permissions
- `rooms`: room types, room status, nightly rates
- `guests`: guest personal details and history
- `bookings`: reservation, check-in, check-out, payments
- `receipts`: printable invoice/receipt PDF

## 5) Development Phases

### Phase 1 - Foundation
- Project setup
- User authentication
- Role-based dashboards

### Phase 2 - Core Operations
- Room management
- Booking flow
- Check-in/check-out

### Phase 3 - Business Features
- Receipt printing
- Reporting (occupancy, revenue, unpaid balances)
- Activity logs

### Phase 4 - Hardening
- Security review
- Backups
- Deployment

See full roadmap in:
- [`docs/PROJECT_ROADMAP.md`](/Users/work/Documents/Fosua%20Guesthouse%20Management%20System/docs/PROJECT_ROADMAP.md)

## 6) Current Progress

Completed:
1) secure auth entry points (login/logout)
2) role-based dashboards (Admin + Receptionist)
3) core data models (`Room`, `Guest`, `Booking`)
4) booking overlap validation and initial tests

Next:
1) booking create/check-in/check-out screens
2) room availability calendar/search
3) printable booking receipt PDF

## 7) Current Working Features

- Role-based login and dashboard routing
- Room management pages (list, create, edit)
- Guest management pages (list, create, edit)
- Booking management pages:
  - create and edit booking
  - confirm booking
  - check-in
  - check-out
  - cancel
- Room availability search by date range

## 8) Daily Startup Commands

```bash
cd "/Users/work/Documents/Fosua Guesthouse Management System"
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8000
```

## 9) Cloud-Ready Setup

Cloud deployment files added:
- [`Dockerfile`](/Users/work/Documents/Fosua Guesthouse Management System/Dockerfile)
- [`docker-compose.yml`](/Users/work/Documents/Fosua Guesthouse Management System/docker-compose.yml)
- [`Procfile`](/Users/work/Documents/Fosua Guesthouse Management System/Procfile)
- [`scripts/start-cloud.sh`](/Users/work/Documents/Fosua Guesthouse Management System/scripts/start-cloud.sh)

Detailed cloud guide:
- [`docs/CLOUD_DEPLOYMENT.md`](/Users/work/Documents/Fosua Guesthouse Management System/docs/CLOUD_DEPLOYMENT.md)
