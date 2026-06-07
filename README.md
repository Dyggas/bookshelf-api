# Bookshelf API

A Book Management API built with FastAPI and PostgreSQL.

## Quick Start

```bash
# Clone and enter the project
cd bookshelf-api

# Copy the example env file
cp .env.example .env

# Start the services
docker compose up --build -d

# Run database migrations
docker compose exec api alembic upgrade head

# Verify it works
 curl http://localhost:8000/health
```

The Swagger UI is available at `http://localhost:8000/docs`.

## Running Tests

```bash
docker compose exec api pytest -v
```

Tests use an isolated `bookshelf_test` database with transactional rollback per test.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@db:5432/bookshelf` | PostgreSQL connection string |
| `SECRET_KEY` | `change-me-in-production...` | JWT signing key (≥32 bytes) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `DEBUG` | `false` | Enable debug logging |

## API Endpoints

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | No | Register, returns access + refresh tokens |
| POST | `/api/v1/auth/login` | No | Login (OAuth2 form), returns tokens |
| POST | `/api/v1/auth/refresh` | No | Rotate refresh token, get new pair |
| POST | `/api/v1/auth/logout` | No | Revoke a refresh token |

### Books

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/books/` | No | List books (filtering, sorting, pagination) |
| POST | `/api/v1/books/` | Yes | Create a book |
| POST | `/api/v1/books/import` | Yes | Bulk import (JSON or CSV) |
| GET | `/api/v1/books/export` | No | Export all books as JSON |
| GET | `/api/v1/books/{id}` | No | Get a single book |
| PATCH | `/api/v1/books/{id}` | Yes | Partial update |
| DELETE | `/api/v1/books/{id}` | Yes | Delete |

### Operational

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Health check (verifies DB connectivity) |

### Query Parameters for List Endpoint

```
GET /api/v1/books/?title=gatsby&author=fitz&genre=fiction&year_from=1920&year_to=1930&sort_by=year&sort_order=asc&page=1&page_size=20
```

| Parameter | Default | Description |
|---|---|---|
| `title` | — | Case-insensitive partial match |
| `author` | — | Case-insensitive partial match on author name |
| `genre` | — | Exact match (enum: fiction, non_fiction, science_fiction, fantasy, mystery, thriller, romance, horror, historical, biography, poetry, drama) |
| `year_from` | — | Minimum year (≥1800) |
| `year_to` | — | Maximum year (≤ current year) |
| `sort_by` | `created_at` | Sort field: title, year, genre, created_at |
| `sort_order` | `desc` | Sort direction: asc, desc |
| `page` | `1` | Page number (≥1) |
| `page_size` | `20` | Items per page (1–100) |

### Bulk Import

Send a JSON array or CSV body:

```bash
# JSON
curl -X POST http://localhost:8000/api/v1/books/import \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '[{"title":"1984","author":"George Orwell","genre":"science_fiction","year":1949}]'

# CSV
curl -X POST http://localhost:8000/api/v1/books/import \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: text/csv" \
  --data-binary @books.csv
```

Returns `{"total": N, "created": M, "skipped": K}`. Duplicates (same title + author) are skipped. Invalid data rejects the entire file with 422.

## Query Plan Analysis

A script is included to seed the database and run `EXPLAIN ANALYZE` on all list endpoint queries:

```bash
docker compose exec api python scripts/seed_and_analyze.py
```

Results at 1M rows:

| Query | Time | Method |
|---|---|---|
| Default pagination | ~100ms | Parallel Seq Scan |
| Filter by genre | ~60ms | Parallel Seq Scan (no index — low cardinality) |
| Filter by year range | ~48ms | **Bitmap Index Scan** on `ix_books_year` |
| Filter by author name | ~150ms | Hash Join |
| Filter by title ILIKE | ~210ms | Parallel Seq Scan |
| Count all | ~50ms | **Index Only Scan** on `ix_books_year` |
| Deep pagination | ~108ms | Parallel Seq Scan |

## Design Decisions

### Invariant Enforcement — Database First

The database is the source of truth for constraints:

- `UNIQUE(name)` on authors
- `UNIQUE(title, author_id)` on books
- `CHECK(year >= 1800)` on books
- `UNIQUE(email)` on users

Pydantic schemas mirror these constraints for client-friendly error messages (422 with field details). The service layer only handles what neither can express — author resolution, bulk import orchestration, token hashing.


### Concurrency — Let PostgreSQL Handle It

No application-level locks, no Redis mutexes:

- **Simultaneous author creation:** `INSERT` with savepoint (`begin_nested()`) + `IntegrityError` catch → fetch existing
- **Duplicate books:** `UNIQUE(title, author_id)` → 409 Conflict
- **Refresh token reuse:** Atomic `UPDATE ... WHERE revoked_at IS NULL`; if already revoked → revoke ALL user tokens

### Authentication — JWT + Opaque Refresh Tokens with Rotation

- **Access tokens:** Short-lived JWT (15 min) with `jti` claim
- **Refresh tokens:** Opaque random strings, SHA-256 hashed in DB, revocable by design
- **Rotation:** Each refresh revokes old token, issues new pair
- **Reuse detection:** Reusing a revoked token terminates all sessions for that user

### Data Access — ORM Everywhere, Core for Bulk

SQLAlchemy 2.0 async ORM for all CRUD operations. SQLAlchemy Core (`pg_insert ... ON CONFLICT DO NOTHING`) only for bulk import where batch performance matters.

### Bulk Import — Idempotent and Atomic

- `ON CONFLICT DO NOTHING` on both authors and books makes import idempotent
- Uploading the same file twice creates nothing on the second run
- Validation is fail-fast: if any row is invalid, the entire file is rejected with 422

### Request Tracing

Every request gets a unique `X-Request-ID` (UUID4) in the response header. Clients can send their own via the `X-Request-ID` request header for distributed tracing. All log lines include the request ID for correlation.

### API Design — Flat Resources

Flat routes (`/books`, `/authors`) rather than nested (`/authors/{id}/books`)

### Indexes

Only two indexes beyond what constraints provide:

- `ix_books_year` — used by the planner for year range queries and counts at scale
- `ix_books_author_id` — supports JOIN performance and FK integrity checks

