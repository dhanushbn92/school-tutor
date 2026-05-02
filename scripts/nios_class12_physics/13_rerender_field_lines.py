"""Re-render every live three_d_field_lines simulation row with the
fixed template (outward integration, drawRange tracking, live
sliders, fixed flow animation, fixed pause-flow restore).

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/13_rerender_field_lines.py
"""

from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm.schemas.simulation import SimulationOutput
from app.models.generation import GeneratedContent, GeneratedContentType
from app.rendering.simulation_html import render_simulation_html
from app.services.artifact_store import get_artifact_store


def main() -> None:
    db = SessionLocal()
    store = get_artifact_store()
    try:
        rows = db.scalars(
            select(GeneratedContent).where(
                GeneratedContent.content_type == GeneratedContentType.SIMULATION
            )
        ).all()
        affected = 0
        for r in rows:
            payload = r.output_json or {}
            if payload.get("template") != "three_d_field_lines":
                continue
            try:
                validated = SimulationOutput.model_validate(payload)
            except Exception as e:
                print(f"[skip] row {r.id}: invalid payload ({e})")
                continue
            data = render_simulation_html(validated)
            ext = (r.artifact_url or f"{r.id}.html").rsplit(".", 1)[-1] or "html"
            r.artifact_url = store.save(content_id=r.id, extension=ext, data=data)
            affected += 1
            print(f"[ok] row {r.id} (chapter {r.chapter_id}): re-rendered, {len(data):,} bytes")
        db.commit()
        print(f"\nDone. Re-rendered {affected} three_d_field_lines rows.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
