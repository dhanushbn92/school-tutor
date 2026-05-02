"""Load NIOS Class 12 Physics, Chapter 2 (Motion in a Straight Line):
chapter full_text + topics + outcomes + question bank + 6 content blobs.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/03_load_ch74.py
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


CHAPTER_ID = 74
PREFIX = "ch74"


TOPICS = [
    {"name": "Position Distance And Displacement",
     "description": "Frame of reference, position as a signed coordinate, scalar distance vs vector displacement, and the inequality distance ≥ |displacement|.",
     "section_header": "2.1 POSITION, DISTANCE AND DISPLACEMENT",
     "next_section_header": "2.2 SPEED AND VELOCITY"},
    {"name": "Speed And Velocity",
     "description": "Average and instantaneous speed and velocity, the difference between them, and the geometric meaning of velocity as the slope of an x–t graph.",
     "section_header": "2.2 SPEED AND VELOCITY",
     "next_section_header": "2.3 ACCELERATION"},
    {"name": "Acceleration",
     "description": "Average and instantaneous acceleration, uniform vs non-uniform acceleration, the relationship between the signs of acceleration and velocity, and the slope of a v–t graph.",
     "section_header": "2.3 ACCELERATION",
     "next_section_header": "2.4 KINEMATIC EQUATIONS FOR UNIFORM ACCELERATION"},
    {"name": "Kinematic Equations",
     "description": "The three equations of motion for uniform acceleration: v = u + at, s = ut + (1/2)at², v² = u² + 2as. Their derivations and the displacement-vs-distance caveat.",
     "section_header": "2.4 KINEMATIC EQUATIONS FOR UNIFORM ACCELERATION",
     "next_section_header": "2.5 MOTION UNDER GRAVITY"},
    {"name": "Motion Under Gravity",
     "description": "Free fall near Earth's surface, constant acceleration g ≈ 9.8 m/s², expressions for time of rise, maximum height and time of flight for a vertical throw.",
     "section_header": "2.5 MOTION UNDER GRAVITY",
     "next_section_header": "2.6 POSITION–TIME AND VELOCITY–TIME GRAPHS"},
    {"name": "Motion Graphs",
     "description": "Reading and interpreting position–time and velocity–time graphs: slopes give velocity / acceleration; the area under a v–t graph gives displacement.",
     "section_header": "2.6 POSITION–TIME AND VELOCITY–TIME GRAPHS",
     "next_section_header": "SUMMARY"},
]


OUTCOMES = [
    {"code": "12-NIOS-PHY-MSL-01", "topic_name": "Position Distance And Displacement", "bloom": BloomLevel.UNDERSTAND,
     "description": "Distinguish distance from displacement; explain why distance ≥ |displacement| and identify when equality holds."},
    {"code": "12-NIOS-PHY-MSL-02", "topic_name": "Speed And Velocity", "bloom": BloomLevel.UNDERSTAND,
     "description": "Distinguish average speed from average velocity; relate instantaneous velocity to the slope of a position–time graph."},
    {"code": "12-NIOS-PHY-MSL-03", "topic_name": "Acceleration", "bloom": BloomLevel.UNDERSTAND,
     "description": "Define average and instantaneous acceleration; explain why the signs of v and a are independent."},
    {"code": "12-NIOS-PHY-MSL-04", "topic_name": "Kinematic Equations", "bloom": BloomLevel.APPLY,
     "description": "Apply the three kinematic equations (v = u + at, s = ut + (1/2)at², v² = u² + 2as) to solve uniform-acceleration problems."},
    {"code": "12-NIOS-PHY-MSL-05", "topic_name": "Kinematic Equations", "bloom": BloomLevel.EVALUATE,
     "description": "Justify when the kinematic equations apply, recognising that a must be constant for them to be valid."},
    {"code": "12-NIOS-PHY-MSL-06", "topic_name": "Motion Under Gravity", "bloom": BloomLevel.APPLY,
     "description": "Apply the kinematic equations to free-fall problems, including computing maximum height, time of rise, and time of flight."},
    {"code": "12-NIOS-PHY-MSL-07", "topic_name": "Motion Graphs", "bloom": BloomLevel.ANALYZE,
     "description": "Interpret a position–time or velocity–time graph: read off velocity from slope of x–t, acceleration from slope of v–t, and displacement from area under v–t."},
    {"code": "12-NIOS-PHY-MSL-08", "topic_name": "Motion Graphs", "bloom": BloomLevel.ANALYZE,
     "description": "Sketch x–t and v–t graphs that match a verbal description of a motion (uniform velocity, uniform acceleration, free fall, etc.)."},
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
