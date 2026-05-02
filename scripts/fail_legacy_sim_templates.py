"""Walk every READY/APPROVED simulation row and mark the ones with
templates that no longer exist in the current ``SimulationTemplate``
Literal as ``status=FAILED``.

Why: clicking these rows in the SPA produces a broken-rendered iframe
or an axios "Network Error" because the auto-heal route can't validate
the row's stored ``output_json`` against the current schema. Marking
them FAILED hides them from non-admin catalog listings and gives admins
a clear signal that the rows need regeneration.

Idempotent — re-running won't double-flag anything.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/fail_legacy_sim_templates.py
"""

from __future__ import annotations

from typing import get_args

from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm.schemas.simulation import SimulationTemplate
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)


VALID_TEMPLATES = set(get_args(SimulationTemplate))


def main() -> int:
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(GeneratedContent).where(
                GeneratedContent.content_type == GeneratedContentType.SIMULATION,
                GeneratedContent.status.in_([
                    GeneratedContentStatus.READY,
                    GeneratedContentStatus.APPROVED,
                ]),
            ).order_by(GeneratedContent.id)
        ).all()

        flagged = 0
        for row in rows:
            payload = row.output_json or {}
            tmpl = payload.get("template")
            if tmpl is None or tmpl not in VALID_TEMPLATES:
                old_status = row.status.value
                row.status = GeneratedContentStatus.FAILED
                old_msg = row.error_message or ""
                row.error_message = (
                    f"Marked FAILED by fail_legacy_sim_templates.py: row's "
                    f"template={tmpl!r} is not in the current SimulationTemplate "
                    f"Literal. Was status={old_status}. Original message: {old_msg or '(none)'}"
                )
                print(
                    f"  [flag] row {row.id:3d} (ch {row.chapter_id}) "
                    f"template={tmpl!r:24s} title={(row.title or '')[:50]!r}"
                )
                flagged += 1

        db.commit()
        print()
        print(f"Done. Flagged {flagged} rows. (Valid templates: {sorted(VALID_TEMPLATES)})")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
