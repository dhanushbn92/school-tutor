"""Seed the platform team and lift existing per-school content into the global catalog.

After this runs:
- A `PLATFORM_ADMIN` user exists (no school_id).
- All currently-READY GeneratedContent rows are bumped to APPROVED with
  published_at set to now and published_by_id pointing at the platform admin.
- Existing creator_id is preserved (for audit), but the catalog visibility
  no longer depends on it.

Idempotent: re-running creates nothing duplicative; status transitions only
move READY → APPROVED.

Usage:
    .venv/Scripts/python.exe -m scripts.seed_platform
"""
from datetime import datetime, timezone

from sqlalchemy import select

from app.auth.security import hash_password
from app.db.session import SessionLocal
from app.models.generation import GeneratedContent, GeneratedContentStatus
from app.models.school import User, UserRole


PLATFORM_ADMIN_EMAIL = "platform.team@anaadi.org"
PLATFORM_ADMIN_PASSWORD = "platform@123"
PLATFORM_ADMIN_NAME = "Anaadi Platform Team"


def main() -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == PLATFORM_ADMIN_EMAIL))
        if admin is None:
            admin = User(
                email=PLATFORM_ADMIN_EMAIL,
                hashed_password=hash_password(PLATFORM_ADMIN_PASSWORD),
                role=UserRole.PLATFORM_ADMIN,
                full_name=PLATFORM_ADMIN_NAME,
                school_id=None,
                is_active=True,
            )
            db.add(admin)
            db.flush()
            print(f"created platform admin id={admin.id}  {PLATFORM_ADMIN_EMAIL}")
        else:
            admin.role = UserRole.PLATFORM_ADMIN
            admin.school_id = None
            print(f"platform admin already exists id={admin.id}  {PLATFORM_ADMIN_EMAIL}")

        # Lift every READY generation to APPROVED and credit the platform admin.
        ready_rows = list(
            db.scalars(
                select(GeneratedContent).where(
                    GeneratedContent.status == GeneratedContentStatus.READY
                )
            )
        )
        now = datetime.now(timezone.utc)
        for row in ready_rows:
            row.status = GeneratedContentStatus.APPROVED
            row.published_at = now
            row.published_by_id = admin.id

        db.commit()

        approved_total = db.scalar(
            select(GeneratedContent).where(
                GeneratedContent.status == GeneratedContentStatus.APPROVED
            ).with_only_columns(GeneratedContent.id)
        )
        # Use len() of fetched IDs for an accurate count (approved_total above
        # only returns the first id; just for a quick number we re-query).
        from sqlalchemy import func
        n_approved = db.scalar(
            select(func.count(GeneratedContent.id)).where(
                GeneratedContent.status == GeneratedContentStatus.APPROVED
            )
        )
        print(f"published {len(ready_rows)} generations; catalog now has {n_approved} APPROVED rows")
        print(f"login : {PLATFORM_ADMIN_EMAIL} / {PLATFORM_ADMIN_PASSWORD}")


if __name__ == "__main__":
    main()
