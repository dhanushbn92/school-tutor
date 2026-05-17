import { useCallback, useEffect, useState } from "react";

/**
 * Client-side quiz countdown for time-bound assessments.
 *
 * The earlier version of this hook had a subtle bug: it initialised
 * `startedAt` in a `useState` lazy initialiser, which runs only on
 * mount. On the first render the assessment data hadn't loaded yet,
 * so `enabled` was false and `startedAt` was set to `null`. Once the
 * assessment data arrived and `enabled` flipped to true, the lazy
 * initialiser never re-ran — `startedAt` stayed null forever, the
 * tick effect early-exited, and no timer ever appeared.
 *
 * Fix: initialise `startedAt` in a useEffect that re-runs whenever
 * `enabled` becomes true. The persisted localStorage value carries
 * the start time across page refreshes within the same attempt.
 *
 * Design choices
 *
 *   - The start time is persisted in `localStorage` keyed by the
 *     assessment id (`dhananjaya:quiz-started:<id>`), so a page
 *     refresh in the middle of an attempt keeps counting from the
 *     same starting moment rather than restarting from zero.
 *   - If a learner walks away and comes back after the deadline,
 *     `secondsLeft` is immediately 0 on the next tick, which lets
 *     the caller trigger an auto-submit with whatever answers are
 *     currently in state (likely none).
 *   - When the parent flips `enabled` to false on submit and calls
 *     `clear()`, the persisted start time is removed so a future
 *     replay starts fresh rather than "already over".
 *
 * Returns
 *   secondsLeft   integer seconds remaining (clamped at 0)
 *   totalSeconds  full duration in seconds (0 when not time-bound)
 *   clear()       remove the persisted start time — call on submit
 */
export function useQuizTimer({
  assessmentId,
  durationMinutes,
  enabled,
}: {
  assessmentId: number | undefined;
  /** From `Assessment.duration_minutes`. null / undefined falls back
   *  to the locally-stashed duration the QuickQuiz form wrote on
   *  creation (see resolveDurationMinutes below). */
  durationMinutes: number | null | undefined;
  /** Master switch — flip to false the moment a submission lands. */
  enabled: boolean;
}): {
  /** Whole seconds remaining until the deadline. Always 0 when the
   *  quiz is untimed (totalSeconds === 0); caller should display
   *  `elapsedSeconds` instead in that case. */
  secondsLeft: number;
  /** Full duration in seconds. 0 when the quiz is untimed. */
  totalSeconds: number;
  /** Whole seconds elapsed since the attempt started. Tracked even
   *  for untimed quizzes so the take-page can show an "elapsed time"
   *  badge instead of leaving the area blank. */
  elapsedSeconds: number;
  /** Remove the persisted start time — call on submit so a future
   *  reopen starts fresh rather than "already over". */
  clear: () => void;
} {
  // Resolve the effective duration. Server value wins when it's a
  // positive integer (teacher-assigned quizzes always have it). When
  // the server returns null — typically a quick-quiz where the
  // backend silently dropped the field — fall back to whatever the
  // QuickQuiz form stashed in localStorage on creation.
  const resolved = resolveDurationMinutes(assessmentId, durationMinutes);
  const totalSeconds = resolved * 60;
  const storageKey =
    assessmentId !== undefined
      ? `dhananjaya:quiz-started:${assessmentId}`
      : null;

  // Start time — null until the timer is first enabled. After that
  // it's a stable epoch-ms value (either freshly captured or
  // restored from localStorage). NOTE: we initialise this for BOTH
  // timed and untimed attempts so the elapsed-time display can run
  // on untimed quizzes too; the totalSeconds check only gates the
  // countdown side.
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  // Initialise startedAt the first time the timer is enabled. We
  // can't do this in a lazy useState initialiser because that runs
  // exactly once on mount — usually BEFORE the assessment data has
  // loaded and `enabled` has flipped true. A useEffect re-runs
  // whenever its deps change, so we pick up the flip.
  //
  // Note: storageKey is required (the elapsed timer needs to
  // survive page reloads) but totalSeconds is NOT — an untimed
  // attempt still gets a startedAt so we can show elapsed time.
  useEffect(() => {
    if (!enabled) return;
    if (storageKey === null) return;
    if (startedAt !== null) return; // already initialised
    let ts: number;
    try {
      const existing = window.localStorage.getItem(storageKey);
      if (existing) {
        const parsed = Number(existing);
        ts = Number.isFinite(parsed) && parsed > 0 ? parsed : Date.now();
      } else {
        ts = Date.now();
        window.localStorage.setItem(storageKey, String(ts));
      }
    } catch {
      ts = Date.now();
    }
    // Intentional setState-in-effect: this is the bridge between
    // the external "assessment loaded → timer enabled" signal and
    // the internal startedAt state. There is no cleaner pure-render
    // way to do this lazy initialisation.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStartedAt(ts);
  }, [enabled, storageKey, startedAt]);

  // The ticker. Runs at 1 Hz once startedAt is captured, regardless
  // of whether the attempt is timed. We compute elapsed seconds
  // from `startedAt` rather than decrementing a counter, which
  // keeps the display correct even if the tab is backgrounded and
  // the interval drifts.
  useEffect(() => {
    if (!enabled || startedAt === null) return;
    const update = () => {
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    };
    update();
    const id = window.setInterval(update, 1000);
    return () => window.clearInterval(id);
  }, [enabled, startedAt]);

  // Derived: how many whole seconds remain until the deadline. For
  // untimed quizzes totalSeconds is 0 and secondsLeft is always 0
  // (caller should display elapsedSeconds instead).
  const secondsLeft =
    totalSeconds > 0 ? Math.max(0, totalSeconds - elapsedSeconds) : 0;

  const clear = useCallback(() => {
    if (storageKey === null) return;
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      /* nothing useful to do */
    }
  }, [storageKey]);

  return { secondsLeft, totalSeconds, elapsedSeconds, clear };
}

/**
 * Pick the effective duration in minutes for an attempt.
 *
 * Priority:
 *   1. Server value (assessment.duration_minutes) — always wins when
 *      it's a positive integer. Teacher-assigned quizzes set this at
 *      creation time, so the take page is fully driven by the DB.
 *   2. Local fallback (localStorage `dhananjaya:quiz-duration:<id>`)
 *      written by the QuickQuiz form on creation. This belt-and-
 *      braces fallback exists because the backend has on at least
 *      one occasion silently dropped the field — the user picked N
 *      minutes, the row went in with NULL, and the take page showed
 *      no banner. Stashing locally means the timer still works for
 *      self-created quizzes regardless of backend state.
 *   3. Zero — no banner.
 *
 * Returns 0 when no timer should run.
 */
function resolveDurationMinutes(
  assessmentId: number | undefined,
  serverValue: number | null | undefined,
): number {
  if (typeof serverValue === "number" && serverValue > 0) return serverValue;
  if (assessmentId === undefined || typeof window === "undefined") return 0;
  try {
    const raw = window.localStorage.getItem(
      `dhananjaya:quiz-duration:${assessmentId}`,
    );
    if (raw == null) return 0;
    const parsed = Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  } catch {
    return 0;
  }
}

/**
 * Format a seconds count for the timer banner. Always shows mm:ss
 * (hours rolled into minutes — a 90-minute quiz reads "90:00", which
 * is unambiguous at a glance).
 */
export function formatClock(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const m = Math.floor(safe / 60);
  const s = safe % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}
