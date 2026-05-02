from app.llm.prompts.worksheet import WorksheetRequest


QUIZ_SYSTEM_PROMPT = """\
You are a CBSE/NCERT curriculum-aligned question writer for the Indian school system.
Your job is to populate a reusable question bank. A teacher will review each question
before it is shown to students.

Strict rules:
1. Use ONLY the chapter content and learning outcomes provided. Do not invent facts
   outside that scope.
2. Favour question types that auto-grade cleanly:
   - Prefer: MCQ, TRUE_FALSE, FILL_BLANK, SHORT_ANSWER.
   - Use LONG_ANSWER only if the request explicitly asks for it.
   - Use CASE_BASED sparingly and only for competency-style items.
3. Every question must map to one of the supplied learning outcome codes via the
   `outcome_code` field. If no outcome perfectly fits, pick the closest one.
4. Match the reading level of the target class.
5. For MCQ: 4 plausible options, one correct; the `answer` must be copied verbatim from
   the options; distractors should be common misconceptions from the chapter.
6. For TRUE_FALSE: options must be exactly ["True", "False"].
7. For FILL_BLANK: mark the blank with "_____"; `answer` is the missing phrase.
8. For SHORT_ANSWER: `answer` is a 1-3 sentence model answer a teacher would accept.
9. Include a concise `explanation` for every question (why the answer is correct, or
   the key idea being tested). This is shown to students after grading.
10. `total_marks` must equal the sum of per-question marks.
11. Set `cognitive_level` on every question using Bloom's taxonomy:
    - REMEMBER: recall a fact verbatim.
    - UNDERSTAND: explain in own words.
    - APPLY: use the concept in a familiar situation.
    - ANALYZE: compare, classify, distinguish.
    - EVALUATE: judge or justify.
    - CREATE: design or propose.
    Pick the level the QUESTION tests, not the underlying outcome's level.
12. Output strictly valid JSON matching the schema. No prose, no markdown fences.
"""


def build_quiz_user_prompt(req: WorksheetRequest) -> str:
    outcomes_block = "\n".join(
        f"- [{o['code']}] ({o['bloom_level']}) {o['description']}"
        for o in req.outcomes
    )
    topics_block = ", ".join(req.topics) if req.topics else "(not enumerated; infer from chapter)"
    difficulty_line = (
        ", ".join(f"{k}={v}" for k, v in req.difficulty_mix.items())
        if req.difficulty_mix
        else "balanced (EASY / MEDIUM / HARD)"
    )
    cognitive_line = (
        ", ".join(f"{k}={v}" for k, v in req.cognitive_mix.items())
        if req.cognitive_mix
        else "balanced mix across Factual (REMEMBER), Understanding (UNDERSTAND), and Application (APPLY/ANALYZE/EVALUATE/CREATE)"
    )
    types_line = (
        ", ".join(req.question_types)
        if req.question_types
        else "MCQ, TRUE_FALSE, FILL_BLANK, SHORT_ANSWER"
    )
    focus_line = (
        f"Focus questions on these outcome codes: {', '.join(req.focus_outcome_codes)}."
        if req.focus_outcome_codes
        else "Distribute questions across ALL outcomes above; do not leave any outcome untested."
    )

    return f"""\
Generate quiz-bank questions for:
- Class: {req.class_level}
- Subject: {req.subject_name}
- Chapter {req.chapter_number}: {req.chapter_title}

Number of questions: {req.question_count}
Allowed question types: {types_line}
Difficulty mix: {difficulty_line}
Cognitive level mix (Bloom buckets — FACTUAL=REMEMBER, UNDERSTANDING=UNDERSTAND, APPLICATION=APPLY/ANALYZE/EVALUATE/CREATE): {cognitive_line}
Language: {req.language_hint}
{focus_line}

Topics in the chapter: {topics_block}

Learning outcomes (use the `code` as each question's `outcome_code`):
{outcomes_block}

Chapter content (source of truth):
<<<CHAPTER_TEXT_START>>>
{req.chapter_text}
<<<CHAPTER_TEXT_END>>>

Produce the quiz now as a single JSON object matching the schema.
Every question needs an `explanation`.
"""
