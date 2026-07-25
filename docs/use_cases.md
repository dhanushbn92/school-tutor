# School Tutor — Product Blueprint

**Status:** active source of truth.
**Last updated:** 2026-04-25.
**Supersedes the scope in:** [implementation_plan.md](implementation_plan.md), [class6_science_mvp_stages.md](class6_science_mvp_stages.md). Those docs remain valid for the **execution detail of work already shipped** (Stages 0–8 of the original plan); this doc redefines what comes next.


## 1. Vision

A CBSE/NCERT-aligned learning platform with three audiences and one shared spine:

- A **central content team** ("Platform") curates a high-quality catalog of AI-generated learning artifacts and approved question banks, anchored to the syllabus.
- **Schools** subscribe to consume that catalog inside a multi-tenant SaaS where teachers, principals, and administrators run their classroom workflow on top of curated content.
- **Individual learners** sign up directly and use the same catalog for self-study, with a slimmer interface.

Generation is centralized, consumption is distributed. Quality, cost, and pedagogical consistency are controlled at the platform; classroom workflow and progress tracking happen per tenant.


## 2. Audience & Use Cases

### UC-1 — Multi-school SaaS

**Who:** principals, school administrators, teachers, students belonging to a school that has subscribed.
**They get:**
- Their own isolated tenant — students, sections, assessments, submissions, mastery, intervention notes.
- Per-school branding (school name in the topbar; logo upload is Phase B+).
- Role-gated dashboards: school-admin school-wide, teacher class-scoped, student self-only.
- Full read access to the global catalog (worksheets / lesson plans / PPTs / diagrams / simulations / quiz bank) for their class levels.
- Ability to *assemble* assessments from the question bank and assign them to sections.
**They do not:**
- Generate or modify content. Cannot create generations. Cannot approve or reject questions.
- See any other school's data — students, scores, notes, assessments, anything.
- Add platform-level curriculum entries.

### UC-2 — Individual learner (B2C)

**Who:** a student or self-learner not part of any school.
**They get:**
- Self-signup with class level chosen at registration.
- Same catalog as schools.
- Personal mastery dashboard.
- Personal quiz history.
- Random-sampled quizzes on demand from the question bank.
**They do not:**
- See teachers, sections, schools, gradebooks, or any group features.
- Generate content.
- Get teacher feedback or intervention notes (no teacher exists in their tenant).

**Implementation choice — "school of one":** an individual signup creates a hidden personal `School` record with `is_personal=True`, a default `Section`, and an `Enrollment` for the user as their own student. All existing assessment / submission / mastery code reuses unchanged. The frontend hides school/section UI for personal accounts.

### UC-3 — Centralized content catalog (the inversion)

**Who controls it:** a small Platform team — the original Anaadi admin role, elevated.
**Who consumes it:** every school and every individual.
**What's in the catalog:**
- Approved learning artifacts: worksheets (PDF), lesson plans (DOCX), PPT outlines (PPTX), diagrams (SVG), simulations (HTML — three_d_scene, categorize, match_pairs, future templates).
- Approved question bank: typed (MCQ / SHORT_ANSWER / LONG_ANSWER / FILL_BLANK / TRUE_FALSE / CASE_BASED), tagged to chapter + outcome + difficulty.
**Lifecycle:**
1. **Generate** (Platform admin uses LLM via the existing pipeline; or batch CLI for bulk).
2. **Review** (Platform admin or curator).
3. **Approve** → published to the catalog.
4. **Reject / Retire** → never visible to schools.

The platform's *own* version of the existing Generate page becomes the editorial workbench. Schools never see this surface.

### UC-4 — Quiz from question bank (no LLM at request time)

**Trigger:** teacher in a school, or an individual learner, wants a quiz.
**Mechanism:** server samples N approved questions from the global bank matching `(class, subject, chapter [, topic, difficulty, type])`, builds an `Assessment`, returns it.
**Why:** instant teacher experience; predictable cost; deterministic quality (every question was already reviewed); platform pays the LLM bill once per question, not once per quiz.
**Sampling rules** (default + configurable):
- Random with no repeats inside the same quiz.
- Honor `difficulty_mix` if specified (`{EASY: 4, MEDIUM: 4, HARD: 2}`).
- Honor `type_mix` if specified (`{MCQ: 6, SHORT_ANSWER: 2, TRUE_FALSE: 2}`).
- Honor `topic_id` if specified — filter to questions tagged on that topic; otherwise spread across all outcomes for the chapter (one outcome's worth of questions per N/outcomes slot).
- *Configurable later:* exclude questions a particular student has seen in the last X days.
**Coverage gate:** the bank must contain at least 3× the requested count of APPROVED questions for the requested scope, otherwise return `409 Bank coverage insufficient` with a structured payload telling the platform admin which (chapter, outcome, difficulty) cells are thin.


## 3. Roles & Tenancy

### Role hierarchy

```
PLATFORM_ADMIN     ← Anaadi team; sees everything; generates and approves catalog
   ↑
SCHOOL_ADMIN       ← school principal/operations; sees their school school-wide
   ↑
TEACHER            ← consumes catalog, assigns assessments, grades, files notes
   ↑
STUDENT            ← takes assessments, sees own mastery and own results
   ↑                    
INDIVIDUAL_LEARNER ← parallel role to STUDENT but in their personal school
```

The current `UserRole` enum (`admin / teacher / student`) gets renamed:
- `admin` → `school_admin` (school-scoped admin of a tenant).
- new `platform_admin` introduced above it (no school_id required).
- `teacher`, `student` unchanged.
- `individual_learner` added (lives in a personal `School` row).

### Tenancy model

| Entity | Scope |
|---|---|
| `AcademicYear`, `SchoolClass`, `Subject`, `Book`, `Chapter`, `ChapterSection`, `Topic`, `LearningOutcome` | **Global** (curriculum). Same syllabus for everyone. |
| `GeneratedContent` (post-pivot) | **Global** when status=APPROVED; only platform admin can mutate. |
| `Question` (post-pivot) | **Global** when status=APPROVED; only platform admin can create/approve. |
| `School`, `Section`, `Teacher`, `Student`, `Enrollment` | **School-scoped.** |
| `Assessment`, `AssessmentQuestion`, `Submission`, `SubmissionAnswer` | **School-scoped** (assessment.section_id → section.school_id). |
| `SkillMastery` | **School-scoped** (student-bound). |
| `InterventionNote` | **School-scoped** (teacher in a school). |
| `User` | **Either school-scoped (school_admin / teacher / student) or platform-scoped (platform_admin) or individual (individual_learner with personal_school).** |

### Auth boundaries (enforcement)

A request-time helper `current_school_scope(user)` returns:
- For `platform_admin`: no scope (sees all schools, but in practice mostly hits global tables anyway).
- For `school_admin / teacher / student`: their `school_id`.
- For `individual_learner`: their personal school_id.

Every school-scoped query MUST run through a `require_same_school` guard or call a service that filters by `current_school_scope`. We're partway there today; this gets locked down in Phase B.


## 4. Domain Model Changes

### What stays the same

- All curriculum tables (already global).
- All school-management tables (already school-scoped).
- All assessment/submission/mastery tables (already school-scoped via section).
- `LearningOutcome` (global).

### What moves from per-school to global

| Table | Today | After pivot |
|---|---|---|
| `generated_contents` | `created_by_id` is any teacher/admin | Only `platform_admin` can insert; `school_id` removed (was implicit via creator); add `published_at`, `published_by_id` for audit |
| `questions` | Inserted by any teacher/admin via quiz generation | Only `platform_admin` can insert/approve; `created_by_id` always a platform admin |

These are still the same SQLAlchemy tables; the change is in **which role can mutate them** + a few audit columns.

### What's new

- `User.role` enum extended with `platform_admin`, `individual_learner`; `admin` renamed to `school_admin` (migration).
- `User.account_type: PLATFORM | SCHOOL | INDIVIDUAL` (derived but cached for query efficiency).
- `User.usage_count_30d` — running counter for future billing/quotas (no enforcement yet).
- `School.is_personal: bool` — distinguishes "school of one" from real schools. Defaults `false`.
- `School.brand_name`, `School.logo_url` — optional branding.
- `GeneratedContent`: add `published_at`, `published_by_id` (FK platform_admin user); add `topic_id` is already there.
- New table `QuestionBankCoverage` (materialized view or recomputed): `(class_level, subject_id, chapter_id, outcome_id, difficulty, count_approved)` — supports the quiz-from-bank coverage gate without aggregating live each request. *Optional optimization; pure live aggregation works for MVP.*

### Migration plan from current state

1. **Pre-migration backup** of Supabase Postgres.
2. **Add the new columns + new role values** in a forward migration. Existing `admin` rows stay as `admin` until step 3 renames them.
3. **Pick a Platform admin user.** Either elevate `admin@anaadi.demo` to `platform_admin` OR create a new `platform.team@anaadi.org` and re-attribute all existing `generated_contents` and `questions` records to it via `created_by_id`. *Recommend the latter — clearer audit.*
4. **Rename role:** all remaining `admin` users become `school_admin`. The demo's school admin (`school.demo@anaadi.org`, `admin@anaadi.demo`) become `school_admin`.
5. **Mark existing demo school** `is_personal=false`.
6. **Lift catalog content:** mark all currently-READY `generated_contents` for `fecu1` as published (`published_at=now()`, `published_by_id=<platform admin>`). The teacher who originally created them keeps the `created_by_id` for audit but content is visible to all schools.
7. **Lift question bank:** all `questions` with status=APPROVED become globally visible. `created_by_id` retained for audit; visibility no longer depends on it.
8. **Verify** with a script: every existing assessment + submission + mastery row still resolves; no tenant accidentally sees another's data.

A reversible Alembic migration covers steps 2, 4, 5, 6, 7. Steps 1, 3, 8 are operator actions.


## 5. Content Pipeline

### Old (deprecated by this pivot)

```
Teacher → POST /generated-content (their school) → LLM → READY
Teacher → POST /generated-content type=quiz → questions land as DRAFT in *that teacher's* bank
Teacher → review + approve → questions usable in their assessments only
```

### New

```
Platform admin → POST /platform/generations → LLM → READY (private to platform)
Platform admin → review + edit → POST /platform/generations/:id/publish → APPROVED + global
                                                                            │
                                                                            ▼
                                                              School teachers + individuals
                                                                            │
                                                                            ▼
Teacher / Individual → POST /assessments/from-bank → sample → assigned (school) or self-quiz (individual)
```

### Quality gates

1. **Pydantic schema validation** on every LLM output (already in place per content type).
2. **Platform-admin review** before publish (new): platform admin reviews, optionally edits, then explicitly publishes.
3. **No public visibility before publish** — `status=READY` (LLM done) is private to platform; `status=APPROVED` (post-publish) is what schools and individuals see.

We add a status to `GeneratedContent` enum: `pending → ready → approved → published`. Catalog browse filters on `status=published`.

### Batch generation CLI

`scripts/bulk_generate.py` — fills the bank without manual clicking:

```powershell
.\.venv\Scripts\python.exe -m scripts.bulk_generate `
   --class-level 6 --subject Science --chapter 2 `
   --content-type quiz --count 30 `
   --difficulty-mix EASY=10,MEDIUM=15,HARD=5 `
   --types MCQ,SHORT_ANSWER,TRUE_FALSE,FILL_BLANK
```

Output: N successful generations, deduped against existing approved questions on the chapter. Output report: how many questions per outcome × difficulty cell now exist.

A complementary `scripts/coverage_report.py` shows the current bank fill: per `(chapter, outcome, difficulty)` how many APPROVED questions exist, and which cells are below the gate threshold (default ≥3 per cell to safely serve quizzes).


## 6. Curriculum Scope

### MVP (today's data)

- Class 6, Science, NCERT *Curiosity* (`fecu1`)
- 12 chapters, 51 learning outcomes already authored
- All chapters' full text + page-level sections in DB

### Post-MVP roadmap

- Classes 7, 8, 9, 10 — same NCERT pipeline
- Other Class 6 subjects (Maths, Social Science, English) — same pipeline
- Class 11 / 12 — explicitly **out of MVP** per the original plan; subject streams + electives need different schema work

Curriculum ingestion is already a one-command CLI per book (`app.ingestion.ncert_import`). Adding a class-subject is operator-time, not engineering-time, once outcomes are authored.


## 7. Content Types & Roles

| Type | Generated by | Consumed by | Notes |
|---|---|---|---|
| Worksheet (PDF) | Platform admin | Teachers (assign as homework / classroom), individuals (self-practice) | Existing pipeline. |
| Lesson plan (DOCX) | Platform admin | Teachers only | Not surfaced in individual learner UI. |
| PPT outline (PPTX) | Platform admin | Teachers only | Same. |
| Diagram / concept map (SVG) | Platform admin | Teachers + individuals | Existing matplotlib pipeline. |
| Simulation (HTML) | Platform admin | Teachers + individuals | Three templates today: `three_d_scene` (any centre+orbit 3D scene — solar systems, atoms, cells, plant parts), `categorize`, `match_pairs`. New templates plug in via the architecture in `app/sims/templates/`. |
| Question (in bank) | Platform admin | Sampled at quiz request time | Schools/individuals never see DRAFT/REJECTED questions. |
| Quiz / Assessment (assembled) | Teacher (school) or self (individual) | Students | Built from sampled bank questions; no LLM call at this step. |


## 8. Analytics & Dashboards

### School dashboards (UC-1)

Already built (Stage 8 of original plan). What changes with the pivot:

- **School admin** gets a *school-wide* dashboard: average mastery per class/section, weakest topics across all sections, per-section comparison cards.
- **Teacher** dashboard already exists per-class; layout unchanged.
- **Student** dashboard already exists; layout unchanged.

### Individual learner dashboard (UC-2, new)

- "Your progress" page: mastery heatmap (their own), recent quizzes (with scores), weakest topics.
- "Browse content" page: catalog filtered to their class level.
- "Take a quiz" form: pick chapter/topic + difficulty, sample-and-go.

### Platform dashboard (UC-3, new)

- **Catalog coverage matrix** per class × subject × chapter:
  - Worksheets: count
  - Lesson plans: count
  - PPTs: count
  - Diagrams: count
  - Simulations: count
  - Question bank: per-outcome × difficulty count, with the gate threshold visible (red/yellow/green cells)
- **Approval queue:** pending review (`status=ready`).
- **Usage by school** (post-Phase-B): which schools are most active, which content types are most-fetched, which quizzes are sampled most.
- **Platform health:** LLM cost trend, generation latency, validation failure rate.


## 9. Phased Roadmap

### Phase A — Catalog reorientation + quiz-from-bank (highest leverage; foundation)

Deliverables:
- New role `platform_admin`; rename `admin` → `school_admin`.
- Migration to add `published_at`, `published_by_id` on `generated_contents`.
- Lock `POST /generated-content`, `PATCH /questions/:id`, `POST /questions/:id/approve` to platform-admin only.
- New status `approved` on `GeneratedContent`; only `approved` is visible to non-platform-admin clients.
- New endpoint `POST /generated-content/:id/publish` (platform-admin transitions ready → approved).
- New endpoint `POST /assessments/from-bank` — random sampling builder.
- Coverage gate enforcement: returns 409 with structured payload when bank is too thin.
- New CLI: `scripts/bulk_generate.py` (batch generation).
- New CLI: `scripts/coverage_report.py` (where the bank is thin).
- Migrate existing demo data: lift current generations + question bank to global.
- Frontend: hide Generate from teachers; replace with "Catalog" browse view (already mostly there). Add quiz-from-bank as a one-click action. Platform admins still see Generate but at a `/platform/...` route.
- Teachers' Question Bank page becomes read-only.

Exit criteria:
- A teacher in the demo school can build a 10-question quiz in under 2 seconds without any LLM call.
- Coverage report shows `fecu1` Chapter 1 has ≥30 approved questions, properly distributed across the 4 outcomes and 3 difficulty levels.

### Phase B — Multi-school onboarding (UC-1)

Deliverables:
- Public school-signup endpoint and page (creates `School` + `school_admin` user).
- School admin self-service: create sections, invite teachers (email link), bulk-import students (CSV).
- Per-school branding (school name in topbar; optional logo upload to Supabase Storage).
- Tenant-boundary audit + lockdown: every school-scoped service must filter by `current_school_scope`. Add an automated test that creates two schools and asserts each cannot see the other's data.
- School-admin dashboard: school-wide rollup of teacher/section/section-mastery views.

Exit criteria:
- Two schools can sign up, onboard, and use the platform with no overlap.
- A pen-test attempt to read another school's data via crafted query parameters is rejected with 403.

### Phase C — Individual learners (UC-2)

Deliverables:
- Individual signup endpoint + page (collects email, password, class level).
- Auto-create personal school + section + enrollment on signup.
- New role `individual_learner`; lock down endpoints they can/can't reach.
- Slimmer SPA navigation when `account_type=INDIVIDUAL`: hides Sections, Roster, Gradebook, Intervention notes.
- "My progress" dashboard (mastery heatmap + trend line + weakest topics) — reuses the per-student components.
- "Take a quiz" page: pick chapter/topic, difficulty mix, click → sampled quiz, take it inline, see score immediately.

Exit criteria:
- An individual signs up, picks Class 6 Science Chapter 1, takes a 10-question quiz, sees their mastery update on the heatmap.

### Phase D — Operations / pilot launch

Deliverables:
- Dockerfile + docker-compose for production.
- Background worker hardening (move from in-process FastAPI BackgroundTasks to `arq` + Redis).
- Sentry / structured logging.
- Rate limiting per user / per school / per platform-admin.
- Secret rotation (the credential currently in README.md must be rotated before any external pilot — already flagged earlier).
- Backup automation for Supabase.
- One pilot school onboarded end-to-end.


## 10. Open Decisions (need answers before Phase A starts)

| # | Question | Recommendation | Need final call from you |
|---|---|---|---|
| D1 | Single platform admin user, or multiple with audit trail? | Multiple. `published_by_id` on every catalog row; usage-attributed. | Yes |
| D2 | Existing demo content — keep + globalize, or wipe and rebuild? | Keep + globalize. fecu1 Chapter 1 already has solid generations; don't waste them. | Yes |
| D3 | Quiz sampling rules — which to ship in Phase A? | Random + difficulty mix + type mix + topic narrowing. **Defer:** "exclude student-seen-recently". | Yes |
| D4 | Individual learner — paid or free for MVP? | Free, with a usage counter on `User` so we can layer billing later without schema migration. | Yes |
| D5 | Bank coverage gate threshold? | `min(approved_count_per_(chapter,outcome,difficulty)) >= 3` before that cell is quiz-eligible. | Yes |
| D6 | Branding — logo upload in Phase B or later? | Phase B (basic). Custom theme colors deferred to post-MVP. | Optional |
| D7 | School signup — open public or invite-only? | Invite-only for MVP (one platform admin sends a signup link). Public open signup is post-MVP marketing. | Optional |
| D8 | Email delivery for invites + password resets — provider? | TBD. Resend / Supabase Auth email if we adopt it / Postmark. Phase B blocker. | Optional, Phase B |


## 11. Non-goals (explicit deferrals)

- **Classes 11 and 12** — different schema needs (subject streams, electives, board exam paper structure).
- **OCR on uploaded answer sheets** — manual marking only for MVP.
- **Real-time co-editing of content** between platform admins — single-editor model.
- **Live classroom features** — chat, video, screensharing.
- **Parent portal** — out of MVP.
- **Mobile / offline apps** — web-only MVP.
- **Vector / semantic retrieval (RAG)** — direct lookup from `(chapter, topic)` is sufficient for the catalog model. RAG is documented in `implementation_plan.md` as a future trigger when fuzzy / cross-chapter queries arise.
- **Custom curriculum per school** — schools follow the platform's syllabus for MVP. Custom course definitions are post-MVP.
- **Attendance correlation analytics** — out of MVP per the original plan.
- **Adaptive learning** — algorithmic next-question selection based on prior performance is out of MVP. Random sampling is the rule.


## 12. Success Metrics per Use Case

| UC | Metric | Target (MVP launch) |
|---|---|---|
| UC-1 | Schools onboarded | 1 pilot school running real classes for ≥30 days |
| UC-1 | Tenant isolation incidents | 0 |
| UC-2 | Individual signups | 50 active learners in 90 days post-launch |
| UC-2 | Quiz completions per learner per week | ≥2 |
| UC-3 | Catalog size at launch | ≥6 chapters of Class 6 Science with full content suite + 30+ questions per chapter |
| UC-3 | Generation cost per quiz served | <₹0.50 (fully amortized, post-bank-fill) |
| UC-4 | Quiz request → response p95 latency | <500ms (DB-only sampling) |
| UC-4 | Bank coverage gate false negatives (refused quiz when adequate questions exist) | 0 |


## 13. What this means for code already in tree

| Existing surface | Disposition under new model |
|---|---|
| `POST /generated-content` | **Restricted to platform_admin.** Schools/teachers lose access. Add `POST /generated-content/:id/publish` (platform_admin) for ready→approved transition. |
| `GET /generated-content?status=ready` | **Restricted to platform_admin.** Public callers can only filter on `status=approved`. |
| `POST /generated-content/:id/approve` (bulk-approve questions on a generation) | Move to platform_admin. |
| `POST /questions/:id/approve` / `reject` / `PATCH` | Restricted to platform_admin. Teachers see read-only. |
| `POST /assessments` (build from explicit question_ids) | Stays as-is for teachers / school admins / individuals. The assembled assessment is school-scoped. |
| **NEW** `POST /assessments/from-bank` | Sampling-based assembly. Available to teachers / individuals. |
| Frontend Generate page | Moves to `/platform/generate` (platform_admin only). Hidden from teacher/admin nav. |
| Frontend Question Bank page | Becomes read-only for school users; full-edit for platform_admin. |
| Frontend Content Library page | Filters now include `status=approved` implicitly for non-platform users; platform admins can also browse `status=ready` (for review). |
| `User.role` enum | Migration: `admin` → `school_admin`, add `platform_admin`, add `individual_learner`. |
| Existing seed script `scripts/seed_demo_school.py` | Augmented with: a platform admin user, plus the migration step that re-attributes existing catalog content. New script `scripts/seed_platform.py` for platform team setup. |


## 14. Cross-references

- [implementation_plan.md](implementation_plan.md) — original MVP plan; remains accurate for backend stages 0–8 (curriculum, auth, question bank, assessments, mastery, analytics, content types) and frontend v1. Use it for **historical context and execution detail of work already shipped**. Phase numbering in this doc starts fresh.
- [class6_science_mvp_stages.md](class6_science_mvp_stages.md) — chapter-level execution plan; stages already complete remain accurate, but the *organizational model* (single-school, teacher-creates-content) is being inverted by this doc.
- `frontend/README.md` — frontend ops; will need a paragraph added in Phase A noting the new role split and `/platform/*` routes.

When this blueprint is signed off (decisions D1–D5 answered), I'll:
1. Mark the obsolete sections of `implementation_plan.md` and `class6_science_mvp_stages.md` clearly as "superseded by use_cases.md from 2026-04-25 onward."
2. Begin Phase A.
