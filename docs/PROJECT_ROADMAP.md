# Project Roadmap - Fosua Guesthouse Management System

## Milestone 0: Project Bootstrap (Day 1)

- [ ] Install Python 3.12, PostgreSQL 16
- [ ] Create virtual environment
- [ ] Install Django + dependencies
- [ ] Start Django project and apps
- [ ] Configure `.env` and settings split (`dev` and `prod`)
- [ ] First git commit

## Milestone 1: Authentication and Roles (Day 2-3)

- [ ] Custom user model (email/username strategy)
- [ ] Login/logout pages
- [ ] Role groups:
  - Admin
  - Receptionist
- [ ] Permission checks on views
- [ ] Basic dashboards by role

## Milestone 2: Rooms and Availability (Day 4-6)

- [ ] Room model (number, type, status, rate)
- [ ] Room status transitions:
  - Available
  - Occupied
  - Maintenance
- [ ] Availability search by date range
- [ ] Room CRUD screens (Admin-only)

## Milestone 3: Guests and Bookings (Week 2)

- [ ] Guest model (name, phone, ID, address)
- [ ] Booking model (guest, room, dates, total, status)
- [ ] Booking validation (no double-booking)
- [ ] Check-in flow
- [ ] Check-out flow

## Milestone 4: Receipts and Reports (Week 3)

- [ ] Generate printable PDF receipt
- [ ] Receipt number sequence
- [ ] Daily occupancy report
- [ ] Daily/weekly revenue report

## Milestone 5: Security and Stability (Week 4)

- [ ] Password policy
- [ ] Account lockout/rate limiting
- [ ] CSRF and secure cookie settings
- [ ] Audit log for sensitive actions
- [ ] Error pages and server logging
- [ ] Automated daily backups

## Milestone 6: Deployment and Handover (Week 5)

- [ ] Deploy on Ubuntu server
- [ ] Nginx + Gunicorn setup
- [ ] HTTPS certificate
- [ ] Domain/subdomain setup
- [ ] Admin manual (1-2 pages)
- [ ] Receptionist quick guide

## Quality Gates (must pass each milestone)

1. Feature works on local test data.
2. Permissions are enforced correctly.
3. No known high-risk security issues.
4. Basic test coverage added for new logic.
5. Documentation updated.

