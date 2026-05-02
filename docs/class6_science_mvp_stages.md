# Class 6 Science MVP — Stage-wise Execution Plan

**Scope:** one vertical slice — Class 6, subject Science, NCERT book **Curiosity** (code `fecu1`), English edition, 12 chapters. Every stage ends with something demoable end-to-end for this slice. Multi-language editions, other classes, and other subjects are deliberately out.

**Companion to:** [docs/implementation_plan.md](implementation_plan.md) (the broader MVP plan). This file is the concrete execution path for the first slice.

**State as of 2026-04-23:**
- SQLite dev DB has Class 12 CS only; `fecu1` is in the manifest but not ingested.
- No learning outcomes authored.
- `GeneratedContent` pipeline is a stub (PENDING row only).
- No auth / school / student models yet.

**Rough size:** 5–6 weeks for one full-stack backend engineer. Parallelizable with a frontend engineer from Stage 2 onwards.


## Stage 0 — Curriculum data foundation (1–2 days)

**Goal:** get clean, outcome-tagged Class 6 Science content sitting in the DB.

**Do:**
1. Run ingest scoped to `fecu1`:
   ```powershell
   .\.venv\Scripts\python.exe -m app.ingestion.ncert_import `
     --manifest data/ncert_manifest.full.json `
     --classes 6 --subjects Science --book-codes fecu1 --workers 4
   ```
2. Sanity-check that all 12 chapters have:
   - `title` populated (from `extract_chapter_title_from_pdf`)
   - `full_text` > 2000 chars
   - `chapter_sections` present (page-level fallback is acceptable)
3. Author `LearningOutcome` rows. 3–5 per chapter → ~50 outcomes for the book. Draft with Claude using the chapter text, then a teacher reviews. Store bloom level (remember/understand/apply/analyze/evaluate/create).
4. Optional: refine section titles for Chapters 1–3 manually (the keyword-match extractor is weak). Accept page-level slices for Ch 4–12.

**Touches:**
- [app/ingestion/ncert_import.py](../app/ingestion/ncert_import.py) (already built)
- NEW: `LearningOutcome` model (do this here so downstream stages bind questions to outcomes from day 1)
- NEW: Alembic migration adding `learning_outcomes` table + nullable `topic.primary_outcome_id`

**Exit:** `GET /curriculum/chapters?class_level=6` returns 12 rows with titles, sections, topics, and each chapter has ≥3 outcomes.


## Stage 1 — End-to-end worksheet pipeline for one chapter (3–5 days)

**Goal:** prove the full LLM → validate → render → store → serve path for a single content type on a single chapter. Nothing downstream works without this.

**Do:**
1. `app/llm/` package:
   - `base.py`: `LLMProvider` Protocol (`generate_structured(prompt, schema, **opts) -> dict`)
   - `stub_provider.py`: returns canned fixture JSON (unblocks dev without keys)
   - `claude_provider.py`: Anthropic SDK, **with prompt caching** for the chapter-text block
   - Factory picking provider from `LLM_PROVIDER` env var
2. Prompt template `app/llm/prompts/worksheet.md` (system + user), parameterized on chapter, topic?, difficulty mix, question count.
3. Pydantic output schema `app/llm/schemas/worksheet.py` — questions list with answer key and topic tags.
4. Retrieval: enrich `curriculum_service.build_curriculum_context` to return `{chapter_text, outcomes, topics, exemplar_questions?}` as a single cacheable block.
5. `arq` worker skeleton at `app/workers/generate.py`:
   - Enqueue on `POST /generated-content`
   - Worker: retrieve context → LLM → validate → render PDF via reportlab → upload to artifact store → update row to READY
6. `app/artifacts/`: `LocalArtifactStore` (writes to `data/artifacts/`), placeholder for `SupabaseArtifactStore`.
7. Worksheet PDF renderer `app/rendering/worksheet_pdf.py` (reportlab).

**Touches:**
- [app/services/generation_service.py](../app/services/generation_service.py) — move body to worker, route only enqueues
- [app/api/routes/generation.py](../app/api/routes/generation.py) — return job id + status URL
- NEW: `GET /generated-content/{id}` and `GET /artifacts/{id}` (presigned/local download)

**Exit:** hitting `POST /generated-content` with `(class_level=6, subject_id=..., chapter_id=<fecu1 Ch 1>, content_type=WORKSHEET)` results in a downloadable PDF worksheet with 10 questions + answer key, topic-tagged. Verified with stub provider and with Claude.


## Stage 2 — School model + auth + one demo school (3–5 days)

**Goal:** a real teacher can log in and see only their curriculum slice.

**Do:**
1. Supabase Auth wiring: email/password signup, login, `GET /auth/me` with role + school_id.
2. Models + migration: `User`, `School`, `Section`, `Student`, `Teacher`, `TeacherSubject`, `Enrollment`.
3. Role-gated dependencies: `require_admin`, `require_teacher`, `require_student`, `require_same_school`.
4. CRUD routers (minimal — only what the demo needs): `/schools`, `/sections`, `/students`, `/teachers`, `/enrollments`.
5. Seed script `scripts/seed_demo.py`:
   - School: "Anaadi Demo School"
   - One Section: "6-A" for academic year 2026-27
   - One Teacher: Science, assigned to 6-A
   - 10 Students enrolled in 6-A

**Touches:**
- NEW: `app/auth/`, `app/models/school.py`, `app/api/routes/{schools,sections,students,teachers}.py`

**Exit:** teacher logs in, `GET /curriculum/chapters?class_level=6&subject_id=<science>` returns the 12 chapters scoped to their assignment; no other class/section is accessible.


## Stage 3 — Question bank + teacher approval workflow (3–4 days)

**Goal:** AI-generated quiz questions land in a reviewable bank, not straight to students.

**Do:**
1. `Question` model + migration: type (MCQ/SHORT/LONG/CASE/COMPETENCY), difficulty, options JSON, correct_answer, explanation, marks, status (DRAFT/APPROVED/RETIRED), topic_id (required), outcome_id (preferred), source_generated_content_id.
2. Extend `GeneratedContent`: status values `DRAFT/PENDING_REVIEW/APPROVED/PUBLISHED/FAILED`, `reviewed_by_id`, `review_notes`.
3. Quiz generator (reuses Stage 1 pipeline):
   - Prompt template `quiz.md`
   - Output schema: array of questions matching `Question` shape, tagged to topic
   - Worker persists each as `Question(status=DRAFT)` linked to the parent `GeneratedContent`
4. Endpoints:
   - `GET /questions?topic_id=...&status=DRAFT` (review queue)
   - `PATCH /questions/{id}` (edit)
   - `POST /questions/{id}/approve` / `/reject`
   - `POST /generated-content/{id}/approve` (bulk-approve all child questions)

**Exit:** teacher generates a 10-question MCQ quiz for Chapter 1, sees them in a review queue, edits two, approves all, and they now exist as `Question(status=APPROVED)` in the bank.


## Stage 4 — Assessment + submission + grading (4–5 days)

**Goal:** approved questions become a quiz that students can take and that grades itself where possible.

**Do:**
1. Models + migration: `Assessment`, `AssessmentQuestion`, `Submission`, `SubmissionAnswer`.
2. Teacher flow:
   - `POST /assessments` — pick topic/chapter, pick N approved questions (or "auto-pick"), set total_marks and due_at
   - `POST /assessments/{id}/publish` — assign to Section 6-A
3. Student flow:
   - `GET /assessments?mine=true`
   - `POST /submissions` — submit answers
   - Auto-grade on save: MCQ exact-match, short-answer normalized string-match
4. Manual marks entry for subjective:
   - `PATCH /submissions/{id}/answers/{qid}` (marks_awarded, teacher_remark)
5. Test upload (no OCR): `POST /submissions/{id}/upload` accepts PDF/image for later manual grading.

**Touches:**
- NEW: `app/services/grading.py` (pure functions, unit-tested)

**Exit:** a seed student submits the Chapter 1 quiz; MCQs auto-score; teacher enters marks on the one short-answer question; submission status flips to `EVALUATED`; `total_awarded` matches expectation.


## Stage 5 — SkillMastery + single-student progress view (2–3 days)

**Goal:** the first real analytics loop — submissions update mastery, mastery feeds a dashboard.

**Do:**
1. `SkillMastery` model + migration (unique on `(student_id, topic_id, outcome_id)`).
2. Update service hook on `Submission` evaluation:
   - For each answered question, update mastery for its `(topic, outcome)` using EWMA (α=0.3) over `marks_awarded / max_marks`.
   - Store `attempts`, `last_updated`.
3. Endpoint `GET /analytics/students/{id}/mastery?class_level=6&subject_id=<science>` → topic-grid JSON for all 12 chapters.

**Exit:** after a student scores 7/10 on the Chapter 1 quiz, API returns mastery ≈ 0.7 for Chapter 1 topics, 0.0 / null for the other 11 chapters. Ready to render as a heatmap.


## Stage 6 — Remaining content types + reusable library (5–7 days, parallelizable)

**Goal:** cover the full content-generation surface the teacher expects, and surface approved simulations/diagrams as a gallery instead of a silent cache hit.

**Do:**
1. **Lesson plan** — JSON schema (objectives, flow, activities, homework, resources) → DOCX via python-docx.
2. **PPT outline** — JSON (slides: title, bullets, speaker notes) → PPTX via python-pptx. One base template.
3. **Diagram** — matplotlib-rendered SVG. Start with two templates: (a) labeled figure, (b) concept map. Pre-build 3 concrete examples from `fecu1` (e.g. parts of a plant, water cycle, food groups).
4. **Simulation** — parameterized HTML under `app/sims/templates/`. Ship 2 for Class 6 Science:
   - Mixture separation (filtration / evaporation / magnetism) — interactive
   - Flower parts labeling — drag-and-drop
5. **Topic-indexed library:**
   - `GET /generated-content?topic_id=...&content_type=simulation&status=APPROVED` — browse
   - Before enqueuing a new job, generator checks for an APPROVED match on `(content_type, topic_id, key_params)`; UI returns `existing_matches: [...]` so the teacher can **Reuse** instead of **Regenerate**.
   - Scope per-school.

**Touches:**
- NEW: `app/rendering/{lesson_plan_docx,ppt_outline_pptx,diagram_svg}.py`
- NEW: `app/sims/templates/` + registry
- EXTEND: `app/api/routes/generation.py` with library-lookup and reuse paths

**Exit:** teacher can generate all 6 content types for any Class 6 Science chapter; approved sims and diagrams appear in the library for the next teacher to reuse.


## Stage 7 — Teacher & admin dashboards (4–5 days)

**Goal:** turn mastery + submissions + approvals into actionable views.

**Do:**
1. `GET /analytics/sections/{id}/performance?assessment_id=...` — per-student score + topic-mastery summary.
2. `GET /analytics/sections/{id}/topic-averages?subject_id=...` — class average per topic (heatmap shape).
3. `GET /analytics/students/{id}/trend?subject_id=...` — time series of test scores.
4. `GET /analytics/sections/{id}/weakest-topics` — ranked list.
5. `GET /generated-content?status=PENDING_REVIEW` — teacher approval queue with counts.
6. `POST /intervention-notes` — teacher notes on a student and optional topic.

**Exit:** admin dashboard shows Section 6-A averages and weakest topics for Science; teacher dashboard shows their approval queue, their students' progress, and lets them file an intervention note after seeing a weak student.


## Stage 8 — Pilot launch for Class 6 Science (2–3 days)

**Goal:** one real teacher uses this for a real Chapter 1 quiz.

**Do:**
1. Dockerize: API + arq worker + Redis in `docker-compose.yml`. Postgres provided by Supabase.
2. Deploy to Railway/Fly/Render (staging).
3. Run Supabase Auth setup for the demo school.
4. Run `scripts/seed_demo.py` against Supabase.
5. Structured logging with `structlog`; Sentry DSN configured.
6. Per-school LLM rate limit (e.g. 50 gens/day).
7. Remove the Supabase credential leaked at [README.md:85](../README.md) (spawned task already covers this).
8. Brief onboarding doc for the pilot teacher (1 page).

**Exit:** a real pilot teacher logs in, generates + approves + assigns a Chapter 1 quiz, real students submit, teacher sees a real mastery dashboard. Feedback logged for v1.1 triage.


## What is intentionally NOT in this slice

- Other classes (7–10) — deferred to **slice 2**; replicates Stages 0, 3-subject outcome-authoring, and Stage 6 content additions. No new code shape needed.
- Other subjects for Class 6 (Maths, Social Science, etc.) — same shape as the Science slice, deferred.
- Other language editions of Curiosity (Jigyasa, Tajassus, regional) — structural, not blocking for pilot.
- OCR on uploaded test images.
- Attendance correlation analytics.
- Parent portal.
- Cross-chapter / cross-topic queries (the RAG triggers from [implementation_plan.md §6](implementation_plan.md)).
- Classes 11–12.


## Risks unique to this slice

1. **`fecu1` text quality** — if PDF extraction for any chapter is poor (e.g. heavy diagrams drop text context), LLM output for that chapter will suffer. Mitigation: after Stage 0 ingest, manually spot-check each chapter's `full_text`; flag weak ones for manual review before Stage 1.
2. **LearningOutcome authoring latency** — ~50 outcomes need a teacher review. Don't let this block Stage 1 code work; author outcomes in parallel, stub the FK as nullable, backfill before Stage 3.
3. **Chapter titles** — manifest has none; rely on `extract_chapter_title_from_pdf`. Verify all 12 populated cleanly after ingest; hand-fix any that come back as page headers or empty.
4. **Prompt-cache hit rate** — Anthropic's ephemeral cache is 5 minutes. If a teacher session stretches longer, cache misses hurt cost. Log cache hit/miss per provider call from day 1 so Stage 8 rate-limit tuning is grounded.
