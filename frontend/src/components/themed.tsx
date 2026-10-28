import { type ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Shared page primitives. They used to carry a tinted canvas, a dot grid, a
 * coloured top stripe and glow blobs; the app now uses one flat, calm look
 * (as on the learner home page), so these are thin wrappers. The `themeColor`
 * prop is still accepted so existing call sites keep compiling, and is used
 * only for the small title mark.
 */

const PRIMARY = "var(--color-primary)";

/** A rounded content card. */
export function ThemedSection({
  children,
  className,
}: {
  themeColor?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("overflow-hidden rounded-2xl border-(--color-border)", className)}>
      {children}
    </Card>
  );
}

/**
 * Small coloured square + dot rendered inline before a CardTitle, tying a
 * section title to the page's identity.
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
      style={{ background: themeColor }}
    >
      <span className="h-2 w-2 rounded-full bg-white opacity-90" />
    </span>
  );
}

/** Page-level wrapper: the page content on the shell's own background. */
export function ThemedPage({
  children,
  className,
}: {
  themeColor?: string;
  children: ReactNode;
  className?: string;
}) {
  return <div className={className}>{children}</div>;
}
