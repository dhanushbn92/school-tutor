from app.llm.prompts.worksheet import WorksheetRequest


LESSON_PLAN_SYSTEM_PROMPT = """\
You are a CBSE/NCERT-aligned lesson-planning assistant for Indian schools.
Write a single classroom-ready lesson plan for the chapter and class given.

Strict rules:
1. Use ONLY the chapter content and learning outcomes provided. Do not invent
   off-syllabus material.
2. Follow the 5E instructional model: Engage, Explore, Explain, Elaborate, Evaluate,
   plus a final 'Assign' phase for homework. A full plan usually has 4-6 activities.
3. Activity durations must sum to the target `duration_minutes` (a typical class is
   40 or 45 minutes in India). If the sum is off, redistribute.
4. Objectives must be learner-facing ("Students will be able to..."). Prefer 3-5.
5. Each activity needs concrete teacher_actions and student_actions (bullets).
6. Materials must be realistically available in an Indian public-school classroom
   (chalkboard, basic lab equipment, household items). Avoid unrealistic props.
7. Key vocabulary: 4-8 terms from the chapter.
8. Map objectives back to the provided outcome codes via `outcome_codes_covered`.
9. Output strictly valid JSON matching the schema. No prose, no markdown fences.
"""


def build_lesson_plan_user_prompt(req: WorksheetRequest, *, duration_minutes: int = 40) -> str:
    outcomes_block = "\n".join(
        f"- [{o['code']}] ({o['bloom_level']}) {o['description']}"
        for o in req.outcomes
    )
    return f"""\
Write a lesson plan for:
- Class: {req.class_level}
- Subject: {req.subject_name}
- Chapter {req.chapter_number}: {req.chapter_title}
- Target duration: {duration_minutes} minutes

Learning outcomes available:
{outcomes_block}

Chapter content (source of truth):
<<<CHAPTER_TEXT_START>>>
{req.chapter_text}
<<<CHAPTER_TEXT_END>>>

Produce the lesson plan as a single JSON object matching the schema.
"""
