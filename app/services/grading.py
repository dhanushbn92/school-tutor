"""Auto-grading for question types.

Returns `(marks_awarded, auto_graded, grading_details)`:
- `marks_awarded=None, auto_graded=False` → subjective; left for student
  self-evaluation against the answer key (eventually AI-graded).
- `marks_awarded=<int>, auto_graded=True` → machine-graded objective answer.
- `grading_details` is reserved for future graders; currently always None.

Rules (current beta — keyword/rubric grading is paused because the rule-based
output was unreliable; AI grading will replace it later):
- Objective types — auto-graded, full or zero marks:
    * MCQ          → exact match against `correct_answer`.
    * TRUE_FALSE   → boolean parse, exact match.
    * FILL_BLANK   → normalised exact match.
- Subjective types — never auto-graded; the student sees their answer next to
  the answer key in the results view and self-evaluates:
    * SHORT_ANSWER, LONG_ANSWER, CASE_BASED → return `(None, False, None)`.
"""
import unicodedata
from typing import Any

from app.models.question import Question, QuestionType


# Question types that the system can auto-grade today. SHORT_ANSWER and
# LONG_ANSWER were removed from this set when keyword-rubric grading was
# retired — they will return when AI evaluation lands.
_AUTO_TYPES = {
    QuestionType.MCQ,
    QuestionType.TRUE_FALSE,
    QuestionType.FILL_BLANK,
}


def is_auto_gradable(question_type: QuestionType) -> bool:
    return question_type in _AUTO_TYPES


def is_subjective(question_type: QuestionType) -> bool:
    """Subjective = student self-evaluates; the platform won't score it."""
    return question_type not in _AUTO_TYPES


def auto_grade(
    question: Question, answer_text: str | None, max_marks: int
) -> tuple[int | None, bool, dict[str, Any] | None]:
    if question.type not in _AUTO_TYPES:
        # Subjective: never auto-grade. The frontend shows the answer key and
        # the student self-evaluates. Mastery updates skip None scores.
        return (None, False, None)

    if answer_text is None or not answer_text.strip():
        return (0, True, None)

    normalised_answer = _normalise(answer_text)
    normalised_expected = _normalise(question.correct_answer)

    if question.type == QuestionType.MCQ:
        return (max_marks if normalised_answer == normalised_expected else 0, True, None)

    if question.type == QuestionType.TRUE_FALSE:
        got = _truthy(normalised_answer)
        want = _truthy(normalised_expected)
        if got is None:
            return (0, True, None)
        return (max_marks if got == want else 0, True, None)

    if question.type == QuestionType.FILL_BLANK:
        return (max_marks if normalised_answer == normalised_expected else 0, True, None)

    # Defensive fallback — should not reach here given the _AUTO_TYPES guard.
    return (None, False, None)


def _normalise(text: str) -> str:
    # NFC first so that visually identical strings compare equal regardless of
    # how the input method composed them. This matters for scripts like
    # Devanagari, where the same grapheme can be encoded as a precomposed
    # character or as a base + combining mark (e.g. क़ = U+0958 vs क + U+093C),
    # and for accented Latin text. Without it, a correct typed answer can be
    # marked wrong. .lower() is a harmless no-op for caseless scripts.
    normalised = unicodedata.normalize("NFC", text)
    return " ".join(normalised.strip().lower().split())


def _truthy(value: str) -> bool | None:
    if value in ("true", "t", "yes", "y", "1"):
        return True
    if value in ("false", "f", "no", "n", "0"):
        return False
    return None
