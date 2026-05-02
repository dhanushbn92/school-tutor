"""Auto-derive a keyword rubric for every subjective question that doesn't
already have one.

For each SHORT_ANSWER / LONG_ANSWER question without `auto_grade`:
  1. Tokenise the model answer (`correct_answer`).
  2. Strip stopwords and short tokens; pick the top-N most informative words.
  3. Build N keyword groups, each holding the word + a 4/5-char stem so common
     morphological variants ('carbohydrate' / 'carbohydrates' / 'carbs') still
     match via substring.
  4. Distribute the question's marks evenly across the N groups.
  5. Set a `min_words` threshold proportional to marks.

Hand-authored rubrics (already present on the question) are NEVER overwritten.

Usage:
    .venv/Scripts/python.exe -m scripts.backfill_rubrics
    .venv/Scripts/python.exe -m scripts.backfill_rubrics --class-level 6 --subject Science
    .venv/Scripts/python.exe -m scripts.backfill_rubrics --chapter-id 60 --replace-existing
"""
import argparse
import logging
import re

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Book, Chapter, SchoolClass, Subject
from app.models.question import (
    Question,
    QuestionStatus,
    QuestionType,
)


log = logging.getLogger(__name__)


_SUBJECTIVE = {QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER}


# Standard English stopwords + classroom filler ("sample", "answer", etc.).
_STOPWORDS = set(
    """
    a about above after again against all am an and any are as at be because been
    before being below between both but by can cant could did do does doing don
    dont down during each few for from further had has have having he her here
    hers him his how i if in into is it its itself just like let lets me mine
    more most my no nor not now of off on once only or other our ours out over
    own re same she should so some such than that the their theirs them themselves
    then there these they this those through to too under until up very was way
    were we what when where which while who whom why will with would you your you
    yours yourself yourselves above answer answers e.g. example examples sample
    samples explanation explain explains acceptable also students student class
    classes case grade many one ones full mark marks credit accepted point points
    show shows give gives given thing things item items something someone could
    would might should must may instead just etc others ans
    """.split()
)


def _stem(word: str) -> str:
    """Best-effort 4-5 char prefix to allow morphological matches.
    'carbohydrates' -> 'carbo' which is a substring of carbohydrate/carbs."""
    if len(word) <= 4:
        return word
    return word[: min(5, len(word))]


def _content_tokens(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    seen: set[str] = set()
    out: list[str] = []
    for token in cleaned.split():
        if len(token) < 4:
            continue
        if token in _STOPWORDS:
            continue
        if token.isdigit():
            continue
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _groups_for_marks(marks: int) -> int:
    if marks <= 1:
        return 2
    if marks <= 3:
        return 3
    if marks <= 5:
        return 5
    return 6


def _min_words_for_marks(marks: int) -> int:
    if marks <= 1:
        return 3
    if marks <= 2:
        return 6
    if marks <= 3:
        return 10
    if marks <= 5:
        return 15
    return 25


def derive_rubric(answer_text: str, marks: int) -> dict | None:
    """Return None when the answer is too short to derive useful keywords."""
    tokens = _content_tokens(answer_text or "")
    if len(tokens) < 2:
        return None

    n_groups = min(_groups_for_marks(marks), len(tokens))
    chosen = tokens[:n_groups]
    per = round(marks / n_groups, 2) if n_groups else 0
    groups = []
    for word in chosen:
        stem = _stem(word)
        any_of = [word]
        if stem != word and stem not in any_of:
            any_of.append(stem)
        groups.append({
            "label": word.capitalize(),
            "any_of": any_of,
            "marks": per,
        })
    return {
        "method": "keywords",
        "min_words": _min_words_for_marks(marks),
        "groups": groups,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter-id", type=int, default=None)
    parser.add_argument("--class-level", type=int, default=None)
    parser.add_argument("--subject", default=None, help="Subject name (e.g. 'Science').")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace rubrics that are already attached. By default we keep them.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        stmt = select(Question).where(
            Question.status == QuestionStatus.APPROVED,
            Question.type.in_(_SUBJECTIVE),
        )
        if args.chapter_id is not None:
            stmt = stmt.where(Question.chapter_id == args.chapter_id)
        elif args.class_level is not None and args.subject is not None:
            stmt = (
                stmt.join(Chapter, Question.chapter_id == Chapter.id)
                .join(Book, Chapter.book_id == Book.id)
                .join(Subject, Book.subject_id == Subject.id)
                .join(SchoolClass, Subject.class_id == SchoolClass.id)
                .where(SchoolClass.level == args.class_level, Subject.name == args.subject)
            )
        questions = list(db.scalars(stmt))
        added = 0
        skipped_existing = 0
        skipped_short = 0
        for q in questions:
            if q.auto_grade and not args.replace_existing:
                skipped_existing += 1
                continue
            rubric = derive_rubric(q.correct_answer or "", q.marks)
            if rubric is None:
                skipped_short += 1
                continue
            q.auto_grade = rubric
            added += 1
        db.commit()

    print(
        f"Backfill done. attached={added}, kept_existing={skipped_existing}, "
        f"skipped_short={skipped_short}, scanned={len(questions)}"
    )


if __name__ == "__main__":
    main()
