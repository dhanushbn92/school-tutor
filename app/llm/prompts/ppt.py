from app.llm.prompts.worksheet import WorksheetRequest


PPT_SYSTEM_PROMPT = """\
You are a CBSE/NCERT-aligned slide-deck writer for Indian classrooms.
Write a classroom-ready slide outline for the chapter and class given.

Strict rules:
1. Use ONLY the chapter content and learning outcomes provided.
2. Produce 8-14 slides unless the request says otherwise. Structure:
   - Slide 1: TITLE (title + one-liner)
   - Slide 2: OBJECTIVES (4-5 bullets, learner-facing)
   - Next 4-8: CONCEPT, EXAMPLE, ACTIVITY, QUICK_CHECK slides mixed to suit flow
   - Last 1-2: SUMMARY (and optional QUICK_CHECK review)
3. Each content slide: 3-6 concise bullets. No paragraphs on a slide.
4. Speaker notes: 2-4 sentences the teacher can read or paraphrase.
5. Match the reading level of the class; prefer short sentences.
6. Record `outcome_codes_covered` — the full set of outcome codes this deck teaches.
7. Output strictly valid JSON matching the schema. No prose, no markdown fences.
"""


def build_ppt_user_prompt(req: WorksheetRequest, *, slide_count_target: int = 10) -> str:
    outcomes_block = "\n".join(
        f"- [{o['code']}] ({o['bloom_level']}) {o['description']}"
        for o in req.outcomes
    )
    return f"""\
Write a slide deck outline for:
- Class: {req.class_level}
- Subject: {req.subject_name}
- Chapter {req.chapter_number}: {req.chapter_title}
- Target slide count: ~{slide_count_target}

Learning outcomes (use codes in `outcome_codes_covered`):
{outcomes_block}

Chapter content (source of truth):
<<<CHAPTER_TEXT_START>>>
{req.chapter_text}
<<<CHAPTER_TEXT_END>>>

Produce the deck outline as a single JSON object matching the schema.
"""
