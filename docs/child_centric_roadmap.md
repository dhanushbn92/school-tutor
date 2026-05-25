# Child-Centric Roadmap — Dhananjaya

Living document for the staged transformation of Dhananjaya from a
teacher-tool-that-students-also-use into a learning platform a child
actually wants to come back to.

## Guiding principles

- **Practice is the engine.** Every feature should reinforce the
  platform's core promise: *practice, again and again, refined into
  mastery*.
- **Children, not graders.** A 10-year-old shouldn't have to decode
  "67% mastery"; meaning is built into the chrome.
- **Growth mindset.** Mistakes are practice, not failure. The UX
  should treat "not yet" as a stepping stone, not a verdict.
- **Mascot-first identity.** The Vidyārthi archer is the brand;
  reuse the same visual language everywhere children touch the
  product.
- **Calm by default.** Streaks, rewards, and animations are
  calibrated for kids — no dark-pattern engagement loops.

## Stages — execution order

The numbering below (Stage 1, Stage 2, …) is the execution sequence
the team agreed on. The `Idea #` in parentheses is the original
brainstorm number from the proposal — kept for cross-reference but
not the execution order.

| # | Stage | Idea # | State |
|---|---|---|---|
| 1 | Streaks + small rewards, calibrated for kids | 3 | ✅ Shipped 2026-05-17 (d503ab0) |
| 2 | Mistake review — collect + spaced-revisit the things they got wrong | 4 | ✅ Shipped 2026-05-25 |
| 3 | "Why?" — tell-me-more chain on every explanation | 6 | ✅ Shipped 2026-05-25 |
| 4 | Story-shaped progress for learners (replace bare numbers) | 2 | ✅ Shipped 2026-05-25 |
| 5 | Vidyārthi mascot reactions throughout the app | 1 | ✅ Shipped 2026-05-26 |
| 6 | Parent / guardian view | 9 | ✅ Shipped 2026-05-26 |
| 7 | Practice variety — flashcards / speedrun / surprise me | 7 | ✅ Shipped 2026-05-26 |
| 8 | Audio support — read-aloud everywhere | 5 | ✅ Shipped 2026-05-26 |
| 9 | Kinder UX for wrong answers ("Not yet", hint chain) | 8 | ✅ Shipped 2026-05-26 |
| 10 | UX polish — large targets, dyslexia font, take-a-break | 10 | **Up next** |

### Cadence

- One stage at a time.
- Each stage ends with a **review break**: I stop, summarise what
  shipped + what's tunable, and wait for feedback before starting
  the next stage.
- A stage may itself span multiple commits; only when the stage is
  complete do we pause.

---

## Stage 1 — Streaks + small rewards (Idea #3)

**Why it's first.** Habit-formation pays back every later stage —
once a child has a reason to open the app most days, every other
feature compounds. Doing this before any content depth means kids
have a reason to come back even while later features are still in
flight.

**Scope**
- **Practice-days counter** per learner. Not "consecutive" — kids
  miss days; we just count total days with at least one
  submission. Stored per User.
- **Weekly goal**, learner-set: "Aim for 3 / 4 / 5 practice days
  this week." Default 4. Shown as a tiny progress ring on the
  learner dashboard.
- **Stamps** — a stamp is earned for each completed quiz /
  worksheet attempt. Collected in a virtual stamp book, viewable
  on the learner profile. Stamp art uses the brand palette + arrow
  motifs.
- **Streak shield** — one free missed day per week. Prevents the
  goal-streak from feeling punishing.

**Out of scope for Stage 1**
- Leaderboards (private comparisons only; we are explicitly not
  building competitive social features for children).
- Notifications / emails (Stage 6 will do family-side comms).
- Server-side cron for daily resets (we compute on read).

**Backend**
- Materialise practice days from `submissions.submitted_at` —
  no new tables, just a query/service that groups by day.
- New tiny tables: `learner_weekly_goal(user_id, week_start,
  target_days)`, `learner_stamp(user_id, stamp_kind, earned_at,
  metadata jsonb)`.
- Endpoint `GET /me/practice-summary` returning: practice days
  this week, this month, current week goal, stamps recently
  earned.

**Frontend**
- Learner dashboard gains a "**Your practice**" card at top of
  the existing widgets — practice-day ring, weekly goal,
  next stamp to earn.
- New page `/me/stamps` — collection view.
- A small "+1 day" celebration when the first submission of the
  day lands.

**Success looks like**
- A learner opens the dashboard and immediately sees how their
  week is going.
- Completing a worksheet leaves a tangible mark (stamp) without
  inventing fake currency.
- No part of this feels like a slot machine — celebrations are
  brief and tied to real completion, not clicks.

### What shipped (commit d503ab0)
- New `learner_weekly_goals` + `learner_stamps` tables (migration
  `20260517_0023`).
- `learner_practice_service` with read-time practice-day query
  and a post-commit stamp awarder that never poisons a submission.
- `/me/practice-summary`, `/me/practice-summary/goal`,
  `/me/stamps` endpoints — all learner-role-gated.
- `<PracticeCard />` on the learner dashboard: SVG ring, narrative
  summary line, inline weekly-goal editor (2..7), recent-stamps
  strip.
- `/me/stamps` route + `StampBookPage` — per-kind tally cards on
  top, chronological full list below.
- All four initial stamp kinds wired: `QUIZ_COMPLETED`,
  `PERFECT_SCORE`, `PRACTICE_DAY`, `WEEKLY_GOAL_MET`.

### Deployment note
Run the migration before deploying:
```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```
The frontend gracefully no-ops if the endpoints return 404 — so a
half-deployed state won't break the dashboard.

### Stage 1.5 — Login streak + points + levels (extension)

Follow-up extension to Stage 1, motivated by the need for stronger
practice-encouragement signals than stamps alone provided. The
original Stage 1 design deliberately avoided points; the trade-off
was reconsidered with product ownership and points were added
behind the rationale "we can disable points visibility later if it
ever feels off-brand."

**What shipped (migration `20260525_0025`)**
- `learner_login_days(user_id, day)` — composite PK, written by the
  auth dependency on every authenticated learner request. Streak
  source-of-truth.
- `learner_points_ledger(id, user_id, source_kind, source_id,
  points, awarded_at, dedupe_key)` — append-only ledger with a
  UNIQUE(user_id, dedupe_key) constraint so duplicate awards are
  blocked at the DB.
- `learner_practice_service` extensions:
  - `record_login_day` — savepoint-guarded, never breaks auth.
  - `compute_login_streak` — "kinder" grace policy: 1 missed day per
    ISO week is forgiven (a second miss in the same week ends the
    streak). Returns `current`, `longest`, `grace_used_this_week`.
  - `award_points_for_submission` — post-commit hook awarding:
    - **+1** per correct auto-graded answer
    - **+5** perfect-score bonus
    - **+2** practice-day bonus (first submission of the day)
    - **+10** weekly-goal bonus (once per ISO week)
    - Retry attempts (Stage 2) do NOT award points — anti-grinding.
  - `compute_level` — 5 Sanskrit / age-of-Indian-archery tiers:
    Shishya (0+), Vidyārthi (50+), Ārya (200+), Ācārya (500+),
    Mahā-Ācārya (1000+). Returns name + progress-to-next.
  - `compute_heatmap` — 12 weeks × 7 days; one cell per UTC date.
  - `compute_weekly_goal_progress` — aggregates `WEEKLY_GOAL_MET`
    stamps into all-time count + current consecutive run.
- `GET /me/practice-summary` extended with `streak`, `points_total`,
  `level`, `weekly_goal_progress`, `heatmap`.
- `<PracticeCard />` gained a three-tile stats row (streak, level
  with progress bar, weeks-goal-met) and a GitHub-style 12-week
  consistency heatmap underneath.

**Tunable later (no migration needed)**
- Per-event point values (constants in `learner_practice_service.py`).
- Level names + thresholds (`LEVEL_TIERS` constant).
- Streak grace policy (`STREAK_MISSES_ALLOWED_PER_WEEK`).
- Hide points visibility — future toggle on the PracticeCard.

### Deployment note (Stage 1.5)
Re-run the migration:
```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```
Starts everyone at 0 points (no backfill). Streaks begin from the
first authenticated request after the migration applies.

---

## Stage 2 — Mistake review (Idea #4)

**Why second.** Highest learning-outcome impact. Once kids are
showing up, this is what makes them better — every wrong answer
becomes a future practice opportunity.

**Scope**
- "**Things I got wrong**" page on the learner sidebar.
- Surfaces every question the learner answered incorrectly across
  any quiz / worksheet.
- Tap to retry — single-question practice mode.
- A question leaves the list after **two consecutive corrects**
  (twice-right rule prevents lucky guesses).
- **Light spaced repetition**: mistakes from 1, 3, 7 days ago can
  be opted into the daily quick-quiz mix as "today's revision".

**Backend**
- `learner_mistake(user_id, question_id, first_wrong_at,
  last_attempted_at, consecutive_corrects)` — upserted on every
  graded submission_answer.
- Endpoint `GET /me/mistakes` (paginated, filterable by chapter /
  subject).
- Endpoint `POST /me/mistakes/{question_id}/attempt` —
  single-question retry, updates `consecutive_corrects`.

**Frontend**
- New `/me/mistakes` route.
- Card per mistake: question, chapter context, last attempted,
  "Try again" button.
- Quick-quiz form gains a "**Include questions I got wrong**"
  toggle that pulls from this pool.

**Out of scope for Stage 2**
- AI-generated similar questions (Stage 7 territory).
- Teacher-visible mistake patterns (a useful follow-up but separate).
- "**Include questions I got wrong**" toggle on the Quick Quiz form —
  deferred to a follow-up; the standalone review page already gives
  learners the retry loop without taking on quick-quiz sampler
  changes in the same stage.
- Spaced-repetition mixing of 1/3/7-day-old mistakes — deferred with
  the toggle.

### What shipped
- New `learner_mistakes` table (migration `20260517_0024`,
  UNIQUE(user_id, question_id) + index on `last_attempted_at`).
- `learner_mistake_service`:
  - `upsert_for_submission` — runs post-commit in the submission
    flow, in its own transaction so a bug here costs a mistake row
    not a quiz attempt. Skips subjective answers entirely.
  - `list_active` — bulk-fetches the question + chapter + subject
    context in one round trip; resolved rows (consecutive_corrects
    >= 2) are filtered out server-side.
  - `record_retry_attempt` — single-question retry path; grades
    via `auto_grade`, updates the row, never creates a Submission.
- Two new endpoints on `/me`, both learner-role-gated:
  - `GET /me/mistakes` with optional `chapter_id` / `subject_id`
    filters and a `total_active` count alongside the items.
  - `POST /me/mistakes/{question_id}/attempt` — returns verdict +
    correct answer + explanation + new `consecutive_corrects` +
    `resolved` flag.
- `/me/mistakes` route + `MyMistakesPage` — card-per-mistake with
  inline retry (MCQ / TRUE_FALSE render choice buttons; FILL_BLANK
  uses a text input). Verdict panel reveals the correct answer
  and explanation; "Have another go" resets the card for the next
  attempt; "Cleared!" disables the button once the twice-right
  rule retires the row.
- Sidebar nav: "Review mistakes" link for `student` and
  `individual_learner`.

### Deployment note
Run the new migration before deploying Stage 2:
```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```
Until the migration runs the `/me/mistakes*` endpoints will 500 on
the missing table; the sidebar link still routes safely (the page
just shows the loader + an empty state once the query resolves).

---

## Stage 3 — "Why?" chain on explanations (Idea #6)

**Why third.** Rewards curiosity. Once kids are practising +
revisiting mistakes, the next leap is depth of understanding.

**Scope**
- "Tell me more" button on every revealed explanation
  (worksheets, quiz results, learn-chapter reading).
- Three escalating clicks:
  1. **Deeper explanation** — fuller paragraph version of the
     same answer.
  2. **Analogy** — "Imagine you're packing for a trip…" style.
  3. **Worked example** — a fresh worked problem at the same
     concept.
- Generated on demand via LLM, cached aggressively (deterministic
  cache key per question_id + tier).
- Falls back gracefully if the LLM is rate-limited.

**Backend**
- New table: `question_extended_explanation(question_id, tier,
  text, generated_at, generated_by)` — tier in {deeper, analogy,
  example}.
- Endpoint `POST /questions/{id}/explain/{tier}` — return cached
  if present, else generate + cache.
- LLM prompt template per tier in `app/llm/prompts/`.

**Frontend**
- Inline expansion under each answer block — same component used
  in WorksheetView, TakeAssessment (results), and the AI-tutor
  chat panel.
- Loading spinner; cached tiers return instantly.

### What shipped
- Migration `20260525_0026` — `question_extended_explanation` table
  with UNIQUE(question_id, tier) for race-safe lazy caching.
- `ExplanationTier` StrEnum (DEEPER / ANALOGY / EXAMPLE) +
  `QuestionExtendedExplanation` model.
- `app/llm/prompts/explain.py` — shared India-context system voice
  with three tier-specific directives. Tone matches the AI-tutor
  chat so the two surfaces feel like one companion.
- `app/services/explain_service.py` — `get_or_generate` reads the
  cache first; on a miss, calls `LLMProvider.chat` with per-tier
  temperature, writes the row, returns. Concurrent miss-races are
  resolved by the UNIQUE constraint (loser re-reads winner's row).
- `POST /questions/{question_id}/explain/{tier}` — any
  authenticated role may request a tier. Returns 503 with a
  friendly message on LLM failure so the UI can surface a "try
  again" affordance without panicking.
- `<TellMeMore />` component — three chips (Explain more / Give me
  an analogy / Show a worked example). Each chip lazy-loads its
  tier; loaded tiers expand inline with a clean re-collapse. Errors
  show an in-place "try again" link.
- Wired into TakeAssessment results (every question card) and
  MyMistakes verdict panel (after a retry attempt).

**Out of scope for Stage 3 (deliberately deferred)**
- WorksheetView integration — the worksheet results surface lives
  in a different render pipeline; adding TellMeMore there is a
  thin follow-up but adds zero new architecture.
- "Tell me more" on the AI-tutor chat panel — chat already has its
  own follow-up mechanism (just type another message), so adding
  the chip there is redundant.

### Deployment note (Stage 3)
Run the migration:
```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```
Requires a working `LLM_PROVIDER` (anthropic / openai / groq /
stub). The stub provider returns canned text — handy for end-to-end
tests where the real LLM would be flaky / expensive.

---

## Stage 4 — Story-shaped progress (Idea #2)

**Why fourth.** Once the learner has practised, revisited mistakes,
and dug deeper into individual questions, the dashboard should
reflect their journey in human terms — not just numbers.

**Scope** (learner role only — teacher / admin dashboards unchanged)
- Replace the percentage-mastery stat cards with **3 narrative
  tiles**:
  - "Chapters mastered" + count
  - "Chapters in practice" + count
  - "Chapters to explore" + count
- Add a **topic-tree visual**: each chapter is a branch, each
  outcome a leaf. Filled-in leaves show what's been mastered.
- "**Strongest concept right now**" tile + "**Best place to
  practise next**" tile — same data as the existing weak-topics
  panel but framed positively.

**Backend**
- No new endpoints — derive everything from the existing
  mastery query.

**Frontend**
- New `LearnerProgressNarrative.tsx` component.
- Used inside `LearnerDashboard`, REPLACING the four stat-card
  row (only for the learner; teachers keep their dashboard).

### What shipped
- New `LearnerProgressNarrative` component derives everything
  client-side from the existing `StudentMasteryGrid` — no new
  endpoints, no migration.
- Three narrative tiles framed as a journey:
  - Chapters mastered (≥80% of outcomes individually mastered)
  - Chapters in practice (some attempts, not yet mastered)
  - Chapters to explore (no attempts yet)
- Two complementary tiles below the trio:
  - "Strongest concept right now" — highest-mastery attempted
    outcome (anchors the learner on a win)
  - "Best place to practise next" — weakest attempted outcome,
    falling back to an untouched outcome in an in-progress
    chapter, falling back to the lowest-numbered fresh chapter
- Topic-tree visual: one row per chapter with a dot per outcome
  (green = mastered, amber = practising, faint = untouched).
  Hover a dot for the outcome code + mastery %.
- Retired the four-card `<StatCard />` row that read like a school
  report. The lower per-outcome "Your strengths" / "Areas to focus"
  lists stay — they show top-3 with more depth than the new
  headline tiles.
- Self-learners get a "Practise this" CTA on the best-place tile;
  school students don't (their quizzes are teacher-assigned).

### Tuning knobs (no migration / no API change needed)
- `MASTERY_FLOOR` (0.75) — per-outcome mastered threshold.
- `CHAPTER_MASTERED_RATIO` (0.8) — fraction of a chapter's outcomes
  that must be individually mastered to call the chapter "mastered".

---

## Stage 5 — Vidyārthi mascot reactions (Idea #1)

**Why fifth.** Now that the platform has the substance (practice
+ mistakes + explanations + narrative progress), give it a soul
by making the mascot react to the child's progress.

**Scope**
- Tiny SVG state machine for the archer:
  - **Idle** — current splash pose.
  - **Bow drawn** — when the child is mid-quiz.
  - **Arrow flies** + **hits target** — when they get a question right.
  - **Tilted head / restring** — when they get a question wrong.
  - **Victory pose** — when they finish a quiz / earn a stamp.
- Speech bubble for context-appropriate one-liners:
  - "Two more questions to your weekly goal!"
  - "Same question, fresh try — that's how mastery is built."
- A small archer figurine fixed bottom-right on learner pages —
  togglable.
- **Outfit unlocks** — same character gains a small visual
  upgrade per N stamps (different colour kurta, a quiver,
  eventually a bow upgrade).

**Backend**
- `learner_mascot_state(user_id, equipped_kurta, equipped_quiver,
  ...)` — small.
- Endpoint `GET /me/mascot` + `POST /me/mascot/equip`.

**Frontend**
- New `<MascotCompanion />` component, mountable per page.
- Reuses the existing brand palette + arrow path.

### What shipped
- Migration `20260526_0027`: `learner_mascot_state(user_id,
  enabled, current_outfit)` — lazy-created on first GET.
- `GET /me/mascot` + `PATCH /me/mascot` — toggle visibility or
  equip an outfit. Learner-role-gated.
- `<MascotCompanion />` — pinned bottom-right, hidden for
  non-learners. Self-contained SVG: head + kurta + bow, five poses
  toggled by mood. CSS-keyframe breathing animation per pose so
  the figure feels alive without burning the main thread.
- Mascot state machine (`mascotContext.ts` + `MascotProvider.tsx`):
  - `IDLE` — default, gentle breathing
  - `DRAWN` — bow drawn, focused (while taking a quiz)
  - `FIRES` — arrow flies; correct answer / submission
  - `RESTRING` — bow lowered, wobble; wrong retry
  - `VICTORY` — bow overhead with confetti dots; perfect score /
    cleared mistake
- Speech bubble overlay with context-appropriate one-liners:
  - "Bullseye! Every mark earned." (perfect quiz)
  - "Same question, fresh try — that's how mastery is built."
    (wrong retry)
  - "Cleared! That mistake is off your list." (resolved mistake)
- Three layers of visibility control:
  1. Role gating — mounts only for student / individual_learner
  2. Server-side `enabled` flag — persists across devices, toggled
     via the small "Turn off Vidyārthi" link
  3. Session × button — quiets the mascot until next reload
     without hitting the server (a friendly "I want quiet now")
- Wired reactions into TakeAssessment (DRAWN mid-quiz, VICTORY on
  perfect submission, FIRES otherwise) and MyMistakes retry
  verdicts (VICTORY on resolved, FIRES on correct-not-yet-resolved,
  RESTRING on wrong).

**Out of scope for Stage 5 (deliberately deferred)**
- Outfit unlocks — the `current_outfit` column + endpoint payload
  are forward-compatible (any new outfit value can be added without
  a migration) but only "default" is shipped. Multiple outfits
  multiply asset count (5 poses × N outfits) and benefit from real
  illustration work rather than geometric placeholders.
- Mascot reactions on the dashboard / heatmap milestones — current
  code triggers on quiz / retry events only.

### Deployment note (Stage 5)
Run the migration:
```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```
The mascot is opt-out, not opt-in — existing learners get
`enabled=True` on first `GET /me/mascot`.

---

## Stage 6 — Parent / guardian view (Idea #9)

**Why sixth.** With the child-side experience now strong, open the
window to parents — but only the encouraging view, not surveillance.

**Scope**
- New role: `parent` (or extend existing roles with a `linked_to`
  relation).
- Parent-only dashboard: weekly summary of practice days, time
  spent, chapters touched. **NO mistake detail.**
- Weekly email summary, opt-in.
- One-click "Send well-done note" → sends a small toast to the
  child's dashboard.

**Backend**
- `parent_child_link(parent_user_id, student_user_id,
  approved_at)` with approval flow (child or school admin
  approves).
- `GET /me/children/{id}/weekly-summary`.
- `POST /me/children/{id}/encouragement` (creates a one-off
  notification record).

**Frontend**
- New `/parent` route.
- New "Notes from family" card on learner dashboard.

### What shipped
- Migration `20260526_0028` — three new tables:
  - `parent_invite_codes(code PK, student_user_id, expires_at, consumed_at, consumed_by_user_id)` — 8-char single-use codes, 7-day TTL.
  - `parent_child_link(parent_user_id, student_user_id, status, ...)` — UNIQUE pair; status APPROVED/REVOKED (PENDING reserved for future admin-mediated flow).
  - `parent_encouragement(parent_user_id, student_user_id, message, sent_at, dismissed_at)` — append-only; learner dismiss is a timestamp, not a DELETE.
- New `PARENT` value on `UserRole` (column is VARCHAR(18) with app-level validation; no ALTER TYPE needed).
- `parent_link_service`: `generate_invite_code`, `consume_invite_code`, `list_children`, `list_parents`, `revoke_link`, `assert_link_active`.
- `parent_encouragement_service`: `send`, `list_for_learner`, `list_sent_by_parent`, `dismiss`. 280-char cap; validates active link before accepting a send.
- Endpoints (all role-gated; parents = `require_parent`, learners = `require_learner`):
  - Auth: `POST /auth/signup-parent` (atomically creates User + consumes code + writes link; failures roll back the whole transaction).
  - Learner-side: `POST/GET /me/parent-invite-codes`, `GET /me/parents`, `DELETE /me/parents/{id}`, `GET /me/encouragements`, `POST /me/encouragements/{id}/dismiss`.
  - Parent-side: `GET /me/children`, `GET /me/children/{id}/weekly-summary` (NO mistake detail — the "encouraging view" promise enforced at the endpoint), `POST /me/children/{id}/encouragement`, `GET /me/children/{id}/encouragements`.
- Frontend wired:
  - `<SignupParentPage />` at `/signup-parent`. Accepts `?code=ABCD1234` as a query param for deep-link sharing.
  - `<ParentDashboard />` — per-child card with streak / level / weekly-goal tiles + recent stamps + inline encouragement composer with 4 preset messages + 280-char free text. **No mistake detail visible.**
  - `<ParentInviteCard />` on the learner dashboard — list linked parents (with revoke), list active codes (with copy-to-clipboard), button to mint a new code.
  - `<FamilyNotesCard />` on the learner dashboard — renders only when there are undismissed encouragements; per-note × dismiss button.
  - Login page footer link "Parent / guardian? Sign up with an invite code".

**Out of scope for Stage 6 (deliberately deferred)**
- **Weekly email summaries** — listed in the roadmap but require email infrastructure (SMTP / Mailgun / SES + scheduler + opt-in management) that isn't wired up in the codebase. Substantial separate piece of work; deferred to a follow-up.
- Admin-mediated approval flow (the `PENDING` state on `parent_child_link` is reserved for it).
- Multi-language preset encouragement messages.

### Stage 6.1 — Deeper parent insights (extension)

Follow-up extension to Stage 6, motivated by parent feedback wanting
more meaningful detail than just "your child has a 3-day streak".
The "encouraging view, not surveillance" principle still applies:
the new payloads are aggregates, not per-mistake / per-quiz lists.

**What shipped**
- `parent_link_service.compute_child_insights(db, child_user_id)`
  — resolves the child's primary subject (Science preferred,
  fallback to first subject of their class) and derives:
  - `chapter_rollup` — counts of mastered / in-practice /
    to-explore chapters, using the same thresholds as the
    learner's own narrative tiles (Stage 4).
  - `strengths` — top 3 outcomes by mastery (≥75%, ≥1 attempt).
  - `growing_in` — top 3 outcomes still being practised
    (<75% mastery, ≥1 attempt). Framed as "growing in", never as
    failures, per the encouraging-view principle.
  - `stamps_by_kind` — total counts grouped by stamp kind.
- `GET /me/children/{id}/weekly-summary` enriched with the
  insights payload + full `heatmap` (12-week practice grid) + full
  level info (`points_into_level`, `points_to_next`, `next_name`).
  Empty/zero values for fresh accounts so the parent sees the
  framing even before any practice.
- `<ParentDashboard />` parent ChildCard restructured:
  - Goal-met badge on the card header when the child has hit
    this week's target.
  - **Level progress bar** under the stat strip with
    "X pts to <next tier>" caption.
  - **Chapter rollup tiles** (mastered / in-practice / to-explore)
    mirroring the learner's own narrative tiles.
  - **"What they're doing well"** + **"Growing in"** lists with
    chapter context per outcome.
  - **12-week consistency heatmap** with hover tooltips per day.
  - **Stamps tally** — four-tile grid (Quizzes done / Perfect
    scores / Practice days / Weekly goals hit).

**Privacy invariants (still enforced)**
- Endpoint never returns mistake detail / per-quiz scores / the
  full mastery grid. Only aggregates.
- Parent hitting `/me/mistakes` still returns 403.
- Service helper deliberately lives inside `parent_link_service`
  so there's exactly one place where parent-facing data is shaped
  — easier to audit.

### Deployment note (Stage 6)
Run the migration:
```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```
No data backfill needed — existing learners just have empty parent /
encouragement lists until they generate their first code.

---

## Stage 7 — Practice variety (Idea #7)

**Why seventh.** Quiz fatigue is real; variety keeps kids opening
the app. Now that streaks + stamps + mascot exist, new game modes
have rewards to plug into.

**Scope**
- **Flashcards mode** — drawn from the question bank's FACTUAL
  / REMEMBER bucket. Term ↔ definition flip. No grading; user
  marks "got it" or "tricky".
- **Speedrun** — 5 questions, 30 s each, no penalty for skipping.
  Stamp on completion.
- **Surprise me** — random chapter, random question. One click.
- Wire the existing **match_pairs / categorize / timeline_order**
  simulation templates into this surface — they currently only
  appear in the content library.

**Backend**
- `GET /me/flashcards?chapter_id=...` — sample factual questions.
- `POST /me/speedrun/start` — returns 5 question_ids + a
  client-side timer hint.
- `GET /me/surprise` — one random question, scoped to the
  learner's syllabus.

**Frontend**
- New `/practice` route hub with cards for each mode.
- Reuse the existing question-rendering components.

### What shipped
- `app/services/practice_variety_service.py` — `resolve_syllabus`
  (class_level + subject_ids + chapter_ids for one learner),
  `pick_surprise` (random APPROVED question via `ORDER BY
  random()`), `sample_flashcards` (REMEMBER bucket with
  UNDERSTAND-bucket top-up so a thin chapter still fills a deck).
- Two new endpoints on `/me`, both learner-role-gated:
  - `GET /me/practice/surprise` — one card payload.
  - `GET /me/practice/flashcards?count=10&chapter_id=...` — N
    factual cards for flip-card practice.
- Speedrun deliberately reuses `/me/quick-quiz` with preset
  params (5 questions, kind=objective, 3-minute timer) — no new
  endpoint needed. All existing post-commit hooks (stamps,
  points, mistakes, mascot reactions) fire automatically.
- New `/practice` route (`<PracticePage />`):
  - Three mode cards (Speedrun / Surprise me / Flashcards) each
    with its own brand accent colour and a short tagline.
  - Speedrun launcher samples a chapter via `/me/practice/surprise`
    then posts `/me/quick-quiz`, navigates to take-quiz on success.
  - "Surprise me" renders inline below the hub — answer is hidden
    by default, "Show the answer" reveals correct + explanation.
    "Another one" fetches a fresh question.
- New `/practice/flashcards` route (`<FlashcardsPage />`):
  - CSS 3D flip card (perspective + rotateY) — front shows the
    question, back shows the answer + explanation.
  - "Got it" / "Tricky" buttons advance the deck. Mascot reacts:
    FIRES on "got it", RESTRING on "tricky".
  - End-of-deck summary screen with got/tricky tallies + restart.
- Sidebar nav: "Practice variety" link for `student` and
  `individual_learner` (Layers icon).
- Mascot integration throughout: DRAWN when launching speedrun
  or rolling a surprise; FIRES on right-flashcard / answer reveal;
  RESTRING on tricky-flashcard. All with short context messages.

**Out of scope for Stage 7 (deliberately deferred)**
- Wiring `match_pairs / categorize / timeline_order` simulation
  templates into the practice hub — their interaction model
  differs enough from MCQ/text that they need their own component.
  The templates still render in the content library.
- Persisting "tricky" flashcard marks to the DB. For v1 the tally
  is session-only (in-memory). A future iteration could write to
  a `flashcard_tricky(user_id, question_id, last_seen_at, count)`
  table and surface a "revisit tricky cards" deck.
- Speedrun-specific stamp kind. Speedrun completions earn the
  regular `QUIZ_COMPLETED` stamp via the existing post-commit
  hooks; if "speedrun completed X times" turns into a meaningful
  signal we can add a `SPEEDRUN_COMPLETED` stamp kind later.

---

## Stage 8 — Audio support (Idea #5)

**Why eighth.** Big accessibility unlock; deliberately deferred
because it cuts across every question-rendering surface — best
done once the question surfaces are stable.

**Scope**
- Browser-native `SpeechSynthesis` (no backend cost, no API key).
- 🔊 button on every question text + explanation across
  WorksheetView, TakeAssessment, LearnChapter reading,
  AI-tutor chat.
- Optional autoplay on question-open (per-learner setting).
- **"Listen + repeat"** mode for English: hear → read aloud →
  type (uses `SpeechRecognition` where supported).
- Voice picker (multilingual coverage for Hindi / Sanskrit
  questions where the browser supports the language).

**Backend**
- `learner_audio_preferences(user_id, autoplay_questions,
  preferred_voice_uri)`.

**Frontend**
- New `<ReadAloudButton text={...} lang={...} />` component.
- Sprinkled in every text-rendering site.

### What shipped
- Migration `20260526_0030` — `learner_audio_preferences(user_id,
  autoplay_questions, preferred_voice_uri)`. Lazy-created on first
  GET so existing accounts don't need a backfill.
- `GET /me/audio-preferences` + `PATCH /me/audio-preferences` —
  toggle autoplay or pick a voice. Learner-role-gated.
- `frontend/src/lib/speech.ts` — pure utilities around
  `window.speechSynthesis`:
  - `isSpeechAvailable()` — feature detect.
  - `useVoices()` — reactive voice list (handles Chrome's async
    `voiceschanged` event).
  - `pickVoice(voices, lang, preferredUri)` — voice resolver with
    sensible fallbacks (exact URI -> exact lang -> lang family ->
    system default).
  - `useSpeech({lang, voiceUri})` — imperative speak/stop with
    auto-cancel on unmount and rate=0.95 (slightly slower for
    younger learners).
- `<ReadAloudButton text lang autoStart size label />` — drops in
  next to any text. Renders nothing on browsers without
  SpeechSynthesis support (some older Android). Toggles between
  Volume2 / Pause icons; click toggles play / stop.
- `<AudioSettingsCard />` on the learner dashboard — voice picker
  (browser voices grouped by lang), autoplay toggle, "Test voice"
  button that reads a short sample sentence.
- ReadAloudButton wired into:
  - **TakeAssessment** — every results-card question + correct
    answer + explanation.
  - **MyMistakes** — question text + retry verdict's correct
    answer + explanation.
  - **TellMeMore** — every revealed tier (deeper / analogy /
    example) is read-aloud-able.
  - **Surprise me** — question + answer reveal (honours autoplay).
  - **Flashcards** — question side + answer side (autoplay fires
    on each new card when enabled).
- Autoplay support — surfaces that benefit from it (Surprise me
  reveal, each Flashcard front) read `prefs.autoplay_questions`
  and pass it as `autoStart`. Busy surfaces (TakeAssessment mid-
  quiz) deliberately don't autoplay even when the toggle is on.

**Out of scope for Stage 8 (deliberately deferred)**
- "Listen + repeat" mode (`SpeechRecognition` API). Browser
  support is patchy (Chrome-only, requires HTTPS, microphone
  permission flows). When it lands we can add it behind a "if
  recognition.available" gate.
- Server-side TTS (e.g. ElevenLabs, AWS Polly) for richer voices.
  The browser-native approach is free + offline-capable; we'll
  revisit if voice quality becomes the bottleneck.
- Per-language voice override (separate voice for English vs.
  Hindi questions). Currently one voice picker covers all langs;
  a future iteration could store a `{lang: voice_uri}` map.

### Deployment note (Stage 8)
Run the migration:
```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```
Browsers that don't support `window.speechSynthesis` (some older
Android stock browsers) render the rest of the UI unchanged — the
🔊 buttons just don't appear.

---

## Stage 9 — Kinder UX for wrong answers (Idea #8)

**Why ninth.** Polish on top of the question-rendering surfaces;
needs the hint chain (Stage 3) and the practice variety (Stage 7)
to be in place so we have hint material to draw from.

**Scope**
- Replace **"Wrong"** with **"Not yet — try again"** everywhere a
  verdict is shown.
- After 3 failed attempts on the same question, surface
  "**Want a hint?**" — uses the Stage 3 tier-2 (analogy) by
  default.
- Bigger celebration on **success-after-struggle** than
  first-try: confetti + an explicit "You stuck with it. That's
  mastery." line.
- Sound effects (Stage 8 hooks make this easy), toggleable.

### What shipped
- Migration `20260526_0031` — `learner_mistakes.wrong_streak` column
  (default 0). Wrong-side counterpart to `consecutive_corrects`;
  resets on every correct retry, +1 on every wrong retry.
- `learner_mistake_service`:
  - `HINT_THRESHOLD = 3` — three honest tries before the hint
    surfaces, not one.
  - `record_retry_attempt` maintains `wrong_streak` alongside
    `consecutive_corrects`. Returns `wrong_streak`, `hint_available`
    (= wrong_streak >= threshold), and `was_struggling` (= correct
    after a prior streak of 2+ wrongs) on every retry verdict.
  - `entry_to_dict` also exposes `wrong_streak` + `hint_available`
    so the dashboard's mistake list renders the hint button even
    before the next retry, surviving page reloads.
- Verdict copy softened from "Wrong" to **"Not yet — have another
  look"** everywhere it appeared (TakeAssessment results badge +
  MyMistakes verdict panel). Badge variant changed from
  destructive-red to warning-amber on TakeAssessment for the same
  reason: kids see this label often, it should read as "keep
  going", not "you failed".
- **Hint banner** on MyMistakes: once `hint_available` is true, a
  one-click "Show me a hint" button appears. It fetches the
  Stage-3 ANALOGY tier (the gentlest of the three) and reveals it
  inline with a 🔊 button so the hint can be read aloud.
- **Success-after-struggle celebration**: when a retry is correct
  AND the learner had been wrong at least twice in a row before,
  the verdict panel renders a bigger gradient banner with a
  bouncing 🎉 and the line *"You stuck with it. That's mastery."*
  Mascot transitions to VICTORY in parallel.
- **Verdict chimes** (Stage 8 audio plumbing):
  - `playCorrectChime` — rising third (C5 → E5) on a regular
    correct retry.
  - `playNotYetChime` — soft descending pair (G4 → E4) on a wrong
    retry. Deliberately not a buzzer or error sound.
  - `playStruggleSuccessChime` — three-note C-E-G arpeggio on a
    resolved mistake or success-after-struggle.
  - Web Audio API generates tones inline — no asset files.
- **Sounds toggle** on the AudioSettings card (per-device,
  localStorage) with two preview buttons: "Hear 'right!'" and
  "Hear 'not yet'" so a learner can sanity-check before
  committing.

**Tuning knobs**
- `HINT_THRESHOLD = 3` in `learner_mistake_service.py` — change
  here to make the hint eagerer (lower) or rarer (higher).
- Chime tones / durations in `frontend/src/lib/speech.ts` — Web
  Audio frequencies are plain numbers; swap freely.

### Deployment note (Stage 9)
Run the migration:
```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```
Existing mistake rows get `wrong_streak=0` via the server_default;
the streak starts counting from the next wrong retry forward.

---

## Stage 10 — UX polish (Idea #10)

**Why last.** Pure polish; should land on a feature-complete
product so we're polishing a finished thing, not chasing a moving
target.

**Scope**
- Larger touch targets on the learner surfaces.
- Dyslexia-friendly font option (OpenDyslexic, MIT-licensed).
- High-contrast mode.
- "Take a break" gentle nudge after 20 min continuous use.
- Avatar customisation (extends the Stage 5 mascot work).
- Settings page consolidating audio prefs (Stage 8), font (10),
  motion (existing), mascot equip (5), notifications (6).

---

## How to update this document

After each stage:
1. Move the stage's row in the table from **Up next** /
   **In progress** to **Done** with the date.
2. Update the next stage's row to **Up next**.
3. Add a short "what shipped" summary at the end of that
   stage's section.

This doc lives at `docs/child_centric_roadmap.md`. Keep it
current — it is the canonical plan.
