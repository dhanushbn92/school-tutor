"""Tests for auto-grading, with emphasis on Unicode-correct comparison so that
Devanagari (and accented) typed answers grade reliably regardless of how the
input method composed them.
"""
from app.models.question import Question, QuestionType
from app.services.grading import auto_grade


def _q(qtype: QuestionType, correct: str) -> Question:
    # Declarative models can be built with kwargs without a DB session; auto_grade
    # only reads .type and .correct_answer.
    return Question(type=qtype, correct_answer=correct)


def test_fill_blank_exact_match_awards_full_marks():
    q = _q(QuestionType.FILL_BLANK, "मनोरथैः")
    assert auto_grade(q, "मनोरथैः", 1) == (1, True, None)


def test_fill_blank_wrong_answer_scores_zero():
    q = _q(QuestionType.FILL_BLANK, "मनोरथैः")
    assert auto_grade(q, "कार्याणि", 1) == (0, True, None)


def test_fill_blank_devanagari_composed_vs_decomposed_are_equal():
    # "क़लम" (qalam) can be encoded with the precomposed nukta-qa U+0958, or as
    # base क (U+0915) + combining nukta (U+093C). They render identically; a
    # naive == would mark a correct typed answer wrong. Escapes are used so the
    # two byte sequences survive editor/Unicode normalisation intact.
    precomposed = chr(0x0958) + chr(0x0932) + chr(0x092E)               # qa(precomposed) la ma
    decomposed = chr(0x0915) + chr(0x093C) + chr(0x0932) + chr(0x092E)  # ka + nukta la ma
    assert precomposed != decomposed  # guard: the raw inputs really do differ
    q = _q(QuestionType.FILL_BLANK, precomposed)
    assert auto_grade(q, decomposed, 2) == (2, True, None)


def test_fill_blank_trims_and_collapses_whitespace():
    q = _q(QuestionType.FILL_BLANK, "भाषितम्")
    assert auto_grade(q, "  भाषितम्  ", 1) == (1, True, None)


def test_mcq_case_insensitive_latin_match():
    q = _q(QuestionType.MCQ, "A short well-said verse")
    assert auto_grade(q, "a short well-said verse", 1) == (1, True, None)


def test_true_false_boolean_parse():
    q = _q(QuestionType.TRUE_FALSE, "True")
    assert auto_grade(q, "true", 1) == (1, True, None)
    assert auto_grade(q, "False", 1) == (0, True, None)


def test_blank_answer_scores_zero_but_is_graded():
    q = _q(QuestionType.FILL_BLANK, "भाषितम्")
    assert auto_grade(q, "   ", 1) == (0, True, None)
    assert auto_grade(q, None, 1) == (0, True, None)


def test_subjective_types_are_not_auto_graded():
    for qtype in (QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER, QuestionType.CASE_BASED):
        q = _q(qtype, "some model answer")
        assert auto_grade(q, "anything", 3) == (None, False, None)
