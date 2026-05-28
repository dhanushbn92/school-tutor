import { Link } from "react-router-dom";
import { ArrowLeft, Award, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Empty } from "@/components/ui/empty";
import { Badge } from "@/components/ui/badge";
import { StampBadge } from "@/components/StampBadge";
import {
  STAMP_KIND_ORDER,
  STAMP_PRESENTATION,
  type StampTier,
} from "@/lib/stamps";
import { useMyStamps } from "@/lib/queries";
import type { LearnerStamp, StampKind } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

/**
 * The learner's stamp collection — designed as a SHOWCASE.
 *
 * Three sections:
 *   1. Trophy showcase — a hero strip featuring the learner's biggest
 *      EARNED achievements (platinum + gold + silver tiers) with full
 *      ribbon-decorated badges. This is the prideful 'these are mine'
 *      moment up front.
 *   2. Full tally grid — every kind, with a tier-aware badge plus a
 *      count and label, including locked-but-not-yet-earned slots in
 *      muted form so the learner sees what's still ahead.
 *   3. Chronological feed — newest stamps first, small badge + metadata.
 *
 * Stamps are immutable; this page is read-only.
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

  // Group by kind for tallies + first-earned lookup.
  const byKind = new Map<StampKind, LearnerStamp[]>();
  for (const s of stamps) {
    const key = s.kind as StampKind;
    if (!byKind.has(key)) byKind.set(key, []);
    byKind.get(key)!.push(s);
  }

  // Tier-aware showcase: pick the learner's most prestigious earned
  // kinds for the hero strip, capped at 5 so the layout stays balanced.
  const tierOrder: StampTier[] = ["platinum", "gold", "silver"];
  const showcaseKinds: StampKind[] = [];
  for (const tier of tierOrder) {
    for (const kind of STAMP_KIND_ORDER) {
      if (showcaseKinds.length >= 5) break;
      if ((byKind.get(kind)?.length ?? 0) === 0) continue;
      if (STAMP_PRESENTATION[kind].tier !== tier) continue;
      showcaseKinds.push(kind);
    }
  }

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
          {/* ─── Trophy showcase ─────────────────────────────────────
              Hero strip of the learner's biggest wins. Each badge is
              fully decorated (ribbon, big tier shape) — this is the
              section that makes the learner feel proud. */}
          {showcaseKinds.length > 0 && (
            <Card className="mb-6 overflow-hidden border-(--color-primary)/30 bg-gradient-to-br from-(--color-primary)/5 via-transparent to-(--color-accent)/10">
              <CardHeader>
                <CardTitle className="font-display text-2xl">
                  Trophy showcase
                </CardTitle>
                <CardDescription>
                  Your biggest wins so far. Earned, not given.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-end justify-center gap-6 sm:gap-10 py-4">
                  {showcaseKinds.map((kind) => {
                    const meta = STAMP_PRESENTATION[kind];
                    const count = byKind.get(kind)?.length ?? 0;
                    return (
                      <div
                        key={kind}
                        className="flex flex-col items-center gap-1.5 text-center"
                      >
                        <StampBadge kind={kind} size="lg" showRibbon />
                        <div className="text-sm font-semibold">{meta.label}</div>
                        {count > 1 && (
                          <Badge
                            variant="outline"
                            className="text-[10px] uppercase tracking-wide"
                            style={{
                              borderColor: meta.color,
                              color: meta.color,
                            }}
                          >
                            ×{count} earned
                          </Badge>
                        )}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* ─── Full tally grid ─────────────────────────────────────
              Earned badges first (most prestigious among them at the
              front), then locked / not-yet-earned slots in muted form.
              This puts the learner's actual achievements at the top
              of the grid; what's still ahead reads as a second-tier
              "next up" section underneath. */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>All badges</CardTitle>
              <CardDescription>
                Your earned badges first. Greyed-out ones below are still
                ahead of you — keep practising to unlock them.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                {(() => {
                  const earned = STAMP_KIND_ORDER.filter(
                    (k) => (byKind.get(k)?.length ?? 0) > 0,
                  );
                  const locked = STAMP_KIND_ORDER.filter(
                    (k) => (byKind.get(k)?.length ?? 0) === 0,
                  );
                  return [...earned, ...locked];
                })().map((kind) => {
                  const meta = STAMP_PRESENTATION[kind];
                  const count = byKind.get(kind)?.length ?? 0;
                  const locked = count === 0;
                  return (
                    <div
                      key={kind}
                      className={`flex flex-col items-center gap-2 rounded-lg border p-3 text-center transition-colors ${
                        locked
                          ? "border-dashed border-(--color-border) bg-(--color-muted)/20"
                          : "border-(--color-border) bg-(--color-card)"
                      }`}
                    >
                      <StampBadge kind={kind} size="md" locked={locked} />
                      <div
                        className={`text-sm font-medium ${locked ? "text-(--color-muted-foreground)" : ""}`}
                      >
                        {meta.label}
                      </div>
                      <div className="text-[10px] uppercase tracking-wide text-(--color-muted-foreground)">
                        {meta.tier} · {meta.tagline}
                      </div>
                      {!locked && (
                        <div className="font-display text-xl font-bold tabular-nums">
                          ×{count}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* ─── Chronological feed — newest first ─────────────────── */}
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
                      <StampBadge kind={s.kind as StampKind} size="sm" />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2 text-sm">
                          <span className="font-medium">
                            {meta?.label ?? s.kind}
                          </span>
                          {meta && (
                            <Badge
                              variant="outline"
                              className="text-[10px] uppercase tracking-wide"
                              style={{ borderColor: meta.color, color: meta.color }}
                            >
                              {meta.tier} · {meta.tagline}
                            </Badge>
                          )}
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
