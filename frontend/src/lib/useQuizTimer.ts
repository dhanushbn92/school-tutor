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
}): { secondsLeft: number; totalSeconds: number; clear: () => void } {
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

  // Start time — null until the timer is first enabled with a
  // positive duration. After that it's a stable epoch-ms value
  // (either freshly captured or restored from localStorage).
  const [startedAt, setStartedAt] = useState<number | null>(null);
  // Default to the full duration so the banner renders sensibly
  // during the brief moment before the tick effect computes the
  // actual remaining time.
  const [secondsLeft, setSecondsLeft] = useState<number>(totalSeconds);

  // Initialise startedAt the first time the timer is enabled. We
  // can't do this in a lazy useState initialiser because that runs
  // exactly once on mount — usually BEFORE the assessment data has
  // loaded and `enabled` has flipped true. A useEffect re-runs
  // whenever its deps change, so we pick up the flip.
  useEffect(() => {
    if (!enabled) return;
    if (storageKey === null || totalSeconds === 0) return;
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
  }, [enabled, storageKey, totalSeconds, startedAt]);

  // Keep secondsLeft in sync with totalSeconds when the duration
  // changes (e.g. it was 0 on first render before the assessment
  // loaded, then became a positive number afterwards). Without this
  // the banner can briefly read "0:00" before the tick effect runs.
  useEffect(() => {
    if (startedAt === null) {
      // Intentional setState-in-effect: external value changed
      // (totalSeconds went from 0 to N), the banner needs to update.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSecondsLeft(totalSeconds);
    }
  }, [totalSeconds, startedAt]);

  // The ticker. Runs at 1 Hz while the timer is active. We compute
  // remaining time from `startedAt` rather than decrementing a
  // counter, which keeps the display correct even if the tab is
  // backgrounded and the interval drifts.
  useEffect(() => {
    if (!enabled || startedAt === null || totalSeconds === 0) return;
    // Update once immediately so the banner doesn't show stale
    // "full duration" for up to 1 s after startedAt is set.
    const update = () => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setSecondsLeft(Math.max(0, totalSeconds - elapsed));
    };
    update();
    const id = window.setInterval(update, 1000);
    return () => window.clearInterval(id);
  }, [enabled, startedAt, totalSeconds]);

  const clear = useCallback(() => {
    if (storageKey === null) return;
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      /* nothing useful to do */
    }
  }, [storageKey]);

  return { secondsLeft, totalSeconds, clear };
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
