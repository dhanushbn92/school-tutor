import type { ReactNode } from "react";

/**
 * The standard page heading used across the app: a flat title, an optional
 * description and an optional row of actions. It matches the learner home
 * page, so every page starts the same way.
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
   * Optional small context label rendered above the title, for
   * breadcrumb-style hints like "Assessments · Quiz". Stays out of the way
   * when not supplied.
   */
  eyebrow?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 md:mb-8 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        {eyebrow && (
          <div className="mb-1.5 text-xs font-semibold text-(--color-muted-foreground)">
            {eyebrow}
          </div>
        )}
        <h1 className="font-display text-2xl font-extrabold leading-tight tracking-tight md:text-3xl">
          {title}
        </h1>
        {description && (
          <p className="mt-1.5 max-w-2xl text-sm text-(--color-muted-foreground) md:text-base">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
