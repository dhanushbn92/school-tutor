import type { HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-(--color-primary) text-(--color-primary-foreground)",
        secondary:
          "border-transparent bg-(--color-secondary) text-(--color-secondary-foreground)",
        outline: "border-(--color-border) text-(--color-foreground)",
        success:
          "border-transparent bg-[color-mix(in_oklab,var(--color-success)_18%,transparent)] text-(--color-success)",
        warning:
          "border-transparent bg-[color-mix(in_oklab,var(--color-warning)_18%,transparent)] text-(--color-warning)",
        destructive:
          "border-transparent bg-(--color-destructive) text-(--color-destructive-foreground)",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
