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

type SubjectThemeKey =
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
    "data entry operations",
    "data entry operations (deo)",
    "statistics",
    "applied mathematics",
  ],
  science: [
    "science",
    "science and technology",
    "science & technology",
    "environmental science",
    "environmental studies",
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
    "painting",
    "indian culture and heritage",
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
function subjectIcon(theme: SubjectThemeKey): LucideIcon {
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
 * Static theme-to-icon lookup. Rendering `const Icon = SUBJECT_ICONS[theme]`
 * keeps React's compiler lint happy (calling `subjectIcon()` in a component
 * body reads as creating a component during render).
 */
export const SUBJECT_ICONS: Record<SubjectThemeKey, LucideIcon> = {
  math: subjectIcon("math"),
  science: subjectIcon("science"),
  social: subjectIcon("social"),
  english: subjectIcon("english"),
  indian: subjectIcon("indian"),
  arts: subjectIcon("arts"),
  default: subjectIcon("default"),
};

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
