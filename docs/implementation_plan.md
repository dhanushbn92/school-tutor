# School Tuter — MVP Implementation Plan

Target: CBSE/NCERT Classes 6–10 tutoring + school-management backend.
Last updated: 2026-04-23.

This plan builds on what is already in the repo (curriculum models, NCERT ingestion CLI, `/curriculum/*` routes, a stub `GeneratedContent` pipeline) and walks through the remaining work phase-by-phase.


## 1. Scope

### In for v1
- School / Section / Student / Teacher / Enrollment management
- Curriculum browser restricted to Classes 6–10
- LearningOutcome layer on top of existing Chapter/Topic
- Question bank with type + difficulty metadata
- Assessment + Submission with **manual marks entry** (MCQ auto-graded)
- SkillMastery tracking per student × topic (× outcome)
- AI-generated Worksheet, Quiz, Lesson Plan, PPT outline, Diagram, Simulation — with teacher approval workflow
- LLM provider abstraction (OpenAI / Claude / Gemini / local / stub)
- Dashboards: student progress, teacher content hub, admin class/section performance

### Deferred to v2+
- Classes 11–12 (streams, electives, higher stakes)
- OCR-based answer-sheet evaluation
- Attendance vs performance correlation
- Parent portal, mobile apps
- Real-time collaboration, multi-tenant billing


## 2. Architectural Decisions

| Area | Choice | Rationale |
|---|---|---|
| Backend | Keep FastAPI + SQLAlchemy + Alembic | Already in place, fits PDF/LLM/analytics workload |
| DB | Supabase Postgres (prod), SQLite (dev) | Already wired via `app/db/url.py` |
| Auth | Supabase Auth + local `User` profile table | Avoid building auth; row-level security option |
| Background jobs | `arq` (Redis-backed async) | Simpler than Celery, fits FastAPI's async model |
| File storage | Supabase Storage (prod), `data/artifacts/` (dev) | Same vendor; presigned URLs |
| LLM | Provider abstraction with Protocol | Avoid lock-in; support local models later |
| Retrieval | Direct DB lookup by `(chapter, topic)`; **no pgvector in v1** | NCERT is structured and bounded; a full chapter fits in modern LLM context |
| LLM cost control | Provider-side prompt caching (Anthropic ephemeral / OpenAI automatic) | Same chapter is re-used across worksheet + quiz + lesson plan; ~10× cheaper repeat reads |
| PDF / DOCX / PPTX | reportlab / python-docx / python-pptx | Pure Python, no system deps |
| Diagrams | matplotlib SVG + mermaid concept maps | Simple, deterministic first |
| Simulations | Pre-built HTML/JS templates with param injection | Safe, reviewable, no code generation |
| Frontend | Next.js 14 + shadcn/ui + Recharts | Separate effort; tracked here only via expected API contracts |


## 3. Data Model — Additions & Extensions

### New tables

| Entity | Key columns |
|---|---|
| `User` | id, email, auth_id (Supabase), role (ADMIN/TEACHER/STUDENT), school_id, created_at |
| `School` | id, name, board, address, contact, created_at |
| `Section` | id, school_id, class_id, academic_year_id, name ("A","B"), class_teacher_id |
| `Student` | id, school_id, full_name, roll_number, dob, gender, guardian_name, guardian_phone, user_id |
| `Teacher` | id, school_id, full_name, qualification, user_id |
| `TeacherSubject` | teacher_id, subject_id, class_id |
| `Enrollment` | id, student_id, section_id, academic_year_id, enrolled_at, status |
| `LearningOutcome` | id, topic_id, code ("6-SCI-LIV-01"), description, bloom_level |
| `Question` | id, topic_id, outcome_id?, type, difficulty, text, options JSON, correct_answer, explanation, marks, status, source_content_id?, created_by |
| `Assessment` | id, section_id, subject_id, type (WORKSHEET/QUIZ/TEST/EXAM), title, total_marks, duration_min, due_at, published_at, created_by |
| `AssessmentQuestion` | assessment_id, question_id, order, marks_override |
| `Submission` | id, assessment_id, student_id, submitted_at, status, total_awarded, uploaded_file_url |
| `SubmissionAnswer` | id, submission_id, question_id, answer_text, marks_awarded, teacher_remark |
| `SkillMastery` | id, student_id, topic_id, outcome_id?, mastery (0..1), attempts, last_updated |
| `InterventionNote` | id, student_id, teacher_id, topic_id?, note, created_at |
| `ContentTemplate` | id, content_type, name, template_spec JSON (for PPT layouts, sim templates) |

### Extensions to existing tables
- `GeneratedContent`: add status values `DRAFT` / `PENDING_REVIEW` / `APPROVED` / `PUBLISHED`; add `reviewed_by_id`, `review_notes`, `artifact_format`, `assessment_id?`.
- `SchoolClass`: service-layer validator restricts `level` to 6..10 for v1.
- `Topic`: add nullable FK `primary_outcome_id` so each topic has a canonical outcome.

### Canonical path rules
- **`Question` and `SkillMastery`** must always bind to a specific topic (outcome preferred). This is what makes mastery tracking, weak-topic detection, and personalization work.
- **`Assessment` and `GeneratedContent`** require at minimum `(class, subject)`; `chapter_id` and `topic_id` are optional. This supports requests like "quiz for Class 7 Maths Chapter 3 (all topics)" or "weekly practice for Class 8 Science (mix of chapters)".
- The full path `academic_year → class → subject → chapter → topic → learning_outcome` is what dashboards aggregate on. Generation requests can be coarser than a single topic; Questions produced by the generator are still tagged to a specific topic at creation time.


## 4. Phases

Estimated at ~10 weeks for one full-stack engineer; parallelizable with a frontend engineer from week 3.

### Phase 1 — School-management foundation (wk 1–2)
- Models + migration: `User`, `School`, `Section`, `Student`, `Teacher`, `TeacherSubject`, `Enrollment`, `LearningOutcome`.
- Supabase Auth wiring: login / signup / `GET /auth/me`; role claims in JWT.
- Dependency helpers: `require_admin`, `require_teacher`, `require_student`, `require_same_school`.
- CRUD routers: `/schools`, `/sections`, `/students`, `/teachers`, `/enrollments`, `/learning-outcomes`.
- Class-level validator clamped to 6–10.
- Seed script: one demo school, 2 sections, 1 teacher, 30 students.
- **Exit:** admin logs in, creates a school and sections, enrolls students; teacher logs in and sees assigned sections.

### Phase 2 — Question bank & assessment core (wk 3)
- Models + migration: `Question`, `Assessment`, `AssessmentQuestion`, `Submission`, `SubmissionAnswer`, `SkillMastery`, `InterventionNote`.
- Routers: `/questions`, `/assessments`, `/submissions`, `/intervention-notes`.
- Auto-grading service for MCQ and short-answer string-match (with case/whitespace-tolerant comparison).
- `SkillMastery` update hook on submission evaluation (EWMA over recent attempts).
- **Exit:** teacher creates an assessment from existing questions, student submits, MCQs auto-grade, SkillMastery updates visibly.

### Phase 3 — LLM provider abstraction + RAG + worker (wk 4)
- `app/llm/` package:
  - `base.py` (Protocol: `generate_text`, `generate_structured`)
  - `openai_provider.py`, `claude_provider.py`, `gemini_provider.py`, `stub_provider.py`
  - Factory reading from settings
- Retrieval utility: given `(class, subject, chapter, topic, outcome)` return a context blob (chapter full_text slice + topic/outcome descriptions + exemplar approved questions).
- Prompt templates in `app/llm/prompts/`, one per content type; versioned.
- Pydantic schemas for structured outputs (one per content type); validate before persisting.
- Artifact storage service abstraction (`LocalArtifactStore`, `SupabaseArtifactStore`).
- `arq` worker skeleton: FastAPI enqueues generation job; worker runs LLM → validate → render artifact → update `GeneratedContent`.
- **Exit:** `POST /generated-content` enqueues, worker completes, status flips to `READY` with `artifact_url`. Provider swappable via `LLM_PROVIDER` env var.

### Phase 4 — Content generators (wk 5–7)
In order (quality compounds):
1. **Worksheet** — LLM → JSON (questions + answer key) → PDF via reportlab. Difficulty-mix parameter (e.g. 40/40/20 E/M/H).
2. **Quiz** — reuses `Question` schema; saves generated questions to bank as `DRAFT` and optionally builds an `Assessment`.
3. **Lesson plan** — JSON (objectives, flow, activities, homework, resources) → DOCX via python-docx.
4. **PPT outline** — JSON (slides: title, bullets, speaker notes) → PPTX via python-pptx; uses `ContentTemplate` for layouts.
5. **Diagram** — matplotlib-rendered SVG for concept maps and labeled figures (e.g. parts of a cell). Later: image model.
6. **Simulation** — parameterized HTML templates at `app/sims/templates/` with JSON params. Target 3 per subject for MVP (e.g. ohm's law, fraction bars, pH indicator, photosynthesis). Simulations and diagrams are **deterministic and topic-scoped**, so every approved instance is added to a reusable per-school library (see §6 "Topic-indexed content library"). Regenerating is a fallback, not the default.

All output lands as `DRAFT` → teacher reviews → `APPROVED` → can be attached to an `Assessment` or shared with a section.

- **Exit:** teacher can generate each content type, preview, edit, approve; approved artifacts are downloadable and assignable.

### Phase 5 — Test upload & manual marking (wk 8)
- Upload endpoint: PDF/image → `Submission.uploaded_file_url` (virus scan optional).
- Manual marks entry per `(submission, question)`; bulk marks CSV import.
- Teacher remark field per answer.
- Marks → `SkillMastery` propagation.
- **Exit:** teacher uploads a scanned test, enters per-question marks, dashboards update.

### Phase 6 — Progress analytics (wk 9)
- Service computing:
  - Student topic-mastery grid (topic × outcome → mastery color)
  - Class/section averages by subject & topic
  - Section comparison (A vs B) for same assessment
  - Per-student test-trend time series
  - Weakest-topics ranking (class-level and student-level)
  - Improvement delta vs previous test
  - Intervention-note feed
- APIs under `/analytics/...` returning chart-ready payloads (line, heatmap, stacked-bar, mastery-grid shapes).
- Materialized views for heavy aggregates if query time grows.
- **Exit:** admin/teacher pulls JSON payloads that frontend charts render directly.

### Phase 7 — Frontend (parallel, wk 4–10)
Out of scope for this backend plan, but anchor the APIs to these views:
- **Admin:** school → sections → student roster; class/section performance grids.
- **Teacher:** content hub (generator + approval queue); gradebook; section analytics; intervention notes.
- **Student:** assigned work, results, mastery map.

### Phase 8 — Ops hardening (wk 10)
- Dockerfile + docker-compose (api + arq worker + Redis + Postgres).
- GitHub Actions CI: ruff / mypy / pytest.
- Structured logging (`structlog`), Sentry integration.
- Rate limiting on LLM endpoints (per school).
- Secret audit: remove Supabase credential currently in `README.md`, move to `.env`.
- **Exit:** one-command deploy, CI green, no plaintext secrets in repo.


## 5. API Surface (target)

Grouped by router prefix:

- `/auth/...` — signup, login, me (thin wrapper over Supabase Auth)
- `/schools/...`
- `/sections/...`
- `/students/...`
- `/teachers/...`
- `/enrollments/...`
- `/curriculum/...` (exists; extend with `/learning-outcomes`)
- `/questions/...` (CRUD, search by topic/outcome/difficulty, approve)
- `/assessments/...` (CRUD, publish, results summary)
- `/submissions/...` (create, upload file, enter marks, bulk import, get)
- `/generated-content/...` (extend: GET by id, list, approve, publish, re-run)
- `/artifacts/...` (presigned download URLs)
- `/analytics/...` (student, class, section, topic, trend, weakest)
- `/intervention-notes/...`


## 6. AI flow (enforced for every content type)

1. Teacher picks `(class, subject [, chapter] [, topic] [, outcome])` and content type + params. Minimum scope is `(class, subject)`; narrower scope is encouraged but optional.
2. Backend retrieves structured curriculum context from DB (chapter text, outcomes, exemplar approved questions).
3. `arq` worker calls provider with prompt template + context; requests JSON matching a Pydantic schema.
4. Response is validated; failure → retry once with schema-repair prompt, else `FAILED` with error.
5. Artifact is rendered (PDF/DOCX/PPTX/SVG/HTML) and uploaded to storage.
6. Row saved with `status=PENDING_REVIEW`, `source_context`, `llm_provider`, `llm_model`, `artifact_url`.
7. Teacher reviews → edits (optional) → approves → `status=APPROVED`.
8. Approved content can be attached to an `Assessment` or shared with a section.

**The teacher-approval gate is non-negotiable for v1.** Students must not see unreviewed AI output.

### Retrieval strategy — direct lookup, not RAG

For v1 we do **not** use embeddings or pgvector. The generation flow is:

1. Request arrives with `(class, subject, chapter, topic [, outcome])`.
2. `curriculum_service.build_curriculum_context(chapter_id, topic_id)` pulls `Chapter.full_text` (and relevant `ChapterSection` / `Topic` / `LearningOutcome` rows) straight from Postgres.
3. The full chapter text is passed to the LLM along with the prompt template; the prompt tells the model to scope output to the named topic/outcome.
4. Provider-side prompt caching keeps repeat generations on the same chapter cheap.

This works because the NCERT corpus is small, structured, and already aligned to the same `(chapter, topic)` keys that every request uses. Vector search would add cost and ops without earning its keep.

### When to introduce vector retrieval (post-MVP)

Add pgvector + chunk embeddings when requests become fuzzy, cross-chapter, or adaptive. Triggers:

- "Quiz covering nutrition, digestion, and respiration across chapters"
- "Find prerequisite concepts for this weak topic"
- "Remedial practice for students who confuse evaporation and condensation"
- "Use similar examples from previous chapters"
- "Generate competency-based questions spanning the whole syllabus"
- "Find all chapters where linear equations are used"

All context assembly already flows through `build_curriculum_context`; the retrieval swap is isolated to that one function. Call sites (generators, worker, cache key) do not change.

### Topic-indexed content library (reuse before regenerate)

Generated artifacts — **especially simulations and diagrams** — are deterministic and stable for a given `(content_type, topic, params)`. Once approved, they belong in a reusable per-school library rather than being regenerated on demand.

- `GET /generated-content?topic_id=...&content_type=simulation&status=APPROVED` — browse by topic.
- Before enqueuing a new LLM job, the generator first checks for an approved match. If found, the UI offers "Reuse" alongside "Regenerate".
- `cache_key` already dedups identical requests silently; the library surface turns that dedup into a first-class teacher-facing gallery.
- Reuse value by content type:
  - **High:** simulations, diagrams (expensive, stable, visually identifiable).
  - **Medium:** PPT decks, lesson plans (teachers want variants but a good base saves time).
  - **Low:** worksheets, quizzes (teachers typically want fresh question sets to prevent leakage).
- Scope is per-school in v1. Cross-school sharing is a v2 consideration with its own privacy and attribution questions.


## 7. Risks & open questions

- **Generation latency & cost** — worksheet ~10–30s, a few cents. Keep `cache_key` reuse; add per-school quotas in Phase 8.
- **Content quality** — heavy reliance on teacher approval; invest in good prompt templates and exemplar questions early.
- **PDF ingestion quality** — section extraction is currently keyword-based in `_extract_section_text`. If outcome mapping needs section text, revisit PDF layout parsing (e.g. pdfplumber with font-size heuristics).
- **Simulation scope** — keep to templated parameter injection for MVP; full dynamic code generation is not in scope.
- **Auth decision** — Supabase Auth vs self-managed JWT. Recommend Supabase Auth (avoid building auth). One-hour spike before Phase 1.
- **Data residency** — confirm Supabase region for Indian schools.
- **Secret in README** — `README.md:85` leaks a Supabase credential; rotate and remove before anything public.


## 8. First concrete tasks (start here)

1. One-hour spike: pick auth approach (Supabase Auth vs local JWT); commit an ADR.
2. Rotate the Supabase credential leaked in `README.md:85`; remove from repo.
3. Add `LearningOutcome` model + Alembic migration; add nullable `outcome_id` FK plan to future `Question`.
4. Define `app/llm/base.py` `LLMProvider` Protocol and `StubProvider` returning canned JSON, so later phases can proceed without vendor keys.
5. Stand up `arq` worker skeleton; wire existing `POST /generated-content` to enqueue instead of returning the PENDING row synchronously.
6. Start Phase 1 models + migrations.

ADRs go under `docs/adr/NNNN-title.md`.
