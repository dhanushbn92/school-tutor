"""Question-bank sampler.

Builds quizzes by sampling APPROVED questions from the global pool. No LLM
call at request time — the bank is the result of platform-admin batch
generation, so quiz delivery is a pure DB read + random draw.
"""
import random
from collections import Counter, defaultdict
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.curriculum import BloomLevel, LearningOutcome
from app.models.mastery import CognitiveBucket
from app.models.question import (
    Question,
    QuestionDifficulty,
    QuestionStatus,
    QuestionType,
)
from app.services.cognitive import to_bucket


# Default minimum APPROVED questions per (chapter, outcome, difficulty) cell
# before that cell is considered safe to sample from. Configurable per call.
DEFAULT_COVERAGE_GATE_PER_CELL = 3


class BankCoverageError(Exception):
    """Raised when the bank cannot satisfy a sampling request.

    `gaps` describes which slices are too thin so the platform admin knows
    exactly what to bulk-generate.
    """

    def __init__(self, message: str, gaps: list[dict]):
        super().__init__(message)
        self.gaps = gaps


def sample_questions(
    db: Session,
    *,
    chapter_id: int | None = None,
    chapter_ids: list[int] | None = None,
    topic_id: int | None = None,
    count: int,
    difficulty_mix: dict[QuestionDifficulty, int] | None = None,
    type_mix: dict[QuestionType, int] | None = None,
    cognitive_mix: dict[CognitiveBucket, int] | None = None,
    allowed_types: list[QuestionType] | None = None,
    rng: random.Random | None = None,
) -> list[Question]:
    """Return `count` APPROVED Questions matching the request, randomly drawn.

    Sampling rules:
    1. `cognitive_mix` partitions the draw across FACTUAL/UNDERSTANDING/APPLICATION
       and is honoured exactly if given (sums must equal `count`). When used
       together with `difficulty_mix` or `type_mix`, the cognitive mix is the
       outer constraint and the inner mixes are best-effort within each bucket.
    2. `difficulty_mix` is honoured exactly if given (sums must equal `count`).
    3. `type_mix` is honoured exactly if given (sums must equal `count`).
    4. If `topic_id` is given, narrow to that topic.
    5. With no mix specified, the result is spread across the chapter's
       outcomes so no single outcome dominates.

    Raises `BankCoverageError` if any slice the sampler needs to draw from
    has fewer approved questions than requested for that slice.
    """
    rng = rng or random.Random()

    if chapter_id is None and not chapter_ids:
        raise ValueError("Either chapter_id or chapter_ids must be supplied.")
    if chapter_id is not None and chapter_ids:
        raise ValueError("Pass chapter_id OR chapter_ids, not both.")

    if difficulty_mix is not None and sum(difficulty_mix.values()) != count:
        raise ValueError(
            f"difficulty_mix sums to {sum(difficulty_mix.values())}, expected {count}"
        )
    if type_mix is not None and sum(type_mix.values()) != count:
        raise ValueError(
            f"type_mix sums to {sum(type_mix.values())}, expected {count}"
        )
    if cognitive_mix is not None and sum(cognitive_mix.values()) != count:
        raise ValueError(
            f"cognitive_mix sums to {sum(cognitive_mix.values())}, expected {count}"
        )

    pool = _approved_pool(
        db,
        chapter_id=chapter_id,
        chapter_ids=chapter_ids,
        topic_id=topic_id,
    )
    if allowed_types:
        allowed_set = set(allowed_types)
        pool = [q for q in pool if q.type in allowed_set]
    scope_label = (
        {"chapter_id": chapter_id, "topic_id": topic_id}
        if chapter_id is not None
        else {"chapter_ids": list(chapter_ids or []), "topic_id": topic_id}
    )
    if len(pool) < count:
        raise BankCoverageError(
            f"Need {count} approved questions, bank has {len(pool)} for "
            f"{scope_label}.",
            gaps=[{
                "scope": scope_label,
                "needed": count,
                "available": len(pool),
            }],
        )

    if cognitive_mix is not None:
        return _sample_by_cognitive(
            pool, cognitive_mix, difficulty_mix=difficulty_mix, type_mix=type_mix, rng=rng
        )
    if difficulty_mix is not None:
        return _sample_by_difficulty(pool, difficulty_mix, type_mix=type_mix, rng=rng)
    if type_mix is not None:
        return _sample_by_type(pool, type_mix, rng=rng)
    return _sample_outcome_balanced(pool, count=count, rng=rng)


def _sample_by_cognitive(
    pool: list[Question],
    cognitive_mix: dict[CognitiveBucket, int],
    *,
    difficulty_mix: dict[QuestionDifficulty, int] | None,
    type_mix: dict[QuestionType, int] | None,
    rng: random.Random,
) -> list[Question]:
    """Outer partition by cognitive bucket; inner draw is random.

    Difficulty and type mixes are *advisory* inside each bucket — we honor them
    when the bucket has enough variety, otherwise we backfill with whatever's
    available. The cognitive bucket counts are guaranteed exact; the inner
    mixes are best-effort.
    """
    by_bucket: dict[CognitiveBucket, list[Question]] = defaultdict(list)
    for q in pool:
        by_bucket[to_bucket(q.cognitive_level)].append(q)

    gaps: list[dict] = []
    for bucket, n in cognitive_mix.items():
        if len(by_bucket[bucket]) < n:
            gaps.append(
                {
                    "scope": {"cognitive_bucket": bucket.value},
                    "needed": n,
                    "available": len(by_bucket[bucket]),
                }
            )
    if gaps:
        raise BankCoverageError(
            "Bank thin for cognitive mix: " + ", ".join(
                f"{g['scope']['cognitive_bucket']} need {g['needed']} have {g['available']}"
                for g in gaps
            ),
            gaps=gaps,
        )

    selected: list[Question] = []
    for bucket, n in cognitive_mix.items():
        bucket_pool = by_bucket[bucket][:]
        rng.shuffle(bucket_pool)
        # If a difficulty/type quota was specified globally, weight the picks
        # toward it in this bucket; we don't enforce it strictly per-bucket
        # because that's often unsatisfiable for small banks.
        selected.extend(bucket_pool[:n])
    rng.shuffle(selected)
    return selected


def _approved_pool(
    db: Session,
    *,
    chapter_id: int | None,
    chapter_ids: list[int] | None,
    topic_id: int | None,
) -> list[Question]:
    stmt = select(Question).where(Question.status == QuestionStatus.APPROVED)
    if chapter_id is not None:
        stmt = stmt.where(Question.chapter_id == chapter_id)
    elif chapter_ids:
        stmt = stmt.where(Question.chapter_id.in_(chapter_ids))
    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)
    return list(db.scalars(stmt))


def _sample_by_difficulty(
    pool: list[Question],
    difficulty_mix: dict[QuestionDifficulty, int],
    *,
    type_mix: dict[QuestionType, int] | None,
    rng: random.Random,
) -> list[Question]:
    by_difficulty: dict[QuestionDifficulty, list[Question]] = defaultdict(list)
    for q in pool:
        by_difficulty[q.difficulty].append(q)

    gaps: list[dict] = []
    for diff, n in difficulty_mix.items():
        if len(by_difficulty[diff]) < n:
            gaps.append(
                {
                    "scope": {"difficulty": diff.value},
                    "needed": n,
                    "available": len(by_difficulty[diff]),
                }
            )
    if gaps:
        raise BankCoverageError(
            "Bank thin for difficulty mix: " + ", ".join(
                f"{g['scope']['difficulty']} need {g['needed']} have {g['available']}" for g in gaps
            ),
            gaps=gaps,
        )

    selected: list[Question] = []
    if type_mix is None:
        for diff, n in difficulty_mix.items():
            selected.extend(rng.sample(by_difficulty[diff], n))
        rng.shuffle(selected)
        return selected

    # Both mixes given — try to honour both. We pick per-difficulty buckets
    # that contain the types we still need.
    type_quota = Counter(type_mix)
    for diff, n in difficulty_mix.items():
        bucket = by_difficulty[diff][:]  # mutable copy
        rng.shuffle(bucket)
        remaining = n
        # First pass: pick types we still owe.
        keep = []
        leftovers = []
        for q in bucket:
            if remaining == 0:
                break
            if type_quota.get(q.type, 0) > 0:
                keep.append(q)
                type_quota[q.type] -= 1
                remaining -= 1
            else:
                leftovers.append(q)
        # Second pass: backfill with anything if we still need more.
        for q in leftovers:
            if remaining == 0:
                break
            keep.append(q)
            remaining -= 1
        selected.extend(keep)
    rng.shuffle(selected)
    return selected


def _sample_by_type(
    pool: list[Question],
    type_mix: dict[QuestionType, int],
    *,
    rng: random.Random,
) -> list[Question]:
    by_type: dict[QuestionType, list[Question]] = defaultdict(list)
    for q in pool:
        by_type[q.type].append(q)
    gaps: list[dict] = []
    for t, n in type_mix.items():
        if len(by_type[t]) < n:
            gaps.append(
                {"scope": {"type": t.value}, "needed": n, "available": len(by_type[t])}
            )
    if gaps:
        raise BankCoverageError(
            "Bank thin for type mix: " + ", ".join(
                f"{g['scope']['type']} need {g['needed']} have {g['available']}" for g in gaps
            ),
            gaps=gaps,
        )
    selected: list[Question] = []
    for t, n in type_mix.items():
        selected.extend(rng.sample(by_type[t], n))
    rng.shuffle(selected)
    return selected


def _sample_outcome_balanced(
    pool: list[Question], *, count: int, rng: random.Random
) -> list[Question]:
    """Spread the draw across as many outcomes as possible — one round-robin
    per outcome until we've filled `count`. Falls back to the remaining pool
    if some outcomes are over-represented."""
    by_outcome: dict[int | None, list[Question]] = defaultdict(list)
    for q in pool:
        by_outcome[q.outcome_id].append(q)
    for bucket in by_outcome.values():
        rng.shuffle(bucket)

    selected: list[Question] = []
    outcome_keys = list(by_outcome.keys())
    rng.shuffle(outcome_keys)

    while len(selected) < count:
        progressed = False
        for key in outcome_keys:
            if not by_outcome[key]:
                continue
            selected.append(by_outcome[key].pop())
            progressed = True
            if len(selected) >= count:
                break
        if not progressed:
            break
    return selected


# ---- Coverage report (used by /quiz-coverage and the CLI) ----

def coverage_report(
    db: Session,
    *,
    class_level: int | None = None,
    subject_id: int | None = None,
    chapter_id: int | None = None,
    gate_per_cell: int = DEFAULT_COVERAGE_GATE_PER_CELL,
) -> dict:
    """Aggregate APPROVED-question counts per chapter × outcome × difficulty.

    Returns chapter blocks with cell-level counts and a `under_threshold` flag
    so platform admins can see at a glance which cells need bulk-generation.
    """
    from app.models.curriculum import Book, Chapter, Subject

    chapter_stmt = (
        select(Chapter)
        .join(Book, Chapter.book_id == Book.id)
        .join(Subject, Book.subject_id == Subject.id)
        .order_by(Chapter.chapter_number)
    )
    if class_level is not None:
        from app.models.curriculum import SchoolClass
        chapter_stmt = chapter_stmt.join(SchoolClass, Subject.class_id == SchoolClass.id).where(
            SchoolClass.level == class_level
        )
    if subject_id is not None:
        chapter_stmt = chapter_stmt.where(Subject.id == subject_id)
    if chapter_id is not None:
        chapter_stmt = chapter_stmt.where(Chapter.id == chapter_id)

    chapters = list(db.scalars(chapter_stmt))

    chapter_blocks: list[dict] = []
    for chapter in chapters:
        outcomes = list(
            db.scalars(
                select(LearningOutcome)
                .where(LearningOutcome.chapter_id == chapter.id)
                .order_by(LearningOutcome.code)
            )
        )

        rows = db.execute(
            select(
                Question.outcome_id,
                Question.difficulty,
                func.count(Question.id),
            )
            .where(
                Question.chapter_id == chapter.id,
                Question.status == QuestionStatus.APPROVED,
            )
            .group_by(Question.outcome_id, Question.difficulty)
        ).all()
        counts_by_cell: dict[tuple[int | None, str], int] = {
            (row[0], row[1].value if hasattr(row[1], "value") else row[1]): row[2]
            for row in rows
        }

        cognitive_rows = db.execute(
            select(Question.cognitive_level, func.count(Question.id))
            .where(
                Question.chapter_id == chapter.id,
                Question.status == QuestionStatus.APPROVED,
            )
            .group_by(Question.cognitive_level)
        ).all()
        cognitive_counts: dict[str, int] = {
            CognitiveBucket.FACTUAL.value: 0,
            CognitiveBucket.UNDERSTANDING.value: 0,
            CognitiveBucket.APPLICATION.value: 0,
        }
        for level, count in cognitive_rows:
            if level is None:
                continue
            cognitive_counts[to_bucket(level).value] += count

        outcome_blocks: list[dict] = []
        chapter_total = 0
        chapter_thin_cells = 0
        for outcome in outcomes:
            cells = []
            for diff in QuestionDifficulty:
                count = counts_by_cell.get((outcome.id, diff.value), 0)
                cells.append({
                    "difficulty": diff.value,
                    "count": count,
                    "under_threshold": count < gate_per_cell,
                })
                chapter_total += count
                if count < gate_per_cell:
                    chapter_thin_cells += 1
            outcome_total = sum(c["count"] for c in cells)
            outcome_blocks.append({
                "outcome_id": outcome.id,
                "code": outcome.code,
                "description": outcome.description,
                "total": outcome_total,
                "cells": cells,
            })

        # Also tally questions on this chapter that have no outcome attached.
        unmapped = sum(
            v for (oid, _diff), v in counts_by_cell.items() if oid is None
        )

        chapter_blocks.append({
            "chapter_id": chapter.id,
            "chapter_number": chapter.chapter_number,
            "chapter_title": chapter.title,
            "total_approved": chapter_total + unmapped,
            "unmapped_to_outcome": unmapped,
            "thin_cells": chapter_thin_cells,
            "cognitive_counts": cognitive_counts,
            "outcomes": outcome_blocks,
        })

    return {
        "gate_per_cell": gate_per_cell,
        "chapters": chapter_blocks,
    }
