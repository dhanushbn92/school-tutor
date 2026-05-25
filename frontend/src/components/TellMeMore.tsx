import { useState } from "react";
import {
  AlertCircle,
  BookOpen,
  Layers,
  Lightbulb,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useExplainTier } from "@/lib/queries";
import type { ExplanationTier, ExtendedExplanation } from "@/lib/types";
import { ReadAloudButton } from "@/components/ReadAloudButton";

/**
 * "Tell me more" chain — Stage 3 of the child-centric roadmap.
 *
 * Three escalating chips beneath every revealed explanation:
 *   1. Deeper — unpacks the reasoning step by step
 *   2. Analogy — relatable everyday parallel
 *   3. Worked example — fresh problem at the same concept
 *
 * Each chip lazy-loads its tier from the backend (cached forever per
 * question, so the second click is instant). Loaded tiers stay
 * expanded inline; collapsing a tier just hides the panel without
 * dropping the data, so reopening is instant. A request error shows
 * a tiny "try again" affordance instead of disappearing.
 *
 * Self-contained: pass a `question_id` and the component does the
 * rest. No store, no context, no parent prop drilling beyond that
 * one number.
 */
export function TellMeMore({ questionId }: { questionId: number }) {
  return (
    <div className="mt-3 flex flex-col gap-2">
      <div className="text-xs font-medium text-(--color-muted-foreground)">
        Want to go deeper?
      </div>
      <div className="flex flex-wrap gap-2">
        <TierBlock
          questionId={questionId}
          tier="DEEPER"
          label="Explain more"
          icon={<BookOpen className="h-3.5 w-3.5" />}
        />
        <TierBlock
          questionId={questionId}
          tier="ANALOGY"
          label="Give me an analogy"
          icon={<Lightbulb className="h-3.5 w-3.5" />}
        />
        <TierBlock
          questionId={questionId}
          tier="EXAMPLE"
          label="Show a worked example"
          icon={<Layers className="h-3.5 w-3.5" />}
        />
      </div>
    </div>
  );
}

/** A single tier chip + expandable panel. Owns its own load state
 *  so each tier can be clicked independently without stomping on
 *  the others. */
function TierBlock({
  questionId,
  tier,
  label,
  icon,
}: {
  questionId: number;
  tier: ExplanationTier;
  label: string;
  icon: React.ReactNode;
}) {
  const explain = useExplainTier();
  const [data, setData] = useState<ExtendedExplanation | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle() {
    if (data) {
      // Already loaded — just collapse / re-expand. Cached on the
      // frontend so a re-open is free.
      setOpen((o) => !o);
      return;
    }
    if (explain.isPending) return;
    setError(null);
    setOpen(true);
    explain.mutate(
      { question_id: questionId, tier },
      {
        onSuccess: (res) => setData(res),
        onError: (err) => {
          // The backend returns a friendly message on 503; surface
          // it verbatim. Other errors fall back to a generic.
          const detail =
            (err as { response?: { data?: { detail?: string } } })?.response
              ?.data?.detail;
          setError(
            typeof detail === "string"
              ? detail
              : "Couldn't load that right now — try again in a moment.",
          );
        },
      },
    );
  }

  return (
    <div className="w-full">
      <button
        type="button"
        onClick={toggle}
        disabled={explain.isPending && !data}
        className={
          "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition " +
          (open && data
            ? "border-(--color-primary) bg-(--color-primary)/10 text-(--color-primary)"
            : "border-(--color-border) hover:bg-(--color-muted)")
        }
      >
        {explain.isPending && !data ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          icon
        )}
        <span>{label}</span>
        {data && (
          <Sparkles className="h-3 w-3 text-(--color-primary)" aria-hidden="true" />
        )}
      </button>

      {open && data && (
        <div className="mt-2 rounded-md border border-(--color-border) bg-(--color-muted)/40 p-3 text-sm leading-relaxed text-(--color-foreground)">
          <div className="flex items-start gap-2">
            <div className="flex-1 whitespace-pre-line">{data.text}</div>
            <ReadAloudButton text={data.text} label="Read this aloud" />
          </div>
        </div>
      )}
      {open && error && (
        <div className="mt-2 flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <div className="flex-1">
            {error}
            <button
              type="button"
              className="ml-2 underline-offset-2 hover:underline"
              onClick={() => {
                setError(null);
                toggle();
              }}
            >
              Try again
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
