"""Attach video lectures (NIOS 309 Sanskrit by default) to their chapters.

Reads a videos manifest (``data/videos_manifest.json`` here, or any other via
``--manifest``; lesson number -> ordered Google Drive video ids) and upserts ``chapter_videos`` rows. Safe to re-run: rows are matched on
(chapter_id, sequence) and updated in place.

A lesson is attached ONLY if its name (as written in the Drive file titles)
resembles the database chapter title for that number. If it does not (the video
set and the curriculum disagree about what lesson N is), the lesson is skipped
and reported rather than attached to the wrong chapter.

Dry run by default - nothing is written without --apply:

    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.nios_class12_sanskrit.seed_chapter_videos
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.nios_class12_sanskrit.seed_chapter_videos --apply

--prune also deletes every video link of this book that the manifest no longer lists
(a file moved out of the Drive folder or removed from the manifest), so the app never
shows a video that is not in its place. Build the manifest from the live folder only,
never from files in the Drive trash.

Another subject, e.g. NIOS 311 Mathematics:

    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.nios_class12_sanskrit.seed_chapter_videos \
        --manifest scripts/nios_class12_maths/data/videos_manifest.json --apply
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.chapter_video import ChapterVideo, VideoProvider
from app.models.curriculum import Book, Chapter

MANIFEST = Path(__file__).parent / "data" / "videos_manifest.json"
DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{20,100}$")
# Loose on purpose: Drive names and chapter titles transliterate the same Sanskrit
# slightly differently (Parartha/Pararthe, Samrakshanam/Sanrakshanam).
MIN_NAME_SIMILARITY = 0.8


def _squash(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


def _roman_part(title: str) -> str:
    """'जीवनसंदेशः (Jivana-Sandeshah)' -> 'Jivana-Sandeshah'."""
    m = re.search(r"\(([^)]*)\)\s*$", title)
    return m.group(1) if m else title


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default is a dry run)")
    ap.add_argument("--manifest", type=Path, default=MANIFEST, help="videos manifest to load")
    ap.add_argument(
        "--prune",
        action="store_true",
        help="delete this book's video links that are not in the manifest",
    )
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    code = manifest["_meta"]["book_ncert_code"]
    provider = manifest["_meta"]["provider"]
    assert provider == VideoProvider.GDRIVE.value

    db = SessionLocal()
    attached = skipped = inserted = updated = unchanged = pruned = 0
    keep: set[tuple[int, str]] = set()
    try:
        chapters = {
            c.chapter_number: c
            for c in db.scalars(
                select(Chapter).join(Book, Chapter.book_id == Book.id).where(Book.ncert_code == code)
            )
        }
        for lesson in manifest["lessons"]:
            num, name = lesson["lesson"], lesson["name"]
            chapter = chapters.get(num)
            if chapter is None:
                print(f"[skip]  lesson {num:>2} {name!r}: no chapter {num} in {code}")
                skipped += 1
                continue
            score = difflib.SequenceMatcher(
                None, _squash(name), _squash(_roman_part(chapter.title))
            ).ratio()
            if score < MIN_NAME_SIMILARITY:
                print(
                    f"[SKIP]  lesson {num:>2} {name!r} does NOT match chapter {num} "
                    f"{_roman_part(chapter.title)!r} (similarity {score:.2f}) - not attached"
                )
                skipped += 1
                continue

            attached += 1
            for v in lesson["videos"]:
                keep.add((chapter.id, v["id"]))
                if not DRIVE_ID.match(v["id"]):
                    raise SystemExit(f"bad Drive id in lesson {num}: {v['id']!r}")
                row = db.scalar(
                    select(ChapterVideo).where(
                        ChapterVideo.chapter_id == chapter.id, ChapterVideo.sequence == v["seq"]
                    )
                )
                if row is None:
                    inserted += 1
                    db.add(
                        ChapterVideo(
                            chapter_id=chapter.id,
                            sequence=v["seq"],
                            title=v["title"],
                            kind=v["kind"],
                            provider=provider,
                            external_id=v["id"],
                        )
                    )
                elif (row.title, row.kind, row.provider, row.external_id) != (
                    v["title"], v["kind"], provider, v["id"]
                ):
                    updated += 1
                    row.title, row.kind, row.provider, row.external_id = (
                        v["title"], v["kind"], provider, v["id"],
                    )
                else:
                    unchanged += 1
            print(f"[ok]    lesson {num:>2} -> chapter {chapter.id} ({len(lesson['videos'])} videos, match {score:.2f})")

        if args.prune:
            stale = [
                row
                for row in db.scalars(
                    select(ChapterVideo)
                    .join(Chapter, ChapterVideo.chapter_id == Chapter.id)
                    .join(Book, Chapter.book_id == Book.id)
                    .where(Book.ncert_code == code)
                )
                if (row.chapter_id, row.external_id) not in keep
            ]
            for row in stale:
                print(f"[prune] chapter {row.chapter_id} seq {row.sequence} {row.title!r}")
                db.delete(row)
            pruned = len(stale)

        if args.apply:
            db.commit()
        else:
            db.rollback()
        mode = "APPLIED" if args.apply else "DRY RUN (nothing written)"
        print(
            f"\n{mode}: lessons attached={attached} skipped={skipped} | "
            f"videos inserted={inserted} updated={updated} unchanged={unchanged} pruned={pruned}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
