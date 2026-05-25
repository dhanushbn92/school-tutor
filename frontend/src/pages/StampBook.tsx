import { Link } from "react-router-dom";
import { ArrowLeft, Award, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Empty } from "@/components/ui/empty";
import { Badge } from "@/components/ui/badge";
import { STAMP_PRESENTATION } from "@/lib/stamps";
import { useMyStamps } from "@/lib/queries";
import type { LearnerStamp, StampKind } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

/**
 * The learner's stamp collection — the more-detailed cousin of the
 * recent-stamps strip on the dashboard's "Your practice" card.
 *
 * Lays out every stamp the learner has earned, grouped by kind so
 * "I have N practice-day stamps" is readable at a glance. Each kind's
 * presentation (icon colour + label) comes from STAMP_PRESENTATION so
 * the dashboard chips and this page stay visually in sync.
 *
 * Stamps are immutable; this page is read-only. No mutate / delete
 * affordances — earned is earned.
 */
export function StampBookPage() {
  const stampsQ = useMyStamps(500);

  if (stampsQ.isLoading) {
    return (
      <ThemedPage>
        <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading your stamps…
        </div>
      </ThemedPage>
    );
  }
  const stamps = stampsQ.data ?? [];

  // Group by kind for the per-kind tally; the all-stamps section
  // below renders them chronologically so a learner can see their
  // most recent wins at the top.
  const byKind = new Map<string, LearnerStamp[]>();
  for (const s of stamps) {
    const key = s.kind;
    if (!byKind.has(key)) byKind.set(key, []);
    byKind.get(key)!.push(s);
  }
  const kindOrder: StampKind[] = [
    "WEEKLY_GOAL_MET",
    "PERFECT_SCORE",
    "PRACTICE_DAY",
    "QUIZ_COMPLETED",
  ];

  return (
    <ThemedPage>
      <PageHeader
        title="Your stamp book"
        description={
          stamps.length === 0
            ? "Stamps for the practice you've done will appear here."
            : `${stamps.length} stamps so far. Keep practising — there's always one more to earn.`
        }
        actions={
          <Button asChild variant="outline">
            <Link to="/">
              <ArrowLeft className="h-4 w-4" /> Back to dashboard
            </Link>
          </Button>
        }
      />

      {stamps.length === 0 ? (
        <Empty
          icon={<Award className="h-6 w-6" />}
          title="No stamps yet"
          description="Complete any quiz and you'll earn your first stamp."
          action={
            <Button asChild>
              <Link to="/quick-quiz">Start a quiz</Link>
            </Button>
          }
        />
      ) : (
        <>
          {/* Per-kind tally row — quick "how many of each have I earned?" */}
          <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {kindOrder.map((kind) => {
              const meta = STAMP_PRESENTATION[kind];
              const count = byKind.get(kind)?.length ?? 0;
              return (
                <Card key={kind}>
                  <CardContent className="flex items-center gap-3 py-4">
                    <span
                      className="inline-flex h-10 w-10 items-center justify-center rounded-full border"
                      style={{
                        backgroundColor: `${meta.color}1a`,
                        borderColor: meta.color,
                        color: meta.color,
                      }}
                    >
                      <Award className="h-5 w-5" />
                    </span>
                    <div className="min-w-0">
                      <div className="font-display text-2xl font-semibold leading-none tabular-nums">
                        {count}
                      </div>
                      <div className="mt-0.5 text-xs text-(--color-muted-foreground)">
                        {meta.label}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Chronological full list — newest first. Each card shows
              kind + when + a short metadata blurb. */}
          <Card>
            <CardHeader>
              <CardTitle>Every stamp, newest first</CardTitle>
              <CardDescription>
                Tap nothing — this is a record of practice you've already done.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-(--color-border)">
                {stamps.map((s) => {
                  const meta = STAMP_PRESENTATION[s.kind as StampKind];
                  return (
                    <li key={s.id} className="flex items-start gap-3 py-3">
                      <span
                        className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border"
                        style={
                          meta
                            ? {
                                backgroundColor: `${meta.color}1a`,
                                borderColor: meta.color,
                                color: meta.color,
                              }
                            : undefined
                        }
                      >
                        <Award className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2 text-sm">
                          <span className="font-medium">
                            {meta?.label ?? s.kind}
                          </span>
                          <Badge variant="outline" className="text-[10px]">
                            {s.kind}
                          </Badge>
                          <span className="text-xs text-(--color-muted-foreground)">
                            {formatDateTime(s.earned_at)}
                          </span>
                        </div>
                        <p className="mt-0.5 text-xs text-(--color-muted-foreground)">
                          {meta?.description}
                          {summariseStamp(s)}
                        </p>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </CardContent>
          </Card>
        </>
      )}
    </ThemedPage>
  );
}

/**
 * Render a stamp's metadata as a short readable phrase. Defensive
 * about unknown shapes — unrecognised metadata just disappears
 * rather than crashing.
 */
function summariseStamp(s: LearnerStamp): string {
  const m = s.metadata ?? {};
  switch (s.kind) {
    case "QUIZ_COMPLETED": {
      const awarded = m.total_awarded;
      const max = m.max_marks;
      if (typeof awarded === "number" && typeof max === "number") {
        return ` Score: ${awarded}/${max}.`;
      }
      return "";
    }
    case "PERFECT_SCORE": {
      return typeof m.marks === "number" ? ` ${m.marks} marks.` : "";
    }
    case "PRACTICE_DAY": {
      return typeof m.date === "string" ? ` ${m.date}.` : "";
    }
    case "WEEKLY_GOAL_MET": {
      const days = m.days_achieved;
      const target = m.target_days;
      if (typeof days === "number" && typeof target === "number") {
        return ` ${days} of ${target} target days.`;
      }
      return "";
    }
    default:
      return "";
  }
}
