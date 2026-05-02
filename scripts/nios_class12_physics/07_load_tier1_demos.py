"""Insert one demo simulation per Tier-1 template, attached to the
most pedagogically relevant chapter:

  - graph_explorer    → ch74 (Motion in a Straight Line) — projectile range
  - labeled_hotspots  → ch73 (Units, Dimensions and Vectors) — vector diagram
  - sentence_builder  → ch73 (Units, Dimensions and Vectors) — order the
                        steps of a dimensional-analysis derivation
  - vocab_pairs       → ch73 — match unit symbols to physical quantities
  - molecule_3d       → ch73 — H2O as a vector example (bond vectors)
  - circuit_2d        → ch75 (Laws of Motion — placeholder; production
                        would attach this to a circuits chapter)

Each row gets a distinct cache_key via ``request_options`` so it does
not collide with previously loaded demo simulations.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/07_load_tier1_demos.py
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


# (chapter_id, variant_label, payload)
DEMOS: list[tuple[int, str, dict]] = [
    (74, "graph-projectile", {
        "template": "graph_explorer",
        "title": "Projectile range vs launch angle",
        "instructions": "Slide v0 and g; the curve plots R(theta) = v0^2 sin(2 theta)/g. Notice the peak at 45 deg.",
        "outcome_codes_covered": ["12-NIOS-PHY-MSL-06"],
        "graph": {
            "expression": "v0^2 * sin(2 * theta * pi / 180) / g",
            "x_var": "theta", "x_min": 0, "x_max": 90,
            "x_label": "Launch angle theta (deg)", "y_label": "Range (m)",
            "sliders": [
                {"name": "v0", "label": "Initial speed", "min": 5, "max": 60, "initial": 25, "step": 0.5, "unit": "m/s"},
                {"name": "g",  "label": "Gravity",       "min": 1, "max": 25, "initial": 9.8, "step": 0.1, "unit": "m/s^2"},
            ],
            "samples": 200,
        },
    }),
    (73, "hotspots-vector", {
        "template": "labeled_hotspots",
        "title": "Anatomy of a vector — labelled diagram",
        "instructions": "Click each part of the vector to learn its name and meaning.",
        "outcome_codes_covered": ["12-NIOS-PHY-UDV-07"],
        "hotspots": {
            # Public-domain vector image used as a placeholder; can be
            # replaced by an in-house diagram once Phase 2 (custom HTML)
            # gives admins finer-grained control.
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Vector_components.svg/640px-Vector_components.svg.png",
            "image_alt": "Vector diagram with components",
            "hotspots": [
                {"label": "Tail",      "description": "Starting point of the vector — its 'origin'.", "x_pct": 12, "y_pct": 80, "radius_pct": 4},
                {"label": "Head",      "description": "The arrow tip — direction of the vector.",     "x_pct": 80, "y_pct": 25, "radius_pct": 4},
                {"label": "x-component", "description": "Projection of the vector on the x-axis (a cos theta).", "x_pct": 50, "y_pct": 80, "radius_pct": 4},
                {"label": "y-component", "description": "Projection of the vector on the y-axis (a sin theta).", "x_pct": 80, "y_pct": 55, "radius_pct": 4},
            ],
            "quiz_mode": False,
        },
    }),
    (73, "sentence-dim-analysis", {
        "template": "sentence_builder",
        "title": "Build the dimensional-analysis derivation of pendulum period",
        "instructions": "Drag the steps into the order you would carry out a dimensional-analysis derivation of T for a simple pendulum.",
        "outcome_codes_covered": ["12-NIOS-PHY-UDV-03"],
        "sentence": {
            "target_label": "Goal: derive T proportional to sqrt(L / g) using only dimensions.",
            "tiles": [
                {"text": "Assume T = k L^a g^b",                                "correct_position": 1},
                {"text": "Match dimensions: T^1 = L^(a+b) T^(-2b)",            "correct_position": 2},
                {"text": "Equate exponents of T: -2b = 1 so b = -1/2",         "correct_position": 3},
                {"text": "Equate exponents of L: a + b = 0 so a = +1/2",       "correct_position": 4},
                {"text": "Substitute back: T proportional to sqrt(L / g)",    "correct_position": 5},
                {"text": "Note: the dimensionless 2 pi must come from physics", "correct_position": 6},
            ],
            "distractor_tiles": ["Cross-multiply to eliminate fractions", "Differentiate both sides"],
        },
    }),
    (73, "vocab-units", {
        "template": "vocab_pairs",
        "title": "Match SI quantities to their units",
        "instructions": "Pair each physical quantity with its SI unit. Try Memory mode for a flip-and-find game.",
        "outcome_codes_covered": ["12-NIOS-PHY-UDV-02"],
        "vocab": {
            "mode": "pairs",
            "cards": [
                {"term": "Force",      "translation": "newton (N)"},
                {"term": "Energy",     "translation": "joule (J)"},
                {"term": "Power",      "translation": "watt (W)"},
                {"term": "Pressure",   "translation": "pascal (Pa)"},
                {"term": "Frequency",  "translation": "hertz (Hz)"},
                {"term": "Charge",     "translation": "coulomb (C)"},
                {"term": "Resistance", "translation": "ohm (Omega)"},
                {"term": "Capacitance","translation": "farad (F)"},
            ],
        },
    }),
    (73, "molecule-water", {
        "template": "molecule_3d",
        "title": "Vectors in chemistry — H2O bond vectors in 3D",
        "instructions": "Drag to rotate. The two O-H bonds are vector quantities; their geometric sum (the dipole moment) is non-zero, which is why water is polar.",
        "outcome_codes_covered": ["12-NIOS-PHY-UDV-07"],
        "molecule": {
            "name": "Water (H2O)",
            "description": "Bent geometry; H-O-H bond angle approx 104.5 degrees.",
            "atoms": [
                {"name": "O1", "element": "O", "x": 0,     "y": 0,    "z": 0, "description": "Central oxygen atom (sp3 hybrid). Each O-H bond is a vector pointing toward a hydrogen."},
                {"name": "H1", "element": "H", "x": 0.76,  "y": 0.59, "z": 0, "description": "One of two hydrogens, bonded by a single covalent bond."},
                {"name": "H2", "element": "H", "x": -0.76, "y": 0.59, "z": 0, "description": "The other hydrogen."},
            ],
            "bonds": [
                {"from_atom": "O1", "to_atom": "H1", "order": 1},
                {"from_atom": "O1", "to_atom": "H2", "order": 1},
            ],
        },
    }),
    (75, "circuit-series", {
        "template": "circuit_2d",
        "title": "Series circuit — Newton's-3rd-law analogue in electricity (charge conservation)",
        "instructions": "A 12-V battery driving two resistors in series. Side panel shows total R and the current via Ohm's law.",
        "outcome_codes_covered": ["12-NIOS-PHY-LM-03"],
        "circuit": {
            "description": "Two resistors (4 ohm and 8 ohm) connected in series with a 12-V battery. Just as forces in a Newton's-laws problem must balance, the voltage drops across the resistors here must add up to the battery EMF.",
            "analysis": "series",
            "components": [
                {"kind": "battery",  "name": "B1", "value": 12, "unit": "V",   "x": 8,  "y": 12},
                {"kind": "resistor", "name": "R1", "value": 4,  "unit": "ohm", "x": 20, "y": 6},
                {"kind": "resistor", "name": "R2", "value": 8,  "unit": "ohm", "x": 32, "y": 6},
                {"kind": "junction", "name": "J1", "x": 8,  "y": 6},
                {"kind": "junction", "name": "J2", "x": 38, "y": 6},
                {"kind": "junction", "name": "J3", "x": 38, "y": 18},
                {"kind": "junction", "name": "J4", "x": 8,  "y": 18},
            ],
            "wires": [
                {"from_component": "B1", "to_component": "J1"},
                {"from_component": "J1", "to_component": "R1"},
                {"from_component": "R1", "to_component": "R2"},
                {"from_component": "R2", "to_component": "J2"},
                {"from_component": "J2", "to_component": "J3"},
                {"from_component": "J3", "to_component": "J4"},
                {"from_component": "J4", "to_component": "B1"},
            ],
        },
    }),
]


def main() -> None:
    db = SessionLocal()
    store = get_artifact_store()
    try:
        loaded = 0
        skipped = 0
        for chapter_id, variant, payload in DEMOS:
            chapter = db.get(Chapter, chapter_id)
            if chapter is None:
                print(f"[skip] chapter {chapter_id} not found")
                continue
            subject_name = chapter.book.subject.name
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
                    f"Simulation ({validated.template}) - Class {CLASS_LEVEL} - "
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
