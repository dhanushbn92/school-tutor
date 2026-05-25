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
| 2 | Mistake review — collect + spaced-revisit the things they got wrong | 4 | **Up next** |
| 3 | "Why?" — tell-me-more chain on every explanation | 6 | Planned |
| 4 | Story-shaped progress for learners (replace bare numbers) | 2 | Planned |
| 5 | Vidyārthi mascot reactions throughout the app | 1 | Planned |
| 6 | Parent / guardian view | 9 | Planned |
| 7 | Practice variety — flashcards / speedrun / surprise me | 7 | Planned |
| 8 | Audio support — read-aloud everywhere | 5 | Planned |
| 9 | Kinder UX for wrong answers ("Not yet", hint chain) | 8 | Planned |
| 10 | UX polish — large targets, dyslexia font, take-a-break | 10 | Planned |

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
