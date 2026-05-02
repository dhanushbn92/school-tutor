/**
 * Abstract SVG scene illustrations for the Empty component.
 *
 * Each scene is a small inline SVG (<2 KB) using the surrounding
 * `currentColor` for line work + the `accent` prop for the focal
 * shape. Designed to read as friendly geometric collages rather than
 * literal drawings, so they feel original and don't need licensing.
 *
 * Naming follows the kind of thing the panel says is missing:
 *   - "books"      → stack of papers / pages (worksheets, summaries)
 *   - "spark"      → a small explosion of dots and lines (no data yet)
 *   - "telescope"  → a chevron + dots sweeping outward (visuals)
 *   - "trophy"     → tiered shape with a star (tests / assessments)
 *   - "puzzle"     → connected geometric blocks (activities)
 *   - "compass"    → circle with a directional triangle (no chapters)
 *   - "leaf"       → curved shape (extras, generic)
 *
 * Callers pass `accent` (a colour string) so the illustration can pick
 * up the surrounding subject theme — e.g. green leaf for science,
 * violet for English. Defaults to `--color-primary` if not provided.
 */
export type EmptySceneName =
  | "books"
  | "spark"
  | "telescope"
  | "trophy"
  | "puzzle"
  | "compass"
  | "leaf";

export function EmptyScene({
  name,
  accent,
  className,
}: {
  name: EmptySceneName;
  accent?: string;
  className?: string;
}) {
  const fill = accent ?? "var(--color-primary)";
  // Soft tint of the accent for the secondary shape — `color-mix` keeps
  // it readable against any background.
  const fillSoft = accent
    ? `color-mix(in oklab, ${accent} 30%, transparent)`
    : "color-mix(in oklab, var(--color-primary) 30%, transparent)";

  switch (name) {
    case "books":
      // Stack of three rounded papers, slightly fanned. Suggests
      // worksheets / reading material in a friendly way.
      return (
        <svg
          viewBox="0 0 96 96"
          className={className}
          fill="none"
          aria-hidden="true"
        >
          <rect
            x="14"
            y="32"
            width="60"
            height="46"
            rx="6"
            fill={fillSoft}
            transform="rotate(-6 14 32)"
          />
          <rect
            x="22"
            y="28"
            width="60"
            height="46"
            rx="6"
            fill={fillSoft}
          />
          <rect
            x="20"
            y="20"
            width="56"
            height="46"
            rx="6"
            fill={fill}
          />
          <rect x="28" y="32" width="40" height="3" rx="1.5" fill="white" opacity="0.85" />
          <rect x="28" y="40" width="32" height="3" rx="1.5" fill="white" opacity="0.7" />
          <rect x="28" y="48" width="36" height="3" rx="1.5" fill="white" opacity="0.55" />
        </svg>
      );

    case "spark":
      // A bold central circle ringed by dashes and small dots —
      // reads as "spark of an idea" or generic placeholder.
      return (
        <svg
          viewBox="0 0 96 96"
          className={className}
          fill="none"
          aria-hidden="true"
        >
          <circle cx="48" cy="48" r="14" fill={fill} />
          <circle cx="48" cy="48" r="22" fill="none" stroke={fillSoft} strokeWidth="2" strokeDasharray="3 4" />
          <circle cx="78" cy="32" r="3" fill={fill} />
          <circle cx="22" cy="38" r="2.5" fill={fillSoft} />
          <circle cx="74" cy="68" r="2.5" fill={fillSoft} />
          <circle cx="20" cy="68" r="3" fill={fill} />
          <circle cx="50" cy="14" r="2" fill={fillSoft} />
          <circle cx="50" cy="84" r="2" fill={fillSoft} />
        </svg>
      );

    case "telescope":
      // Three growing chevrons radiating outward — used when a tab
      // promises visuals/diagrams that haven't been generated.
      return (
        <svg
          viewBox="0 0 96 96"
          className={className}
          fill="none"
          aria-hidden="true"
        >
          <path d="M 18 78 L 32 64 L 46 78" stroke={fillSoft} strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M 24 60 L 42 42 L 60 60" stroke={fillSoft} strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M 32 38 L 52 18 L 72 38" stroke={fill} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="78" cy="20" r="5" fill={fill} />
        </svg>
      );

    case "trophy":
      // Tiered podium shape with a star on top — used for tests /
      // assessments empty states.
      return (
        <svg
          viewBox="0 0 96 96"
          className={className}
          fill="none"
          aria-hidden="true"
        >
          <rect x="20" y="62" width="56" height="20" rx="3" fill={fillSoft} />
          <rect x="32" y="42" width="32" height="20" rx="3" fill={fill} />
          <path
            d="M 48 14 L 52 26 L 64 26 L 54 33 L 58 45 L 48 38 L 38 45 L 42 33 L 32 26 L 44 26 Z"
            fill={fill}
          />
        </svg>
      );

    case "puzzle":
      // Two interlocking rounded squares — activities / something
      // collaborative that pieces together.
      return (
        <svg
          viewBox="0 0 96 96"
          className={className}
          fill="none"
          aria-hidden="true"
        >
          <rect x="14" y="20" width="36" height="36" rx="6" fill={fillSoft} />
          <rect x="46" y="40" width="36" height="36" rx="6" fill={fill} />
          <circle cx="50" cy="38" r="6" fill={fill} />
          <circle cx="46" cy="56" r="5" fill={fillSoft} />
        </svg>
      );

    case "compass":
      // Circle with a diamond rose inside — generic "you're early"
      // / "no chapters yet" sort of empty state.
      return (
        <svg
          viewBox="0 0 96 96"
          className={className}
          fill="none"
          aria-hidden="true"
        >
          <circle cx="48" cy="48" r="32" fill="none" stroke={fillSoft} strokeWidth="3" />
          <path
            d="M 48 22 L 54 48 L 48 74 L 42 48 Z"
            fill={fill}
          />
          <path
            d="M 22 48 L 48 42 L 74 48 L 48 54 Z"
            fill={fillSoft}
          />
          <circle cx="48" cy="48" r="4" fill={fill} />
        </svg>
      );

    case "leaf":
      // A simple curved leaf — calm, generic positive vibe. Good
      // for "extras coming soon" or "no notes yet".
      return (
        <svg
          viewBox="0 0 96 96"
          className={className}
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M 26 70 Q 16 40 48 18 Q 80 30 70 64 Q 58 80 26 70 Z"
            fill={fill}
          />
          <path
            d="M 30 66 Q 36 50 56 38"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
            opacity="0.75"
            fill="none"
          />
        </svg>
      );

    default:
      return null;
  }
}
