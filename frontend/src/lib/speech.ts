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


// ---------------------------------------------------------------------------
// Stage 9 — verdict sound effects (Web Audio API)
// ---------------------------------------------------------------------------
//
// Two tiny ear-pleasing chimes that play after a retry: a rising
// pair of notes on correct, a single low note on wrong. Web Audio
// gives us "play a short tone" without shipping audio files; we
// generate them on the fly with an OscillatorNode.
//
// The toggle lives on the AudioSettings card; effects only fire
// when `audio.sounds_enabled` (Stage 9 added) is True.


type Note = { freq: number; duration: number; type?: OscillatorType };


let _sharedCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return null;
  if (_sharedCtx === null) {
    _sharedCtx = new Ctor();
  }
  // Some browsers suspend the AudioContext until a user gesture
  // unlocks it. The verdict tone runs immediately after a click so
  // the context should already be running, but resume defensively.
  if (_sharedCtx.state === "suspended") {
    void _sharedCtx.resume();
  }
  return _sharedCtx;
}


/** Play a sequence of notes via Web Audio. Each note is a short
 *  oscillator + gain envelope; no external audio files. */
function playSequence(notes: Note[]): void {
  const ctx = getAudioContext();
  if (!ctx) return;
  let when = ctx.currentTime;
  for (const note of notes) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = note.type ?? "sine";
    osc.frequency.value = note.freq;
    // Small fade-in / fade-out so the note doesn't click on
    // start / end. 8ms ramps are inaudible as ramps but kill
    // the click.
    gain.gain.setValueAtTime(0, when);
    gain.gain.linearRampToValueAtTime(0.2, when + 0.008);
    gain.gain.linearRampToValueAtTime(0, when + note.duration);
    osc.connect(gain).connect(ctx.destination);
    osc.start(when);
    osc.stop(when + note.duration + 0.05);
    when += note.duration;
  }
}


/** Cheerful rising chime — major third (C5 -> E5). */
export function playCorrectChime(): void {
  playSequence([
    { freq: 523.25, duration: 0.12 }, // C5
    { freq: 659.25, duration: 0.18 }, // E5
  ]);
}


/** Soft "not yet" — single descending note in the alto register.
 *  Deliberately NOT a buzzer or error sound; we don't want kids
 *  to associate the chime with shame. */
export function playNotYetChime(): void {
  playSequence([
    { freq: 392.0, duration: 0.18 }, // G4
    { freq: 329.63, duration: 0.16 }, // E4
  ]);
}


/** Bigger celebration chord progression for success-after-struggle. */
export function playStruggleSuccessChime(): void {
  playSequence([
    { freq: 523.25, duration: 0.1 }, // C5
    { freq: 659.25, duration: 0.1 }, // E5
    { freq: 783.99, duration: 0.22 }, // G5
  ]);
}


// ---------------------------------------------------------------------------
// Sounds-enabled preference — per device, persisted in localStorage
// ---------------------------------------------------------------------------
//
// Deliberately NOT stored server-side: "do my speakers chime?" is a
// per-device concern (the school laptop and the phone want different
// answers), and persisting it via localStorage keeps the existing
// audio_preferences migration count down.


const SOUNDS_STORAGE_KEY = "dhananjaya.sounds_enabled";


export function getSoundsEnabled(): boolean {
  if (typeof window === "undefined") return true;
  const raw = window.localStorage.getItem(SOUNDS_STORAGE_KEY);
  // Default ON — the chimes are short and pleasant. Users who want
  // quiet flip the toggle on the AudioSettings card.
  if (raw === null) return true;
  return raw === "true";
}


export function setSoundsEnabled(value: boolean): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SOUNDS_STORAGE_KEY, String(value));
  // Custom storage event so other tabs / siblings re-read.
  window.dispatchEvent(
    new StorageEvent("storage", {
      key: SOUNDS_STORAGE_KEY,
      newValue: String(value),
    }),
  );
}


export function useSoundsEnabled(): [boolean, (v: boolean) => void] {
  const [enabled, setEnabled] = useState<boolean>(() => getSoundsEnabled());
  useEffect(() => {
    const onChange = (e: StorageEvent) => {
      if (e.key !== SOUNDS_STORAGE_KEY) return;
      setEnabled(e.newValue === "true");
    };
    window.addEventListener("storage", onChange);
    return () => window.removeEventListener("storage", onChange);
  }, []);
  return [
    enabled,
    (v: boolean) => {
      setSoundsEnabled(v);
      setEnabled(v);
    },
  ];
}


/** Guard helper for verdict chimes — caller passes the chime fn,
 *  we no-op when sounds are off. Saves callers a conditional. */
export function maybePlay(chime: () => void): void {
  if (!getSoundsEnabled()) return;
  chime();
}

