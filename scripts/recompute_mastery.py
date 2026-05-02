"""Wipe and rebuild SkillMastery from EVALUATED submissions.

Runs the EWMA pipeline over historical submissions in chronological order so
existing mastery rows (which were keyed on `(student, outcome)` before the
Bloom rollout) are reconstructed at the new
`(student, outcome, cognitive_bucket)` granularity.

Use this once after the Bloom 6 deploy, or any time mastery looks drifted
from grade edits.

Usage:
    .venv/Scripts/python.exe -m scripts.recompute_mastery
    .venv/Scripts/python.exe -m scripts.recompute_mastery --student-id 42
    .venv/Scripts/python.exe -m scripts.recompute_mastery --school-id 1 --dry-run
"""
import argparse
import logging

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.assessment import Submission, SubmissionStatus
from app.models.mastery import SkillMastery
from app.models.school import Student
from app.services.mastery_service import apply_updates_for_submission


log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--student-id",
        type=int,
        default=None,
        help="Recompute only this student. Omit to recompute everyone.",
    )
    parser.add_argument(
        "--school-id",
        type=int,
        default=None,
        help="Recompute only students belonging to this school.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report counts but don't write.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        student_ids = _resolve_student_ids(db, args.student_id, args.school_id)
        if not student_ids:
            print("No students match the filter.")
            return

        sub_stmt = (
            select(Submission)
            .where(
                Submission.student_id.in_(student_ids),
                Submission.status == SubmissionStatus.EVALUATED,
            )
            .order_by(
                Submission.evaluated_at.asc().nullslast(),
                Submission.submitted_at.asc().nullslast(),
                Submission.id.asc(),
            )
        )
        submissions = list(db.scalars(sub_stmt))

        print(
            f"Will recompute mastery for {len(student_ids)} students "
            f"from {len(submissions)} EVALUATED submissions."
        )
        if args.dry_run:
            return

        deleted = db.execute(
            delete(SkillMastery).where(SkillMastery.student_id.in_(student_ids))
        ).rowcount
        log.info("cleared %s existing mastery rows", deleted)

        pair_total = 0
        for sub in submissions:
            pair_total += apply_updates_for_submission(db, sub)
        db.commit()

        print(
            f"Done. Touched {pair_total} (outcome, bucket) pairs across "
            f"{len(submissions)} submissions."
        )


def _resolve_student_ids(
    db, student_id: int | None, school_id: int | None
) -> list[int]:
    stmt = select(Student.id)
    if student_id is not None:
        stmt = stmt.where(Student.id == student_id)
    if school_id is not None:
        stmt = stmt.where(Student.school_id == school_id)
    return list(db.scalars(stmt))


if __name__ == "__main__":
    main()
