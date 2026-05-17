import { useCallback, useEffect, useState } from "react";

/**
 * Client-side quiz countdown for time-bound assessments.
 *
 * Design choices
 *
 *   - The start time is persisted in `localStorage` keyed by the
 *     assessment id, so a page refresh in the middle of an attempt
 *     keeps counting from the same starting moment rather than
 *     restarting from zero.
 *   - If a learner walks away and comes back after the deadline,
 *     `secondsLeft` is immediately 0 on mount, which lets the caller
 *     trigger an auto-submit with whatever answers are currently in
 *     state (likely none) on the very next render.
 *   - The hook only runs the interval when `enabled` is true. Once
 *     the parent submits — manually or automatically — it should
 *     flip `enabled` to false and call `clear()` so the persisted
 *     start time is removed and a future replay isn't immediately
 *     "already over".
 *
 * What this hook is NOT
 *
 *   - Server-enforced. The backend will accept a submission whenever
 *     it arrives; this hook is a learner-facing nudge + an auto-
 *     submit convenience. A determined user can clear localStorage
 *     and reset their own clock — which we consider acceptable for
 *     v1. Strict enforcement is a server "started_at" field, which
 *     is a clean follow-up if it's needed.
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

  // Lazy init: read or create the start timestamp. We do this once on
  // mount; subsequent renders don't re-evaluate. The check guards
  // against SSR (no window) and the not-yet-known assessment id case.
  const [startedAt] = useState<number | null>(() => {
    if (
      !enabled ||
      storageKey === null ||
      totalSeconds === 0 ||
      typeof window === "undefined"
    ) {
      return null;
    }
    try {
      const existing = window.localStorage.getItem(storageKey);
      if (existing) {
        const parsed = Number(existing);
        if (Number.isFinite(parsed) && parsed > 0) return parsed;
      }
      const now = Date.now();
      window.localStorage.setItem(storageKey, String(now));
      return now;
    } catch {
      // Storage blocked → fall back to in-memory only. The countdown
      // still works for this session; refresh will reset it.
      return Date.now();
    }
  });

  const [secondsLeft, setSecondsLeft] = useState<number>(() => {
    if (startedAt === null) return totalSeconds;
    const elapsed = Math.floor((Date.now() - startedAt) / 1000);
    return Math.max(0, totalSeconds - elapsed);
  });

  // The ticker. Runs at 1 Hz while the timer is active. We compute
  // remaining time from `startedAt` rather than decrementing a
  // counter, which keeps the display correct even if the tab is
  // backgrounded and the interval drifts.
  useEffect(() => {
    if (!enabled || startedAt === null) return;
    const id = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setSecondsLeft(Math.max(0, totalSeconds - elapsed));
    }, 1000);
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
 *      one occasion silently dropped the field — the user picked 3
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
