import type { ReactNode } from "react";

/**
 * The standard page hero used across the app.
 *
 * Visual structure:
 *
 *   ┌──────────────────────────────────────────────────────┐
 *   │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │  ← top stripe
 *   │  ◯                                                   │
 *   │     EYEBROW (optional, uppercase)                    │
 *   │     Title                          [ actions row ]   │
 *   │     Description (muted, max 2xl wide)                │
 *   │                                            ◯ ← blob │
 *   └──────────────────────────────────────────────────────┘
 *
 * The panel carries the platform's signature decorations:
 *   - 3px gradient top stripe in `--color-primary` so every page reads
 *     as part of the platform without subject context
 *   - Soft blurred corner blob in the corner — matches the hero blobs
 *     used on subject/chapter heroes
 *   - Subtle dot-grid texture inside the panel for paper feel
 *   - Bigger title + display font (cascaded from index.css)
 *
 * Pages that own their own subject-themed hero (Learn / LearnSubject /
 * LearnChapter) skip this component entirely — those carry their own
 * coloured banners. Everywhere else gets a unified look.
 *
 * Backwards compatible: existing call-sites pass only title /
 * description / actions — the new `eyebrow` prop is optional.
 */
export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  /**
   * Optional uppercase context label rendered above the title — used
   * for breadcrumb-style hints like "ASSESSMENTS · QUIZ" or "CLASS 8".
   * Stays out of the way when not supplied.
   */
  eyebrow?: ReactNode;
}) {
  return (
    <div className="relative mb-6 overflow-hidden rounded-2xl border border-(--color-border) bg-(--color-card) shadow-md md:mb-8">
      {/* Top gradient stripe — 3px, in the platform primary. Same
          visual marker used by ThemedSection across the app. */}
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-1"
        style={{
          background:
            "linear-gradient(90deg, var(--color-primary), color-mix(in oklab, var(--color-primary) 70%, black), var(--color-primary))",
        }}
      />
      {/* Soft corner blob — same shape language as subject heroes. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full opacity-20 blur-2xl"
        style={{ background: "var(--color-primary)" }}
      />
      {/* Subtle dot grid texture. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-30"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, color-mix(in oklab, var(--color-primary) 25%, transparent) 1px, transparent 0)",
          backgroundSize: "28px 28px",
        }}
      />
      {/* Soft diagonal wash — primary at ~6% opacity, fades to
          transparent. Adds warmth without dominating. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "linear-gradient(135deg, color-mix(in oklab, var(--color-primary) 6%, transparent), transparent 60%)",
        }}
      />
      <div className="relative px-5 py-5 md:px-7 md:py-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            {eyebrow && (
              <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-(--color-muted-foreground)">
                {eyebrow}
              </div>
            )}
            <h1 className="text-2xl font-bold leading-tight md:text-3xl">
              {title}
            </h1>
            {description && (
              <p className="mt-1.5 max-w-2xl text-sm text-(--color-muted-foreground) md:text-base">
                {description}
              </p>
            )}
          </div>
          {actions && (
            <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>
          )}
        </div>
      </div>
    </div>
  );
}
