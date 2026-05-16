import { BRAND_ARROW_COLORS, BRAND_NAME } from "@/lib/brand";
import { cn } from "@/lib/utils";

/**
 * The Dhananjaya brand mark — a flock of L-bend arrows surging up
 * and to the right behind a bold navy leader.
 *
 * Shape language
 *   Each arrow is the "L-bend" silhouette from the reference image:
 *   a horizontal tail joins a vertical riser at a hard right-angle,
 *   topped with a chevron arrowhead. That distinctive corner is what
 *   gives the mark personality — without it the arrows are generic.
 *
 * Composition
 *   - One bold lead arrow (navy) sits forward and largest.
 *   - Two mid-size followers (green + orange) trail close behind it.
 *   - Three small accent arrows (purple, teal, yellow) scatter in
 *     formation, adding colour and density without competing with
 *     the lead.
 *   - The whole group is rotated 22 deg clockwise so the arrows
 *     lean into their direction of travel — the visual cue that
 *     reads as "effort" rather than "frozen". A static, upright
 *     arrow is at rest; a tilted one is in motion.
 *
 * Why it stays legible small
 *   The lead arrow dominates the silhouette. Even at 24-32 px the
 *   navy shape is the primary read; the smaller arrows register as
 *   colour flecks adding texture rather than as distinct objects.
 *   So the mark still works as a favicon while gaining body at
 *   logo size.
 *
 * Two variants:
 *   <BrandLogo />          — icon only, square.
 *   <BrandLogo withText /> — icon + Dhananjaya wordmark.
 */
export function BrandLogo({
  withText = false,
  size = 32,
  className,
}: {
  withText?: boolean;
  size?: number;
  className?: string;
}) {
  const C = BRAND_ARROW_COLORS;
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        xmlns="http://www.w3.org/2000/svg"
        aria-label={`${BRAND_NAME} logo`}
        role="img"
      >
        <defs>
          {/*
            The L-bend arrow.
            - Horizontal tail:  x = 10..50, y = 75..90   (width 40, height 15)
            - Vertical riser:   x = 50..70, y = 25..90   (width 20, height 65)
            - Chevron head:     base from x = 30 to x = 90 at y = 25,
                                tip at (60, 5)
            The shape is built as a single filled polygon — no strokes,
            no curves — so it stays crisp at any size and renders
            identically on every browser.
          */}
          <path
            id="dh-arrow"
            d="M 10 75 L 50 75 L 50 25 L 30 25 L 60 5 L 90 25 L 70 25 L 70 90 L 10 90 Z"
          />
        </defs>

        {/*
          Whole formation tilted 22 deg clockwise. The tilt is the
          single most important detail for the "effort" feeling — it
          makes the arrows look like they're leaning into a run
          rather than standing at attention.
        */}
        <g transform="rotate(22 50 50)">
          {/* Lead arrow — navy, biggest, forward of the pack. */}
          <use href="#dh-arrow" transform="translate(28 -6) scale(0.66)" fill={C.navy} />

          {/* Green follower — second largest, just behind and below
              the lead. The slight stagger reads as "chasing". */}
          <use href="#dh-arrow" transform="translate(8 30) scale(0.48)" fill={C.green} />

          {/* Orange follower — back-left, smaller still. */}
          <use href="#dh-arrow" transform="translate(-6 8) scale(0.34)" fill={C.orange} />

          {/* Purple accent — front-right, lower than the lead so it
              fills the gap between lead and the rear of the flock. */}
          <use href="#dh-arrow" transform="translate(50 48) scale(0.30)" fill={C.purple} />

          {/* Teal accent — lower-left, ground-floor of the flock. */}
          <use href="#dh-arrow" transform="translate(0 55) scale(0.24)" fill={C.teal} />

          {/* Yellow flash — tiny, tucked beside the lead. Adds a
              pop of brightness without competing for attention. */}
          <use href="#dh-arrow" transform="translate(58 0) scale(0.16)" fill={C.yellow} />
        </g>
      </svg>
      {withText && (
        <span className="flex flex-col leading-tight">
          <span className="font-display text-base font-semibold tracking-tight text-(--color-foreground)">
            {BRAND_NAME}
          </span>
        </span>
      )}
    </span>
  );
}
