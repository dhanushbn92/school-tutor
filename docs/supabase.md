# Supabase Setup

Use Supabase as the first real hosted database for the backend.

## 1. Create Project

Create a Supabase project and keep the database password available.

## 2. Configure Environment

Create `.env` from `.env.example` and set:

```text
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:6543/postgres?sslmode=require
AUTO_CREATE_TABLES=false
```

Use the session pooler or transaction pooler host shown in Supabase project settings. For a deployed API, the pooler is usually better than a direct database connection because server processes can scale without opening too many database connections.

## 3. Run Migrations

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## 4. Verify Connection

```powershell
.\.venv\Scripts\python.exe -m app.db.check
```

## 5. Import NCERT Data

```powershell
.\.venv\Scripts\python.exe -m app.ingestion.ncert_import --manifest data\ncert_manifest.sample.json
```

## Notes

- Keep `AUTO_CREATE_TABLES=false` for Supabase. Schema should be changed through Alembic migrations.
- Keep the Supabase service-role key out of this backend until we actually need Supabase Storage or auth admin operations.
- Do not commit `.env`; it is ignored by `.gitignore`.
