import { useCallback, useState } from "react";
import Sanscript from "@indic-transliteration/sanscript";
import { cn } from "@/lib/utils";
import { DevanagariHelp } from "@/components/DevanagariHelp";

/**
 * Answer input that lets a student type Devanagari with no device setup.
 *
 * In "अ" (Devanagari) mode the student types in Roman/English letters using the
 * ITRANS scheme (e.g. `vidyaa dadaati` → विद्या ददाति); the field shows what
 * they type and a live preview shows the Devanagari that will actually be
 * submitted. Transliteration runs fully offline (bundled scheme data — no
 * network, no data leaves the device). In "A" mode it behaves as a plain field.
 *
 * The stored/submitted value is always the final script: Devanagari in अ mode,
 * literal text in A mode. Switching to अ mode starts a fresh Roman buffer, so
 * toggling clears the box (intentional — the two scripts aren't interchangeable).
 */

const SCHEME = "itrans";

function toDevanagari(roman: string): string {
  try {
    return Sanscript.t(roman, SCHEME, "devanagari");
  } catch {
    return roman;
  }
}

type Mode = "en" | "dev";

export function DevanagariInput({
  as = "input",
  value,
  onChange,
  defaultMode = "dev",
  id,
  rows,
  placeholder,
  className,
}: {
  as?: "input" | "textarea";
  value: string;
  onChange: (v: string) => void;
  /** Which mode the field opens in. Sanskrit answers default to "dev". */
  defaultMode?: Mode;
  id?: string;
  rows?: number;
  placeholder?: string;
  className?: string;
}) {
  const [mode, setMode] = useState<Mode>(defaultMode);
  // In dev mode the visible field holds the Roman source; the parent holds the
  // transliterated Devanagari. In en mode the field mirrors the parent value.
  const [roman, setRoman] = useState("");

  const switchMode = useCallback(
    (next: Mode) => {
      if (next === mode) return;
      if (next === "dev") {
        setRoman("");
        onChange(""); // Roman buffer resets; clear the stale value too.
      }
      setMode(next);
    },
    [mode, onChange],
  );

  const fieldValue = mode === "dev" ? roman : value;
  const preview = mode === "dev" ? toDevanagari(roman) : "";

  const handleChange = (raw: string) => {
    if (mode === "dev") {
      setRoman(raw);
      onChange(toDevanagari(raw));
    } else {
      onChange(raw);
    }
  };

  const fieldClass = cn(
    "flex w-full rounded-md border border-(--color-input) bg-transparent px-3 py-2 text-sm shadow-sm transition-colors",
    "placeholder:text-(--color-muted-foreground)",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--color-ring)",
    as === "input" && "h-9 py-1",
    className,
  );

  return (
    <div className="space-y-1.5">
      {as === "textarea" ? (
        <textarea
          id={id}
          value={fieldValue}
          onChange={(e) => handleChange(e.target.value)}
          rows={rows ?? 3}
          placeholder={placeholder}
          lang={mode === "dev" ? "en" : undefined}
          className={fieldClass}
        />
      ) : (
        <input
          id={id}
          value={fieldValue}
          onChange={(e) => handleChange(e.target.value)}
          placeholder={placeholder}
          lang={mode === "dev" ? "en" : undefined}
          className={fieldClass}
        />
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div
          className="inline-flex overflow-hidden rounded-md border border-(--color-border) text-xs font-medium"
          role="group"
          aria-label="Typing mode"
        >
          <button
            type="button"
            onClick={() => switchMode("dev")}
            aria-pressed={mode === "dev"}
            title="Type in English letters, get Devanagari"
            className={cn(
              "px-2.5 py-1",
              mode === "dev"
                ? "bg-(--color-primary) text-(--color-primary-foreground)"
                : "text-(--color-muted-foreground) hover:bg-(--color-muted)",
            )}
          >
            <span lang="sa" className="text-sm">
              अ
            </span>
          </button>
          <button
            type="button"
            onClick={() => switchMode("en")}
            aria-pressed={mode === "en"}
            title="Type normally (English / other)"
            className={cn(
              "border-l border-(--color-border) px-2.5 py-1",
              mode === "en"
                ? "bg-(--color-primary) text-(--color-primary-foreground)"
                : "text-(--color-muted-foreground) hover:bg-(--color-muted)",
            )}
          >
            A
          </button>
        </div>

        {mode === "dev" && (
          <span className="text-xs text-(--color-muted-foreground)">
            Type in English letters (e.g. <code className="font-mono">vidyaa</code>)
          </span>
        )}

        <DevanagariHelp className="ml-auto" />
      </div>

      {mode === "dev" && roman.trim() !== "" && (
        <div className="rounded-md border border-(--color-border) bg-(--color-muted) px-3 py-2 text-sm">
          <span className="mr-1 text-xs text-(--color-muted-foreground)">
            Will submit:
          </span>
          <span lang="sa" className="text-base">
            {preview}
          </span>
        </div>
      )}
    </div>
  );
}
