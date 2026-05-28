import { Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useMascotState, useUpdateMascot } from "@/lib/queries";

/**
 * Stage 5 reversal affordance — a small dashboard hint that lets
 * a learner bring the Dhananjaya mascot back if it is currently disabled.
 *
 * Renders ONLY when the mascot is currently disabled, so once the
 * learner has re-enabled the companion this component disappears and
 * stops competing for dashboard real estate. The placement (just
 * below the practice card on the learner dashboard) was chosen
 * because that's where learners spend the most time.
 *
 * Note: the persistent off-switch was removed from MascotCompanion (it
 * read as "turn off a person", which is wrong). This hint is kept for
 * legacy users whose mascot is disabled from earlier — it gives them a
 * one-click path to re-enable. New learners default to enabled.
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
          Dhananjaya is currently hidden. Want the companion back as you practise?
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
          "Bring Dhananjaya back"
        )}
      </Button>
    </div>
  );
}
