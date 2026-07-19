"""Scaffold NIOS Class 12 (Senior Secondary) Sanskrit (309): create the
Subject, Book, and all 30 lesson rows.

Titles carry the Devanagari lesson name plus a roman gloss so the bundle
ingester can resolve each chapter unambiguously (it also matches by
chapter_number). Content is authored bilingually: Sanskrit/Devanagari text
and grammar, with English explanations and answer keys.

For lessons 26-29 the NIOS 309 syllabus offers an A/B optional-module choice;
this scaffold wires the A-track (literature / knowledge-tradition) as 26-30.

Source: NIOS Senior Secondary Sanskrit (309) syllabus.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.nios_class12_sanskrit.01_scaffold_curriculum
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject


BOARD = "NIOS"
CLASS_LEVEL = 12
SUBJECT_NAME = "Sanskrit"
SUBJECT_LANGUAGE = "en"
BOOK_TITLE = "NIOS Senior Secondary Sanskrit (309)"
BOOK_NCERT_CODE = "NIOS-309"
BOOK_ACADEMIC_YEAR = "2026-27"
BOOK_SOURCE_URL = (
    "https://www.nios.ac.in/online-course-material/sr-secondary-courses/"
    "sanskrit-(309).aspx"
)

# 30 lessons of NIOS Senior Secondary Sanskrit (309), in syllabus order.
CHAPTERS: list[tuple[int, str]] = [
    (1, "जीवनसंदेशः (Jivana-Sandeshah)"),
    (2, "यदि जानासि तद् वद (Yadi Janasi Tad Vada)"),
    (3, "आरोग्यं परमं सुखम् (Arogyam Paramam Sukham)"),
    (4, "वाचां मण्डनं सत्यम् (Vacham Mandanam Satyam)"),
    (5, "अतिलोभः न कर्तव्यः (Atilobhah Na Kartavyah)"),
    (6, "राजते खलु कन्याकुमारी (Rajate Khalu Kanyakumari)"),
    (7, "एतद् उपास्यम् (Etad Upasyam)"),
    (8, "परार्थे आत्मोत्सर्गः (Pararthe Atmotsargah)"),
    (9, "काले फलति सौभाग्यम् (Kale Phalati Saubhagyam)"),
    (10, "पतन्ति परपीडकाः (Patanti Parapidakah)"),
    (11, "अनुच्छेदलेखनम् (Anucchedalekhanam)"),
    (12, "संवादलेखनम् (Samvadalekhanam)"),
    (13, "वर्षर्तुवर्णनम् (Varsharttu-Varnanam)"),
    (14, "अमृतस्य पन्थाः (Amritasya Panthah)"),
    (15, "हिमालयो नाम नगाधिराजः (Himalayo Nama Nagadhirajah)"),
    (16, "मानो हि महतां धनम् (Mano Hi Mahatam Dhanam)"),
    (17, "कल्पनाकीर्तिः विजयते (Kalpanakirtih Vijayate)"),
    (18, "पर्यावरणस्य संरक्षणम् (Paryavaranasya Sanrakshanam)"),
    (19, "क्रोधोऽनर्थकारकः (Krodho'narthakarakah)"),
    (20, "अनन्तज्ञानसागरः (Ananta-Jnanasagarah)"),
    (21, "शल्यचिकित्साजनकः सुश्रुतः (Shalyachikitsa-Janakah Sushrutah)"),
    (22, "कष्टं न्यासस्य रक्षणम् (Kashtam Nyasasya Rakshanam)"),
    (23, "हृदयपरिवर्तनम् (Hridaya-Parivartanam)"),
    (24, "पत्रं लिखामः (Patram Likhamah)"),
    (25, "परियोजना-निर्माणम् (Pariyojana-Nirmanam)"),
    (26, "समसामयिकं संस्कृतसाहित्यम् (Samsamayikam Sanskrita-Sahityam)"),
    (27, "भारतीयज्ञानविज्ञानपरम्परा (Bharatiya Jnana-Vijnana-Parampara)"),
    (28, "संस्कृतम् अन्याः भारतीयाः भाषाः च (Sanskritam Anyah Bharatiyah Bhashah Cha)"),
    (29, "भारतीयसंस्कृतौ संस्काराः (Bharatiya-Sanskritau Samskarah)"),
    (30, "मुद्रणत्रुटिशोधनम् (Mudrana-Truti-Shodhanam)"),
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
