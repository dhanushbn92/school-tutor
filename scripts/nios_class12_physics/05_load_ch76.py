"""Load NIOS Class 12 Physics, Chapter 4 (Motion in a Plane):
chapter full_text + topics + outcomes + question bank + 6 content blobs.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/05_load_ch76.py
"""

from app.db.session import SessionLocal
from app.models.curriculum import BloomLevel

from scripts.nios_class12_physics.lib import (
    DATA_DIR,
    insert_outcomes,
    insert_topics,
    load_content_blobs,
    load_questions_from_file,
    update_chapter_full_text,
)


CHAPTER_ID = 76
PREFIX = "ch76"


TOPICS = [
    {"name": "Scalars And Vectors",
     "description": "Scalars versus vectors, the arrow representation, equality of vectors, unit vectors (î, ĵ, k̂), and writing a 2D vector in component form.",
     "section_header": "4.1 SCALARS AND VECTORS",
     "next_section_header": "4.2 ADDITION AND RESOLUTION OF VECTORS"},
    {"name": "Vector Addition And Resolution",
     "description": "Triangle and parallelogram laws of vector addition; magnitude and direction of the resultant; resolving a vector into perpendicular components; dot and cross products at a basic level.",
     "section_header": "4.2 ADDITION AND RESOLUTION OF VECTORS",
     "next_section_header": "4.3 MOTION IN A PLANE — VELOCITY AND ACCELERATION"},
    {"name": "Velocity And Acceleration In 2D",
     "description": "Position, velocity and acceleration as vectors in 2D; the component-wise form of the kinematic equations when acceleration is constant; the decoupling of x- and y-motion.",
     "section_header": "4.3 MOTION IN A PLANE — VELOCITY AND ACCELERATION",
     "next_section_header": "4.4 PROJECTILE MOTION"},
    {"name": "Projectile Motion",
     "description": "Motion of a body launched at an angle under gravity alone: parabolic trajectory, time of flight T = 2u sinθ/g, maximum height H = u²sin²θ/(2g), and range R = u²sin2θ/g (maximised at 45°).",
     "section_header": "4.4 PROJECTILE MOTION",
     "next_section_header": "4.5 UNIFORM CIRCULAR MOTION"},
    {"name": "Uniform Circular Motion",
     "description": "Motion at constant speed along a circle; centripetal acceleration a_c = v²/r = ω²r toward the centre; centripetal force F = mv²/r and its physical sources (tension, friction, gravity).",
     "section_header": "4.5 UNIFORM CIRCULAR MOTION",
     "next_section_header": "4.6 RELATIVE VELOCITY IN A PLANE"},
    {"name": "Relative Velocity In A Plane",
     "description": "Velocity of one body as seen from another in 2D as a vector subtraction; river-crossing problem (shortest path vs shortest time) and aeroplane in a crosswind.",
     "section_header": "4.6 RELATIVE VELOCITY IN A PLANE",
     "next_section_header": "SUMMARY"},
]


OUTCOMES = [
    {"code": "12-NIOS-PHY-MIP-01", "topic_name": "Scalars And Vectors", "bloom": BloomLevel.UNDERSTAND,
     "description": "Distinguish scalar and vector quantities; classify common physical quantities (mass, displacement, velocity, force, energy) as scalar or vector."},
    {"code": "12-NIOS-PHY-MIP-02", "topic_name": "Scalars And Vectors", "bloom": BloomLevel.REMEMBER,
     "description": "Identify the conditions under which two vectors are equal and explain why a vector's position on the page is irrelevant."},
    {"code": "12-NIOS-PHY-MIP-03", "topic_name": "Vector Addition And Resolution", "bloom": BloomLevel.APPLY,
     "description": "Apply the triangle or parallelogram law to find the magnitude and direction of the resultant of two vectors using R² = A² + B² + 2AB cos θ."},
    {"code": "12-NIOS-PHY-MIP-04", "topic_name": "Vector Addition And Resolution", "bloom": BloomLevel.APPLY,
     "description": "Resolve a vector into perpendicular components and reassemble components into a single vector; use components to add three or more vectors."},
    {"code": "12-NIOS-PHY-MIP-05", "topic_name": "Velocity And Acceleration In 2D", "bloom": BloomLevel.UNDERSTAND,
     "description": "Express the kinematic equations component-wise for constant acceleration in 2D and explain why the x- and y-motions are independent."},
    {"code": "12-NIOS-PHY-MIP-06", "topic_name": "Projectile Motion", "bloom": BloomLevel.APPLY,
     "description": "Apply the projectile equations to compute time of flight, maximum height, range, and the trajectory equation for a projectile launched at angle θ with speed u."},
    {"code": "12-NIOS-PHY-MIP-07", "topic_name": "Projectile Motion", "bloom": BloomLevel.ANALYZE,
     "description": "Analyse why the range is maximised at 45° and why complementary launch angles give the same range; identify the conditions implicit in each projectile formula."},
    {"code": "12-NIOS-PHY-MIP-08", "topic_name": "Uniform Circular Motion", "bloom": BloomLevel.UNDERSTAND,
     "description": "Explain why uniform circular motion is accelerated motion even though the speed is constant; derive a_c = v²/r and relate v, ω, T."},
    {"code": "12-NIOS-PHY-MIP-09", "topic_name": "Uniform Circular Motion", "bloom": BloomLevel.APPLY,
     "description": "Compute centripetal acceleration and the required centripetal force in mechanical scenarios (whirled stone, car on a curve, satellite in orbit)."},
    {"code": "12-NIOS-PHY-MIP-10", "topic_name": "Relative Velocity In A Plane", "bloom": BloomLevel.APPLY,
     "description": "Use v_AB = v_A − v_B to solve river-crossing problems (shortest path / shortest time) and crosswind-flying problems."},
]


def main() -> None:
    full_text = (DATA_DIR / f"{PREFIX}_full_text.txt").read_text(encoding="utf-8")
    db = SessionLocal()
    try:
        update_chapter_full_text(db, CHAPTER_ID, full_text)
        topic_ids = insert_topics(db, chapter_id=CHAPTER_ID, full_text=full_text, topic_specs=TOPICS)
        insert_outcomes(db, chapter_id=CHAPTER_ID, outcome_specs=OUTCOMES, topic_id_by_name=topic_ids)
        db.commit()
        load_questions_from_file(db, chapter_id=CHAPTER_ID, filename=f"{PREFIX}_questions.json")
        db.commit()
        load_content_blobs(db, chapter_id=CHAPTER_ID, prefix=PREFIX)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
