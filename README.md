# School Tuter Backend

FastAPI backend for a CBSE/NCERT school tutor and school-management platform.

The first implementation focuses on:

- NCERT content storage by class, subject, book, chapter, and optional topic.
- REST APIs for curriculum lookup.
- Generation request tracking for worksheets, quizzes, exams, PPTs, diagrams, and simulations.
- Reusable generated simulations and other content through deterministic cache keys.
- A manifest-driven NCERT chapter PDF ingestion CLI.

## Backend Choice

The backend is Python/FastAPI because the product will rely heavily on PDF extraction, LLM orchestration, content generation, analytics, and later OCR. PostgreSQL is the intended production database. SQLite works for local development.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000/docs
```

## Local Database

By default, the app uses:

```text
sqlite:///./school_tuter.db
```

For production, set:

```text
DATABASE_URL=postgresql+psycopg://user:password@host:5432/postgres?sslmode=require
AUTO_CREATE_TABLES=false
```

## Supabase Database

Create a Supabase project, copy a Postgres connection string, and place it in `.env`.

For Supabase, prefer the connection pooler URL for deployed APIs:

```text
DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:6543/postgres?sslmode=require
AUTO_CREATE_TABLES=false
```

The backend also accepts plain Supabase URLs like `postgresql://...`; it normalizes them to the installed `psycopg` driver automatically.

Run migrations:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Check the database connection:

```powershell
.\.venv\Scripts\python.exe -m app.db.check
```

## NCERT Ingestion

The importer reads a manifest of NCERT book codes and chapter metadata, downloads official chapter PDFs, extracts text, and upserts chapter content.

Example:

```powershell
python -m app.ingestion.ncert_import --manifest data/ncert_manifest.sample.json
```

The manifest is intentionally explicit. NCERT dropdowns and pages can change, while official chapter PDF URLs are generally stable once the book code is known.

## Generate NCERT Manifest

Build a chapter-wise NCERT manifest directly from the live NCERT textbook page:

```powershell
.\.venv\Scripts\python.exe -m app.ingestion.ncert_manifest_builder --output data\ncert_manifest.generated.json
```

For a quick test run, limit the work:

```powershell
.\.venv\Scripts\python.exe -m app.ingestion.ncert_manifest_builder --output data\ncert_manifest.generated.json --limit-books 2 --limit-chapters-per-book 2
```
