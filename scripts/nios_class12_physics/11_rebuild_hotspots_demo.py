"""Rebuild the row-121 vector-anatomy hotspots demo with an inline-SVG
image (data URL) instead of a fragile external Wikimedia link. The
SVG draws the vector, its x and y components, the angle theta, and
labelled axes; the four hotspots are positioned to land cleanly on
each labelled feature.

Re-uses the existing row + cache_key, so the artifact at
/generated-content/121/artifact will be overwritten with the new
HTML and the SPA will pick it up on next reload.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/11_rebuild_hotspots_demo.py
"""

from __future__ import annotations

import urllib.parse

from app.db.session import SessionLocal
from app.llm.schemas.simulation import SimulationOutput
from app.models.generation import GeneratedContent
from app.rendering.simulation_html import render_simulation_html
from app.services.artifact_store import get_artifact_store


ROW_ID = 121


# 640x400 inline SVG diagram. Authored once; we then percent-encode
# it for use in a data: URL.
#
# Layout, in viewBox coordinates:
#   - Origin / tail at (80, 320). "Up" on screen is decreasing y.
#   - Vector head at (475, 85).
#   - x-component: horizontal dashed line on y = 320, ending at x = 475.
#   - y-component: vertical dashed line on x = 480, ending at y = 85.
#   - Angle theta arc anchored at the origin, between the +x axis and
#     the vector.
#
# The hotspot percentages below are calculated from this layout:
#   tail      -> (80 / 640, 320 / 400)  = (12.5, 80)
#   head      -> (475 / 640, 85 / 400)  = (74.2, 21.3)
#   x-comp    -> (280 / 640, 320 / 400) = (43.8, 80)
#   y-comp    -> (480 / 640, 200 / 400) = (75, 50)
SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 400" width="640" height="400" preserveAspectRatio="xMidYMid meet">
  <defs>
    <marker id="va" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
      <polygon points="0,0 12,6 0,12" fill="#22d3ee"/>
    </marker>
    <marker id="ca" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
      <polygon points="0,0 12,6 0,12" fill="#a855f7"/>
    </marker>
    <marker id="aa" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
      <polygon points="0,0 10,5 0,10" fill="#94a3b8"/>
    </marker>
  </defs>
  <rect width="640" height="400" fill="#0f1730"/>
  <!-- Faint grid for orientation -->
  <g stroke="rgba(255,255,255,0.04)" stroke-width="1">
    <line x1="80"  y1="40" x2="80"  y2="320"/>
    <line x1="180" y1="40" x2="180" y2="320"/>
    <line x1="280" y1="40" x2="280" y2="320"/>
    <line x1="380" y1="40" x2="380" y2="320"/>
    <line x1="480" y1="40" x2="480" y2="320"/>
    <line x1="580" y1="40" x2="580" y2="320"/>
    <line x1="80" y1="40"  x2="600" y2="40"/>
    <line x1="80" y1="100" x2="600" y2="100"/>
    <line x1="80" y1="160" x2="600" y2="160"/>
    <line x1="80" y1="220" x2="600" y2="220"/>
    <line x1="80" y1="280" x2="600" y2="280"/>
  </g>
  <!-- Axes (slightly thicker, with arrows) -->
  <line x1="80" y1="320" x2="608" y2="320" stroke="#94a3b8" stroke-width="2" marker-end="url(#aa)"/>
  <line x1="80" y1="320" x2="80"  y2="32"  stroke="#94a3b8" stroke-width="2" marker-end="url(#aa)"/>
  <text x="615" y="335" fill="#cbd5e1" font-family="sans-serif" font-size="18">x</text>
  <text x="58" y="28" fill="#cbd5e1" font-family="sans-serif" font-size="18">y</text>
  <text x="58" y="340" fill="#cbd5e1" font-family="sans-serif" font-size="14">O</text>
  <!-- Component projections (drawn behind the vector for layering) -->
  <line x1="80" y1="320" x2="473" y2="320" stroke="#a855f7" stroke-width="3" stroke-dasharray="7 4" marker-end="url(#ca)"/>
  <line x1="480" y1="320" x2="480" y2="88" stroke="#a855f7" stroke-width="3" stroke-dasharray="7 4" marker-end="url(#ca)"/>
  <!-- The vector itself (cyan, on top) -->
  <line x1="80" y1="320" x2="473" y2="85" stroke="#22d3ee" stroke-width="5" marker-end="url(#va)"/>
  <!-- Vector / component labels -->
  <text x="252" y="190" fill="#22d3ee" font-family="sans-serif" font-size="22" font-weight="bold" font-style="italic">a</text>
  <text x="232" y="356" fill="#a855f7" font-family="sans-serif" font-size="15">a_x = a cos &#952;</text>
  <text x="498" y="208" fill="#a855f7" font-family="sans-serif" font-size="15">a_y = a sin &#952;</text>
  <!-- Angle arc and theta label -->
  <path d="M 140 320 A 60 60 0 0 0 117 282" stroke="#22d3ee" stroke-width="2.5" fill="none"/>
  <text x="148" y="308" fill="#22d3ee" font-family="sans-serif" font-size="20" font-style="italic">&#952;</text>
</svg>"""


def to_data_url(svg: str) -> str:
    # `quote` keeps `[]:/-_~` etc.; that's fine inside a data URL value.
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg, safe="")


def main() -> None:
    db = SessionLocal()
    store = get_artifact_store()
    try:
        row = db.get(GeneratedContent, ROW_ID)
        if row is None:
            raise SystemExit(f"row {ROW_ID} not found")

        old = row.output_json or {}
        # Hotspots are pre-computed for the SVG layout above.
        new_payload = {
            "template": "labeled_hotspots",
            "title": old.get("title", "Anatomy of a vector — labelled diagram"),
            "instructions": old.get(
                "instructions",
                "Click each part of the vector to learn its name and meaning.",
            ),
            "outcome_codes_covered": old.get("outcome_codes_covered", []),
            "hotspots": {
                "image_url": to_data_url(SVG),
                "image_alt": "Vector diagram with components and angle theta",
                "hotspots": [
                    {
                        "label": "Tail (origin)",
                        "description": (
                            "Starting point of the vector. By convention we anchor "
                            "vectors at the origin so their components can be read "
                            "directly off the axes."
                        ),
                        "x_pct": 12.5, "y_pct": 80, "radius_pct": 4,
                    },
                    {
                        "label": "Head (arrow tip)",
                        "description": (
                            "The pointed end. The vector's direction is from tail "
                            "to head; its magnitude is the length |a| of this "
                            "segment."
                        ),
                        "x_pct": 74.2, "y_pct": 21.3, "radius_pct": 4,
                    },
                    {
                        "label": "x-component",
                        "description": (
                            "Projection of the vector onto the x-axis: a_x = a cos θ. "
                            "This is the part of the vector that points along x."
                        ),
                        "x_pct": 43.8, "y_pct": 80, "radius_pct": 4,
                    },
                    {
                        "label": "y-component",
                        "description": (
                            "Projection of the vector onto the y-axis: a_y = a sin θ. "
                            "This is the part of the vector that points along y."
                        ),
                        "x_pct": 75, "y_pct": 50, "radius_pct": 4,
                    },
                ],
                "quiz_mode": False,
            },
        }
        validated = SimulationOutput.model_validate(new_payload)
        row.output_json = validated.model_dump(mode="json")

        data = render_simulation_html(validated)
        ext = (row.artifact_url or f"{row.id}.html").rsplit(".", 1)[-1] or "html"
        row.artifact_url = store.save(content_id=row.id, extension=ext, data=data)
        db.commit()
        print(
            f"[ok] row {row.id}: rebuilt with inline SVG (data URL, {len(SVG):,} bytes), "
            f"artifact = {row.artifact_url} ({len(data):,} bytes)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
