import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  icon,
  sub,
  intent = "default",
  className,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  icon?: ReactNode;
  intent?: "default" | "success" | "warning" | "danger";
  className?: string;
}) {
  const intentClass = {
    default: "text-(--color-primary) bg-[color-mix(in_oklab,var(--color-primary)_10%,transparent)]",
    success: "text-(--color-success) bg-[color-mix(in_oklab,var(--color-success)_14%,transparent)]",
    warning: "text-(--color-warning) bg-[color-mix(in_oklab,var(--color-warning)_14%,transparent)]",
    danger: "text-(--color-destructive) bg-[color-mix(in_oklab,var(--color-destructive)_14%,transparent)]",
  }[intent];
  return (
    <Card className={cn("flex items-start gap-4 p-5", className)}>
      {icon && (
        <div className={cn("flex h-11 w-11 items-center justify-center rounded-md", intentClass)}>
          {icon}
        </div>
      )}
      <div className="flex-1">
        <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
          {label}
        </div>
        <div className="mt-1 text-2xl font-semibold leading-none">{value}</div>
        {sub && <div className="mt-1 text-xs text-(--color-muted-foreground)">{sub}</div>}
      </div>
    </Card>
  );
}
