import { useEffect, useRef, useState } from "react";
import { Coffee, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { useBreakNudgeEnabled } from "@/lib/accessibility";

/**
 * Take-a-break nudge — Stage 10 of the child-centric roadmap.
 *
 * Mounts once at the Shell level. After 20 minutes of CONTINUOUS
 * activity (pointer / keyboard / scroll), shows a small floating
 * banner suggesting a break. The banner doesn't pause anything;
 * dismissing it just hides it.
 *
 * "Continuous" means the learner hasn't been idle for more than 5
 * minutes — if they walk away for a smoke (or, you know, dinner)
 * and come back, the timer restarts so we don't fire the nudge
 * the instant they sit back down.
 *
 * Gated by:
 *   1. Role — only learners see it.
 *   2. `useBreakNudgeEnabled()` localStorage flag (default true) —
 *      flipped from the AccessibilityCard.
 *   3. Dismiss button — hides for the rest of the session.
 *
 * Dismissal explicitly does NOT persist across reloads. The whole
 * point is "we noticed you've been at it a while" and that's a
 * per-session observation.
 */

const NUDGE_AFTER_MS = 20 * 60_000; // 20 minutes of continuous use
const IDLE_RESET_MS = 5 * 60_000; // 5 minutes idle restarts the timer

export function TakeABreakNudge() {
  const { user } = useAuth();
  const isLearner =
    user?.role === "student" || user?.role === "individual_learner";
  const [breakNudgeEnabled] = useBreakNudgeEnabled();
  const [show, setShow] = useState(false);
  const [dismissedThisSession, setDismissedThisSession] = useState(false);

  // Track when the current "continuous use" window started, and
  // when the last interaction happened. If `Date.now() -
  // lastInteractionAt` exceeds IDLE_RESET_MS we reset the start.
  // Initialised to 0 here (purity rule forbids Date.now() in
  // render); the mount effect seeds them to the real time.
  const startRef = useRef<number>(0);
  const lastRef = useRef<number>(0);

  useEffect(() => {
    if (!isLearner || !breakNudgeEnabled || dismissedThisSession) return;
    // Seed the timestamps on mount, not at construction, so the
    // purity rule is happy and the values are deterministic on
    // re-renders.
    const now = Date.now();
    startRef.current = now;
    lastRef.current = now;

    const onActivity = () => {
      const now = Date.now();
      if (now - lastRef.current > IDLE_RESET_MS) {
        // Treated as a fresh session — they came back from being
        // away. Reset the start so the nudge fires after a fresh
        // 20-minute window, not immediately.
        startRef.current = now;
      }
      lastRef.current = now;
    };

    // A small set of events is enough to detect "still here". We
    // deliberately skip mousemove (too chatty) — pointerdown +
    // keydown + scroll covers tapping, typing, reading.
    window.addEventListener("pointerdown", onActivity);
    window.addEventListener("keydown", onActivity);
    window.addEventListener("scroll", onActivity, { passive: true });

    const check = window.setInterval(() => {
      if (Date.now() - startRef.current >= NUDGE_AFTER_MS) {
        setShow(true);
        // Reset the start so a dismissed nudge doesn't immediately
        // re-fire on the next tick.
        startRef.current = Date.now();
      }
    }, 30_000);

    return () => {
      window.removeEventListener("pointerdown", onActivity);
      window.removeEventListener("keydown", onActivity);
      window.removeEventListener("scroll", onActivity);
      window.clearInterval(check);
    };
  }, [isLearner, breakNudgeEnabled, dismissedThisSession]);

  if (!isLearner || !breakNudgeEnabled || dismissedThisSession || !show) {
    return null;
  }

  return (
    <div
      role="status"
      className="fixed bottom-24 right-4 z-40 max-w-sm rounded-lg border border-(--color-border) bg-(--color-card) p-4 shadow-xl md:right-6"
    >
      <div className="flex items-start gap-3">
        <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-200">
          <Coffee className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-display text-sm font-semibold">
            You've been at it a while.
          </div>
          <p className="mt-1 text-xs leading-relaxed text-(--color-muted-foreground)">
            How about a five-minute break? Stretch, sip water, look out
            the window. Your streak waits.
          </p>
          <div className="mt-3 flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShow(false)}
            >
              Five more minutes
            </Button>
            <Button
              size="sm"
              onClick={() => setDismissedThisSession(true)}
            >
              Got it
            </Button>
          </div>
        </div>
        <button
          type="button"
          aria-label="Dismiss break reminder"
          onClick={() => setShow(false)}
          className="text-(--color-muted-foreground) hover:text-(--color-foreground)"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
