import { useEffect, useState } from "react";

/**
 * Accessibility preferences — Stage 10 of the child-centric roadmap.
 *
 * Three independent toggles, all per-device (localStorage), all
 * applied as `data-*` attributes on the document root so CSS in
 * `index.css` can light up the corresponding overrides without
 * cascading className management.
 *
 * Why localStorage and not the backend:
 *   - Touch-target sizes belong to the device (phone vs. desktop).
 *   - Dyslexia font + contrast preferences often differ by device
 *     too (some learners only want it on a small phone screen).
 *   - Keeps the migration count down; we already shipped 31.
 *
 * The "take a break" nudge timeout also lives here for symmetry —
 * it's not a preference per se, but it's part of the same
 * accessibility kit and the hooks all share an opt-out pattern.
 */

export type FontPreference = "default" | "dyslexia-friendly";
export type ContrastPreference = "default" | "high";
export type TouchPreference = "default" | "large";

const STORAGE_KEYS = {
  font: "dhananjaya.a11y.font",
  contrast: "dhananjaya.a11y.contrast",
  touch: "dhananjaya.a11y.touch",
  breakNudge: "dhananjaya.a11y.break_nudge",
} as const;

const DATA_ATTRIBUTES = {
  font: "data-font",
  contrast: "data-contrast",
  touch: "data-touch",
} as const;

/** Apply the value as a data-* attribute on <html>, or remove it
 *  entirely when the value is the default (smaller DOM, no
 *  redundant CSS selectors). */
function applyAttr(attr: string, value: string, isDefault: boolean): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (isDefault) {
    root.removeAttribute(attr);
  } else {
    root.setAttribute(attr, value);
  }
}

function readPref<T extends string>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  const raw = window.localStorage.getItem(key);
  return (raw ?? fallback) as T;
}

function writePref(key: string, value: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, value);
  window.dispatchEvent(
    new StorageEvent("storage", { key, newValue: value }),
  );
}

/* --- Font (dyslexia-friendly) ---------------------------------- */

export function useFontPreference(): [FontPreference, (v: FontPreference) => void] {
  const [value, setValue] = useState<FontPreference>(() =>
    readPref(STORAGE_KEYS.font, "default"),
  );
  useEffect(() => {
    applyAttr(DATA_ATTRIBUTES.font, value, value === "default");
  }, [value]);
  useEffect(() => {
    const onChange = (e: StorageEvent) => {
      if (e.key !== STORAGE_KEYS.font) return;
      setValue((e.newValue as FontPreference) ?? "default");
    };
    window.addEventListener("storage", onChange);
    return () => window.removeEventListener("storage", onChange);
  }, []);
  return [
    value,
    (v) => {
      writePref(STORAGE_KEYS.font, v);
      setValue(v);
    },
  ];
}

/* --- Contrast ---------------------------------------------------- */

export function useContrastPreference(): [ContrastPreference, (v: ContrastPreference) => void] {
  const [value, setValue] = useState<ContrastPreference>(() =>
    readPref(STORAGE_KEYS.contrast, "default"),
  );
  useEffect(() => {
    applyAttr(DATA_ATTRIBUTES.contrast, value, value === "default");
  }, [value]);
  useEffect(() => {
    const onChange = (e: StorageEvent) => {
      if (e.key !== STORAGE_KEYS.contrast) return;
      setValue((e.newValue as ContrastPreference) ?? "default");
    };
    window.addEventListener("storage", onChange);
    return () => window.removeEventListener("storage", onChange);
  }, []);
  return [
    value,
    (v) => {
      writePref(STORAGE_KEYS.contrast, v);
      setValue(v);
    },
  ];
}

/* --- Touch targets ---------------------------------------------- */

export function useTouchPreference(): [TouchPreference, (v: TouchPreference) => void] {
  const [value, setValue] = useState<TouchPreference>(() =>
    readPref(STORAGE_KEYS.touch, "default"),
  );
  useEffect(() => {
    applyAttr(DATA_ATTRIBUTES.touch, value, value === "default");
  }, [value]);
  useEffect(() => {
    const onChange = (e: StorageEvent) => {
      if (e.key !== STORAGE_KEYS.touch) return;
      setValue((e.newValue as TouchPreference) ?? "default");
    };
    window.addEventListener("storage", onChange);
    return () => window.removeEventListener("storage", onChange);
  }, []);
  return [
    value,
    (v) => {
      writePref(STORAGE_KEYS.touch, v);
      setValue(v);
    },
  ];
}

/* --- Take-a-break nudge ----------------------------------------- */

export function getBreakNudgeEnabled(): boolean {
  if (typeof window === "undefined") return true;
  const raw = window.localStorage.getItem(STORAGE_KEYS.breakNudge);
  // Default ON — learners benefit from the prompt; those who don't
  // want it can flip it off.
  if (raw === null) return true;
  return raw === "true";
}

export function useBreakNudgeEnabled(): [boolean, (v: boolean) => void] {
  const [value, setValue] = useState<boolean>(() => getBreakNudgeEnabled());
  useEffect(() => {
    const onChange = (e: StorageEvent) => {
      if (e.key !== STORAGE_KEYS.breakNudge) return;
      setValue(e.newValue === "true");
    };
    window.addEventListener("storage", onChange);
    return () => window.removeEventListener("storage", onChange);
  }, []);
  return [
    value,
    (v) => {
      writePref(STORAGE_KEYS.breakNudge, String(v));
      setValue(v);
    },
  ];
}
