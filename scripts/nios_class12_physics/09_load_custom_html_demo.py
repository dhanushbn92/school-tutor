"""Load the Tier-2 custom_html demo: a 1D collision sandbox attached
to chapter 75 (Laws of Motion). Renders + publishes as APPROVED.

For LLM-GENERATED custom_html in production, the worker should leave
the row at READY so a platform admin can spot-check the body before
publish. We approve here because this row is hand-curated.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/09_load_custom_html_demo.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm.schemas.simulation import SimulationOutput
from app.models.curriculum import Chapter
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)
from app.rendering.simulation_html import render_simulation_html
from app.services.artifact_store import get_artifact_store
from app.services.cache_keys import build_generation_cache_key


SUBJECT_ID = 14
CLASS_LEVEL = 12
ACADEMIC_YEAR = "2026-27"
CREATED_BY_ID = 14
CHAPTER_ID = 75
VARIANT = "custom-collision"

DATA_PATH = Path(__file__).parent / "data" / "ch75_sim_custom_collision.json"


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    validated = SimulationOutput.model_validate(payload)

    db = SessionLocal()
    store = get_artifact_store()
    try:
        chapter = db.get(Chapter, CHAPTER_ID)
        if chapter is None:
            raise SystemExit(f"chapter {CHAPTER_ID} not found")
        subject_name = chapter.book.subject.name

        options = {"demo_variant": VARIANT, "template": validated.template}
        cache_key = build_generation_cache_key(
            content_type="simulation",
            academic_year=ACADEMIC_YEAR,
            class_level=CLASS_LEVEL,
            subject_id=SUBJECT_ID,
            chapter_id=CHAPTER_ID,
            topic_id=None,
            prompt=None,
            options=options,
        )
        existing = db.scalar(
            select(GeneratedContent).where(GeneratedContent.cache_key == cache_key)
        )
        if existing is not None:
            print(f"[skip] row {existing.id} already exists for {VARIANT}")
            return

        now = datetime.now(timezone.utc)
        row = GeneratedContent(
            content_type=GeneratedContentType.SIMULATION,
            status=GeneratedContentStatus.APPROVED,
            cache_key=cache_key,
            academic_year=ACADEMIC_YEAR,
            class_level=CLASS_LEVEL,
            subject_id=SUBJECT_ID,
            chapter_id=CHAPTER_ID,
            topic_id=None,
            title=(
                f"Simulation (custom_html) - Class {CLASS_LEVEL} - "
                f"{subject_name} - Chapter {chapter.chapter_number}: {chapter.title}"
            ),
            source_context=(chapter.full_text or "")[:4000],
            output_json=validated.model_dump(mode="json"),
            request_options=options,
            llm_provider="hand-authored",
            llm_model="curated-claude-agent",
            created_by_id=CREATED_BY_ID,
            published_at=now,
            published_by_id=CREATED_BY_ID,
        )
        db.add(row)
        db.flush()
        data = render_simulation_html(validated)
        row.artifact_url = store.save(content_id=row.id, extension="html", data=data)
        db.commit()
        print(f"[ok] {VARIANT}: row {row.id} -> {row.artifact_url}, {len(data):,} bytes")
    finally:
        db.close()


if __name__ == "__main__":
    main()
