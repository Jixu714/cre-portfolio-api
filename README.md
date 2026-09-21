# CRE Portfolio API

A REST API for commercial real estate portfolio management. Property owners can store buildings and leases, then query occupancy, revenue, and upcoming lease expirations — including through a natural-language endpoint backed by an LLM.

**Live:** https://cre-portfolio-api-production.up.railway.app/docs
**Repo:** github.com/Jixu714/cre-portfolio-api

## Stack

Python · FastAPI · PostgreSQL · psycopg2 · Pydantic · JWT (python-jose) · bcrypt (passlib) · Docker · pytest · slowapi · Anthropic API

## Trying it out

Every endpoint except signup and login requires authentication.

1. `POST /signup` with a username and password
2. `POST /login` with the same credentials — returns a token
3. Click **Authorize** in the docs and paste the token
4. Explore

## Endpoints

**Auth**
- `POST /signup` — create an account
- `POST /login` — get a JWT

**Properties**
- `GET /properties` — list all
- `GET /properties?city=Austin` — search by city
- `GET /properties/{id}` — one property
- `POST /properties` — create
- `DELETE /properties/{id}` — delete (blocked if leases exist)

**Leases**
- `GET /leases` — list all
- `GET /properties/{id}/leases` — leases for one property
- `POST /properties/{id}/leases` — create
- `DELETE /leases/{id}` — delete

**Analytics**
- `GET /properties/occupancy` — leased vs. available square footage and occupancy % per property
- `GET /properties/{id}/revenue` — total monthly rent
- `GET /properties/expiring_leases?days=90` — leases expiring in a window
- `POST /ask` — natural-language questions answered from live portfolio data

## Design decisions

**Foreign key blocks property deletion.** Deleting a building with active leases returns 409, not a cascade. Lease records are contracts and shouldn't disappear silently.

**Empty collections return `[]`, not 404.** A vacant building legitimately has zero leases. A 404 is reserved for a property that doesn't exist, which is checked separately.

**JWT over server-side sessions.** Stateless — no session table, no lookup per request, and it works across multiple instances. The tradeoff is that a token can't be revoked before it expires, so expiry is 30 minutes.

**Raw SQL over an ORM.** Every query is visible and intentional.

**Aggregates computed in SQL.** Occupancy and revenue use `SUM`, `COALESCE`, `NULLIF`, and `GROUP BY` rather than loading rows into Python. `LEFT JOIN` on the occupancy query so that fully vacant properties — the ones that matter most in an occupancy report still appear.

**Connection pooling.** Opening a Postgres connection per request is expensive and exhausts the server's connection limit under load. The pool opens a small set once and hands them out.

**Rate limiting on `/ask`.** It calls an external API that costs money and takes several seconds. Five requests per minute.

**Cache invalidated on write, not on a timer.** Answers are cached by normalized question text and cleared whenever a property or lease changes. Time-based expiry would serve stale occupancy data for the length of the window; invalidation keeps it correct.

**Separate models for input and output.** `PropertyCreate` has no `id` because the client doesn't choose one; `Property` does.

## Known limitations

- **Authentication without authorization.** Any logged-in user can see and modify every property. The fix is an `owner_id` foreign key on `properties` with the user id carried in the token payload.
- **Exact-match caching.** "Which property is underperforming?" and "Which property is doing worst?" are stored as two different cache entries even though they're the same question. Semantic caching would handle rewording.
- **Rate limiting keys on IP, not user identity.** `get_remote_address` means everyone behind a shared network counts as one caller, so a busy office could throttle each other. Keying `/ask` on the username from the token would be more precise, with IP as the fallback for unauthenticated endpoints like `/login`, where there's no username to key on yet.
- **Single-turn `/ask`.** No conversation history, so follow-up questions have no context.
- **In-memory cache.** Doesn't survive restarts and isn't shared across instances. Redis would fix both.
- **No migrations.** Schema changes are applied by hand; production would use Alembic.

## Running locally

```bash
git clone https://github.com/Jixu714/cre-portfolio-api.git
cd cre-portfolio-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

docker run --name portfolio-db -e POSTGRES_PASSWORD=devpass -p 5432:5432 -d postgres
docker exec -i portfolio-db psql -U postgres < schema.sql

cp .env.example .env   # fill in SECRET_KEY and ANTHROPIC_API_KEY

uvicorn main:app --reload
```

## Tests

```bash
pytest
```

Runs automatically on every push via GitHub Actions.