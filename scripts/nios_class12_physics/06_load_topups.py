"""Load top-up question banks for NIOS Class 12 Physics, Chapters 1-3.

Each chXX_questions_topup.json adds questions to bring the chapter up to
the 100 objective + 30 subjective + ~10 case-based minimum. Idempotent
on question text — re-running is safe.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/06_load_topups.py
"""

from app.db.session import SessionLocal

from scripts.nios_class12_physics.lib import load_questions_from_file


TOPUPS = [
    (73, "ch73_questions_topup.json"),
    (74, "ch74_questions_topup.json"),
    (75, "ch75_questions_topup.json"),
]


def main() -> None:
    db = SessionLocal()
    try:
        for chapter_id, filename in TOPUPS:
            print(f"--- chapter {chapter_id}: {filename} ---")
            load_questions_from_file(db, chapter_id=chapter_id, filename=filename)
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
