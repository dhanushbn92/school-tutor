import { createContext, useContext } from "react";

/**
 * Dhananjaya's learning buddy — a friendly robot companion (Stage 5 of the
 * child-centric roadmap).
 *
 * The mascot is a single component mounted once at the Shell level so
 * the same character figure follows the learner across pages. Pages
 * push reactions into this context via the `useMascot()` hook
 * instead of mounting their own component instance — that keeps the
 * mascot a single source of truth (no two mascots fighting on a
 * page) and lets reactions stay on screen across navigation if we
 * want them to.
 *
 * Mood is a small state machine; each mood is one pose of the character:
 *
 *   IDLE       — normal; default, at rest
 *   DRAWN      — thinking; "I'm focused, you're in the middle of a quiz"
 *   FIRES      — happy; used on a right answer
 *   RESTRING   — encouraging; used on a wrong retry ("you can do it")
 *   VICTORY    — excited / celebrating; quiz completion, a cleared mistake
 *   HINT       — giving a hint; the lightbulb pose
 *   REMINDER   — holding a bell; a gentle nudge about something waiting
 *   READING    — studying with a book; while the learner reads a chapter
 *   SURPRISED  — wide-eyed; for a surprise such as a new stamp
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

export type MascotMood =
  | "IDLE"
  | "DRAWN"
  | "FIRES"
  | "RESTRING"
  | "VICTORY"
  | "HINT"
  | "REMINDER"
  | "READING"
  | "SURPRISED";

/** Small icon shown at the start of the speech bubble. */
export type MascotBubbleIcon = "bell" | "trophy" | "bulb" | "calendar";

export interface MascotReactionOptions {
  /** Speech bubble text. Pass null/undefined to hide. */
  message?: string | null;
  /** Icon for the bubble; defaults per mood (bell, trophy, bulb) when omitted. */
  icon?: MascotBubbleIcon | null;
  /** If set, the mood reverts to IDLE (and message clears) after this
   *  many milliseconds. Use 0 / undefined to make the mood sticky. */
  autoResetMs?: number;
}

export interface MascotContextValue {
  mood: MascotMood;
  message: string | null;
  icon: MascotBubbleIcon | null;
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
    icon: null,
    setMood: () => {},
    setMessage: () => {},
    reactWith: () => {},
    reset: () => {},
  };
}
