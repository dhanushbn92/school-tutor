import { type ReactNode } from "react";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { EmptyScene, type EmptySceneName } from "./empty-scene";

/**
 * Standardised empty state — used across the app whenever a list / panel
 * has no rows to show.
 *
 * Visual structure:
 *
 *           · · · · · · · · ·          ← dashed decorative halo
 *         ·                   ·
 *        ·    ┌─────────┐      ·
 *         ·   │  scene  │     ·       ← scene illustration OR icon
 *        ·    └─────────┘      ·         (scene if `scene` prop given)
 *         ·                   ·
 *           · · · · · · · · ·
 *
 *           Title text here              ← display font, h3-weight
 *           Optional description
 *
 *           [ optional action ]
 *
 * Two illustration paths:
 *   - Pass `scene="books"` (or any EmptySceneName) → renders a bigger
 *     abstract SVG illustration in the centre. Friendlier and more
 *     specific — recommended for high-traffic empty states.
 *   - Pass nothing or pass `icon={<Foo />}` → renders the icon (or
 *     default Sparkles) in a soft tinted circle. Compact, generic.
 *
 * The optional `accent` prop tints the scene illustration to match the
 * surrounding subject theme. Falls back to `--color-primary` if absent.
 */
export function Empty({
  title,
  description,
  icon,
  scene,
  accent,
  action,
  className,
}: {
  title: string;
  description?: string;
  icon?: ReactNode;
  /** Abstract SVG illustration name. Takes precedence over `icon`. */
  scene?: EmptySceneName;
  /** Colour string used to tint the scene (e.g. a subject theme). */
  accent?: string;
  action?: ReactNode;
  className?: string;
}) {
  // Sparkles is a friendly, neutral default — works equally well for "no
  // worksheets yet" and "no notes yet". Callers that want a more specific
  // glyph keep passing `icon` explicitly and override the default.
  const renderedIcon = icon ?? <Sparkles className="h-6 w-6" />;

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl border border-dashed border-(--color-border) px-6 py-12 text-center",
        className,
      )}
    >
      {scene ? (
        // Big illustrated scene — no halo, the SVG IS the focal point.
        // Sized at 28 (112px) so the illustration breathes; smaller
        // and the geometric details get muddy.
        <div className="mb-5 h-28 w-28">
          <EmptyScene name={scene} accent={accent} className="h-full w-full" />
        </div>
      ) : (
        <div className="relative mb-4 flex h-20 w-20 items-center justify-center">
          <svg
            className="absolute inset-0 text-(--color-border)"
            viewBox="0 0 80 80"
            aria-hidden="true"
          >
            <circle
              cx="40"
              cy="40"
              r="38"
              fill="none"
              stroke="currentColor"
              strokeWidth="1"
              strokeDasharray="3 5"
            />
          </svg>
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[color-mix(in_oklab,var(--color-primary)_10%,transparent)] text-(--color-primary)">
            {renderedIcon}
          </div>
        </div>
      )}
      <h4 className="text-base font-semibold tracking-tight md:text-lg">
        {title}
      </h4>
      {description && (
        <p className="mt-2 max-w-md text-sm text-(--color-muted-foreground) md:text-base">
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
