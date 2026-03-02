# AutoRia Clone

Car marketplace REST API built with Django 5.1 + Django REST Framework.

## Tech Stack

- **Backend:** Django 5.1.4, Django REST Framework 3.15.2
- **Database:** MySQL 8.0 (cloud-hosted via Railway)
- **Cache / Broker:** Redis 7
- **Task Queue:** Celery 5.4 + Celery Beat
- **Auth:** JWT (`djangorestframework-simplejwt`) with token blacklist
- **API Docs:** drf-spectacular (Swagger UI at `/api/docs/`)
- **Containerization:** Docker, Docker Compose

## Requirements

- Docker & Docker Compose (tested with Docker 29.x, Compose v5.x)

> The MySQL database is hosted on Railway (cloud). No local MySQL installation needed.

---

## Quick Start

```bash
git clone <repo-url>
cd exam-python-drf

# Create .env file (copy the ready-to-use test config below)
cp .env.example .env
```

Edit `.env` with the following values (test database on Railway is already provisioned):

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (MySQL — Railway Cloud)
MYSQL_DB=railway
MYSQL_USER=root
MYSQL_PASSWORD=WwvfhrSVInoMcySuHcgksrqzeHZTgQch
MYSQL_HOST=ballast.proxy.rlwy.net
MYSQL_PORT=10837

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Admin user (created automatically on first run by seed_data)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=Admin123456
```

Then build and start all services:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.
Swagger UI: `http://localhost:8000/api/docs/`

On first start the container automatically:
1. Runs all database migrations
2. Seeds roles, permissions, regions, car brands/models, and the admin user

---

## Test Credentials

### Admin account (seeded automatically)

| Field | Value |
|-------|-------|
| Email | `admin@example.com` |
| Password | `Admin123456` |
| Role | `admin` |

### Test database (Railway Cloud MySQL)

| Parameter | Value |
|-----------|-------|
| Host | `ballast.proxy.rlwy.net` |
| Port | `10837` |
| Database | `railway` |
| User | `root` |
| Password | `WwvfhrSVInoMcySuHcgksrqzeHZTgQch` |

> This is a shared test database. It is pre-seeded with roles, permissions, regions, car brands and models on first `docker compose up`.

---

## Docker Services

| Service | Description | Port |
|---------|-------------|------|
| `app` | Django + Gunicorn | 8000 |
| `celery` | Celery worker (currency rates) | — |
| `celery-beat` | Celery scheduler (daily task) | — |
| `redis` | Message broker + cache | internal only |

> Redis port is not exposed externally — it is only accessible between containers.
> The database runs externally on Railway. No local MySQL container is needed.

---

## Running Tests

Tests use SQLite in-memory (no MySQL connection required):

```bash
docker compose run --rm app python manage.py test --verbosity=2
```

Expected result: **120 tests, 0 failures**.

---

## API Endpoints

### Authentication (`/api/auth/`)
| Method | URL | Description | Access |
|--------|-----|-------------|--------|
| POST | `/api/auth/register` | Register buyer or seller | Public |
| POST | `/api/auth/login` | Login, receive JWT | Public |
| POST | `/api/auth/refresh` | Refresh access token | Authenticated |
| POST | `/api/auth/logout` | Logout, blacklist refresh token | Authenticated |

### Users (`/api/users/`)
| Method | URL | Description | Access |
|--------|-----|-------------|--------|
| GET | `/api/users/me` | My profile | Authenticated |
| PATCH | `/api/users/me` | Update profile | Authenticated |
| GET | `/api/users/` | List all users | Manager / Admin |
| GET | `/api/users/{id}` | User details | Manager / Admin |
| PATCH | `/api/users/{id}/ban` | Ban user | Manager / Admin |
| PATCH | `/api/users/{id}/unban` | Unban user | Manager / Admin |
| POST | `/api/users/create-manager` | Create manager account | Admin |
| POST | `/api/users/upgrade-premium` | Upgrade seller to premium | Seller |

### Cars (`/api/cars/`)
| Method | URL | Description | Access |
|--------|-----|-------------|--------|
| GET | `/api/cars/brands` | List all brands | Public |
| POST | `/api/cars/brands` | Add brand | Admin |
| GET | `/api/cars/brands/{id}/models` | List models for a brand | Public |
| POST | `/api/cars/brands/{id}/models` | Add model | Admin |
| POST | `/api/cars/brand-requests` | Request new brand / model | Seller |
| GET | `/api/cars/brand-requests` | List brand requests | Manager / Admin |
| PATCH | `/api/cars/brand-requests/{id}` | Approve or reject request | Admin |

### Listings (`/api/listings/`)
| Method | URL | Description | Access |
|--------|-----|-------------|--------|
| GET | `/api/listings/` | Browse listings (filterable) | Public |
| POST | `/api/listings/` | Create listing | Seller |
| GET | `/api/listings/{id}` | Listing detail + seller contacts | Public |
| PATCH | `/api/listings/{id}` | Edit listing | Owner |
| DELETE | `/api/listings/{id}` | Delete listing | Owner / Manager / Admin |
| GET | `/api/listings/my` | My listings | Seller |
| GET | `/api/listings/pending` | Listings needing review | Manager / Admin |
| PATCH | `/api/listings/{id}/deactivate` | Deactivate listing | Manager / Admin |
| PATCH | `/api/listings/{id}/activate` | Activate listing | Manager / Admin |

### Statistics (`/api/statistics/`) — Premium sellers only
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/statistics/listings/{id}` | Full stats (views + avg prices) |
| GET | `/api/statistics/listings/{id}/views` | View counts (today / week / month / all) |
| GET | `/api/statistics/listings/{id}/avg-price` | Average prices by region / Ukraine |

### Currency (`/api/currency/`)
| Method | URL | Description | Access |
|--------|-----|-------------|--------|
| GET | `/api/currency/rates` | Current USD/EUR exchange rates | Public |

> Rates are fetched automatically from PrivatBank every day via Celery Beat.

### Dealerships (`/api/dealerships/`)
| Method | URL | Description | Access |
|--------|-----|-------------|--------|
| GET | `/api/dealerships/` | List dealerships | Public |
| POST | `/api/dealerships/` | Create dealership | Authenticated |

---

## Listing Filters

```
GET /api/listings/?car_brand=1&car_model=2&region=3&price_min=5000&price_max=30000&year_min=2015&year_max=2024&engine_type=diesel
```

---

## Business Rules

- **Basic seller**: 1 active listing limit. Upgrade to premium to create more.
- **Profanity filter**: listing description is checked on create/edit. Clean → `active`. Profanity detected → `needs_edit`. After 3 failed edit attempts → `inactive` + manager notified by email.
- **Currency**: listing price is stored in the original currency and converted to USD / EUR / UAH automatically using the latest PrivatBank rates.
- **Statistics**: view counts and average prices are available only to premium account sellers for their own listings.

---

## Project Structure

```
exam-python-drf/
├── apps/
│   ├── authentication/   # Register, login, JWT refresh & logout
│   ├── users/            # Profiles, premium upgrade, ban/unban
│   ├── roles/            # Custom RBAC: roles + permissions
│   ├── cars/             # Brands, models, brand requests
│   ├── listings/         # Listings CRUD, profanity, price conversion
│   ├── currency/         # PrivatBank rates, Celery task
│   ├── statistics/       # Premium view counts & average prices
│   ├── notifications/    # Email notifications to managers
│   └── dealerships/      # Dealership management
├── core/                 # Shared pagination and permissions
├── configs/              # Django settings, URLs, Celery config
├── profanity/words.txt   # Profanity word list
├── postman/              # Postman collection (42 requests)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── manage.py
```
