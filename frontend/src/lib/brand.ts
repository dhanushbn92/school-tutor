/**
 * Centralised brand identity for the platform.
 *
 * Why a constants module: the product name, the tagline, the philosophy
 * quotes and the colour palette of the arrows logo all need to land in
 * exactly the same way across the Shell, Login, Signup pages, the
 * Dashboard hero and the index.html <title>. A single source of truth
 * means renaming or retuning happens in one place.
 *
 * The arrow palette is the reference image the design ask was rooted
 * in — multi-coloured arrows pointing up and forward. We re-use that
 * palette across the logo, the hero accents and the archer animation
 * so the whole brand feels cohesive.
 */

export const BRAND_NAME = "Dhananjaya";

/** Short subtitle used under the logo in the sidebar / login chrome. */
export const BRAND_TAGLINE = "Practice. Master. Conquer.";

/**
 * Longer philosophy line shown on the dashboard hero. The verb "again"
 * is intentional — the platform is built around repeated, low-friction
 * practice cycles rather than one-shot tests.
 */
export const BRAND_PHILOSOPHY = "Practice, again. And again. Mastery is just repetition refined.";

/**
 * Quotes shown in the rotating philosophy banner on the dashboard hero.
 * Kept short so they read at a glance; mixed Sanskrit-tinged sayings and
 * plain-English encouragements so it doesn't feel like a single voice.
 */
export const BRAND_QUOTES: ReadonlyArray<{ text: string; attribution?: string }> = [
  { text: "Practice makes a person perfect — and practice again makes them unstoppable." },
  { text: "Abhyāsa eva sarva-siddhi-mūlam — Practice is the root of all attainment.", attribution: "Sanskrit" },
  { text: "The arrow doesn't ask the bow how far. It simply trusts the draw, the aim, the release." },
  { text: "Do it once for the answer. Do it ten times for the understanding. Do it a hundred times for the mastery." },
  { text: "Yogaḥ karmasu kauśalam — Skill in action is the very definition of yoga.", attribution: "Bhagavad Gita 2.50" },
  { text: "Every quiz is another arrow drawn. Every review is the bowstring tightening." },
];

/**
 * The arrow palette used by BrandLogo and VidyarthiArcher. Listed in
 * the visual order they appear in the reference image: the big navy
 * lead arrow at the top-right, with the others scattered around it.
 */
export const BRAND_ARROW_COLORS = {
  navy: "#0E2A4D",       // the lead arrow; matches the primary navy tone
  green: "#3AB54A",      // bright green
  orange: "#F36C21",     // warm orange
  purple: "#A04CC9",     // soft violet
  teal: "#7FA9A4",       // dusty teal
  yellow: "#F7DD2A",     // bright yellow
  magenta: "#E1338F",    // hot pink
  gray: "#6E7A82",       // neutral slate
} as const;
