import { Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useMascotState, useUpdateMascot } from "@/lib/queries";

/**
 * Stage 5 reversal affordance — a small dashboard hint that lets
 * a learner bring the Vidyārthi mascot back after they previously
 * disabled it via the off switch.
 *
 * Renders ONLY when the mascot is currently disabled, so once the
 * learner has re-enabled the companion this component disappears and
 * stops competing for dashboard real estate. The placement (just
 * below the practice card on the learner dashboard) was chosen
 * because that's where learners spend the most time and where they'll
 * naturally look if they remember "I turned that thing off".
 */
export function MascotToggleHint() {
  const mascotQ = useMascotState();
  const updateMascot = useUpdateMascot();

  // Don't render while we're still figuring out the current state —
  // an optimistic render here would briefly show "bring it back" on
  // every dashboard load before the query resolves. Loading is fine
  // because the rest of the dashboard is already showing useful
  // content; the hint isn't load-bearing.
  if (!mascotQ.data) return null;
  if (mascotQ.data.enabled) return null;

  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-md border border-dashed border-(--color-border) bg-(--color-card) px-4 py-3 text-sm">
      <div className="flex items-center gap-2 text-(--color-muted-foreground)">
        <Sparkles className="h-4 w-4 text-(--color-primary)" />
        <span>
          Vidyārthi is currently off. Want the mascot back as you practise?
        </span>
      </div>
      <Button
        size="sm"
        variant="outline"
        onClick={() => updateMascot.mutate({ enabled: true })}
        disabled={updateMascot.isPending}
      >
        {updateMascot.isPending ? (
          <>
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Bringing back…
          </>
        ) : (
          "Bring Vidyārthi back"
        )}
      </Button>
    </div>
  );
}
