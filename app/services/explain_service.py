"""Service for the "Tell me more" / "Why?" chain (Stage 3 of the
child-centric roadmap).

One public entrypoint: `get_or_generate(db, question_id, tier, user)`
returns a (cached or freshly-generated) extended explanation block.

Caching strategy
----------------
Look up the (question_id, tier) row first. If it exists, return its
text immediately — no LLM call, instant response. If it doesn't,
build the prompt, call the LLM, write the row, return.

The UNIQUE(question_id, tier) constraint at the DB level handles
the concurrent-click race: two simultaneous clicks both miss the
cache, both call the LLM, and one wins the INSERT. The loser
catches the IntegrityError, rolls back its own row, and re-reads.

Error policy
------------
LLM failures raise `ExplainError` with a friendly message. The
endpoint translates this into a 503 + a structured payload so the
frontend can show "I can't fetch that right now — try again in a
moment" without panicking. No retries here — the LLM provider
already retries internally.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.llm import LLMError, get_llm_provider
from app.llm.prompts.explain import build_user_prompt, system_prompt_for


logger = logging.getLogger(__name__)
from app.models import (
    Book,
    Chapter,
    ExplanationTier,
    Question,
    QuestionExtendedExplanation,
    SchoolClass,
    Subject,
    User,
)


class ExplainError(Exception):
    """Domain-level error for the explain pipeline. Caught at the API
    layer and translated to an HTTP response."""


# Token budget for one "Tell me more" reply. 800 tokens ≈ 2-3 short
# paragraphs of plain text — plenty for any of the three tiers,
# none of which is meant to be an essay.
MAX_OUTPUT_TOKENS = 800

# Temperature picked per-tier. ANALOGY and EXAMPLE want a touch of
# creativity for variety; DEEPER stays conservative because we're
# unpacking a known answer.
_TIER_TEMPERATURE: dict[ExplanationTier, float] = {
    ExplanationTier.DEEPER: 0.3,
    ExplanationTier.ANALOGY: 0.6,
    ExplanationTier.EXAMPLE: 0.5,
}


def get_or_generate(
    db: Session,
    *,
    question_id: int,
    tier: ExplanationTier,
    user: User | None,
) -> QuestionExtendedExplanation:
    """Return the cached row if present, otherwise generate + cache.

    `user` is optional — only used to attribute `generated_by_id` for
    auditing. A None user (e.g. system batch job) still works; the FK
    is nullable.
    """
    cached = db.scalar(
        select(QuestionExtendedExplanation).where(
            QuestionExtendedExplanation.question_id == question_id,
            QuestionExtendedExplanation.tier == tier,
        )
    )
    if cached is not None:
        return cached

    question = db.get(Question, question_id)
    if question is None:
        raise ExplainError(f"Question {question_id} not found")

    # Resolve curriculum context for the prompt. All optional — the
    # prompt template handles missing fields.
    chapter: Chapter | None = db.get(Chapter, question.chapter_id) if question.chapter_id else None
    book: Book | None = db.get(Book, chapter.book_id) if chapter and chapter.book_id else None
    subject: Subject | None = (
        db.get(Subject, book.subject_id) if book and book.subject_id else None
    )
    # Class level lives on SchoolClass, not Subject — subject.class_id
    # points there. Missing classes are tolerated; the prompt just
    # omits the line.
    school_class: SchoolClass | None = (
        db.get(SchoolClass, subject.class_id) if subject and subject.class_id else None
    )
    class_level = school_class.level if school_class is not None else None

    user_prompt = build_user_prompt(
        question_text=question.text,
        correct_answer=question.correct_answer,
        base_explanation=question.explanation,
        subject_name=subject.name if subject else None,
        chapter_title=chapter.title if chapter else None,
        class_level=class_level,
    )
    system_prompt = system_prompt_for(tier)

    try:
        text = get_llm_provider().chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=_TIER_TEMPERATURE[tier],
            max_tokens=MAX_OUTPUT_TOKENS,
        )
    except LLMError as exc:
        # Log the real cause so a server-log tail diagnoses provider
        # outages / missing keys / rate limits. The user-facing message
        # is intentionally vague to avoid leaking key names / vendor
        # error blobs into the UI.
        logger.warning(
            "explain_service: LLM call failed for question_id=%s tier=%s: %s",
            question_id,
            tier,
            exc,
        )
        raise ExplainError(
            "I can't generate that explanation right now. Please try again in a moment."
        ) from exc
    except Exception as exc:  # pragma: no cover — defensive net
        logger.exception(
            "explain_service: unexpected error for question_id=%s tier=%s",
            question_id,
            tier,
        )
        raise ExplainError(
            "I can't generate that explanation right now. Please try again in a moment."
        ) from exc

    text = (text or "").strip()
    if not text:
        logger.warning(
            "explain_service: LLM returned empty text for question_id=%s tier=%s",
            question_id,
            tier,
        )
        raise ExplainError("The model returned an empty response — try again in a moment.")

    row = QuestionExtendedExplanation(
        question_id=question_id,
        tier=tier,
        text=text,
        generated_by_id=user.id if user is not None else None,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        # Encouragement: award DEEPER_LEARNER stamp once the learner
        # has opened 5 unique (question, tier) pairs. Fire-and-forget
        # — a stamp bug shouldn't poison the explanation reveal.
        if user is not None:
            try:
                from app.services import learner_practice_service

                learner_practice_service.award_explain_stamp(
                    db, user_id=user.id
                )
                db.commit()
            except Exception:  # pragma: no cover — best-effort
                db.rollback()
        return row
    except IntegrityError:
        # Lost the race against a concurrent click. Roll back and
        # re-read the winner's row.
        db.rollback()
        winner = db.scalar(
            select(QuestionExtendedExplanation).where(
                QuestionExtendedExplanation.question_id == question_id,
                QuestionExtendedExplanation.tier == tier,
            )
        )
        if winner is None:  # pragma: no cover — should never happen
            raise ExplainError(
                "Something went wrong saving the explanation. Try again."
            )
        return winner


def to_dict(row: QuestionExtendedExplanation) -> dict:
    """Shape the row for the API response. Kept tiny on purpose —
    the frontend renders the text as a paragraph block."""
    return {
        "question_id": row.question_id,
        "tier": row.tier.value if hasattr(row.tier, "value") else row.tier,
        "text": row.text,
        "generated_at": row.generated_at,
    }
