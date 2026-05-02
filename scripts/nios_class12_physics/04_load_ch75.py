"""Load NIOS Class 12 Physics, Chapter 3 (Laws of Motion)."""

from app.db.session import SessionLocal
from app.models.curriculum import BloomLevel

from scripts.nios_class12_physics.lib import (
    DATA_DIR, insert_outcomes, insert_topics, load_content_blobs,
    load_questions_from_file, update_chapter_full_text,
)


CHAPTER_ID = 75
PREFIX = "ch75"


TOPICS = [
    {"name": "Force And Inertia",
     "description": "Definition of force as a vector, the newton as the SI unit, and inertia as the property that resists changes in motion (rest, motion, direction).",
     "section_header": "3.1 FORCE AND INERTIA",
     "next_section_header": "3.2 NEWTON'S FIRST LAW"},
    {"name": "Newton's First Law",
     "description": "Statement, the concept of an inertial frame of reference, and the role of the first law in defining what a force is.",
     "section_header": "3.2 NEWTON'S FIRST LAW",
     "next_section_header": "3.3 NEWTON'S SECOND LAW"},
    {"name": "Newton's Second Law",
     "description": "F = dp/dt and its constant-mass form F = ma, the SI definition of the newton, free-body diagrams, linear momentum and impulse.",
     "section_header": "3.3 NEWTON'S SECOND LAW",
     "next_section_header": "3.4 NEWTON'S THIRD LAW"},
    {"name": "Newton's Third Law",
     "description": "Action–reaction pairs, the precise statement that the two forces act on different bodies, and standard examples (walking, recoil, rocket).",
     "section_header": "3.4 NEWTON'S THIRD LAW",
     "next_section_header": "3.5 CONSERVATION OF LINEAR MOMENTUM"},
    {"name": "Conservation Of Momentum",
     "description": "Conservation of total linear momentum in an isolated system, derivation from the third law, and applications to recoil, collisions and rocket propulsion.",
     "section_header": "3.5 CONSERVATION OF LINEAR MOMENTUM",
     "next_section_header": "3.6 FRICTION"},
    {"name": "Friction",
     "description": "Static vs kinetic friction, the inequalities f_s ≤ μ_s N and f_k = μ_k N, and the empirical properties of friction.",
     "section_header": "3.6 FRICTION",
     "next_section_header": "3.7 PROBLEM-SOLVING WITH NEWTON'S LAWS"},
]


OUTCOMES = [
    {"code": "12-NIOS-PHY-LM-01", "topic_name": "Force And Inertia", "bloom": BloomLevel.UNDERSTAND,
     "description": "Define force, identify the newton as the SI unit, and explain the three kinds of inertia (rest, motion, direction)."},
    {"code": "12-NIOS-PHY-LM-02", "topic_name": "Newton's First Law", "bloom": BloomLevel.UNDERSTAND,
     "description": "State Newton's first law and identify which frames of reference are inertial."},
    {"code": "12-NIOS-PHY-LM-03", "topic_name": "Newton's Second Law", "bloom": BloomLevel.APPLY,
     "description": "Apply F = ma and F = dp/dt to compute acceleration, force or change in momentum, including impulse problems."},
    {"code": "12-NIOS-PHY-LM-04", "topic_name": "Newton's Third Law", "bloom": BloomLevel.UNDERSTAND,
     "description": "State Newton's third law and explain why action–reaction forces do not cancel each other."},
    {"code": "12-NIOS-PHY-LM-05", "topic_name": "Conservation Of Momentum", "bloom": BloomLevel.APPLY,
     "description": "Apply the conservation of linear momentum to recoil, collision and rocket-style problems."},
    {"code": "12-NIOS-PHY-LM-06", "topic_name": "Conservation Of Momentum", "bloom": BloomLevel.EVALUATE,
     "description": "Justify conservation of momentum in an isolated system using Newton's third law."},
    {"code": "12-NIOS-PHY-LM-07", "topic_name": "Friction", "bloom": BloomLevel.APPLY,
     "description": "Apply f_s ≤ μ_s N and f_k = μ_k N to decide whether a body slides under an applied force, and compute the resulting acceleration."},
    {"code": "12-NIOS-PHY-LM-08", "topic_name": "Friction", "bloom": BloomLevel.ANALYZE,
     "description": "Analyse and solve free-body-diagram problems on inclined planes and connected-body systems involving friction and tension."},
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
