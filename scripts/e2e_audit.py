"""End-to-end audit of all onboarded curriculum content.

Phases:
  1. INVENTORY  — every loaded chapter, with question / blob counts.
  2. DB integrity — FKs, orphans, NULL violations, missing topics/outcomes.
  3. SCHEMA     — re-validate every GeneratedContent.output_json against its Pydantic schema.
  4. ARTIFACTS  — every blob with a renderer must have a non-empty artifact.
  5. QUESTIONS  — counts (>=100 obj, >=30 subj for loaded chapters), options sanity, outcome FKs.
  6. API smoke  — hit the public endpoints via FastAPI TestClient.

Writes a report to scripts/e2e_audit_report.txt.
"""

from __future__ import annotations

import json
import sys
import traceback
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import select, func, text
from sqlalchemy.exc import SQLAlchemyError

REPORT_PATH = Path(__file__).parent / "e2e_audit_report.txt"
REPORT_LINES: list[str] = []
ERRORS: list[str] = []
WARNINGS: list[str] = []


def w(line: str = "") -> None:
    REPORT_LINES.append(line)


def err(line: str) -> None:
    ERRORS.append(line)
    w(f"  [ERROR] {line}")


def warn(line: str) -> None:
    WARNINGS.append(line)
    w(f"  [WARN]  {line}")


def section(title: str) -> None:
    w()
    w("=" * 78)
    w(f"  {title}")
    w("=" * 78)


def main() -> int:
    from app.db.session import SessionLocal
    from app.models.curriculum import SchoolClass, Subject, Book, Chapter, Topic, LearningOutcome
    from app.models.question import Question, QuestionType
    from app.models.generation import GeneratedContent, GeneratedContentType
    from app.llm.schemas.chapter_summary import ChapterSummaryOutput
    from app.llm.schemas.diagram import DiagramOutput
    from app.llm.schemas.lesson_plan import LessonPlanOutput
    from app.llm.schemas.ppt import PPTOutlineOutput
    from app.llm.schemas.simulation import SimulationOutput
    from app.llm.schemas.worksheet import WorksheetOutput
    from app.models.generation import GeneratedContentStatus

    SCHEMA_BY_TYPE = {
        GeneratedContentType.CHAPTER_SUMMARY: ChapterSummaryOutput,
        GeneratedContentType.LESSON_PLAN: LessonPlanOutput,
        GeneratedContentType.WORKSHEET: WorksheetOutput,
        GeneratedContentType.PPT: PPTOutlineOutput,
        GeneratedContentType.DIAGRAM: DiagramOutput,
        GeneratedContentType.SIMULATION: SimulationOutput,
    }

    w("END-TO-END AUDIT — School-Tuter Curriculum Content")
    w(f"Generated: {Path(__file__).name}")

    db = SessionLocal()
    try:
        # =========================================================
        # PHASE 1 — Inventory
        # =========================================================
        section("PHASE 1 — INVENTORY")
        loaded_chapter_ids: list[int] = []
        scaffold_chapter_ids: list[int] = []
        chapter_meta: dict[int, dict[str, Any]] = {}

        rows = db.execute(text("""
            SELECT sc.level, s.board, s.name AS subject_name, b.title AS book_title,
                   c.id, c.chapter_number, c.title, c.full_text,
                   (SELECT COUNT(*) FROM topics t WHERE t.chapter_id = c.id) AS n_topics,
                   (SELECT COUNT(*) FROM questions q WHERE q.chapter_id = c.id) AS n_questions,
                   (SELECT COUNT(*) FROM generated_contents gc WHERE gc.chapter_id = c.id) AS n_blobs
            FROM chapters c
            JOIN books b ON c.book_id = b.id
            JOIN subjects s ON b.subject_id = s.id
            JOIN school_classes sc ON s.class_id = sc.id
            ORDER BY sc.level, s.board, s.name, b.id, c.chapter_number
        """)).fetchall()

        buckets: dict[str, list[tuple]] = defaultdict(list)
        text_only_chapter_ids: list[int] = []
        for level, board, subject_name, book_title, cid, cnum, title, ft, n_top, n_q, n_b in rows:
            placeholder = (ft or "").startswith("Pending") or (ft or "").startswith("Placeholder") or len(ft or "") < 200
            text_only = (not placeholder) and n_top == 0 and n_q == 0 and n_b == 0
            chapter_meta[cid] = {
                "level": level, "board": board, "subject": subject_name, "book": book_title,
                "chapter_number": cnum, "title": title, "placeholder": placeholder,
                "text_only": text_only, "n_topics": n_top, "n_questions": n_q, "n_blobs": n_b,
            }
            if placeholder:
                scaffold_chapter_ids.append(cid)
            elif text_only:
                text_only_chapter_ids.append(cid)
            else:
                loaded_chapter_ids.append(cid)
                key = f"Class {level} / {board} / {subject_name}"
                buckets[key].append((cid, cnum, title, book_title))

        w(f"\nFully loaded chapters:           {len(loaded_chapter_ids)}")
        w(f"  (full_text + topics + questions + blobs)")
        w(f"Text-only (full_text uploaded but no topics/questions/blobs): {len(text_only_chapter_ids)}")
        w(f"Scaffold-only (placeholder full_text):                        {len(scaffold_chapter_ids)}")
        w(f"Total chapters:                  {len(loaded_chapter_ids) + len(text_only_chapter_ids) + len(scaffold_chapter_ids)}")
        if text_only_chapter_ids:
            w()
            w("  Text-only chapters (text imported but curriculum hierarchy + content not built):")
            for cid in text_only_chapter_ids:
                m = chapter_meta[cid]
                w(f"    ch{cid:3d}  cl{m['level']} {m['board']}/{m['subject']}  ch{m['chapter_number']}: {(m['title'] or '').encode('ascii','replace').decode()[:50]}")
        w()
        for key in sorted(buckets):
            w(f"\n  {key}")
            last_book = None
            for cid, cnum, title, book_title in sorted(buckets[key], key=lambda x: x[0]):
                if book_title != last_book:
                    w(f"    Book: {book_title}")
                    last_book = book_title
                # Strip non-ascii from title for safe printing
                safe = (title or "").encode("ascii", "replace").decode("ascii")
                w(f"      ch{cid:3d}  ch{cnum:2d}: {safe}")

        # =========================================================
        # PHASE 2 — DB integrity
        # =========================================================
        section("PHASE 2 — DB INTEGRITY")

        # Orphan questions: chapter_id not pointing to a chapter
        orphan_q = db.execute(text("""
            SELECT q.id, q.chapter_id FROM questions q
            LEFT JOIN chapters c ON c.id = q.chapter_id
            WHERE c.id IS NULL
        """)).fetchall()
        if orphan_q:
            err(f"{len(orphan_q)} questions have a chapter_id that does not exist")
        else:
            w("  questions → chapters FK: OK")

        # Orphan outcomes
        orphan_o = db.execute(text("""
            SELECT lo.id, lo.chapter_id FROM learning_outcomes lo
            LEFT JOIN chapters c ON c.id = lo.chapter_id
            WHERE c.id IS NULL
        """)).fetchall()
        if orphan_o:
            err(f"{len(orphan_o)} learning_outcomes have a chapter_id that does not exist")
        else:
            w("  learning_outcomes → chapters FK: OK")

        # Question.outcome_id references outcomes
        bad_oc = db.execute(text("""
            SELECT q.id FROM questions q
            LEFT JOIN learning_outcomes lo ON lo.id = q.outcome_id
            WHERE q.outcome_id IS NOT NULL AND lo.id IS NULL
        """)).fetchall()
        if bad_oc:
            err(f"{len(bad_oc)} questions reference a non-existent outcome_id")
        else:
            w("  questions → learning_outcomes FK: OK")

        # GeneratedContent → chapter
        bad_gc = db.execute(text("""
            SELECT gc.id FROM generated_contents gc
            LEFT JOIN chapters c ON c.id = gc.chapter_id
            WHERE gc.chapter_id IS NOT NULL AND c.id IS NULL
        """)).fetchall()
        if bad_gc:
            err(f"{len(bad_gc)} generated_contents rows reference a non-existent chapter_id")
        else:
            w("  generated_contents → chapters FK: OK")

        # Fully loaded chapters MUST have at least one topic and one outcome
        loaded_missing = []
        for cid in loaded_chapter_ids:
            t = db.scalar(select(func.count(Topic.id)).where(Topic.chapter_id == cid))
            o = db.scalar(select(func.count(LearningOutcome.id)).where(LearningOutcome.chapter_id == cid))
            meta = chapter_meta[cid]
            label = f"ch{cid} ({meta['board']} cl{meta['level']} {meta['subject']} ch{meta['chapter_number']})"
            if t == 0:
                err(f"{label}: no topics")
                loaded_missing.append(cid)
            if o == 0:
                err(f"{label}: no learning outcomes")
                loaded_missing.append(cid)
        if not loaded_missing:
            w("  every fully-loaded chapter has topics + outcomes: OK")

        # =========================================================
        # PHASE 3 — Schema re-validation
        # =========================================================
        section("PHASE 3 — SCHEMA VALIDATION (re-validate every output_json)")
        gc_rows = db.scalars(select(GeneratedContent)).all()
        w(f"\n  rows scanned: {len(gc_rows)}")
        schema_ok = 0
        schema_fail = 0
        schema_skipped_failed = 0
        schema_unknown_type = 0
        per_type = Counter()
        for gc in gc_rows:
            # Skip rows where the LLM generation itself failed — these were intentionally aborted.
            if gc.status == GeneratedContentStatus.FAILED:
                schema_skipped_failed += 1
                continue
            schema = SCHEMA_BY_TYPE.get(gc.content_type)
            if schema is None:
                warn(f"GC row {gc.id}: content_type {gc.content_type.value} has no Pydantic schema in audit map")
                schema_unknown_type += 1
                continue
            if gc.output_json is None:
                err(f"GC row {gc.id} ({gc.content_type.value}, ch{gc.chapter_id}, status={gc.status.value}): "
                    f"output_json is NULL but status is not FAILED")
                schema_fail += 1
                continue
            try:
                schema.model_validate(gc.output_json)
                schema_ok += 1
                per_type[gc.content_type.value] += 1
            except Exception as e:
                err(f"GC row {gc.id} ({gc.content_type.value}, ch{gc.chapter_id}): "
                    f"schema VIOLATED — {type(e).__name__}: {str(e)[:200]}")
                schema_fail += 1
        w(f"\n  schema OK:                 {schema_ok}")
        w(f"  schema FAIL:               {schema_fail}")
        w(f"  rows with status=FAILED:   {schema_skipped_failed}  (skipped)")
        w(f"  rows of unmapped type:     {schema_unknown_type}  (skipped)")
        w(f"  by type:")
        for t, n in sorted(per_type.items()):
            w(f"    {t}: {n}")

        # =========================================================
        # PHASE 4 — Artifacts
        # =========================================================
        section("PHASE 4 — ARTIFACT EXISTENCE & SIZE")
        # types that should have an artifact
        ARTIFACT_TYPES = {
            GeneratedContentType.LESSON_PLAN: ".docx",
            GeneratedContentType.WORKSHEET: ".pdf",
            GeneratedContentType.PPT: ".pptx",
            GeneratedContentType.DIAGRAM: ".svg",
            GeneratedContentType.SIMULATION: ".html",
        }

        from app.services.artifact_store import get_artifact_store
        store = get_artifact_store()
        # LocalArtifactStore exposes the root via _base; GCS uses _bucket/_prefix.
        store_root = getattr(store, "_base", None)
        w(f"\n  artifact store class:  {type(store).__name__}")
        w(f"  artifact store root:   {store_root}")
        artifact_ok = 0
        artifact_missing = 0
        artifact_zero_byte = 0
        for gc in gc_rows:
            if gc.content_type not in ARTIFACT_TYPES:
                continue
            # If the row itself is FAILED, don't expect an artifact.
            if gc.status == GeneratedContentStatus.FAILED:
                continue
            if not gc.artifact_url:
                err(f"GC row {gc.id} ({gc.content_type.value}, ch{gc.chapter_id}, status={gc.status.value}): no artifact_url")
                artifact_missing += 1
                continue
            url = gc.artifact_url
            # Use the store's exists() — handles both local and GCS backends.
            try:
                exists_ok = store.exists(url)
            except Exception as ex:
                err(f"GC row {gc.id}: store.exists({url!r}) raised {type(ex).__name__}: {ex}")
                artifact_missing += 1
                continue
            if not exists_ok:
                warn(f"GC row {gc.id}: artifact {url} not found in store")
                artifact_missing += 1
                continue
            # Read size if local store
            size = None
            if store_root and isinstance(store_root, (str, Path)):
                cand = Path(store_root) / url
                if cand.exists():
                    size = cand.stat().st_size
            if size == 0:
                err(f"GC row {gc.id}: artifact {url} is 0 bytes")
                artifact_zero_byte += 1
            else:
                artifact_ok += 1
        w(f"\n  artifact OK:      {artifact_ok}")
        w(f"  artifact missing: {artifact_missing}")
        w(f"  artifact zero:    {artifact_zero_byte}")

        # =========================================================
        # PHASE 5 — Question bank consistency
        # =========================================================
        section("PHASE 5 — QUESTION BANK CONSISTENCY")
        OBJ_TYPES = {QuestionType.MCQ, QuestionType.TRUE_FALSE, QuestionType.FILL_BLANK}
        SUBJ_TYPES = {QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER}
        BAR_OBJ = 100
        BAR_SUBJ = 30

        below_bar: list[str] = []
        all_qs = db.scalars(select(Question)).all()
        by_chapter: dict[int, dict[str, int]] = defaultdict(lambda: {"obj": 0, "subj": 0, "other": 0})
        for q in all_qs:
            if q.type in OBJ_TYPES:
                by_chapter[q.chapter_id]["obj"] += 1
            elif q.type in SUBJ_TYPES:
                by_chapter[q.chapter_id]["subj"] += 1
            else:
                by_chapter[q.chapter_id]["other"] += 1

        # Validate options/answer consistency
        bad_options = 0
        missing_answer = 0
        bad_tf_options = 0
        for q in all_qs:
            if q.type == QuestionType.MCQ:
                opts = (q.options or {}).get("choices") if isinstance(q.options, dict) else None
                if not opts or not isinstance(opts, list) or len(opts) < 2:
                    err(f"q{q.id} (ch{q.chapter_id}): MCQ has malformed options")
                    bad_options += 1
                elif q.correct_answer not in opts:
                    warn(f"q{q.id} (ch{q.chapter_id}): MCQ correct_answer not in options "
                         f"(answer='{(q.correct_answer or '')[:40]}')")
                    bad_options += 1
            elif q.type == QuestionType.TRUE_FALSE:
                opts = (q.options or {}).get("choices") if isinstance(q.options, dict) else None
                if opts != ["True", "False"] and opts != ["False", "True"]:
                    warn(f"q{q.id} (ch{q.chapter_id}): TRUE_FALSE options should be ['True', 'False'] — got {opts!r}")
                    bad_tf_options += 1
            if not (q.correct_answer or "").strip():
                err(f"q{q.id} (ch{q.chapter_id}): no correct_answer")
                missing_answer += 1

        w(f"\n  total questions:                {len(all_qs)}")
        w(f"  malformed MCQ options:          {bad_options}")
        w(f"  unusual TRUE_FALSE options:     {bad_tf_options}")
        w(f"  missing correct_answer:         {missing_answer}")
        w()
        w(f"  loaded chapter coverage (target: >={BAR_OBJ} obj, >={BAR_SUBJ} subj):")
        below = []
        partial = []
        for cid in loaded_chapter_ids:
            counts = by_chapter.get(cid, {"obj": 0, "subj": 0})
            if counts["obj"] < BAR_OBJ or counts["subj"] < BAR_SUBJ:
                meta = chapter_meta[cid]
                label = (
                    f"ch{cid} cl{meta['level']} {meta['board']}/{meta['subject']} "
                    f"ch{meta['chapter_number']}: obj={counts['obj']}, subj={counts['subj']}"
                )
                if counts["obj"] >= BAR_OBJ // 2 and counts["subj"] >= BAR_SUBJ // 2:
                    partial.append(label)
                else:
                    below.append(label)
        if below:
            w(f"\n  Below 50% target ({len(below)} chapters):")
            for line in below:
                w(f"    {line}")
        if partial:
            w(f"\n  Between 50% and 100% target ({len(partial)} chapters):")
            for line in partial:
                w(f"    {line}")
        if not below and not partial:
            w("  All loaded chapters meet the target.")

        # =========================================================
        # PHASE 6 — API smoke test
        # =========================================================
        section("PHASE 6 — FastAPI ENDPOINT SMOKE TEST")
        try:
            from fastapi.testclient import TestClient
            from app.main import app
            client = TestClient(app)
            checks = [
                ("GET", "/health", 200),
                ("GET", "/curriculum/classes", (200, 401, 403)),
                ("GET", "/curriculum/subjects", (200, 401, 403)),
                ("GET", "/curriculum/books", (200, 401, 403)),
                ("GET", "/curriculum/chapters", (200, 401, 403)),
                ("GET", "/curriculum/chapters/256", (200, 401, 403, 404)),
                ("GET", "/openapi.json", 200),
            ]
            for method, path, expected in checks:
                try:
                    resp = client.request(method, path)
                    code = resp.status_code
                    if isinstance(expected, tuple):
                        ok = code in expected
                    else:
                        ok = code == expected
                    if ok:
                        w(f"  {method} {path}  →  {code}  OK")
                    else:
                        warn(f"  {method} {path}  →  {code}  (expected {expected})")
                except Exception as ex:
                    err(f"  {method} {path}  raised {type(ex).__name__}: {ex}")
        except Exception as ex:
            err(f"could not import FastAPI app: {type(ex).__name__}: {ex}")

        # =========================================================
        # FINAL SUMMARY
        # =========================================================
        section("FINAL SUMMARY")
        w(f"\n  Loaded chapters checked:       {len(loaded_chapter_ids)}")
        w(f"  GeneratedContent rows checked: {len(gc_rows)}")
        w(f"  Questions checked:             {len(all_qs)}")
        w(f"  ERRORS:                        {len(ERRORS)}")
        w(f"  WARNINGS:                      {len(WARNINGS)}")

        if ERRORS:
            w("\n  ERROR DETAIL:")
            for e in ERRORS[:50]:
                w(f"    - {e}")
            if len(ERRORS) > 50:
                w(f"    ... and {len(ERRORS) - 50} more")
        if WARNINGS:
            w("\n  WARNING DETAIL (first 30):")
            for x in WARNINGS[:30]:
                w(f"    - {x}")
            if len(WARNINGS) > 30:
                w(f"    ... and {len(WARNINGS) - 30} more")

        verdict = "PASS" if not ERRORS else "FAIL"
        w(f"\n  VERDICT: {verdict}")

    finally:
        db.close()

    REPORT_PATH.write_text("\n".join(REPORT_LINES), encoding="utf-8")
    print(f"Report written to {REPORT_PATH} ({len(REPORT_LINES)} lines)")
    return 0 if not ERRORS else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        REPORT_PATH.write_text("\n".join(REPORT_LINES) + "\n\nFATAL:\n" + traceback.format_exc(), encoding="utf-8")
        sys.exit(2)
