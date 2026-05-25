"""LLM prompts for the "Tell me more" / "Why?" chain — Stage 3 of the
child-centric roadmap.

Three tiers of escalating "go deeper" content for a single question:

  DEEPER  — a longer, more thorough explanation of the same answer.
            Same correctness, but with the reasoning unpacked step by
            step.
  ANALOGY — a relatable everyday parallel that maps the concept onto
            a real-world scenario the learner already knows.
  EXAMPLE — a fresh worked example at the same concept (different
            numbers / setup), walked through end-to-end.

The provider returns plain text (not JSON) — we use `LLMProvider.chat`
rather than `generate_structured` because the output is a single
free-form block. Cached forever in `question_extended_explanation`,
so the LLM is hit at most once per (question, tier).

Tone guidance is shared across tiers and matches the rest of the
platform: friendly, India-context, no condescension. We never label
the learner as wrong — these prompts assume the learner has already
seen the verdict on a separate surface (quiz results or mistake
retry).
"""

from app.models.extended_explanation import ExplanationTier


# Shared voice / role / safety rules. Mirrors the tone of the AI-tutor
# chat prompt so the two surfaces feel like the same companion.
_SHARED_SYSTEM = """\
You are a warm, encouraging tutor for an Indian schoolchild using the
NCERT / CBSE curriculum. Your job is to deepen the learner's
understanding of one question they have already seen the answer to.

Voice rules:
- Be warm but never patronising. Talk like a kind elder sibling, not
  a textbook.
- Use simple sentences. No jargon unless you define it inline.
- Stay India-context — examples should feel familiar (cricket,
  monsoon, autos, kirana shops, school morning routines, festivals)
  rather than imported (baseball, snow days, dollar bills).
- Stay strictly on the question's topic. No tangents, no
  promotion of other content, no "you should also learn X" asides.
- Never tell the learner they are wrong, dumb, or behind. They
  already know the verdict.

Format rules:
- Return PLAIN TEXT only. No markdown headers, no JSON, no bullet
  list syntax (the surface that renders this will paragraph-wrap on
  blank lines).
- Use one or two short paragraphs separated by a blank line. Aim for
  60–180 words total.
- Do NOT restate the question text or the original correct answer
  verbatim — the learner is looking at them already.
"""


_TIER_DIRECTIVES: dict[ExplanationTier, str] = {
    ExplanationTier.DEEPER: """\
Write a DEEPER explanation: unpack the reasoning behind the correct
answer step by step, so a learner who almost got it can see exactly
where the chain of thought breaks. Mention the underlying concept by
name once, then explain it in plain language. Do not introduce
analogies or worked examples — those come later in the chain.
""",
    ExplanationTier.ANALOGY: """\
Write an ANALOGY: pick one familiar everyday scene and map the
concept onto it. Open with "Imagine…" or "Think about…". Walk the
learner through the parallel so the abstract idea has a concrete
hook. End with a single sentence tying the analogy back to the
question's concept. Do not give a worked numerical example.
""",
    ExplanationTier.EXAMPLE: """\
Write a WORKED EXAMPLE: invent ONE fresh problem at the same concept
and difficulty as the question (different numbers / setup, not a
near-duplicate), then solve it step by step. Show the working as
short numbered lines (1., 2., 3.) — not bullet points. The example
should be solvable in the learner's head or on a single line of
paper.
""",
}


def system_prompt_for(tier: ExplanationTier) -> str:
    """Combine the shared voice rules with the tier-specific
    directive. One system message goes to the model per call."""
    return _SHARED_SYSTEM + "\n" + _TIER_DIRECTIVES[tier]


def build_user_prompt(
    *,
    question_text: str,
    correct_answer: str,
    base_explanation: str | None,
    subject_name: str | None,
    chapter_title: str | None,
    class_level: int | None,
) -> str:
    """Compose the user turn for one explain call. Context is kept
    short on purpose — the question itself is usually under 100 words
    and the LLM doesn't need the whole chapter text. We feed just
    enough metadata for the model to anchor its tone to the right
    class level and subject."""
    parts: list[str] = []
    if class_level is not None:
        parts.append(f"Class level: {class_level}.")
    if subject_name:
        parts.append(f"Subject: {subject_name}.")
    if chapter_title:
        parts.append(f"Chapter: {chapter_title}.")
    context_line = " ".join(parts)

    base = (base_explanation or "").strip()
    base_block = (
        f"\n\nExisting brief explanation (for reference, do not repeat verbatim):\n{base}"
        if base
        else ""
    )

    return (
        f"{context_line}\n\n"
        f"Question:\n{question_text.strip()}\n\n"
        f"Correct answer:\n{correct_answer.strip()}"
        f"{base_block}"
    ).strip()
