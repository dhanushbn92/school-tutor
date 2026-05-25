import { useEffect } from "react";
import { Pause, Volume2 } from "lucide-react";
import { useSpeech } from "@/lib/speech";
import { useAudioPreferences } from "@/lib/queries";
import { cn } from "@/lib/utils";

/**
 * 🔊 button — Stage 8 of the child-centric roadmap.
 *
 * Drop it anywhere a learner sees readable text (question, answer,
 * explanation, hint). Reads the supplied text via the browser's
 * native SpeechSynthesis API. Honours the learner's
 * `preferred_voice_uri` from `/me/audio-preferences` so a single
 * voice picker setting follows them across surfaces.
 *
 * Renders nothing on browsers without SpeechSynthesis support (some
 * older Android browsers) — the rest of the UI is unaffected.
 *
 * When `autoStart` is true, the text begins reading on mount. The
 * caller is expected to pass `autoStart={prefs.autoplay_questions}`
 * only on surfaces where autoplay makes sense (Surprise me reveal,
 * each Flashcard front), not on busy surfaces (TakeAssessment mid-
 * quiz) where it would be obnoxious.
 *
 * Sized to sit inline next to a question heading — pass `size="sm"`
 * (the default) for that. `size="md"` is for standalone "Listen to
 * the chapter" affordances.
 */

export interface ReadAloudButtonProps {
  text: string;
  /** BCP 47 lang tag for the text. Defaults to "en-IN". */
  lang?: string;
  /** Start speaking on mount. The component dedupes — multiple
   *  ReadAloud instances on the same screen won't all autoplay. */
  autoStart?: boolean;
  /** Visual size + spacing. */
  size?: "sm" | "md";
  /** Accessible label override; defaults to "Read this aloud". */
  label?: string;
  className?: string;
}

export function ReadAloudButton({
  text,
  lang = "en-IN",
  autoStart = false,
  size = "sm",
  label = "Read this aloud",
  className,
}: ReadAloudButtonProps) {
  const prefsQ = useAudioPreferences();
  const preferredVoiceUri = prefsQ.data?.preferred_voice_uri ?? null;

  const { speak, stop, isSpeaking, available } = useSpeech({
    lang,
    voiceUri: preferredVoiceUri,
  });

  // Autoplay on mount when the prop is true. We deliberately run
  // this only once per mount — re-triggering on text change would
  // make the page chatter as the learner cycles content (e.g.
  // Flashcard advances).
  useEffect(() => {
    if (autoStart && text.trim()) {
      // Tiny delay so the browser has the voice list ready and the
      // user isn't startled by speech the instant a page paints.
      const t = window.setTimeout(() => speak(text), 250);
      return () => {
        window.clearTimeout(t);
        stop();
      };
    }
    return undefined;
    // text change without autoStart re-trigger is intentional.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart]);

  if (!available) return null;

  const dim = size === "sm" ? "h-7 w-7" : "h-9 w-9";
  const icon = size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4";

  return (
    <button
      type="button"
      aria-label={isSpeaking ? "Stop reading" : label}
      title={isSpeaking ? "Stop reading" : label}
      onClick={() => {
        if (isSpeaking) {
          stop();
        } else {
          speak(text);
        }
      }}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full border transition",
        dim,
        isSpeaking
          ? "border-(--color-primary) bg-(--color-primary)/15 text-(--color-primary)"
          : "border-(--color-border) text-(--color-muted-foreground) hover:bg-(--color-muted) hover:text-(--color-foreground)",
        className,
      )}
    >
      {isSpeaking ? (
        <Pause className={icon} />
      ) : (
        <Volume2 className={icon} />
      )}
    </button>
  );
}
