"""Batch-fill the question bank for a chapter.

Generates QUIZ batches via the existing LLM pipeline, deduplicates new
questions against existing APPROVED ones (normalized text match), then
auto-approves the new ones and publishes the parent GeneratedContent. Run
this whenever `coverage_report.py` shows thin cells.

Usage:
    .venv/Scripts/python.exe -m scripts.bulk_generate \\
        --class-level 6 --subject-id 6 --chapter-id 59 \\
        --batches 3 --count 8 \\
        --difficulty-mix EASY=3,MEDIUM=4,HARD=1 \\
        --cognitive-mix FACTUAL=3,UNDERSTANDING=3,APPLICATION=2 \\
        --types MCQ,SHORT_ANSWER,TRUE_FALSE,FILL_BLANK
"""
import argparse
import logging
import re
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import Chapter, SchoolClass, Subject
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)
from app.models.question import Question, QuestionStatus
from app.models.school import User, UserRole
from app.schemas.generation import GenerateContentRequest
from app.services.generation_service import create_or_reuse_generated_content
from app.workers.generate import run_generation_job


log = logging.getLogger(__name__)


def _parse_kv_int_csv(arg: str) -> dict[str, int]:
    """Parse `KEY=N,KEY=N` into a dict. Empty arg returns empty dict."""
    if not arg:
        return {}
    out: dict[str, int] = {}
    for part in arg.split(","):
        if not part.strip():
            continue
        k, v = part.split("=", 1)
        out[k.strip().upper()] = int(v.strip())
    return out


def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--class-level", type=int, required=True)
    parser.add_argument("--subject-id", type=int, default=None)
    parser.add_argument("--subject", default=None, help="Subject name; overrides --subject-id when given.")
    parser.add_argument("--chapter-id", type=int, required=True)
    parser.add_argument("--batches", type=int, default=1, help="Number of generation calls.")
    parser.add_argument("--count", type=int, default=10, help="Questions per batch.")
    parser.add_argument(
        "--difficulty-mix",
        default="",
        help="Per-difficulty counts within a batch, e.g. EASY=3,MEDIUM=4,HARD=1.",
    )
    parser.add_argument(
        "--cognitive-mix",
        default="",
        help=(
            "Per-cognitive-bucket counts within a batch, e.g. "
            "FACTUAL=3,UNDERSTANDING=3,APPLICATION=2. Buckets roll up Bloom: "
            "FACTUAL=REMEMBER, UNDERSTANDING=UNDERSTAND, "
            "APPLICATION=APPLY/ANALYZE/EVALUATE/CREATE."
        ),
    )
    parser.add_argument(
        "--types",
        default="",
        help="Allowed question types, e.g. MCQ,SHORT_ANSWER,TRUE_FALSE,FILL_BLANK.",
    )
    parser.add_argument(
        "--platform-admin-email",
        default="platform.team@anaadi.org",
        help="Platform admin user to credit as creator + publisher.",
    )
    args = parser.parse_args()

    difficulty_mix = _parse_kv_int_csv(args.difficulty_mix)
    if difficulty_mix and sum(difficulty_mix.values()) != args.count:
        raise SystemExit(
            f"--difficulty-mix sums to {sum(difficulty_mix.values())}, "
            f"expected --count {args.count}"
        )

    cognitive_mix = _parse_kv_int_csv(args.cognitive_mix)
    if cognitive_mix:
        allowed_buckets = {"FACTUAL", "UNDERSTANDING", "APPLICATION"}
        bad = set(cognitive_mix) - allowed_buckets
        if bad:
            raise SystemExit(
                f"--cognitive-mix has unknown buckets {sorted(bad)}; "
                f"expected any of {sorted(allowed_buckets)}"
            )
        if sum(cognitive_mix.values()) != args.count:
            raise SystemExit(
                f"--cognitive-mix sums to {sum(cognitive_mix.values())}, "
                f"expected --count {args.count}"
            )

    types = [t.strip().upper() for t in args.types.split(",") if t.strip()]

    with SessionLocal() as db:
        admin = db.scalar(
            select(User).where(
                User.email == args.platform_admin_email,
                User.role == UserRole.PLATFORM_ADMIN,
            )
        )
        if admin is None:
            raise SystemExit(
                f"Platform admin {args.platform_admin_email} not found. "
                "Run scripts.seed_platform first."
            )

        chapter = db.get(Chapter, args.chapter_id)
        if chapter is None:
            raise SystemExit(f"Chapter {args.chapter_id} not found")

        subject_id = args.subject_id
        if args.subject:
            subj = db.scalar(
                select(Subject)
                .join(SchoolClass, Subject.class_id == SchoolClass.id)
                .where(SchoolClass.level == args.class_level, Subject.name == args.subject)
            )
            if subj is None:
                raise SystemExit(
                    f"No subject {args.subject!r} for class {args.class_level}"
                )
            subject_id = subj.id
        if subject_id is None:
            raise SystemExit("Provide --subject-id or --subject")

        existing_norms = {
            _normalize_text(q.text)
            for q in db.scalars(
                select(Question).where(
                    Question.chapter_id == chapter.id,
                    Question.status == QuestionStatus.APPROVED,
                )
            )
        }
        log.info("starting with %s existing approved questions for chapter %s",
                 len(existing_norms), chapter.id)

    total_new = 0
    total_dupes = 0
    total_failed = 0

    for batch_index in range(args.batches):
        log.info("--- batch %s/%s ---", batch_index + 1, args.batches)
        with SessionLocal() as db:
            options: dict = {"question_count": args.count}
            if difficulty_mix:
                options["difficulty_mix"] = difficulty_mix
            if cognitive_mix:
                options["cognitive_mix"] = cognitive_mix
            if types:
                options["question_types"] = types

            req = GenerateContentRequest(
                content_type=GeneratedContentType.QUIZ,
                academic_year="2026-27",
                class_level=args.class_level,
                subject_id=subject_id,
                chapter_id=chapter.id,
                title=f"Bank fill ch{chapter.chapter_number} batch {batch_index + 1}",
                force_regenerate=True,
                options=options,
            )
            row = create_or_reuse_generated_content(db, req, creator_user_id=admin.id)
            cid = row.id

        t0 = time.time()
        run_generation_job(cid)
        log.info("batch %s: job %s ran in %.1fs", batch_index + 1, cid, time.time() - t0)

        # Approve new questions, drop duplicates, publish parent.
        with SessionLocal() as db:
            row = db.get(GeneratedContent, cid)
            if row.status == GeneratedContentStatus.FAILED:
                log.warning("batch %s failed: %s", batch_index + 1, row.error_message)
                total_failed += 1
                continue

            generated_questions = list(
                db.scalars(
                    select(Question).where(
                        Question.source_generated_content_id == cid,
                        Question.status == QuestionStatus.DRAFT,
                    )
                )
            )

            kept = 0
            dropped = 0
            for q in generated_questions:
                norm = _normalize_text(q.text)
                if norm in existing_norms:
                    q.status = QuestionStatus.REJECTED
                    q.review_notes = "Auto-dropped: duplicate of an existing approved question"
                    q.reviewed_by_id = admin.id
                    dropped += 1
                else:
                    q.status = QuestionStatus.APPROVED
                    q.reviewed_by_id = admin.id
                    existing_norms.add(norm)
                    kept += 1

            row.status = GeneratedContentStatus.APPROVED
            row.published_at = datetime.now(timezone.utc)
            row.published_by_id = admin.id

            db.commit()
            total_new += kept
            total_dupes += dropped
            log.info("batch %s: kept %s new, dropped %s duplicates", batch_index + 1, kept, dropped)

    print()
    print("=" * 60)
    print(f"Done. Added {total_new} approved questions to the bank.")
    print(f"Dropped {total_dupes} duplicate questions.")
    if total_failed:
        print(f"{total_failed} batches failed (rate-limit, validation, etc.)")
    print(f"Run scripts.coverage_report to see updated coverage.")


if __name__ == "__main__":
    main()
