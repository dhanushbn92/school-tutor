import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

/** A closed-by-default section: the content only mounts once it is opened. */
export function Disclosure({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex min-h-12 w-full items-center justify-between rounded-2xl border border-(--color-border) bg-(--color-card) px-5 py-3 text-left font-display text-base font-bold shadow-sm hover:bg-(--color-muted)"
      >
        {title}
        <ChevronDown
          className={cn("h-5 w-5 transition-transform", open && "rotate-180")}
          aria-hidden
        />
      </button>
      {open && <div className="mt-6">{children}</div>}
    </div>
  );
}
