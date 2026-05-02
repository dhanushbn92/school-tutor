from app.llm.prompts.worksheet import WorksheetRequest


DIAGRAM_SYSTEM_PROMPT = """\
You are a CBSE/NCERT-aligned visual-summary assistant.
Produce a concept map for the chapter and class given.

Strict rules:
1. Use ONLY the chapter content and learning outcomes provided.
2. Pick a strong `central_term` that names the chapter's core idea.
3. Give 3-6 branches, each a sub-theme. Each branch has 2-5 `details` — keywords,
   not sentences. Prefer single-word or short-phrase leaves (1-4 words each).
4. Keep the tree balanced: don't overload one branch while leaving another empty.
5. Map the branches back to learning outcome codes via `outcome_codes_covered`.
6. Output strictly valid JSON matching the schema. No prose, no markdown fences.
"""


def build_diagram_user_prompt(req: WorksheetRequest) -> str:
    outcomes_block = "\n".join(
        f"- [{o['code']}] ({o['bloom_level']}) {o['description']}"
        for o in req.outcomes
    )
    return f"""\
Produce a concept map for:
- Class: {req.class_level}
- Subject: {req.subject_name}
- Chapter {req.chapter_number}: {req.chapter_title}

Learning outcomes:
{outcomes_block}

Chapter content (source of truth):
<<<CHAPTER_TEXT_START>>>
{req.chapter_text}
<<<CHAPTER_TEXT_END>>>

Produce the concept map as a single JSON object matching the schema.
"""
