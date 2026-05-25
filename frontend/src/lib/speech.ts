import { useEffect, useRef, useState } from "react";

/**
 * Browser SpeechSynthesis utilities — Stage 8 of the child-centric
 * roadmap (read-aloud everywhere).
 *
 * We deliberately use the browser's native TTS:
 *   - No backend cost, no API key.
 *   - Works offline once voices are loaded.
 *   - The user's OS-installed voices are best for languages they
 *     read in — a server-side TTS would either ship one neutral
 *     voice or charge per character.
 *
 * Tradeoffs:
 *   - Voice quality + availability varies by browser + OS. Chrome
 *     on Windows has the deepest list; iOS Safari is solid; some
 *     Android browsers ship a single robotic voice. The UI tells
 *     the learner what's available rather than promising a quality
 *     bar we can't keep.
 *   - `speechSynthesis.getVoices()` is async on Chrome (the
 *     `voiceschanged` event fires once the list is ready). The
 *     `useVoices` hook below handles that.
 */


/** Indicates whether the runtime exposes the SpeechSynthesis API.
 *  Safe to import on the server — returns false during SSR. */
export function isSpeechAvailable(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}


/** All available voices (reactively updated when the browser
 *  finishes loading them). Empty list during SSR or when the API
 *  is missing. */
export function useVoices(): SpeechSynthesisVoice[] {
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>(() =>
    isSpeechAvailable() ? window.speechSynthesis.getVoices() : [],
  );
  useEffect(() => {
    if (!isSpeechAvailable()) return;
    const populate = () => setVoices(window.speechSynthesis.getVoices());
    populate();
    // Chrome fires this once the voice list is ready (it loads
    // asynchronously on first page load).
    window.speechSynthesis.addEventListener("voiceschanged", populate);
    return () =>
      window.speechSynthesis.removeEventListener("voiceschanged", populate);
  }, []);
  return voices;
}


/** Pick a SpeechSynthesisVoice for the given language. Order:
 *   1. The preferred URI if the user has set one.
 *   2. A voice whose `lang` starts with the requested lang prefix.
 *   3. Any default voice on the system.
 *  Returns null when no voices are available yet — caller should
 *  fall back to letting the browser pick. */
export function pickVoice(
  voices: SpeechSynthesisVoice[],
  lang: string,
  preferredUri: string | null,
): SpeechSynthesisVoice | null {
  if (!voices.length) return null;
  if (preferredUri) {
    const v = voices.find((x) => x.voiceURI === preferredUri);
    if (v) return v;
  }
  // Match by lang prefix (e.g. "en-IN" matches "en-IN", "en-US", "en-GB").
  const prefix = lang.slice(0, 2).toLowerCase();
  const byLang = voices.filter(
    (v) => v.lang && v.lang.slice(0, 2).toLowerCase() === prefix,
  );
  // Prefer an exact lang match (en-IN) when available, fall back to
  // any voice in the same language family.
  const exact = byLang.find((v) => v.lang.toLowerCase() === lang.toLowerCase());
  if (exact) return exact;
  if (byLang.length) return byLang[0];
  // Last resort: any default voice.
  return voices.find((v) => v.default) ?? voices[0] ?? null;
}


export interface UseSpeechOptions {
  /** BCP 47 language tag, e.g. "en-IN", "hi-IN". Defaults to "en-IN". */
  lang?: string;
  /** Override the user's preferred voice URI for this utterance. */
  voiceUri?: string | null;
}


/**
 * Imperative read-aloud handle. Each component instance gets its
 * own play/stop state so the ReadAloudButton can show "speaking" vs
 * "idle" without coordinating with sibling buttons.
 *
 * Speaking a fresh text while another is in flight cancels the
 * previous utterance — the browser's queue is a global resource we
 * deliberately don't queue into (overlapping reads would confuse a
 * learner more than they'd help).
 */
export function useSpeech(opts: UseSpeechOptions = {}) {
  const voices = useVoices();
  const [isSpeaking, setIsSpeaking] = useState(false);
  // Track the currently-active utterance so cleanup on unmount can
  // stop it without affecting other ReadAloud instances.
  const utterRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Stop on unmount — otherwise navigating away leaves the voice
  // talking over the next page.
  useEffect(() => {
    return () => {
      if (utterRef.current && isSpeechAvailable()) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const speak = (text: string) => {
    if (!isSpeechAvailable()) return;
    if (!text.trim()) return;

    // Cancel anything currently speaking (ours OR somebody else's).
    window.speechSynthesis.cancel();

    const utter = new SpeechSynthesisUtterance(text);
    const lang = opts.lang ?? "en-IN";
    utter.lang = lang;
    const voice = pickVoice(voices, lang, opts.voiceUri ?? null);
    if (voice) {
      utter.voice = voice;
    }
    // A slightly slower rate suits younger learners better than
    // the system default. Pitch / volume left to the browser.
    utter.rate = 0.95;

    utter.onstart = () => setIsSpeaking(true);
    utter.onend = () => setIsSpeaking(false);
    utter.onerror = () => setIsSpeaking(false);

    utterRef.current = utter;
    window.speechSynthesis.speak(utter);
  };

  const stop = () => {
    if (!isSpeechAvailable()) return;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  };

  return { speak, stop, isSpeaking, available: isSpeechAvailable() };
}
