import logoUrl from "@/assets/brand-logo.png";
import { BRAND_NAME } from "@/lib/brand";
import { cn } from "@/lib/utils";

/**
 * The Dhananjaya brand mark — an open book, a swoosh of practice rising
 * out of it, and an arrow landing in the bullseye, inside a rounded
 * frame. Learn, practise, hit the goal.
 *
 * The artwork is the approved logo image (src/assets/brand-logo.png),
 * used as-is so it matches the approved design exactly. The same image
 * provides the browser-tab icon (public/favicon.png and
 * apple-touch-icon.png).
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
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <img
        src={logoUrl}
        width={size}
        height={size}
        alt={`${BRAND_NAME} logo`}
        className="shrink-0 object-contain"
        draggable={false}
      />
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
