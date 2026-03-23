# AutoRia Clone

Car marketplace REST API — Django REST Framework exam project.

## Tech Stack

- **Backend:** Django 5.1.4, Django REST Framework 3.15.2
- **Database:** MySQL 8.0 (external cloud)
- **Cache / Broker:** Redis 7
- **Task Queue:** Celery 5.4 + Celery Beat
- **Auth:** JWT (`djangorestframework-simplejwt`) with token blacklist
- **API Docs:** Swagger UI at `http://localhost:8000/api/docs/`
- **Containerization:** Docker, Docker Compose

---

## How to Run

### Requirements
- Docker and Docker Compose
- A MySQL 8.0 database (cloud or local)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/IhnatVelykoivan/exam-python-drf.git
cd exam-python-drf

# 2. Create the .env file from the example
cp .env.example .env

# 3. Open .env and fill in your MySQL credentials:
#    MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT

# 4. Build and start all services
docker compose up --build
```

The API will be available at **`http://localhost:8000`**

On first start the app automatically:
1. Connects to the MySQL database
2. Runs all migrations (creates all tables)
3. Seeds initial data: roles, permissions, 25 regions, 15 car brands with models, currency rates
4. Creates the admin user (see credentials below)

---

## Credentials

### Admin account (created automatically on first start)

| Field | Value |
|-------|-------|
| Email | `admin@autoria.ua` |
| Password | `Admin123!` |

### Test accounts (created by running the Postman collection)

| Role | Email | Password |
|------|-------|----------|
| Seller | `seller@test.ua` | `Seller123!` |
| Buyer | `buyer@test.ua` | `Buyer123!` |
| Manager | `manager@test.ua` | `Manager123!` |

---

## Docker Services

| Service | Description | Port |
|---------|-------------|------|
| `redis` | Message broker and cache | 6379 |
| `app` | Django + Gunicorn (main API) | **8000** |
| `celery` | Async worker (currency rate updates) | — |
| `celery-beat` | Scheduler (runs currency update daily) | — |

> The MySQL database runs externally. Connection is configured via `.env`.

---

## Running the Postman Tests

The collection covers the full application flow in 42 requests.

### Reset the database before each test run

If the database already has test data from a previous run, clean it first:

```bash
docker compose exec app python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.cars.models import CarBrand
User = get_user_model()
User.objects.filter(email__in=['seller@test.ua','buyer@test.ua','manager@test.ua']).delete()
CarBrand.objects.filter(name='Lamborghini').delete()
print('DB reset — ready for testing')
"
```

### Import and run

1. Open **Postman**
2. Click **Import** → select `postman/AutoRia_Clone.postman_collection.json`
3. The `base_url` variable is pre-set to `http://localhost:8000`
4. Open **Runner** → select the collection → click **Run AutoRia Clone**

All 42 requests run in order. Tokens and IDs are captured automatically between requests.

Expected result: **91/91 tests pass**

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
| POST | `/api/users/create-manager` | Create manager account | Admin only |
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
| GET | `/api/currency/rates` | Current USD/EUR rates from PrivatBank | Public |

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

- **Basic seller**: max 1 active listing. Upgrade to premium to create more.
- **Profanity filter**: description checked on create/edit. Clean → `active`. Fail → `needs_edit`. After 3 failed edits → `inactive` + manager email notification.
- **Currency**: listing price stored in original currency, auto-converted to USD / EUR / UAH using latest PrivatBank rates (updated daily via Celery Beat).
- **Statistics**: view counts and average prices available only to premium-account sellers for their own listings.

---

## Project Structure

```
exam-python-drf/
├── apps/
│   ├── authentication/   # Register, login, JWT refresh & logout
│   ├── users/            # Profiles, premium upgrade, ban/unban
│   ├── roles/            # Custom RBAC: roles + permissions
│   ├── cars/             # Brands, models, brand requests
│   ├── listings/         # Listings CRUD, profanity filter, price conversion
│   ├── currency/         # PrivatBank rates, Celery task
│   ├── statistics/       # Premium view counts and average prices
│   ├── notifications/    # Email notifications to managers
│   └── dealerships/      # Dealership management
├── core/                 # Shared pagination and permissions
├── configs/              # Django settings, URLs, Celery config
├── profanity/words.txt   # Profanity word list (Ukrainian)
├── postman/              # Postman collection (42 requests, 91 tests)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── manage.py
```
