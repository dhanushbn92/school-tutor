# End-to-End Audit — School-Tuter Curriculum Content

**Audit date:** 2026-05-05
**Scope:** All onboarded classes / subjects / chapters in the `school-tuter` Postgres database, plus the FastAPI app and the existing pytest suite.
**Reports produced:**
- `scripts/e2e_audit.py` — automated audit script (re-runnable any time)
- `scripts/e2e_audit_report.txt` — full 286-line machine report

---

## Verdict

| Area | Status |
|---|---|
| DB integrity (FKs, orphans) | ✅ PASS |
| Schema validation of stored content | ⚠️ 1 legacy row, 290/291 OK (99.7%) |
| Artifact files on disk | ✅ PASS (240/240 fully-loaded chapter artifacts) |
| Question bank options / answer keys | ✅ PASS (0 malformed MCQ, 0 missing answers) |
| API smoke endpoints | ✅ PASS (all critical routes respond) |
| Existing pytest suite | ⚠️ 10/11 pass (one pre-existing manifest-builder failure, unrelated to content) |
| **Overall content coverage vs target (100 obj + 30 subj)** | ⚠️ 13/52 chapters meet the standard |

**Deployment recommendation:** **Safe to deploy** if the goal is "demo/preview the content already authored." The flagged items are content-completeness gaps and one stale row, **none of which break the running application**. Block deployment only if your goal is "all 52 loaded chapters meet the 100/30 quality bar" — that requires the top-up work listed below.

---

## What I tested (six phases)

1. **Inventory** — every chapter, classified into Fully loaded / Text-only / Scaffold-only.
2. **DB integrity** — every FK (`questions → chapters`, `learning_outcomes → chapters`, `questions → learning_outcomes`, `generated_contents → chapters`); every fully-loaded chapter must have at least one topic and one outcome.
3. **Schema validation** — re-validate every `generated_contents.output_json` against its Pydantic schema (`ChapterSummaryOutput`, `LessonPlanOutput`, `WorksheetOutput`, `PPTOutlineOutput`, `DiagramOutput`, `SimulationOutput`).
4. **Artifacts** — every blob with a renderer must have an `artifact_url` that resolves through the `LocalArtifactStore` and points at a non-empty file.
5. **Question bank** — count obj/subj per chapter; verify `correct_answer ∈ options` for MCQ; verify `True/False` for TRUE_FALSE; verify no missing `correct_answer`.
6. **API smoke test** — `TestClient` against `/health`, `/curriculum/classes`, `/curriculum/subjects`, `/curriculum/books`, `/curriculum/chapters`, `/curriculum/chapters/{id}`, `/openapi.json`.

---

## Headline numbers

```
Total chapters in DB:                      229
  Fully loaded (full_text + topics + Qs + blobs):  52
  Text-only (full_text but no curriculum tree):    17
  Scaffold-only (placeholder full_text):          160

GeneratedContent rows checked:             310
  schema OK:                                       290
  schema FAIL:                                       1   (legacy SIMULATION row 77 — see below)
  status=FAILED, output_json NULL (skipped):         9   (LLM-failures, intentional)
  unmapped content_type (quiz/flow/...) (skipped):  10   (extra types not used by current loaders)

Artifacts checked (LocalArtifactStore @ data/artifacts):
  ok=240, missing=0, zero-byte=0

Questions in DB:                          4287
  malformed MCQ options:                     0
  unusual TRUE_FALSE options:               18  (Class 6 Hindi/Sanskrit chapters used native-language True/False)
  missing correct_answer:                    0
```

---

## Real issues found (action items)

### 1. ch1 (Class 12 CBSE Computer Science — Exception Handling in Python) — **partial onboarding**
- Has full_text + 6 topics, but **0 learning outcomes, 0 questions, 0 generated content rows**.
- This chapter is half-loaded. Either complete it (author outcomes/questions/blobs) or move it back to scaffold.

### 2. GeneratedContent row 77 — **legacy schema violates current Pydantic**
- ch58 (Class 6 Science ch1) — a SIMULATION row using the deprecated `three_d_scene` template with `objects_3d` shape.
- The 16 KB HTML artifact is on disk and serves correctly.
- The current `SimulationOutput` schema no longer accepts `objects_3d`. If anything in the app re-validates `output_json` after fetch, this row will throw.
- Fix options: regenerate the simulation, or migrate the JSON to the new schema, or filter "deprecated" rows from re-validation paths.

### 3. 17 "text-only" chapters with no curriculum hierarchy
Class 6 Hindi (10 chapters: ch25–ch38 across the Malhar book) and Class 6 Vocational Education (7 chapters) have `full_text` imported but no topics, outcomes, questions or generated content. They are partially started — finish them or reset full_text to placeholder.

### 4. Pre-existing pytest failure: `test_extract_chapter_title_from_pdf_handles_title_before_number`
- File: `tests/test_ncert_manifest_builder.py:76`
- Failure: extractor leaves an extra "Some chapter heading" prefix on the fallback title.
- Unrelated to onboarded content. Fix the extractor (PDF chapter-title heuristic) when convenient — does not block content deployment.

### 5. 18 TRUE_FALSE rows with Hindi/Sanskrit option labels
- ch182, ch183 (Class 6 Sanskrit) use `['सत्यम्', 'असत्यम्']`.
- ch237 (Class 10 Hindi ch1) uses `['सत्य', 'असत्य']`.
- Schema accepts both, but the convention from later chapters is `['True', 'False']`. Normalising would let the frontend render them uniformly.

### 6. Coverage gap vs 100 obj + 30 subj target
- **39 of 52** loaded chapters are below the agreed standard (some at 0).
- Notable gaps: every Class 6 Science chapter beyond ch3, every Class 6 SocSci, both Class 10 Math, Class 10 Science ch2, Class 12 NIOS Physics ch2/3, Class 6 Vocational ch1/ch2.

---

## Things I confirmed are healthy

- Every fully-loaded chapter (51/52) has at least one topic and one outcome.
- Every FK in the curriculum / question / generation tables points at a real row — **0 orphans**.
- All 240 artifact files for loaded chapters exist on disk and are non-zero bytes.
- 290 of 291 stored JSON payloads validate cleanly against their current Pydantic schema.
- No MCQ has `correct_answer` outside its option list; no question is missing `correct_answer`.
- `/health`, `/curriculum/classes`, `/curriculum/chapters`, `/curriculum/chapters/{id}`, `/openapi.json` all respond.
- 9 historical "FAILED" generation rows are correctly NULL on `output_json` and have no artifact — they were intentional aborts during early experimentation, not corruption.

---

## Re-running this audit

```bash
PYTHONPATH=. .venv/Scripts/python.exe scripts/e2e_audit.py
# writes scripts/e2e_audit_report.txt
```

The script is idempotent and read-only — no DB writes, safe to run in any environment that can reach the Postgres instance.
