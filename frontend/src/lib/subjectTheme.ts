/**
 * Subject theming — maps a free-form CBSE subject name onto one of six
 * colour families and a representative icon.
 *
 * Why grouping (not one colour per subject)?
 *   The NCERT catalogue exposes ~30 distinct subject names (Physics,
 *   Sangeet, Knowledge Traditions Practices of India, …). Giving each its
 *   own hue would be visually noisy and indistinguishable in a list. Six
 *   families on a well-spaced OKLCH wheel reads cleanly at small sizes and
 *   makes Math look obviously different from English at a glance.
 *
 * Tokens live in `index.css` as `--color-subject-<theme>` and
 * `--color-subject-<theme>-foreground`. Use {@link subjectStyle} to get
 * inline CSS variables that any consuming component can `bg-` against, or
 * read the theme directly via {@link subjectTheme} to make a typed switch.
 */

import {
  Atom,
  BookOpen,
  BookText,
  Calculator,
  Globe,
  Languages,
  Palette,
  type LucideIcon,
} from "lucide-react";
import type { CSSProperties } from "react";

export type SubjectThemeKey =
  | "math"
  | "science"
  | "social"
  | "english"
  | "indian"
  | "arts"
  | "default";

// Lower-cased subject names that resolve to each theme. Matched on exact
// equality after lower-casing the input — no fuzzy matching, so add new
// variants as the catalogue grows. Keep all entries lower-case here.
const SUBJECT_GROUPS: Record<Exclude<SubjectThemeKey, "default">, string[]> = {
  math: [
    "math",
    "maths",
    "mathematics",
    "computer science",
    "informatics practices",
    "ict",
  ],
  science: [
    "science",
    "physics",
    "chemistry",
    "biology",
    "biotechnology",
    "health and physical education",
    "home science",
    "physical education and well being",
  ],
  social: [
    "social science",
    "social studies",
    "history",
    "geography",
    "political science",
    "economics",
    "business studies",
    "sociology",
    "psychology",
    "accountancy",
  ],
  english: [
    "english",
    "creative writing & translation",
    "creative writing and translation",
  ],
  indian: ["hindi", "sanskrit", "urdu"],
  arts: [
    "arts",
    "fine art",
    "sangeet",
    "vocational education",
    "knowledge traditions practices of india",
  ],
};

/**
 * Resolve a subject name (any casing, any whitespace) to a theme key.
 * Returns `"default"` if no group matches — callers don't need to special-
 * case unknown subjects; they'll get a neutral primary-tinted look.
 */
export function subjectTheme(name: string | null | undefined): SubjectThemeKey {
  if (!name) return "default";
  const normalised = name.trim().toLowerCase();
  for (const [key, group] of Object.entries(SUBJECT_GROUPS) as [
    Exclude<SubjectThemeKey, "default">,
    string[],
  ][]) {
    if (group.includes(normalised)) return key;
  }
  return "default";
}

/** Lucide icon glyph paired with each theme. Picked to read at 16–24 px. */
export function subjectIcon(theme: SubjectThemeKey): LucideIcon {
  switch (theme) {
    case "math":
      return Calculator;
    case "science":
      return Atom;
    case "social":
      return Globe;
    case "english":
      return BookText;
    case "indian":
      return Languages;
    case "arts":
      return Palette;
    case "default":
    default:
      return BookOpen;
  }
}

/**
 * Inline-style helper that exposes the theme's tokens as generic CSS custom
 * properties — `--theme`, `--theme-foreground`, `--theme-soft`. Components
 * can use these via inline `style` attributes (most reliable) or via
 * Tailwind v4 arbitrary-property syntax like `bg-(--theme)` (works only
 * when the cascade brings the variable down — prefer inline style for
 * consistent rendering).
 *
 * @example
 *   const t = subjectTheme(subject.name);
 *   <div style={{ background: subjectVar(t) }}>{subject.name}</div>
 */
export function subjectStyle(theme: SubjectThemeKey): CSSProperties {
  return {
    ["--theme" as string]: `var(--color-subject-${theme})`,
    ["--theme-foreground" as string]: `var(--color-subject-${theme}-foreground)`,
    ["--theme-soft" as string]: `var(--color-subject-${theme}-soft)`,
  };
}

/**
 * Direct CSS-var reference for the theme's vivid colour. Use in inline
 * `style` props for the most reliable rendering — bypasses any cascade
 * issues that `bg-(--theme)` Tailwind classes can hit.
 */
export function subjectVar(theme: SubjectThemeKey): string {
  return `var(--color-subject-${theme})`;
}

/** Foreground colour to pair with `subjectVar()` (white-ish for most). */
export function subjectVarForeground(theme: SubjectThemeKey): string {
  return `var(--color-subject-${theme}-foreground)`;
}

/** Very light tinted variant — for pale page backgrounds and soft chips. */
export function subjectVarSoft(theme: SubjectThemeKey): string {
  return `var(--color-subject-${theme}-soft)`;
}

/** Human label for the theme — useful for "Math · Science · Languages"
 *  groupings if we ever add a tabbed subject browser. Not used yet but kept
 *  here so the helper stays the single source of truth for subject UX. */
export function subjectThemeLabel(theme: SubjectThemeKey): string {
  switch (theme) {
    case "math":
      return "Math & Computing";
    case "science":
      return "Science & Health";
    case "social":
      return "Social Sciences";
    case "english":
      return "English";
    case "indian":
      return "Indian Languages";
    case "arts":
      return "Arts & Vocational";
    case "default":
    default:
      return "General";
  }
}
