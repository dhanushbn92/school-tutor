"""Print the question-bank coverage matrix.

Shows, per chapter × outcome × difficulty, how many APPROVED questions exist
in the global bank. Cells below the configured gate threshold are highlighted
so the platform admin knows where to bulk-generate next.

Usage:
    .venv/Scripts/python.exe -m scripts.coverage_report --class-level 6 --subject Science
    .venv/Scripts/python.exe -m scripts.coverage_report --chapter-id 58 --gate 5
"""
import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import SchoolClass, Subject
from app.services.question_bank_service import (
    DEFAULT_COVERAGE_GATE_PER_CELL,
    coverage_report,
)


DIFFICULTIES = ["EASY", "MEDIUM", "HARD"]
COGNITIVE_BUCKETS = ["FACTUAL", "UNDERSTANDING", "APPLICATION"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--class-level", type=int, default=None)
    parser.add_argument("--subject", help="Subject name (e.g. 'Science')", default=None)
    parser.add_argument("--subject-id", type=int, default=None)
    parser.add_argument("--chapter-id", type=int, default=None)
    parser.add_argument("--gate", type=int, default=DEFAULT_COVERAGE_GATE_PER_CELL,
                        help="Minimum APPROVED questions per (outcome, difficulty) cell.")
    args = parser.parse_args()

    with SessionLocal() as db:
        subject_id = args.subject_id
        if subject_id is None and args.subject and args.class_level:
            stmt = (
                select(Subject)
                .join(SchoolClass, Subject.class_id == SchoolClass.id)
                .where(SchoolClass.level == args.class_level, Subject.name == args.subject)
            )
            subj = db.scalar(stmt)
            if subj is None:
                raise SystemExit(
                    f"No subject {args.subject!r} for class {args.class_level}"
                )
            subject_id = subj.id

        report = coverage_report(
            db,
            class_level=args.class_level,
            subject_id=subject_id,
            chapter_id=args.chapter_id,
            gate_per_cell=args.gate,
        )

    if not report["chapters"]:
        print("No chapters match the filter.")
        return

    print(f"Coverage report (gate = {report['gate_per_cell']} per cell)")
    print("=" * 88)
    width_diff = max(len(d) for d in DIFFICULTIES) + 2
    for chapter in report["chapters"]:
        thin = chapter["thin_cells"]
        print()
        print(
            f"Ch {chapter['chapter_number']:>2}  {chapter['chapter_title']}"
            f"   total={chapter['total_approved']}  thin_cells={thin}"
        )
        cog = chapter.get("cognitive_counts") or {}
        if cog:
            print(
                "  Bloom buckets: "
                + "  ".join(f"{b}={cog.get(b, 0)}" for b in COGNITIVE_BUCKETS)
            )
        print(
            f"  {'outcome':<22} "
            + " ".join(f"{d:>{width_diff}}" for d in DIFFICULTIES)
            + "  total"
        )
        for o in chapter["outcomes"]:
            counts = {c["difficulty"]: c for c in o["cells"]}
            cells = " ".join(
                _fmt_cell(counts[d]["count"], counts[d]["under_threshold"], width_diff)
                for d in DIFFICULTIES
            )
            print(f"  {o['code']:<22} {cells}  {o['total']:>5}")
        if chapter["unmapped_to_outcome"]:
            print(
                f"  (unmapped to outcome: {chapter['unmapped_to_outcome']} questions)"
            )


def _fmt_cell(count: int, thin: bool, width: int) -> str:
    s = f"{count:>{width}}"
    return f"\033[31m{s}\033[0m" if thin else s


if __name__ == "__main__":
    main()
