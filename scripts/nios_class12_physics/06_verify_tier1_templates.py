"""Smoke-test all 6 Tier-1 simulation templates: validate sample
config against the schema, then render the HTML through the
``render_simulation_html`` pipeline. Prints byte-size of each artifact
so we can spot empty / placeholder-still-present output.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/06_verify_tier1_templates.py
"""

from app.llm.schemas.simulation import SimulationOutput
from app.rendering.simulation_html import render_simulation_html


SAMPLES = [
    ("graph_explorer", {
        "template": "graph_explorer",
        "title": "Projectile range as a function of angle",
        "instructions": "Slide v0 and g; observe how range R = v0^2 sin(2 theta) / g peaks at 45 deg.",
        "graph": {
            "expression": "v0^2 * sin(2 * theta * pi / 180) / g",
            "x_var": "theta",
            "x_min": 0, "x_max": 90,
            "x_label": "Launch angle (deg)", "y_label": "Range (m)",
            "sliders": [
                {"name": "v0", "label": "Initial speed", "min": 5, "max": 60, "initial": 25, "step": 0.5, "unit": "m/s"},
                {"name": "g",  "label": "Gravity",       "min": 1, "max": 25, "initial": 9.8, "step": 0.1, "unit": "m/s^2"},
            ],
            "samples": 200,
        },
    }),
    ("labeled_hotspots", {
        "template": "labeled_hotspots",
        "title": "Parts of a flower",
        "instructions": "Click each labelled part to learn its function.",
        "hotspots": {
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Mature_flower_diagram.svg/640px-Mature_flower_diagram.svg.png",
            "image_alt": "Flower diagram",
            "hotspots": [
                {"label": "Petal",  "description": "Coloured leaf-like structure that attracts pollinators.", "x_pct": 30, "y_pct": 40, "radius_pct": 4},
                {"label": "Stamen", "description": "Male reproductive organ (anther + filament).", "x_pct": 50, "y_pct": 50, "radius_pct": 4},
                {"label": "Pistil", "description": "Female reproductive organ (stigma + style + ovary).", "x_pct": 60, "y_pct": 50, "radius_pct": 4},
                {"label": "Sepal",  "description": "Leaf-like structure that protected the bud.", "x_pct": 40, "y_pct": 70, "radius_pct": 4},
            ],
            "quiz_mode": False,
        },
    }),
    ("sentence_builder", {
        "template": "sentence_builder",
        "title": "Build the French sentence",
        "instructions": "Drag the tiles into the order that means: I would like a coffee, please.",
        "sentence": {
            "target_label": "I would like a coffee, please.",
            "tiles": [
                {"text": "Je",         "correct_position": 1},
                {"text": "voudrais",   "correct_position": 2},
                {"text": "un",         "correct_position": 3},
                {"text": "cafe",       "correct_position": 4},
                {"text": "s'il vous plait", "correct_position": 5},
            ],
            "distractor_tiles": ["avec", "merci"],
        },
    }),
    ("vocab_pairs", {
        "template": "vocab_pairs",
        "title": "Hindi greetings",
        "instructions": "Match each Hindi term with its English meaning. Switch to Memory mode to play a flip-and-find game.",
        "vocab": {
            "mode": "pairs",
            "cards": [
                {"term": "Namaste",        "translation": "Hello / I bow to you"},
                {"term": "Dhanyavaad",     "translation": "Thank you"},
                {"term": "Kshama kijiye",  "translation": "I am sorry / Please forgive"},
                {"term": "Phir milenge",   "translation": "See you again"},
                {"term": "Subh prabhat",   "translation": "Good morning"},
                {"term": "Subh raatri",    "translation": "Good night"},
            ],
        },
    }),
    ("molecule_3d", {
        "template": "molecule_3d",
        "title": "Water (H2O) — 3D structure",
        "instructions": "Drag to rotate. Click an atom for info.",
        "molecule": {
            "name": "Water (H2O)",
            "description": "A bent molecule with H-O-H bond angle ~104.5 degrees.",
            "atoms": [
                {"name": "O1", "element": "O", "x": 0,     "y": 0,    "z": 0, "description": "Central oxygen atom (sp3 hybrid)."},
                {"name": "H1", "element": "H", "x": 0.76,  "y": 0.59, "z": 0, "description": "One of two hydrogens."},
                {"name": "H2", "element": "H", "x": -0.76, "y": 0.59, "z": 0, "description": "The other hydrogen."},
            ],
            "bonds": [
                {"from_atom": "O1", "to_atom": "H1", "order": 1},
                {"from_atom": "O1", "to_atom": "H2", "order": 1},
            ],
        },
    }),
    ("circuit_2d", {
        "template": "circuit_2d",
        "title": "Series resistor circuit",
        "instructions": "A 12-V battery driving two resistors in series. Side panel shows total R and current.",
        "circuit": {
            "description": "Two resistors (4 ohm and 8 ohm) connected in series with a 12-V battery.",
            "analysis": "series",
            "components": [
                {"kind": "battery",  "name": "B1", "value": 12, "unit": "V",   "x": 8,  "y": 12},
                {"kind": "resistor", "name": "R1", "value": 4,  "unit": "ohm", "x": 20, "y": 6},
                {"kind": "resistor", "name": "R2", "value": 8,  "unit": "ohm", "x": 32, "y": 6},
                {"kind": "junction", "name": "J1",                              "x": 8,  "y": 6},
                {"kind": "junction", "name": "J2",                              "x": 38, "y": 6},
                {"kind": "junction", "name": "J3",                              "x": 38, "y": 18},
                {"kind": "junction", "name": "J4",                              "x": 8,  "y": 18},
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
    errors = 0
    for name, payload in SAMPLES:
        try:
            sim = SimulationOutput.model_validate(payload)
            data = render_simulation_html(sim)
            # Spot-check that the placeholder was replaced (no leftover __XXX__).
            if b"__" in data and any(t.encode() in data for t in (
                "GRAPH_JSON", "HOTSPOTS_JSON", "SENTENCE_JSON",
                "VOCAB_JSON", "MOLECULE_JSON", "CIRCUIT_JSON",
            )):
                print(f"  [warn] {name}: placeholder still present — renderer wiring missed")
                errors += 1
            else:
                print(f"  [ok]  {name}: validated + rendered, {len(data)} bytes")
        except Exception as e:
            print(f"  [FAIL] {name}: {type(e).__name__}: {e}")
            errors += 1
    print()
    print(f"Result: {len(SAMPLES) - errors}/{len(SAMPLES)} Tier-1 templates working", "[ALL OK]" if errors == 0 else "[ERRORS]")


if __name__ == "__main__":
    main()
