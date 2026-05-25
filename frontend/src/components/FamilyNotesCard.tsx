import { HeartHandshake, Loader2, X } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useDismissEncouragement, useMyEncouragements } from "@/lib/queries";
import { formatDateTime } from "@/lib/utils";

/**
 * "Notes from family" card — Stage 6 of the child-centric roadmap.
 *
 * Shows undismissed parent encouragements on the learner's dashboard.
 * Each note has a small × to dismiss it off the dashboard (the row
 * stays in the DB so the parent's audit view still shows it — the
 * dismiss is purely a "remove from view" action).
 *
 * Renders nothing when there are no undismissed notes — no empty
 * box on the dashboard for learners whose parent hasn't sent
 * anything yet. The ParentInviteCard above is the discovery
 * affordance for "your parent could be sending these"; we don't
 * also need an empty state here.
 */
export function FamilyNotesCard() {
  const notesQ = useMyEncouragements();
  const dismiss = useDismissEncouragement();

  if (notesQ.isLoading) return null;
  const notes = notesQ.data ?? [];
  if (notes.length === 0) return null;

  return (
    <Card className="mb-6">
      <CardHeader>
        <div className="flex items-center gap-2">
          <HeartHandshake className="h-4 w-4 text-(--color-primary)" />
          <CardTitle className="text-base">Notes from family</CardTitle>
        </div>
        <CardDescription>
          {notes.length === 1
            ? "A note from someone cheering you on."
            : `${notes.length} notes from people cheering you on.`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {notes.map((n) => (
            <li
              key={n.id}
              className="flex items-start gap-3 rounded-md border border-(--color-border) bg-(--color-muted)/40 px-3 py-2"
            >
              <div className="min-w-0 flex-1">
                <p className="whitespace-pre-line text-sm leading-relaxed text-(--color-foreground)">
                  {n.message}
                </p>
                <div className="mt-1 text-[11px] text-(--color-muted-foreground)">
                  {formatDateTime(n.sent_at)}
                </div>
              </div>
              <Button
                size="icon"
                variant="ghost"
                aria-label="Dismiss this note"
                title="Dismiss"
                onClick={() => dismiss.mutate(n.id)}
                disabled={dismiss.isPending}
                className="h-7 w-7"
              >
                {dismiss.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <X className="h-3.5 w-3.5" />
                )}
              </Button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
