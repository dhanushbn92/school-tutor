import { type ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Shared "themed" primitives that carry the platform's visual language
 * (subject-coloured top stripe, soft corner blob, rounded-2xl card,
 * decorative title mark) across every page.
 *
 * Pages that have a subject context (chapter Learn, subject browse,
 * etc.) pass the resolved subject colour. Pages without a subject
 * (Dashboard, Content library, Assessments list) pass nothing — the
 * primitives default to `--color-primary` so the design language stays
 * consistent across the whole platform.
 */

const PRIMARY = "var(--color-primary)";

/**
 * Card surface with the platform's signature decorations:
 *   - 1-3px gradient top stripe (subject or primary colour)
 *   - Soft blurred corner blob in the same colour
 *   - rounded-2xl, shadow-md base
 *
 * Drop-in replacement for `<Card>` on any content surface that wants
 * to feel "designed". Use sparingly on dense list pages — overusing it
 * makes the page busy.
 */
export function ThemedSection({
  themeColor = PRIMARY,
  children,
  className,
}: {
  themeColor?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Card
      className={cn(
        "relative overflow-hidden rounded-2xl border-(--color-border) shadow-md",
        className,
      )}
    >
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-1"
        style={{
          background: `linear-gradient(90deg, ${themeColor}, color-mix(in oklab, ${themeColor} 70%, black), ${themeColor})`,
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full opacity-20 blur-2xl"
        style={{ background: themeColor }}
      />
      <div className="relative">{children}</div>
    </Card>
  );
}

/**
 * Small coloured square + dot rendered inline before a CardTitle. Ties
 * every section title to the page's identity — same shape language as
 * the larger icon tiles in the hero, scaled down.
 *
 * Use inside CardTitle: `<CardTitle className="flex items-center">
 *   <ThemedTitleMark /> Section name
 * </CardTitle>`
 */
export function ThemedTitleMark({
  themeColor = PRIMARY,
}: {
  themeColor?: string;
}) {
  return (
    <span
      aria-hidden
      className="mr-2.5 inline-flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg align-text-bottom"
      style={{
        background: `linear-gradient(135deg, ${themeColor}, color-mix(in oklab, ${themeColor} 70%, black))`,
      }}
    >
      <span className="h-2 w-2 rounded-full bg-white opacity-90" />
    </span>
  );
}

/**
 * Page-level wrapper that applies the platform's tinted canvas + dot
 * grid texture across the whole route content area. Replaces the bare
 * `<div>` that most pages used to wrap their content.
 *
 * - Spans edge-to-edge via negative margins (the route container has
 *   matching positive padding)
 * - Soft tinted gradient that fades through the page (never reaches
 *   pure white) so cards always sit on a coloured canvas
 * - Subtle dot grid in the theme colour at low opacity gives the page
 *   a paper-grain feel
 *
 * Pages with a subject context pass `themeColor`; everywhere else uses
 * the default primary blue so the platform reads as one app.
 */
export function ThemedPage({
  themeColor = PRIMARY,
  children,
  className,
}: {
  themeColor?: string;
  children: ReactNode;
  className?: string;
}) {
  // For inline `style` we need a CSS expression that resolves the
  // soft variant. We can't always pull from `--color-subject-X-soft`
  // (the caller might pass a raw oklch literal), so we synthesize a
  // soft tint via color-mix at usage time.
  const soft = `color-mix(in oklab, ${themeColor} 12%, white)`;
  const softer = `color-mix(in oklab, ${themeColor} 5%, white)`;
  const softest = `color-mix(in oklab, ${themeColor} 3%, white)`;

  return (
    <div className={cn("-mx-4 -my-4 md:-mx-6 md:-my-6", className)}>
      <div
        className="relative min-h-screen px-4 py-4 md:px-6 md:py-6"
        style={{
          // Stronger tint at top fading through the page to a very
          // light wash — never to pure white. Keeps every scroll
          // position visually subject- (or primary-) themed.
          background: `linear-gradient(180deg, ${soft} 0%, ${softer} 600px, ${softest} 100%)`,
        }}
      >
        {/* Page-wide dot grid in the theme colour, very low opacity. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-30"
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, color-mix(in oklab, ${themeColor} 25%, transparent) 1px, transparent 0)`,
            backgroundSize: "32px 32px",
          }}
        />
        <div className="relative">{children}</div>
      </div>
    </div>
  );
}
