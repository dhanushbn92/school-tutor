import {
  useCallback,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  MascotContext,
  type MascotContextValue,
  type MascotMood,
  type MascotReactionOptions,
} from "./mascotContext";

/**
 * Wraps a subtree in the mascot mood/message context. See
 * `mascotContext.ts` for the state-machine documentation and the
 * `useMascot()` consumer hook.
 *
 * Tracks the current auto-reset timer in a ref so a fresh reaction
 * cancels the pending revert rather than letting it stomp on the new
 * mood (i.e. fast-fire of FIRES → VICTORY doesn't see the FIRES
 * autoReset clear the VICTORY two seconds later).
 */
export function MascotProvider({ children }: { children: ReactNode }) {
  const [mood, setMood] = useState<MascotMood>("IDLE");
  const [message, setMessage] = useState<string | null>(null);
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const reset = useCallback(() => {
    if (resetTimer.current) {
      clearTimeout(resetTimer.current);
      resetTimer.current = null;
    }
    setMood("IDLE");
    setMessage(null);
  }, []);

  const reactWith = useCallback(
    (nextMood: MascotMood, opts?: MascotReactionOptions) => {
      if (resetTimer.current) {
        clearTimeout(resetTimer.current);
        resetTimer.current = null;
      }
      setMood(nextMood);
      setMessage(opts?.message ?? null);
      if (opts?.autoResetMs && opts.autoResetMs > 0) {
        resetTimer.current = setTimeout(() => {
          setMood("IDLE");
          setMessage(null);
          resetTimer.current = null;
        }, opts.autoResetMs);
      }
    },
    [],
  );

  const value = useMemo<MascotContextValue>(
    () => ({
      mood,
      message,
      setMood,
      setMessage,
      reactWith,
      reset,
    }),
    [mood, message, reactWith, reset],
  );

  return (
    <MascotContext.Provider value={value}>{children}</MascotContext.Provider>
  );
}
