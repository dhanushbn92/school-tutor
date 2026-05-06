"""Regenerate the 5 simulation rows that fail_legacy_sim_templates.py
just flagged FAILED, using current templates that fit each chapter's
content. Authored hand-by-agent (this session) rather than via an LLM
API call, since the user doesn't have an Anthropic key configured for
the worker.

Strategy per row:
  - Build a payload validating against the current SimulationOutput schema
  - Update the row's output_json + status (FAILED -> APPROVED)
  - Re-render the artifact (overwrites the existing <id>.html on disk)
  - Clear error_message

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/regen_failed_sims_session.py
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.llm.schemas.simulation import SimulationOutput
from app.models.generation import GeneratedContent, GeneratedContentStatus
from app.rendering.simulation_html import render_simulation_html
from app.services.artifact_store import get_artifact_store


# ---- Authored content per row -----------------------------------------------

# Row 13 — Ch12 "Beyond Earth" (Class 6 Science, CBSE).
# Old template was solar_system; the natural current equivalent is three_d_orbit.
SIM_ROW_13 = {
    "template": "three_d_orbit",
    "title": "Our Solar System — orbits and planets",
    "instructions": "Drag to orbit the camera, scroll to zoom, click any body for info. Adjust the speed slider to slow time down. The orbital periods are NOT to scale (Neptune would take 165 years per orbit at real speed) — they are compressed so you can watch the dance.",
    "outcome_codes_covered": [],
    "orbit": {
        "central_name": "Sun",
        "central_description": "A G-type main-sequence star at the centre of the Solar System. Its gravity holds every planet in orbit. About 4.6 billion years old.",
        "central_size": 2.4,
        "central_color": "#fbbf24",
        "bodies": [
            {"name": "Mercury", "description": "Smallest planet, closest to the Sun. Orbital period ~88 Earth-days. No atmosphere; surface temperatures swing from -180°C to 430°C.", "radius": 3.5, "period_seconds": 4, "size": 0.30, "color": "#9ca3af"},
            {"name": "Venus",   "description": "Second planet. Brightest object in our sky after the Sun and Moon. Atmosphere of carbon dioxide; surface ~465°C.", "radius": 5.0, "period_seconds": 7, "size": 0.55, "color": "#fde68a"},
            {"name": "Earth",   "description": "Our home — third planet. The only known world with liquid surface water and life. One Moon.", "radius": 6.5, "period_seconds": 10, "size": 0.60, "color": "#3b82f6"},
            {"name": "Mars",    "description": "The 'Red Planet', fourth from the Sun. Iron-oxide dust gives it the colour. Two small moons (Phobos, Deimos). Orbital period ~687 days.", "radius": 8.0, "period_seconds": 14, "size": 0.45, "color": "#ef4444", "inclination_deg": 5},
            {"name": "Jupiter", "description": "Largest planet — over 300 Earth-masses. A gas giant with a famous Great Red Spot storm. 90+ confirmed moons.", "radius": 10.5, "period_seconds": 22, "size": 1.30, "color": "#fbbf24", "inclination_deg": 3},
            {"name": "Saturn",  "description": "Sixth planet, famous for its spectacular ring system made of ice and rock. Less dense than water.", "radius": 12.5, "period_seconds": 30, "size": 1.10, "color": "#facc15", "inclination_deg": 4},
            {"name": "Uranus",  "description": "Ice giant, tilted on its side (~98° axial tilt). Methane in its atmosphere gives a pale-blue colour.", "radius": 13.8, "period_seconds": 38, "size": 0.85, "color": "#67e8f9", "inclination_deg": 6},
            {"name": "Neptune", "description": "Outermost planet (since Pluto's reclassification). Strong winds (>2 000 km/h). One large moon, Triton.", "radius": 14.8, "period_seconds": 46, "size": 0.85, "color": "#3b82f6", "inclination_deg": 7},
        ],
    },
}


# Row 20 — Ch4 "Exploring Magnets" (Class 6 Science, CBSE).
# Old template was solar_system (mis-categorised). Map to three_d_field_lines as
# a magnetic dipole — directly illustrates the chapter's poles + attraction-and-
# repulsion sections.
SIM_ROW_20 = {
    "template": "three_d_field_lines",
    "title": "Magnetic field lines — bar magnet (N–S poles)",
    "instructions": "Drag to rotate around the bar magnet. Yellow streamlines emerge from the North pole and curve back into the South pole — the same shape iron filings make on paper around a real magnet. Try the Density slider for more / fewer lines.",
    "outcome_codes_covered": [],
    "field_lines": {
        "field_kind": "magnetic",
        "sources": [
            {"name": "north", "x": -3, "y": 0, "z": 0, "magnitude": 3.0,  "label": "N"},
            {"name": "south", "x":  3, "y": 0, "z": 0, "magnitude": -3.0, "label": "S"},
        ],
        "line_density": 24,
        "line_length": 16,
    },
}


# Row 69 — Ch1 "The Wonderful World of Science" (Class 6 Science, CBSE).
# Topic "The Scientific Method" → timeline_order works perfectly.
SIM_ROW_69 = {
    "template": "timeline_order",
    "title": "Scientific Method — put the steps in order",
    "instructions": "Drag the steps into the order a scientist would actually follow. When you're done, hit 'Check order' to see how you did.",
    "outcome_codes_covered": [],
    "events_timeline": [
        {"label": "Observe something interesting in the world",                  "description": "Notice a pattern, a surprise, or something that doesn't quite fit what you'd expect.", "correct_position": 1},
        {"label": "Ask a clear, specific question about it",                     "description": "What exactly do you want to find out? A good question is narrow and answerable.", "correct_position": 2},
        {"label": "Form a hypothesis — your best guess at the answer",          "description": "A hypothesis is a testable prediction, not just a wish. It should be possible to prove it wrong.", "correct_position": 3},
        {"label": "Design and perform an experiment",                            "description": "Decide what to measure, what to keep the same (controls), and what to change. Then do it carefully.", "correct_position": 4},
        {"label": "Record observations and analyse the results",                "description": "Write down what actually happened, then look for patterns. Did the data support your hypothesis?", "correct_position": 5},
        {"label": "Draw a conclusion and share it with others",                 "description": "State what you learned. If others can repeat your work and get the same result, the finding becomes reliable.", "correct_position": 6},
    ],
}


# Row 70 — Ch2 "Diversity in the Living World" (Class 6 Science, CBSE).
# Topics include Plant + Animal Classification. Categorize is the natural fit.
SIM_ROW_70 = {
    "template": "categorize",
    "title": "Sort the Living World — drag each organism into its group",
    "instructions": "Each card shows a living thing. Drop it into the group it belongs to. Some are easy (a tiger is clearly an animal); others are sneaky (is a mushroom a plant?). Don't worry about getting them all right the first time.",
    "outcome_codes_covered": [],
    "bins": [
        {"name": "Mammals",          "description": "Animals with hair / fur, give birth to live young (mostly), feed milk to their babies."},
        {"name": "Birds",            "description": "Animals with feathers, beaks, lay eggs, most can fly."},
        {"name": "Reptiles",         "description": "Cold-blooded animals with scaly skin; lay eggs on land."},
        {"name": "Fish",             "description": "Animals that live in water, breathe with gills, have fins and scales."},
        {"name": "Insects",          "description": "Small animals with three body parts (head, thorax, abdomen), six legs and usually wings."},
        {"name": "Flowering plants", "description": "Plants that produce flowers and seeds (mango tree, rose, wheat)."},
        {"name": "Non-flowering plants", "description": "Plants that reproduce without flowers — ferns, mosses, conifers."},
        {"name": "Fungi",            "description": "Not plants, not animals. Mushrooms, moulds, yeasts."},
    ],
    "items": [
        {"name": "Tiger",      "correct_bin": "Mammals",          "explanation": "A big cat — gives birth to live cubs and feeds them milk."},
        {"name": "Bat",        "correct_bin": "Mammals",          "explanation": "Yes, even though it flies. Bats are mammals — they have fur and feed their young milk."},
        {"name": "Dolphin",    "correct_bin": "Mammals",          "explanation": "Lives in water but breathes air, gives birth to live young, feeds milk. Mammal."},
        {"name": "Sparrow",    "correct_bin": "Birds",            "explanation": "Feathers, beak, lays eggs."},
        {"name": "Penguin",    "correct_bin": "Birds",            "explanation": "Can't fly, but it has feathers and a beak — definitely a bird."},
        {"name": "Crocodile",  "correct_bin": "Reptiles",         "explanation": "Scaly skin, lays eggs on land, cold-blooded."},
        {"name": "Cobra",      "correct_bin": "Reptiles",         "explanation": "A snake — limbless reptile with scales."},
        {"name": "Goldfish",   "correct_bin": "Fish",             "explanation": "Lives in water, breathes through gills, has fins."},
        {"name": "Butterfly",  "correct_bin": "Insects",          "explanation": "Three body segments, six legs, two pairs of wings."},
        {"name": "Honey bee",  "correct_bin": "Insects",          "explanation": "Six legs, wings, lives in colonies."},
        {"name": "Mango tree", "correct_bin": "Flowering plants", "explanation": "Produces flowers in season, then mango fruit with seeds."},
        {"name": "Rose plant", "correct_bin": "Flowering plants", "explanation": "The flower IS the giveaway."},
        {"name": "Fern",       "correct_bin": "Non-flowering plants", "explanation": "Ferns reproduce by spores, not seeds — no flowers."},
        {"name": "Pine tree",  "correct_bin": "Non-flowering plants", "explanation": "A conifer — produces seeds in cones, not flowers."},
        {"name": "Mushroom",   "correct_bin": "Fungi",            "explanation": "Not a plant! Fungi are their own kingdom — they don't photosynthesise."},
    ],
}


# Row 71 — Ch3 "Mindful Eating: A Path to a Healthy Body" (Class 6 Science, CBSE).
# Topics include Components of Food, Protective Nutrients, Balanced Diet.
# Build a Balanced Plate: sort foods into nutrient bins.
SIM_ROW_71 = {
    "template": "categorize",
    "title": "Build a Balanced Plate — sort foods by nutrient",
    "instructions": "Each card shows a food. Drop it into the bin for its MAIN nutrient. A balanced plate has a bit of each — carbohydrates for energy, proteins to build the body, fats for stored energy, plus vitamins, minerals, and roughage to stay healthy.",
    "outcome_codes_covered": [],
    "bins": [
        {"name": "Carbohydrates", "description": "Mainly for energy. Most of our daily food."},
        {"name": "Proteins",      "description": "For growth and repair of the body."},
        {"name": "Fats",          "description": "Stored energy plus help absorb some vitamins."},
        {"name": "Vitamins",      "description": "Tiny amounts needed to keep the body working — eyes, skin, immune system."},
        {"name": "Minerals",      "description": "Calcium for bones, iron for blood, etc."},
        {"name": "Roughage",      "description": "Plant fibre — keeps the digestive system moving."},
    ],
    "items": [
        {"name": "Rice",         "correct_bin": "Carbohydrates", "explanation": "A grain — mostly starch (carbohydrate)."},
        {"name": "Chapati",      "correct_bin": "Carbohydrates", "explanation": "Made from wheat — carbohydrate."},
        {"name": "Potato",       "correct_bin": "Carbohydrates", "explanation": "Mostly starch."},
        {"name": "Banana",       "correct_bin": "Carbohydrates", "explanation": "Fruit sugars + starch — carbohydrate."},
        {"name": "Dal (lentils)","correct_bin": "Proteins",       "explanation": "Pulses are an excellent vegetarian protein source."},
        {"name": "Egg",          "correct_bin": "Proteins",       "explanation": "Egg whites are nearly pure protein."},
        {"name": "Paneer",       "correct_bin": "Proteins",       "explanation": "Indian cottage cheese — milk protein."},
        {"name": "Fish",         "correct_bin": "Proteins",       "explanation": "Animal protein."},
        {"name": "Ghee",         "correct_bin": "Fats",           "explanation": "Clarified butter — almost pure fat."},
        {"name": "Mustard oil",  "correct_bin": "Fats",           "explanation": "Cooking oil — fat."},
        {"name": "Carrot",       "correct_bin": "Vitamins",       "explanation": "Rich in Vitamin A (good for eyes)."},
        {"name": "Lemon",        "correct_bin": "Vitamins",       "explanation": "Vitamin C — boosts immunity, prevents scurvy."},
        {"name": "Spinach",      "correct_bin": "Minerals",       "explanation": "Rich in iron — important for blood."},
        {"name": "Milk",         "correct_bin": "Minerals",       "explanation": "Strong source of calcium for bones (and protein too — but calcium is its standout)."},
        {"name": "Whole-wheat bread", "correct_bin": "Roughage",  "explanation": "The bran in whole-wheat is plant fibre — roughage."},
        {"name": "Cabbage",      "correct_bin": "Roughage",       "explanation": "Leafy vegetable — high in fibre."},
    ],
}


REGEN: list[tuple[int, dict]] = [
    (13, SIM_ROW_13),
    (20, SIM_ROW_20),
    (69, SIM_ROW_69),
    (70, SIM_ROW_70),
    (71, SIM_ROW_71),
]


def main() -> int:
    db = SessionLocal()
    store = get_artifact_store()
    try:
        for row_id, payload in REGEN:
            row = db.get(GeneratedContent, row_id)
            if row is None:
                print(f"[skip] row {row_id} not found")
                continue

            # Validate the new content against the current schema BEFORE
            # touching the row, so a typo in the payload doesn't leave
            # the row half-updated.
            validated = SimulationOutput.model_validate(payload)
            new_json = validated.model_dump(mode="json")

            # Re-render and persist. Keep the existing artifact_url
            # (e.g. 13.html) so cached frontends pick up the new bytes
            # without needing a URL change.
            data = render_simulation_html(validated)
            ext = (row.artifact_url or f"{row.id}.html").rsplit(".", 1)[-1] or "html"
            new_url = store.save(content_id=row.id, extension=ext, data=data)

            # Patch the row.
            row.output_json = new_json
            row.artifact_url = new_url
            row.status = GeneratedContentStatus.APPROVED
            row.error_message = None
            row.published_at = datetime.now(timezone.utc)
            row.published_by_id = 14  # platform.team@anaadi.org
            row.llm_provider = "hand-authored"
            row.llm_model = "curated-claude-agent"
            # Update the title to match the new payload, so the catalog
            # row reads sensibly.
            row.title = payload["title"]
            db.commit()
            print(
                f"[ok] row {row.id:3d} (ch {row.chapter_id}): "
                f"template={validated.template} | bytes={len(data):,} | url={new_url}"
            )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
