import { createContext, useContext } from "react";

/**
 * Dhananjaya mascot — Stage 5 of the child-centric roadmap.
 *
 * The mascot is a single component mounted once at the Shell level so
 * the same character figure follows the learner across pages. Pages
 * push reactions into this context via the `useMascot()` hook
 * instead of mounting their own component instance — that keeps the
 * mascot a single source of truth (no two mascots fighting on a
 * page) and lets reactions stay on screen across navigation if we
 * want them to.
 *
 * Mood is a small state machine:
 *
 *   IDLE       — default; mascot at rest
 *   DRAWN      — bow drawn; "I'm focused, you're in the middle of a quiz"
 *   FIRES      — celebratory; "arrow hits the target", used on a right answer
 *   RESTRING   — encouraging; "still nocking the arrow", used on a wrong retry
 *   VICTORY    — bow held overhead; used on quiz completion / cleared mistake
 *
 * `reactWith(mood, { message, autoResetMs })` is the imperative
 * helper pages call. It sets the mood + speech bubble, then (if
 * autoResetMs is given) reverts to IDLE after the timeout.
 *
 * Provider lives in MascotProvider.tsx — this file is the pure
 * context + types + hook so it can be imported from .ts and .tsx
 * sources without tripping react-refresh's only-export-components
 * rule for .tsx files.
 */

export type MascotMood = "IDLE" | "DRAWN" | "FIRES" | "RESTRING" | "VICTORY";

export interface MascotReactionOptions {
  /** Speech bubble text. Pass null/undefined to hide. */
  message?: string | null;
  /** If set, the mood reverts to IDLE (and message clears) after this
   *  many milliseconds. Use 0 / undefined to make the mood sticky. */
  autoResetMs?: number;
}

export interface MascotContextValue {
  mood: MascotMood;
  message: string | null;
  setMood: (mood: MascotMood) => void;
  setMessage: (msg: string | null) => void;
  /** Convenience: set mood + message together, optionally auto-reset. */
  reactWith: (mood: MascotMood, opts?: MascotReactionOptions) => void;
  /** Reset to IDLE + clear message. */
  reset: () => void;
}

export const MascotContext = createContext<MascotContextValue | null>(null);

/**
 * Read + push to mascot state from any component. Safe to call on
 * non-learner pages: if the provider isn't mounted, returns a no-op
 * shape so callers don't have to gate every dispatch behind a role
 * check. The mascot itself only renders for learners.
 */
export function useMascot(): MascotContextValue {
  const ctx = useContext(MascotContext);
  if (ctx) return ctx;
  // Safe no-op for non-learner pages where the provider isn't mounted.
  return {
    mood: "IDLE",
    message: null,
    setMood: () => {},
    setMessage: () => {},
    reactWith: () => {},
    reset: () => {},
  };
}
