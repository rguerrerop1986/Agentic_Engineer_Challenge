# Checkout service for Agentic engineer challenge

Small FastAPI service for a toy checkout flow: log in, post a basket, get subtotal / tax / discount / total, and persist the transaction. Stack is PostgreSQL, SQLAlchemy, Alembic, JWT bearer auth, and Docker Compose.

If you just want it running, skip ahead to Docker. Local setup is there for when you want hot reload or to run pytest without building an image.

---

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

The app container runs `alembic upgrade head` then `uvicorn`. Postgres listens on **5432**, the API on **8000**. Seed data includes a demo user (`demo@example.com` / `demo12345`) and default tax/discount config.

---

## Run locally (no Docker)

The Docker image uses **Python 3.12**. On newer Python (e.g. 3.14) you can hit missing wheels for `psycopg2-binary`, so matching 3.12 locally saves headaches.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Point DATABASE_URL at your Postgres (localhost if the DB is on your machine)
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Layout

Routes stay thin; most behavior lives under `app/services/`.

| Path | Role |
|------|------|
| `app/main.py` | App factory, routers, `/health` |
| `app/api/` | HTTP handlers, `deps.py` for JWT |
| `app/core/` | Settings (`pydantic-settings`), bcrypt + JWT helpers |
| `app/db/` | Engine + `get_db` session dependency |
| `app/models/` | SQLAlchemy models |
| `app/schemas/` | Pydantic request/response models |
| `app/services/` | Auth + checkout math and persistence |

Money is calculated in `checkout_service.py` with `Decimal`, half-up to two decimal places. Tax and discount rates come from the active `checkout_config` row (if several are active, we take the one with the highest `id`).

---

## Security and validation

Checkout expects `Authorization: Bearer <token>`. Tokens come from `POST /auth/login` after checking email/password against `users` (bcrypt at rest). No server-side session store—each request is validated with the JWT and `SECRET_KEY`. Missing or bad bearer auth returns **401** with `WWW-Authenticate: Bearer`.

Payloads are validated with Pydantic (`app/schemas/`): non-empty item list, non-blank names, `unit_price` and `quantity` strictly positive. Bad input surfaces as **422** before any service code runs.

Internally everything money-related stays `Decimal` so we do not accumulate float error on tax/discount. The checkout JSON response turns those fields into plain JSON numbers at serialization time only.

Because there is no in-memory auth state, you can run multiple workers or replicas behind a load balancer as long as they share Postgres and the same signing secret.

---

## Migrations

Shipped migration (schema + seed): `alembic/versions/001_initial_schema.py`.

After you change models against a real DB:

```bash
alembic revision --autogenerate -m "describe change..."
alembic upgrade head
```

---

## Tests

From the repo root:

```bash
pytest
```

`test_checkout_calculation.py` hits `calculate_checkout` only—no HTTP, no DB.

`test_auth_integration.py` and `test_checkout_integration.py` use FastAPI’s `TestClient` with `get_db` overridden to **in-memory SQLite** (with `StaticPool` so every session sees the same DB). Tables are created from metadata, a user and config row are inserted, tests run, then everything is torn down. Business logic and persistence are not mocked.

What those integration tests cover: happy-path login and JWT shape; checkout without auth → 401; checkout with a good token → 200 and sane totals (as JSON numbers); rows land in `checkout_transactions` / `checkout_items` as expected.

To run tests inside the image (no entrypoint migrations / uvicorn):

```bash
docker compose build app
docker compose run --rm --no-deps --entrypoint pytest app -q
```

---

## Try it with curl

**Login** - `POST /auth/login`

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"demo12345"}'
```

You get something like:

```json
{"access_token":"<jwt>","token_type":"bearer"}
```

**Checkout** — `POST /checkout` (paste a real token)

Example body for a notebook and a SSD:
```bash
curl -s -X POST http://localhost:8000/checkout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt-from-login>" \
  -d '{
	"items": [
		{
			"name": "Notebook",
			"unit_price": "84.50",
			"quantity": 1
		},
		{
			"name": "Notebook SSD",
			"unit_price": "27.99",
			"quantity": 1
		}
	]
}'
```

Seeded config: `tax_rate=0.13`, `discount_rate=0.10`, `discount_threshold=100`. 
Discount only kicks in when subtotal is strictly greater than the threshold defined, in this case the threshold is greater so we apply a discount:

```json{
	"subtotal": "112.49",
	"taxes": "14.62",
	"discount": "11.25",
	"total": "115.86"
}
```

Example body for Macbook accesories (less than threshold $100 so we dont apply any discount):
```bash
curl -s -X POST http://localhost:8000/checkout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt-from-login>" \
  -d '{
	"items": [
		{
			"name": "Macbook accesory",
			"unit_price": "4.50",
			"quantity": 1
		},
		{
			"name": "Macbook keyboard",
			"unit_price": "67.99",
			"quantity": 1
		}
]}'
```

```json
{
	"subtotal": "72.49",
	"taxes": "9.42",
	"discount": "0.00",
	"total": "81.91"
}
```
---

## Tradeoffs (on purpose)

JWT in headers keeps things simple for horizontal scale; we did not build refresh tokens, revocation lists, or OAuth2 metadata.

Rates live in `checkout_config` so you can tweak tax/discount without redeploying. If someone leaves multiple rows `is_active`, we pick the newest by `id`—documented, not hidden.

`persist_checkout` commits inside the service to keep handlers boring. That couples “do work” and “save” for a repo this size; I’d split them if the app grew.

Running migrations in the Compose entrypoint is nice for demos; in production I’d usually run migrations as a separate deploy step.

---

## Out of scope

Roles/admin APIs, refresh tokens, rate limiting, idempotency keys, payments, inventory, shipping, pagination, audit tables beyond `is_active`, and anything LLM/agent/RAG-related—this stays a tight backend exercise.
