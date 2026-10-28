"""Pydantic models for the smart-speaker / voice integration API.

These are the request/response contracts a third-party speaker skill talks to.
Every response carries a ready-to-speak `spoken` string so the device can read
it aloud verbatim without having to compose sentences itself, alongside the
structured fields for skills that want to render or branch on them.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Subjects & progress
# --------------------------------------------------------------------------- #
class SpeakerSubject(BaseModel):
    subject_id: int
    name: str
    board: str
    language: str


class SubjectListResponse(BaseModel):
    class_level: int
    subjects: list[SpeakerSubject]
    spoken: str


class ChapterProgress(BaseModel):
    chapter_id: int
    chapter_number: int
    title: str
    status: str  # "mastered" | "in_progress" | "not_started"
    percent_complete: int  # outcomes attempted / total, 0-100
    average_score: int | None  # avg mastery of attempted outcomes, 0-100


class SubjectProgress(BaseModel):
    subject_id: int
    subject: str
    chapters_total: int
    chapters_mastered: int
    chapters_in_progress: int
    chapters_not_started: int
    outcomes_total: int
    outcomes_attempted: int
    average_score: int | None  # 0-100 across attempted outcomes
    chapters: list[ChapterProgress] = Field(default_factory=list)
    spoken: str


class ProgressResponse(BaseModel):
    class_level: int
    subjects: list[SubjectProgress]
    spoken: str


# --------------------------------------------------------------------------- #
# Chapter summaries (read aloud)
# --------------------------------------------------------------------------- #
class ChapterListItem(BaseModel):
    chapter_id: int
    chapter_number: int
    title: str
    has_summary: bool


class ChapterSummaryResponse(BaseModel):
    subject_id: int
    subject: str
    # When a specific chapter was resolved these are populated; when the caller
    # asked for a subject with no chapter, `chapter_id` is null and `chapters`
    # lists what is available so the speaker can offer a choice.
    chapter_id: int | None = None
    chapter_number: int | None = None
    title: str | None = None
    summary_text: str | None = None
    key_points: list[str] = Field(default_factory=list)
    chapters: list[ChapterListItem] = Field(default_factory=list)
    spoken: str


# --------------------------------------------------------------------------- #
# Turn-by-turn tests
# --------------------------------------------------------------------------- #
class SpeakerQuestion(BaseModel):
    question_number: int
    total_questions: int
    question_id: int
    question_type: str
    text: str
    has_options: bool
    options: list[str] | None = None  # ["45 degrees", ...] — no letters
    options_spoken: list[str] | None = None  # ["A. 45 degrees", ...]
    answer_hint: str  # how the learner should answer this type
    spoken: str  # full read-aloud: number + question + options + hint


class StartTestRequest(BaseModel):
    # Subject may be an id ("11") or a name ("Mathematics"); both accepted.
    subject: str = Field(min_length=1, max_length=120)
    chapter_id: int | None = None
    chapter_number: int | None = None
    question_count: int = Field(default=5, ge=1, le=20)


class StartTestResponse(BaseModel):
    session_token: str
    assessment_id: int
    subject: str
    chapter_title: str
    total_questions: int
    question: SpeakerQuestion
    spoken: str


class AnswerRequest(BaseModel):
    session_token: str
    answer_text: str = Field(default="", max_length=2000)


class TestResult(BaseModel):
    score: int
    max_score: int
    correct_count: int
    total_questions: int
    percent: int


class AnswerResponse(BaseModel):
    question_number: int
    question_id: int
    # is_correct is null for a question that cannot be auto-graded.
    is_correct: bool | None
    verdict: str  # "correct" | "incorrect" | "unscored"
    your_answer: str
    correct_answer: str
    explanation: str | None
    can_explain_more: bool
    finished: bool
    next_question: SpeakerQuestion | None = None
    result: TestResult | None = None  # populated only when finished
    # Updated session token to replay on the next tests/answer call. When the
    # test is finished it still decodes (so tests/more can reference the last
    # question), but there are no further questions to answer.
    session_token: str
    spoken: str


class ExplainMoreRequest(BaseModel):
    # Either replay the session token (uses the just-answered question) or name
    # a question_id directly. session_token takes precedence when both given.
    session_token: str | None = None
    question_id: int | None = None
    # "example" (another worked example), "analogy", or "deeper".
    kind: str = Field(default="example")


class ExplainMoreResponse(BaseModel):
    question_id: int
    kind: str
    text: str
    spoken: str
