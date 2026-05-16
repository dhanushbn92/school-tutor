import { BRAND_ARROW_COLORS, BRAND_NAME } from "@/lib/brand";
import { cn } from "@/lib/utils";

/**
 * The Dhananjaya brand mark.
 *
 * The reference image was a flock of nine multi-colour arrows in
 * formation. Trying to recreate all nine arrows in a 24-48 px logo
 * read as visual noise — the small arrows blurred into specks. So
 * the production mark distils the reference down to its essence:
 *
 *   three chunky upward-pointing arrows in a stair-step formation,
 *   smallest at the bottom-left growing to a bold navy lead arrow at
 *   the top-right.
 *
 * The metaphor is the platform's pitch in one glance: each practice
 * cycle is another arrow rising further than the last. The shape is
 * a single filled polygon (no strokes, no curves) so it stays crisp
 * at any size and renders the same on every browser.
 *
 *   <BrandLogo />          — icon only.
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
  // A 100 × 100 viewBox keeps the per-arrow translate / scale numbers
  // easy to read. Each <use> is one filled polygon, so even at 24 px
  // the logo doesn't lose detail to anti-aliasing.
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
            Master arrow path. A chunky upward arrow with a strong
            triangular head:
              - head spans the top 45 % of the height (y = 5 .. 50)
              - shaft is centred, 30 units wide (x = 35 .. 65)
              - shaft fills the bottom 45 % of the height
            The result reads as a confident "↑" at every scale.
          */}
          <path id="dh-arrow" d="M 50 5 L 90 50 L 65 50 L 65 95 L 35 95 L 35 50 L 10 50 Z" />
        </defs>

        {/*
          All three arrows live inside a single <g> tilted slightly to
          the right — the arrows now look like they're in flight,
          carrying momentum, rather than statically planted. A 12°
          tilt is enough to suggest motion without making the lead
          arrow look unstable.
        */}
        <g transform="rotate(12 50 50)">
          {/* Smallest supporting arrow — orange, bottom-left. */}
          <use href="#dh-arrow" transform="translate(0 58) scale(0.32)" fill={C.orange} />

          {/* Mid supporting arrow — green, slightly above + right of orange. */}
          <use href="#dh-arrow" transform="translate(22 28) scale(0.46)" fill={C.green} />

          {/* Lead arrow — navy, top-right, biggest. */}
          <use href="#dh-arrow" transform="translate(43 -3) scale(0.62)" fill={C.navy} />
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
