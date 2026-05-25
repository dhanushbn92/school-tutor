"""Model for the "Tell me more" chain (Stage 3 of the child-centric
roadmap).

One row per (question_id, tier). Tiers are an ordered escalation:

  DEEPER  → a longer, more thorough version of the same explanation
  ANALOGY → a relatable real-world parallel ("Imagine you're packing
            for a trip…")
  EXAMPLE → a worked example at the same concept, with the student
            walked through the steps

The row is generated lazily — the first click that wants a tier the
DB doesn't have yet triggers an LLM call and writes the result. The
UNIQUE(question_id, tier) constraint also serves as the dedupe
guard for racy concurrent clicks: only one writer wins, the loser
re-reads the cached row.

There is no automatic invalidation: APPROVED questions are
immutable, so the explanations should be too. If a question is
edited (rare), DELETE these rows manually.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExplanationTier(StrEnum):
    """The three escalating "Why?" chain tiers. New tiers may be added
    freely — the UI does an exhaustive switch and falls through to
    the generic "More" rendering for unknowns."""

    DEEPER = "DEEPER"
    ANALOGY = "ANALOGY"
    EXAMPLE = "EXAMPLE"


class QuestionExtendedExplanation(Base):
    __tablename__ = "question_extended_explanation"
    __table_args__ = (
        UniqueConstraint(
            "question_id", "tier", name="uq_question_extended_explanation"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    tier: Mapped[ExplanationTier] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Whose click first triggered generation. Kept for auditing only —
    # never surfaced in the UI. ON DELETE SET NULL so deactivating a
    # user doesn't cascade and wipe the generated content.
    generated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
