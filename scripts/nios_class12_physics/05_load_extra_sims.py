"""Add new-template demo simulations to chapters 73 / 74 / 75.

These rows are inserted alongside the existing simulation content so
that the chapter detail page now exposes multiple kinds of simulation
(classic match_pairs / categorize PLUS the new 3D and timeline ones).

Each new row gets a distinct cache_key by passing a ``demo_variant``
key in ``request_options``, so it does not collide with the existing
chapter-bootstrap simulation row.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/05_load_extra_sims.py
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

DATA_DIR = Path(__file__).parent / "data"


# (chapter_id, filename, variant_label) — variant_label tags the
# request_options so cache_keys are distinct from the bootstrap
# simulation already on the chapter.
EXTRAS: list[tuple[int, str, str]] = [
    (73, "ch73_sim_orbit.json",       "orbit-demo"),
    (74, "ch74_sim_projectile.json",  "projectile-demo"),
    (74, "ch74_sim_timeline.json",    "timeline-demo"),
    (75, "ch75_sim_field.json",       "field-demo"),
]


def main() -> None:
    db = SessionLocal()
    store = get_artifact_store()
    try:
        loaded = 0
        skipped = 0
        for chapter_id, filename, variant in EXTRAS:
            chapter = db.get(Chapter, chapter_id)
            if chapter is None:
                print(f"[skip] chapter {chapter_id} not found")
                continue
            subject_name = chapter.book.subject.name
            payload = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
            validated = SimulationOutput.model_validate(payload)

            options = {"demo_variant": variant, "template": validated.template}
            cache_key = build_generation_cache_key(
                content_type="simulation",
                academic_year=ACADEMIC_YEAR,
                class_level=CLASS_LEVEL,
                subject_id=SUBJECT_ID,
                chapter_id=chapter_id,
                topic_id=None,
                prompt=None,
                options=options,
            )
            existing = db.scalar(
                select(GeneratedContent).where(GeneratedContent.cache_key == cache_key)
            )
            if existing is not None:
                skipped += 1
                print(f"[skip] ch{chapter_id} {variant}: row {existing.id} already exists")
                continue

            now = datetime.now(timezone.utc)
            row = GeneratedContent(
                content_type=GeneratedContentType.SIMULATION,
                status=GeneratedContentStatus.APPROVED,
                cache_key=cache_key,
                academic_year=ACADEMIC_YEAR,
                class_level=CLASS_LEVEL,
                subject_id=SUBJECT_ID,
                chapter_id=chapter_id,
                topic_id=None,
                title=(
                    f"Simulation ({validated.template}) — Class {CLASS_LEVEL} - "
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
            loaded += 1
            print(f"[ok]   ch{chapter_id} {variant} ({validated.template}): row {row.id} -> {row.artifact_url}")
        print(f"\nDone. Loaded {loaded} new simulation rows, skipped {skipped} pre-existing.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
