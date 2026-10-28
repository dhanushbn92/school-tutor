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

/**
 * Colours of the logo, for surfaces that sit beside it (the navy purpose
 * card and its orange call to action on the learner home page).
 */
export const BRAND_NAVY = "#0E2A4D";
export const BRAND_ORANGE = "#F7931E";
