# Session changelog (2026‑05‑02)

A self‑contained summary of everything in commit `922280e` that's
new in this session. Use this as the body of the PR / release note
that ships these changes to production.

---

## TL;DR

| Theme | What changed | Risk |
|---|---|---|
| **Board surfacing** | Every multi‑board page now shows the current board (CBSE / NIOS / …) and prefixes subject dropdowns with `[BOARD]`. New `board` query param on `GET /questions` and `GET /generated-content`. | Low — additive UI + new optional API param. |
| **Simulation library** | Grew from 3 → 15 templates spanning Math / Physics / Chemistry / Biology / Languages / Geography. Added a Tier‑2 `custom_html` escape hatch for genuinely bespoke per‑lesson sims, run inside a sandboxed iframe. | Low — schema is opt‑in; old rows untouched. |
| **Artifact auto‑heal** | `GET /generated-content/{id}/artifact` now re‑renders from `output_json` when the on‑disk file is missing, before returning 410. New `scripts/repair_missing_artifacts.py` for batch repair. | Low — pure defensive code on an existing route; no behaviour change for healthy rows. |
| **Per‑student "Areas of focus"** | New panel on `StudentDetail` page: top‑5 lowest‑mastery outcomes, with chapter / code / mastery bar / attempts count. | Low — derived from data already loaded; no new API. |
| **MindMap layout** | Per‑branch detail text was overlapping with adjacent branches'. Now pushed radially outward with quadrant‑aware text anchoring. | Low — pure rendering tweak. |
| **NIOS content** | NIOS Class 10 Math chapters 1–2 fully onboarded (~260 questions, 12 content blobs). NIOS Class 12 Physics scaffolded (28 chapters) with chapters 1–3 fully populated (~270 questions, 18 content blobs, 7 demo simulations). | Low — additive data only, behind board scoping. |

**No DB migrations required.** `alembic check` reports clean. Latest head `20260430_0022 (subject_board)` is unchanged; this session's schema changes were all in JSON columns.

---

## Detail by area

### 1. Board integration (cross‑subject UI surfacing)

* **New shared component** `frontend/src/components/BoardContextBar.tsx`
  exporting `BoardContextBar` (the "Working on [BOARD] · Class N · Subject"
  strip) and `labelForSubject()` helper.
* **Mounted on every multi‑board page**: Dashboard, Learn (top + per‑card
  badge), Question Bank, Content Library, Curriculum, Generate (refactored
  to use the shared component), NewQuiz, plus prefixes added to dropdowns
  on QuickQuiz, SectionDetail, ReportCard, SchoolReport, StudentDetail.
* **Backend filter parity**:
  * `GET /questions?board=NIOS` (new query param, case‑insensitive),
    joins through `Subject.board`. Service signature on
    `question_service.list_questions` gains a `board: str | None` arg.
  * `GET /generated-content?board=NIOS` (new query param), joins through
    `Subject` when filtering.
* **Files**: `app/api/routes/questions.py`, `app/api/routes/generation.py`,
  `app/services/question_service.py`, plus the 11 frontend pages above.

**Risk**: low. Existing endpoints still accept the same params; the new
`board` param is optional. UI changes are additive (new bar appears,
dropdown labels longer).

### 2. Anthropic LLM provider

* **New provider** `app/llm/anthropic_provider.py` — `AnthropicProvider`
  implementing the `LLMProvider` Protocol via the `anthropic` SDK.
* `get_llm_provider()` in `app/llm/__init__.py` now branches on
  `LLM_PROVIDER=anthropic`. Falls back to `os.environ['ANTHROPIC_API_KEY']`
  if not set in `.env`.
* `app/core/config.py` adds `anthropic_default_model: str = "claude-sonnet-4-5"`.

**Risk**: low. Inactive unless `LLM_PROVIDER=anthropic` is set; existing
Groq path is unchanged.

**Deployment note**: requires `ANTHROPIC_API_KEY` env var on Cloud Run if
you want to use it.

### 3. Simulation library expansion

#### Tier 1 — schema + 11 new template files
`app/llm/schemas/simulation.py` extends `SimulationTemplate` Literal with
12 new entries (8 from earlier in the session + 4 in the cross‑subject
pass). `SimulationOutput` gains optional fields per template
(`projectile`, `orbit`, `field_lines`, `wave`, `events_timeline`,
`graph`, `hotspots`, `sentence`, `vocab`, `molecule`, `circuit`,
`custom`). Each template has a validator branch.

New template HTMLs in `app/sims/templates/`:

| Template | Subject use | Notable |
|---|---|---|
| `timeline_order` | Universal | Drag-and-drop sequencing with per-card ✓/✗ feedback |
| `three_d_projectile` | Physics | Live trajectory animation with sliders |
| `three_d_orbit` | Astronomy / atomic | Configurable bodies, periods, inclinations |
| `three_d_field_lines` | EM / gravitation | Numerical streamlines + flow animation |
| `three_d_wave` | Waves / oscillations | Transverse / longitudinal / standing modes |
| `graph_explorer` | Math / Physics / Chem | math.js‑powered function plotter |
| `labeled_hotspots` | Bio anatomy / Lang | Image with clickable hotspots, optional quiz mode |
| `sentence_builder` | Languages / proofs | Drag tiles into correct order, distractors supported |
| `vocab_pairs` | Languages | Match‑pairs OR memory‑card flip game |
| `molecule_3d` | Chem / Bio | Atoms + bonds with CPK colouring |
| `circuit_2d` | Physics electricity | Auto‑computes series / parallel R + I |
| `custom_html` | **Tier 2 escape hatch** | Sandboxed iframe with `allow-scripts` only |

Renderer (`app/rendering/simulation_html.py`) gains a branch per template.
Worker (`app/workers/generate.py`) `_SIMULATION_TEMPLATES` allow‑list
extended.

#### Tier 2 — `custom_html` escape hatch (security‑critical detail)

The renderer wraps the LLM‑authored HTML in a parent page containing a
single `<iframe sandbox="allow-scripts" srcdoc="...">`. Critical
properties verified by `scripts/nios_class12_physics/08_verify_custom_html.py`:

* iframe `sandbox` attribute is **exactly** `{"allow-scripts"}` — no
  `allow-same-origin`, `allow-top-navigation`, `allow-popups`,
  `allow-forms`, `allow-modals`, `allow-pointer-lock`.
* The author's HTML has access to: CDN scripts, anything inside the
  iframe's null‑origin document.
* The author's HTML **cannot**: read cookies / `localStorage` /
  `sessionStorage`, access the parent window or its DOM, do top‑level
  navigation, submit forms, exfiltrate platform data.
* Operational: status defaults to PENDING/READY for LLM‑generated rows
  (existing READY → APPROVED gate via `/generation/{id}/publish` is the
  human review checkpoint). Hand‑authored rows bypass.

**Risk**: low. New schema entries are opt‑in. Existing rows continue to
render through their original branch. The custom_html sandbox is a new
attack surface but the security posture matches what student-uploaded
files would be.

### 4. Artifact auto‑heal

* **New module** `app/services/artifact_repair.py` — single source of
  truth for "given a row, render its artifact bytes". Knows about the 5
  renderable content types (`lesson_plan`, `worksheet`, `ppt`, `diagram`,
  `simulation`); JSON‑only types are explicitly listed.
* **Patched route** `GET /generated-content/{id}/artifact` in
  `app/api/routes/generation.py` — when the on‑disk file is missing
  *or* the row never had an `artifact_url`, attempts re‑render from
  `output_json` and persists before serving. Replaces the old "410: file
  missing on disk" with either a healed 200 or a 410 carrying a precise
  reason in `detail`.
* **One‑shot** `scripts/repair_missing_artifacts.py` walks every
  READY/APPROVED row, repairs anything broken, flags genuine zombie
  rows (no `output_json` AND no `artifact_url`) as `status=FAILED` so
  they drop out of catalog listings.
* **Already executed** during the session: 5 previously‑broken rows
  repaired (rows 47/48/49 lesson_plans, 75/76 diagrams).

**Risk**: low. Auto‑heal only triggers on the failure path. Healthy rows
take exactly the same code path as before.

### 5. Per‑student "Areas of focus" panel

* **New component** `frontend/src/components/StudentFocusAreas.tsx` —
  reusable, takes `MasteryChapter[]` from existing
  `useStudentMastery()` data. No new API call.
* Filters to attempted outcomes only, sorts by mastery ASC with
  attempts DESC tie‑break, surfaces top N (default 5).
* **Mounted** on `StudentDetail.tsx` between the stats grid and the
  heatmap; can be reused on the student's own `ReportCard`.

**Risk**: low. Pure derived view of data already loaded.

### 6. MindMap overlap fix

`frontend/src/components/MindMap.tsx` now pushes per‑branch detail text
radially outward with quadrant‑aware text anchoring (`start` / `end` /
`middle`), capped at 3 lines × ~30 chars. Used by `chapter_summary`
overview and per‑section diagrams across **every chapter on every
board** automatically — no per‑row migration needed.

**Risk**: low. Pure rendering tweak; data shape unchanged.

### 7. NIOS content additions

* **NIOS Class 10 Mathematics** chapters 1 (Number Systems) and 2
  (Exponents and Radicals) onboarded end‑to‑end. ~260 questions across
  all 6 Bloom levels per chapter, 12 content blobs, all status=APPROVED.
* **NIOS Class 12 Physics** scaffolded (Subject id=14, Book id=15, 28
  chapters mapped to syllabus modules). Chapters 1–3 fully populated
  (~270 questions, 18 content blobs, 7 demo simulations using new
  templates).
* All loaders idempotent (`scripts/nios_class10_math/`,
  `scripts/nios_class12_physics/`).

**Risk**: low. Additive data, scoped behind `Subject.board="NIOS"` so
existing CBSE flows are untouched.

### 8. Other small fixes

* **`graph_explorer` template** — switched math.js CDN from `esm.sh`
  (which serves ESM, doesn't define `window.math`) to
  `cdnjs.cloudflare.com/ajax/libs/mathjs/13.0.3/math.min.js` (UMD,
  exposes the global). Added defensive guard with clear error if the
  library fails to load. Plus an always‑on "Peak value" readout +
  marker dot + Reset button so parameter changes are obviously
  reflected.
* **`three_d_field_lines` template** — fixed gravitational streamlines
  collapsing into the source. Now integrate radially outward; track
  actual filled line length so `setDrawRange` doesn't include zero
  vertices; sliders updated to fire on `input` (live) instead of
  `change` (release‑only); pause‑flow restores correct draw range.
* **`labeled_hotspots` template** — bumped `image_url` cap from 2 KB to
  200 KB to support inline `data:image/svg+xml,…` URLs (preferred for
  diagrams the LLM authors itself; no external network dependency).
* **Vector hotspot demo** — replaced fragile Wikimedia link with an
  inline SVG diagram.
* **1D collision sandbox demo** — sidebar layout so controls are
  always visible; ~280 lines of vanilla JS, demonstrates the
  `custom_html` escape hatch in production.

**Risk**: low. All template-level fixes; affect every row of that
template type via re-render scripts already executed.

---

## Deployment notes

### Env vars (no required new ones)
* `ANTHROPIC_API_KEY` — optional; only needed if `LLM_PROVIDER=anthropic`.
* `LLM_PROVIDER` — accepts new value `anthropic` (existing values still work).
* `ANTHROPIC_DEFAULT_MODEL` — optional, defaults to `claude-sonnet-4-5`.

### Migrations
None required. `alembic check` clean. Production DB head is already at
`20260430_0022 (subject_board)`.

### Artifact backend
On Cloud Run, ensure `ARTIFACT_BACKEND=gcs` and `GCS_BUCKET=…` are set
(unchanged from before this session). The new auto‑heal route uses
the same `get_artifact_store()` interface; works identically against
GCS or local.

### Rollback
The single commit `922280e` is the only diff from the prior production
state. To roll back: revert the deploy. No DB migrations to roll back.

### Smoke tests after deploy
Useful end‑to‑end checks:
1. `GET /healthz` → 200.
2. Open Class 10 → NIOS → Mathematics → Chapter 1 in the SPA. Should
   show 132 questions in the bank, 6 content blobs (worksheet PDF,
   PPTX, lesson plan DOCX, etc.) all downloadable.
3. Open the **graph_explorer** projectile sim (chapter 74). Slide v0;
   "max y" readout in the right panel should change live.
4. Open the **three_d_field_lines** Earth–Moon sim (chapter 75). Should
   see ~36 yellow streamlines emanating from each mass.
5. Open the **custom_html** collision sandbox (chapter 75). Sidebar
   controls visible; press Launch; momentum bars should mark
   "conserved" in green.
6. Click a student profile (`/students/{id}`) — new "Areas of focus"
   card appears between stats and heatmap.

---

## Files changed (summary)

* **Frontend** (15 files): `BoardContextBar.tsx` (new), `StudentFocusAreas.tsx` (new), `MindMap.tsx`, plus 11 page components (Dashboard, Learn, QuestionBank, ContentLibrary, Curriculum, Generate, NewQuiz, QuickQuiz, SectionDetail, ReportCard, SchoolReport, StudentDetail, LearnSubject).
* **Backend services / routes**: `app/llm/anthropic_provider.py` (new), `app/llm/schemas/simulation.py`, `app/rendering/simulation_html.py`, `app/services/artifact_repair.py` (new), `app/services/question_service.py`, `app/api/routes/questions.py`, `app/api/routes/generation.py`, `app/workers/generate.py`, `app/llm/__init__.py`, `app/core/config.py`.
* **Sim templates** (`app/sims/templates/`): 12 new HTML files (timeline_order, three_d_projectile, three_d_orbit, three_d_field_lines, three_d_wave, graph_explorer, labeled_hotspots, sentence_builder, vocab_pairs, molecule_3d, circuit_2d, custom_html).
* **Scripts** (`scripts/`): 1 new at root (`repair_missing_artifacts.py`), 2 subtrees (`scripts/nios_class10_math/`, `scripts/nios_class12_physics/`) with all the data files + loaders + verification scripts.
* **Docs**: this changelog.
