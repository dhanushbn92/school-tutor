from dataclasses import dataclass, field


WORKSHEET_SYSTEM_PROMPT = """\
You are a CBSE/NCERT curriculum-aligned question writer for the Indian school system.
Your job is to write classroom-ready worksheets for the exact class and subject given.

Strict rules:
1. Use ONLY the chapter content and learning outcomes provided. Do not invent facts
   outside that scope.
2. Match the reading level of the target class; prefer short, clear sentences.
3. Every question must map to one of the supplied learning outcome codes via the
   `outcome_code` field. If no outcome perfectly fits, pick the closest one.
4. Follow the requested question-type and difficulty distribution as closely as possible.
5. For MCQ: give 4 plausible options, one correct; options must be unambiguous; the
   `answer` must be copied verbatim from the options.
6. For TRUE_FALSE: options must be exactly ["True", "False"].
7. For FILL_BLANK: indicate the blank with "_____" in the question; `answer` is the
   missing word or phrase.
8. For SHORT_ANSWER and LONG_ANSWER: `answer` is a teacher-quality model answer.
9. For CASE_BASED: include a short scenario in the question, then the sub-question.
10. `total_marks` must equal the sum of per-question marks.
11. Set `cognitive_level` on every question using Bloom's taxonomy:
    - REMEMBER: recall a fact, definition, name, or formula verbatim.
    - UNDERSTAND: explain in own words, identify examples, summarise.
    - APPLY: use a concept or procedure in a familiar situation.
    - ANALYZE: compare, classify, distinguish parts, infer relationships.
    - EVALUATE: judge based on criteria, justify a choice, critique.
    - CREATE: design, propose, plan something new from given parts.
    Pick the level the QUESTION tests, not the level of the underlying outcome.
12. Output strictly valid JSON matching the schema. No prose, no markdown fences.
"""


@dataclass
class WorksheetRequest:
    class_level: int
    subject_name: str
    chapter_number: int
    chapter_title: str
    chapter_text: str
    outcomes: list[dict]  # [{code, description, bloom_level, topic?}, ...]
    topics: list[str] = field(default_factory=list)
    question_count: int = 10
    difficulty_mix: dict[str, int] | None = None  # {"EASY": 4, "MEDIUM": 4, "HARD": 2}
    cognitive_mix: dict[str, int] | None = None  # {"FACTUAL": 3, "UNDERSTANDING": 4, "APPLICATION": 3}
    question_types: list[str] | None = None  # e.g. ["MCQ", "SHORT_ANSWER"]
    focus_outcome_codes: list[str] | None = None
    language_hint: str = "clear English suitable for the target class"


def build_worksheet_user_prompt(req: WorksheetRequest) -> str:
    outcomes_block = "\n".join(
        f"- [{o['code']}] ({o['bloom_level']}) {o['description']}"
        for o in req.outcomes
    )
    topics_block = ", ".join(req.topics) if req.topics else "(not enumerated; infer from chapter)"
    difficulty_line = (
        ", ".join(f"{k}={v}" for k, v in req.difficulty_mix.items())
        if req.difficulty_mix
        else "teacher's discretion (aim for a balanced mix)"
    )
    cognitive_line = (
        ", ".join(f"{k}={v}" for k, v in req.cognitive_mix.items())
        if req.cognitive_mix
        else "balanced mix across Factual (REMEMBER), Understanding (UNDERSTAND), and Application (APPLY/ANALYZE/EVALUATE/CREATE)"
    )
    types_line = ", ".join(req.question_types) if req.question_types else "any mix appropriate for the class"
    focus_line = (
        f"Focus questions on these outcome codes: {', '.join(req.focus_outcome_codes)}."
        if req.focus_outcome_codes
        else "Cover the full set of outcomes above; do not bias toward any single one."
    )

    return f"""\
Write a worksheet for:
- Class: {req.class_level}
- Subject: {req.subject_name}
- Chapter {req.chapter_number}: {req.chapter_title}

Number of questions: {req.question_count}
Question type mix: {types_line}
Difficulty mix: {difficulty_line}
Cognitive level mix (Bloom buckets — FACTUAL=REMEMBER, UNDERSTANDING=UNDERSTAND, APPLICATION=APPLY/ANALYZE/EVALUATE/CREATE): {cognitive_line}
Language: {req.language_hint}
{focus_line}

Topics covered in the chapter: {topics_block}

Learning outcomes (use the `code` in each question's `outcome_code` field):
{outcomes_block}

Chapter content (use ONLY this as your source of truth):
<<<CHAPTER_TEXT_START>>>
{req.chapter_text}
<<<CHAPTER_TEXT_END>>>

Produce the worksheet now as a single JSON object matching the schema.
"""
