"""Scaffold NIOS Class 10 (Secondary) Sanskrit (209): create the Subject,
Book, and all 22 lesson rows (Book 1: Ch1-11, Book 2: Ch12-22).

Titles carry the Devanagari lesson name plus a roman gloss so the bundle
ingester can resolve each chapter unambiguously (it also matches by
chapter_number). Content is authored bilingually: Sanskrit/Devanagari text
and grammar, with English explanations and answer keys.

Source: NIOS Secondary Sanskrit (209) syllabus (nios.ac.in).

Run:
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.nios_class10_sanskrit.01_scaffold_curriculum
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject


BOARD = "NIOS"
CLASS_LEVEL = 10
SUBJECT_NAME = "Sanskrit"
SUBJECT_LANGUAGE = "en"
BOOK_TITLE = "NIOS Sanskrit (209)"
BOOK_NCERT_CODE = "NIOS-209"
BOOK_ACADEMIC_YEAR = "2026-27"
BOOK_SOURCE_URL = (
    "https://www.nios.ac.in/online-course-material/secondary-courses/"
    "Sanskrit-(209)-Syllabus.aspx"
)

# 22 lessons of NIOS Secondary Sanskrit (209), in syllabus order.
CHAPTERS: list[tuple[int, str]] = [
    # --- Book 1 ---
    (1, "सुभाषितानि (Subhashitani)"),
    (2, "प्रेरणा (Prerana)"),
    (3, "त्याज्यं न धैर्यम् (Tyajyam na Dhairyam)"),
    (4, "कस्मात् किं शिक्षेत? (Kasmat Kim Shikshet)"),
    (5, "प्राणस्य श्रेष्ठत्वम् (Pranasya Shreshthatvam)"),
    (6, "यद्भविष्यो विनश्यति (Yadbhavisyo Vinasyati)"),
    (7, "अयोध्यां प्रत्यागमनम् (Ayodhyam Pratyagamanam)"),
    (8, "विरहकातरं तपोवनम् (Virahakataram Tapovanam)"),
    (9, "भारतीयविज्ञानम् (Bharatiya Vijnanam)"),
    (10, "प्रहेलिका (Prahelika)"),
    (11, "रचनाकौशलम् (Rachanakaushalam)"),
    # --- Book 2 ---
    (12, "यक्ष-युधिष्ठिर संवादः (Yaksha-Yudhishthira Samvadah)"),
    (13, "करुणापरा हि साधवः (Karunapara Hi Sadhavah)"),
    (14, "शरीरमाद्यं खलु धर्मसाधनम् (Shariramadyam Khalu Dharmasadhanam)"),
    (15, "ईशः क्व अस्ति (Ishah Kva Asti)"),
    (16, "गीतामृतम् (Gitamritam)"),
    (17, "स्वस्तिपन्थामनुचरेम (Svastipanthamanucharema)"),
    (18, "कर्तव्यनिष्ठा (Kartavyanistha)"),
    (19, "पुत्रोऽहं पृथिव्याः (Putro'ham Prithivyah)"),
    (20, "सत्याग्रहाश्रमः (Satyagrahashramah)"),
    (21, "तेजसां हि न वयः समीक्ष्यते (Tejasam Hi Na Vayah Samikshyate)"),
    (22, "पत्रलेखनम् (Patralekhanam)"),
]


def main() -> None:
    db = SessionLocal()
    try:
        klass = db.scalar(select(SchoolClass).where(SchoolClass.level == CLASS_LEVEL))
        if klass is None:
            raise SystemExit(f"No SchoolClass row for level={CLASS_LEVEL}.")

        subject = db.scalar(
            select(Subject)
            .where(Subject.class_id == klass.id)
            .where(Subject.name == SUBJECT_NAME)
            .where(Subject.language == SUBJECT_LANGUAGE)
            .where(Subject.board == BOARD)
        )
        if subject is None:
            subject = Subject(
                class_id=klass.id, name=SUBJECT_NAME,
                language=SUBJECT_LANGUAGE, board=BOARD,
            )
            db.add(subject); db.flush()
            print(f"[created] Subject id={subject.id}: {BOARD} class={CLASS_LEVEL} {SUBJECT_NAME}")
        else:
            print(f"[exists]  Subject id={subject.id}: {BOARD} class={CLASS_LEVEL} {SUBJECT_NAME}")

        book = db.scalar(
            select(Book)
            .where(Book.subject_id == subject.id)
            .where(Book.ncert_code == BOOK_NCERT_CODE)
            .where(Book.academic_year == BOOK_ACADEMIC_YEAR)
        )
        if book is None:
            book = Book(
                subject_id=subject.id, title=BOOK_TITLE,
                ncert_code=BOOK_NCERT_CODE, academic_year=BOOK_ACADEMIC_YEAR,
                source_url=BOOK_SOURCE_URL,
            )
            db.add(book); db.flush()
            print(f"[created] Book id={book.id}: {BOOK_TITLE}")
        else:
            print(f"[exists]  Book id={book.id}: {BOOK_TITLE}")

        existing = {
            c.chapter_number
            for c in db.scalars(select(Chapter).where(Chapter.book_id == book.id)).all()
        }
        inserted = 0
        for num, title in CHAPTERS:
            if num in existing:
                continue
            db.add(Chapter(book_id=book.id, chapter_number=num, title=title))
            inserted += 1
        db.commit()
        print(f"[ok] chapters: inserted {inserted}, skipped {len(existing)} pre-existing (total {len(CHAPTERS)})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
