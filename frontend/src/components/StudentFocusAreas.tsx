/**
 * Per-student "areas of focus" panel.
 *
 * Distinct from `WeakTopicsCard` (which aggregates across an entire
 * class for the teacher's dashboard) — this one looks at a single
 * student's mastery grid and surfaces the N learning outcomes with
 * the LOWEST current mastery, so the teacher can decide who to
 * intervene on and where.
 *
 * Pure derivation: takes the existing `StudentMasteryGrid` already
 * loaded by the page, no extra API call. Filters to outcomes the
 * student has actually attempted (mastery !== null AND attempts > 0)
 * — there's no signal in "this student hasn't seen this outcome yet"
 * that's actionable here.
 */
import { useMemo } from "react";
import { TrendingDown } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Empty } from "@/components/ui/empty";
import { Badge } from "@/components/ui/badge";
import type { MasteryChapter, MasteryOutcome } from "@/lib/types";
import { cn } from "@/lib/utils";

interface FocusRow {
  chapter: MasteryChapter;
  outcome: MasteryOutcome;
}

interface Props {
  /** Chapters → outcomes from `useStudentMastery().data.chapters`. */
  chapters: MasteryChapter[];
  /** How many rows to surface. Default 5. */
  limit?: number;
}

// Mastery bar colour scales with severity:
//   < 30% red, 30–50 amber, 50–70 yellow-amber. We don't expect rows
// in this card to be > 70% (those wouldn't be the WEAKEST), but the
// gradient handles them gracefully anyway.
function masteryStyle(m: number): { bar: string; text: string; tag: string } {
  if (m < 0.3) return { bar: "bg-red-500", text: "text-red-700", tag: "Critical" };
  if (m < 0.5) return { bar: "bg-orange-500", text: "text-orange-700", tag: "Weak" };
  if (m < 0.7) return { bar: "bg-amber-400", text: "text-amber-700", tag: "Below target" };
  return { bar: "bg-emerald-400", text: "text-emerald-700", tag: "On track" };
}

export function StudentFocusAreas({ chapters, limit = 5 }: Props) {
  const rows = useMemo<FocusRow[]>(() => {
    const flat: FocusRow[] = [];
    for (const ch of chapters) {
      for (const o of ch.outcomes) {
        // Skip un-attempted outcomes — saying "needs focus" on
        // something the student hasn't even seen is misleading.
        if (o.mastery === null || o.attempts <= 0) continue;
        flat.push({ chapter: ch, outcome: o });
      }
    }
    flat.sort((a, b) => {
      const am = a.outcome.mastery ?? 1;
      const bm = b.outcome.mastery ?? 1;
      if (am !== bm) return am - bm;
      // Tie-break: prefer the outcome the student has attempted MORE
      // times (= more confident the low score isn't noise).
      return b.outcome.attempts - a.outcome.attempts;
    });
    return flat.slice(0, limit);
  }, [chapters, limit]);

  return (
    <Card className="mb-6">
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-(--color-warning,#f97316)" />
            Areas of focus
          </CardTitle>
          <CardDescription>
            The {limit} lowest-mastery outcomes this student has actually
            attempted. Use these to plan one-on-one focus or targeted
            practice.
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <Empty
            className="border-0 py-4"
            title="Not enough data yet"
            description="Once the student has attempted at least one assessment, the weakest outcomes will surface here."
          />
        ) : (
          <ul className="space-y-3">
            {rows.map(({ chapter, outcome }) => {
              const m = outcome.mastery ?? 0;
              const pct = Math.max(0, Math.min(100, Math.round(m * 100)));
              const style = masteryStyle(m);
              return (
                <li
                  key={`${chapter.chapter_id}-${outcome.outcome_id}`}
                  className="rounded-md border border-(--color-border) p-3"
                >
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <Badge variant="outline" className="text-xs">
                      Ch&nbsp;{chapter.chapter_number}
                    </Badge>
                    <span className="font-mono text-xs text-(--color-muted-foreground)">
                      {outcome.code}
                    </span>
                    <Badge className={cn("text-[11px]", style.text)} variant="secondary">
                      {style.tag}
                    </Badge>
                    <span className="ml-auto font-mono text-xs tabular-nums text-(--color-muted-foreground)">
                      {outcome.attempts} attempt{outcome.attempts === 1 ? "" : "s"}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-snug text-(--color-foreground)">
                    {outcome.description}
                  </p>
                  {/* Visual mastery bar — colour mirrors the heatmap so
                      teachers can map this card straight onto the grid
                      below. Width is the running mastery; the rail is
                      muted so the empty portion reads as "still to
                      learn", not "wrong". */}
                  <div className="mt-3 flex items-center gap-3">
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-(--color-muted,rgba(0,0,0,0.08))">
                      <div
                        className={cn("h-full rounded-full", style.bar)}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span
                      className={cn(
                        "min-w-[42px] text-right font-mono text-xs tabular-nums",
                        style.text,
                      )}
                    >
                      {pct}%
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
