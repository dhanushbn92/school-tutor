import { BRAND_ARROW_COLORS, BRAND_NAME } from "@/lib/brand";
import { cn } from "@/lib/utils";

/**
 * The Dhananjaya brand mark — a tight cluster of stylised arrows
 * pointing up-and-forward, echoing the reference image the design ask
 * was rooted in: one big lead arrow with smaller arrows trailing in
 * formation.
 *
 * The shape language is the "shoulder + shaft" arrow from the reference:
 * an L-bend that suggests forward motion AND ascent at once. Each arrow
 * is a single path so the SVG is small (under 2 KB) and crisp at any
 * size.
 *
 * Two variants:
 *   - `<BrandLogo />`        — icon only, square. Use in tight chrome.
 *   - `<BrandLogo withText />` — icon + Dhananjaya wordmark. Use in
 *                                sidebars and login chrome.
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
  // 100x100 viewBox keeps the math readable. The "shoulder arrow" path
  // is reused via <use> with transform per arrow, so colour and position
  // are independent variables.
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
            One arrow definition, reused via <use>. The shape is an
            L-bend pointing up-and-right: shaft starts mid-left, bends
            up at the shoulder, and ends in a chevron arrowhead.
            Reference: the multi-colour arrows in the design ask.
          */}
          <path
            id="dh-arrow"
            d="
              M 0 22
              L 14 22
              L 14 14
              L 24 14
              L 24 0
              L 36 0
              L 36 6
              L 30 6
              L 30 14
              L 24 14
              L 24 22
              L 22 22
              L 22 30
              L 0 30
              Z
              M 30 0
              L 36 0
              L 36 6
              Z
            "
          />
        </defs>

        {/* The big lead arrow — navy, top-right, larger than the rest. */}
        <use href="#dh-arrow" transform="translate(52 16) scale(1.25)" fill={C.navy} />

        {/* Smaller arrows trailing in a loose formation. The transforms
            roughly recreate the spatial vibe of the reference: a couple
            on the left, a couple on the bottom, one yellow above the
            lead arrow. */}
        <use href="#dh-arrow" transform="translate(10 36) scale(0.7)" fill={C.orange} />
        <use href="#dh-arrow" transform="translate(34 14) scale(0.45)" fill={C.magenta} />
        <use href="#dh-arrow" transform="translate(44 4)  scale(0.4)"  fill={C.yellow} />
        <use href="#dh-arrow" transform="translate(20 56) scale(0.5)"  fill={C.teal} />
        <use href="#dh-arrow" transform="translate(8 70)  scale(0.55)" fill={C.navy} opacity="0.85" />
        <use href="#dh-arrow" transform="translate(34 68) scale(0.85)" fill={C.green} />
        <use href="#dh-arrow" transform="translate(68 60) scale(0.7)"  fill={C.purple} />
        <use href="#dh-arrow" transform="translate(74 36) scale(0.4)"  fill={C.gray} />
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
