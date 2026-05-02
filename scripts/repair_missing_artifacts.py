"""One-shot repair for ``GeneratedContent`` rows whose on-disk
artifact has gone missing.

Walks every READY/APPROVED row, attempts to re-render from
``output_json`` if the file isn't on disk, and persists the result.

Also flags ZOMBIE rows: rows with no ``output_json`` AND no
``artifact_url`` (typically very old bootstrap attempts that never
completed). These are marked ``status=FAILED`` so they stop appearing
in catalog listings — the catalog filters non-admin reads to APPROVED.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/repair_missing_artifacts.py
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.generation import (
    GeneratedContent,
    GeneratedContentStatus,
    GeneratedContentType,
)
from app.services.artifact_repair import (
    ArtifactRepairError,
    JSON_ONLY_TYPES,
    rerender_from_output_json,
)
from app.services.artifact_store import get_artifact_store


def main() -> int:
    db = SessionLocal()
    store = get_artifact_store()

    repaired = 0
    skipped_json_only = 0
    failed: list[tuple[int, str]] = []
    zombies: list[int] = []

    try:
        rows = db.scalars(
            select(GeneratedContent)
            .where(GeneratedContent.status.in_([
                GeneratedContentStatus.READY,
                GeneratedContentStatus.APPROVED,
            ]))
            .order_by(GeneratedContent.id)
        ).all()
        print(f"Scanning {len(rows)} READY/APPROVED rows…\n")

        for row in rows:
            if row.content_type in JSON_ONLY_TYPES:
                skipped_json_only += 1
                continue

            file_ok = bool(row.artifact_url) and store.exists(row.artifact_url)
            if file_ok:
                continue

            # Zombie? No output_json AND no artifact_url means the row
            # was never populated. Best to take it out of the catalog.
            if not row.output_json and not row.artifact_url:
                zombies.append(row.id)
                continue

            try:
                data, ext = rerender_from_output_json(db, row)
            except ArtifactRepairError as exc:
                failed.append((row.id, str(exc)))
                continue

            # Use the existing artifact_url if present so cache_keys
            # and download URLs stay stable; otherwise mint the
            # canonical "<id>.<ext>".
            target_url = row.artifact_url or f"{row.id}.{ext}"
            target_ext = target_url.rsplit(".", 1)[-1].lower() if "." in target_url else ext
            store.save(content_id=row.id, extension=target_ext, data=data)
            if not row.artifact_url:
                row.artifact_url = f"{row.id}.{target_ext}"
            print(
                f"  [ok]  row {row.id:3d} | type={row.content_type.value:18s} | "
                f"re-rendered {len(data):>8,} bytes -> {row.artifact_url}"
            )
            repaired += 1

        # Mark zombies FAILED so they drop out of catalog listings.
        if zombies:
            print()
            print(f"Found {len(zombies)} zombie rows (no output_json and no artifact_url):")
            for zid in zombies:
                row = db.get(GeneratedContent, zid)
                if row is None:
                    continue
                row.status = GeneratedContentStatus.FAILED
                row.error_message = (
                    "Marked FAILED by repair sweep: row had neither output_json "
                    "nor an artifact file, so it was never populated."
                )
                print(f"  [flag] row {row.id:3d}: marked FAILED")

        db.commit()

        print()
        print("Summary:")
        print(f"  Repaired:        {repaired}")
        print(f"  Already healthy: {len(rows) - repaired - skipped_json_only - len(failed) - len(zombies)}")
        print(f"  JSON-only:       {skipped_json_only}")
        print(f"  Zombies flagged: {len(zombies)}")
        print(f"  Failed:          {len(failed)}")
        if failed:
            print()
            print("Failures (need manual triage):")
            for rid, reason in failed:
                print(f"  row {rid}: {reason}")
        return 0 if not failed else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
