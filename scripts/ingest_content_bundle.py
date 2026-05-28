"""Generic content-bundle uploader for any chapter / board / class.

One bundle = one JSON file. Required curriculum coordinates + any subset
of content blocks (chapter text, topics, outcomes, summary, lesson plan,
worksheet, ppt, diagram, simulation, questions). Whatever is present
gets loaded; whatever is absent is ignored.

Run (single file):
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.ingest_content_bundle path/to/bundle.json

Run (multiple files in a directory — globs all *.json):
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.ingest_content_bundle path/to/folder/

Run dry-run (validate only, don't write to DB):
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.ingest_content_bundle path/to/bundle.json --dry-run

By default attributes all rows to the platform-team user (id from
`CONTENT_BUNDLE_CREATED_BY_ID` env var or 14 — same default as the
chapter-specific NIOS scripts). Override with --created-by-id 42.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.schemas.content_bundle import ContentBundle
from app.services.content_bundle_service import (
    ContentBundleError,
    IngestReport,
    ingest_bundle,
)


DEFAULT_CREATED_BY_ID = int(os.environ.get("CONTENT_BUNDLE_CREATED_BY_ID", "14"))


def _collect_bundle_paths(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(target.glob("*.json"))
    raise SystemExit(f"Path not found: {target}")


def _validate(path: Path) -> ContentBundle:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON — {exc}") from exc
    try:
        return ContentBundle.model_validate(payload)
    except Exception as exc:  # Pydantic ValidationError gives a readable message
        raise SystemExit(f"{path}: bundle failed validation:\n{exc}") from exc


def _print_report(path: Path, report: IngestReport) -> None:
    d = report.as_dict()
    print(f"[ok] {path.name}")
    print(f"     chapter_id={d['chapter_id']}, chapter_text_replaced={d['chapter_text_replaced']}")
    print(f"     topics:    inserted={d['topics']['inserted']} skipped={d['topics']['skipped']}")
    print(f"     outcomes:  inserted={d['outcomes']['inserted']} skipped={d['outcomes']['skipped']}")
    print(f"     questions: inserted={d['questions']['inserted']} skipped={d['questions']['skipped']}")
    if d["content_blobs"]["replaced"]:
        print(f"     blobs replaced: {d['content_blobs']['replaced']}")
    if d["content_blobs"]["inserted"]:
        print(f"     blobs inserted: {d['content_blobs']['inserted']}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", type=Path, help="Path to a bundle .json file or a directory of them.")
    p.add_argument("--dry-run", action="store_true", help="Validate schemas and resolve curriculum coordinates without writing to the DB.")
    p.add_argument("--created-by-id", type=int, default=DEFAULT_CREATED_BY_ID, help=f"User ID to attribute the rows to (default {DEFAULT_CREATED_BY_ID}).")
    args = p.parse_args(argv)

    paths = _collect_bundle_paths(args.path)
    if not paths:
        print(f"No .json files found at {args.path}", file=sys.stderr)
        return 2

    if args.dry_run:
        for path in paths:
            bundle = _validate(path)
            print(
                f"[dry-run] {path.name}: schema OK. "
                f"board={bundle.curriculum.board} class={bundle.curriculum.class_level} "
                f"subject={bundle.curriculum.subject} ch={bundle.curriculum.chapter_number} "
                f"({bundle.curriculum.chapter_title})"
            )
            counts = {
                "chapter_text": bundle.chapter_text is not None,
                "topics": len(bundle.topics),
                "outcomes": len(bundle.learning_outcomes),
                "questions": len(bundle.questions),
                "summary": bundle.chapter_summary is not None,
                "lesson_plan": bundle.lesson_plan is not None,
                "worksheet": bundle.worksheet is not None,
                "ppt": bundle.ppt is not None,
                "diagram": bundle.diagram is not None,
                "simulation": bundle.simulation is not None,
            }
            present = {k: v for k, v in counts.items() if v}
            print(f"     would load: {present}")
        return 0

    failures: list[tuple[Path, str]] = []
    for path in paths:
        bundle = _validate(path)
        db = SessionLocal()
        try:
            report = ingest_bundle(db, bundle, created_by_id=args.created_by_id)
            db.commit()
            _print_report(path, report)
        except ContentBundleError as exc:
            db.rollback()
            failures.append((path, str(exc)))
            print(f"[fail] {path.name}: {exc}", file=sys.stderr)
        except Exception as exc:  # pragma: no cover — defensive
            db.rollback()
            failures.append((path, repr(exc)))
            print(f"[error] {path.name}: {exc!r}", file=sys.stderr)
            raise
        finally:
            db.close()

    if failures:
        print(f"\n{len(failures)} bundle(s) failed. See output above.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
