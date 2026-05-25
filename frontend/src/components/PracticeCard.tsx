import { Link } from "react-router-dom";
import {
  ArrowRight,
  Award,
  Flame,
  Loader2,
  Pencil,
  Sparkles,
  Star,
  Target,
  X,
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useMyStamps, usePracticeSummary, useSetWeeklyGoal } from "@/lib/queries";
import { BRAND_ARROW_COLORS } from "@/lib/brand";
import { STAMP_PRESENTATION } from "@/lib/stamps";
import { cn } from "@/lib/utils";
import type {
  HeatmapCell,
  LearnerStamp,
  LevelInfo,
  PracticeSummary,
  StampKind,
  StreakInfo,
  WeeklyGoalProgress,
} from "@/lib/types";

/**
 * "Your practice" card — the headline child-centric dashboard widget
 * shipped in Stage 1 of the roadmap.
 *
 * Layout: a circular progress ring on the left showing days-this-week
 * / target-this-week, a compact recent-stamps strip on the right, and
 * a one-line summary tying them together. The whole card refuses to
 * show numbers in isolation — "3 of 4 days" reads as a story, not a
 * stat.
 *
 * The card silently no-ops when the practice-summary query fails (a
 * non-learner role hitting the dashboard, or the backend route 404ing
 * during a deploy). That keeps the dashboard robust during the
 * roll-out of the new endpoints.
 */
export function PracticeCard() {
  const summaryQ = usePracticeSummary();
  // The recent stamps embedded in the summary cap at ~12; for the
  // dashboard preview that's plenty. The full collection lives on
  // /me/stamps.
  const data = summaryQ.data;

  // Loading + missing data: render a tiny placeholder so the card
  // reserves vertical space (no layout jump when the data arrives).
  if (summaryQ.isLoading) {
    return (
      <Card className="mb-6">
        <CardContent className="flex items-center gap-2 py-5 text-sm text-(--color-muted-foreground)">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading your practice…
        </CardContent>
      </Card>
    );
  }
  if (!data) {
    // Likely a non-learner role; render nothing rather than an empty card.
    return null;
  }

  return (
    <Card className="mb-6 overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="font-display text-lg tracking-tight">
            Your practice
          </CardTitle>
          {data.weekly_goal_met && (
            <Badge variant="success" className="gap-1">
              <Sparkles className="h-3 w-3" /> Goal hit!
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:gap-6">
          <PracticeRing
            count={data.practice_days_count_this_week}
            target={data.target_days}
          />
          <div className="min-w-0 flex-1 space-y-2">
            <SummaryLine data={data} />
            <WeeklyGoalEditor target={data.target_days} />
          </div>
          <StampsStrip stamps={data.recent_stamps} />
        </div>

        {/* Stage 1.5 — stats row: streak, points/level, weeks-goal-met. */}
        <div className="mt-4 grid gap-3 border-t border-(--color-border) pt-4 sm:grid-cols-3">
          <StreakTile streak={data.streak} />
          <LevelTile level={data.level} points={data.points_total} />
          <WeeklyGoalTile progress={data.weekly_goal_progress} />
        </div>

        {/* Stage 1.5 — 12-week consistency heatmap. */}
        <ConsistencyHeatmap cells={data.heatmap} />
      </CardContent>
    </Card>
  );
}

/* ----------------------------------------------------------------- */
/* Stage 1.5 — streak / level / weekly-goal tiles                    */
/* ----------------------------------------------------------------- */

function StreakTile({ streak }: { streak: StreakInfo }) {
  const used = streak.grace_used_this_week;
  const allowed = streak.grace_allowed_per_week;
  return (
    <div className="rounded-md border border-(--color-border) p-3">
      <div className="flex items-center gap-2 text-(--color-foreground)">
        <Flame className="h-4 w-4 text-orange-500" />
        <span className="font-display text-2xl font-semibold tabular-nums">
          {streak.current}
        </span>
        <span className="text-xs text-(--color-muted-foreground)">
          day{streak.current === 1 ? "" : "s"} in a row
        </span>
      </div>
      <div className="mt-1 text-xs text-(--color-muted-foreground)">
        Longest: {streak.longest}
        {allowed > 0 && (
          <>
            {" · "}
            <span title="One missed day per week is forgiven.">
              freebie {used}/{allowed} used this week
            </span>
          </>
        )}
      </div>
    </div>
  );
}

function LevelTile({ level, points }: { level: LevelInfo; points: number }) {
  const ratio =
    level.next_min_points !== null && level.next_min_points > level.min_points
      ? Math.min(
          1,
          Math.max(
            0,
            (points - level.min_points) /
              (level.next_min_points - level.min_points),
          ),
        )
      : 1;
  return (
    <div className="rounded-md border border-(--color-border) p-3">
      <div className="flex items-center gap-2">
        <Star className="h-4 w-4 text-amber-500" />
        <span className="font-display text-base font-semibold">
          {level.name}
        </span>
        <span className="ml-auto text-xs tabular-nums text-(--color-muted-foreground)">
          {points} pts
        </span>
      </div>
      <div
        className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-(--color-muted)"
        aria-hidden="true"
      >
        <div
          className="h-full rounded-full bg-amber-500 transition-[width]"
          style={{ width: `${ratio * 100}%` }}
        />
      </div>
      <div className="mt-1 text-xs text-(--color-muted-foreground)">
        {level.points_to_next === null
          ? `Top tier — ${level.blurb}`
          : `${level.points_to_next} pts to ${level.next_name}`}
      </div>
    </div>
  );
}

function WeeklyGoalTile({ progress }: { progress: WeeklyGoalProgress }) {
  return (
    <div className="rounded-md border border-(--color-border) p-3">
      <div className="flex items-center gap-2">
        <Target className="h-4 w-4 text-emerald-600" />
        <span className="font-display text-2xl font-semibold tabular-nums">
          {progress.weeks_met_total}
        </span>
        <span className="text-xs text-(--color-muted-foreground)">
          week{progress.weeks_met_total === 1 ? "" : "s"} goal hit
        </span>
      </div>
      <div className="mt-1 text-xs text-(--color-muted-foreground)">
        {progress.weeks_met_run > 1
          ? `🔥 ${progress.weeks_met_run} weeks in a row`
          : progress.weeks_met_run === 1
            ? "Hit it this week — keep going!"
            : "Hit this week's goal to start a run."}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- */
/* Stage 1.5 — 12-week consistency heatmap                           */
/* ----------------------------------------------------------------- */

/**
 * GitHub-style activity grid: 7 rows (Mon→Sun) × N cols (weeks).
 * Each cell is a small square: filled if there was at least one
 * submission that day. Older weeks on the left, current week on
 * the right. Hovering a cell shows the date in a native tooltip.
 *
 * Defensive: trims any cells past today so the future doesn't
 * render as "missed".
 */
function ConsistencyHeatmap({ cells }: { cells: HeatmapCell[] }) {
  if (cells.length === 0) return null;
  // Group cells into weekday rows. Backend yields cells Mon-first
  // for the earliest week, then continuing through; that means
  // index % 7 maps to weekday-of-week-block, but we need rows by
  // weekday across the whole grid. Convert via Date.getDay().
  const today = new Date().toISOString().slice(0, 10);
  const visible = cells.filter((c) => c.day <= today);
  // Bucket by weekday (Mon=0, Sun=6) and by weekIndex.
  const weeks: HeatmapCell[][] = [];
  visible.forEach((c, idx) => {
    const weekIndex = Math.floor(idx / 7);
    if (!weeks[weekIndex]) weeks[weekIndex] = [];
    weeks[weekIndex].push(c);
  });

  return (
    <div className="mt-4 border-t border-(--color-border) pt-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-xs font-medium text-(--color-muted-foreground)">
          Last {weeks.length} weeks
        </div>
        <div className="text-xs text-(--color-muted-foreground)">
          <span className="mr-2 inline-flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-(--color-muted)" />
            quiet
          </span>
          <span className="inline-flex items-center gap-1">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: BRAND_ARROW_COLORS.green }}
            />
            practised
          </span>
        </div>
      </div>
      <div className="flex gap-1 overflow-x-auto">
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-1">
            {week.map((cell) => (
              <span
                key={cell.day}
                title={`${cell.day} — ${cell.practiced ? "practised" : "no practice"}`}
                className="h-3 w-3 rounded-sm"
                style={{
                  backgroundColor: cell.practiced
                    ? BRAND_ARROW_COLORS.green
                    : "color-mix(in srgb, currentColor 10%, transparent)",
                }}
                aria-label={`${cell.day} ${cell.practiced ? "practised" : "no practice"}`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- */
/* Ring                                                              */
/* ----------------------------------------------------------------- */

/**
 * Circular SVG progress ring. Filled segment scales with
 * count/target; over-100% (the rare "I crushed my goal" case) clamps
 * at full ring rather than overflowing.
 */
function PracticeRing({ count, target }: { count: number; target: number }) {
  const safeTarget = Math.max(1, target);
  const ratio = Math.min(1, count / safeTarget);
  const size = 96;
  const stroke = 10;
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const filled = circumference * ratio;
  const isHit = count >= target;
  return (
    <div className="relative" aria-hidden="true">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="currentColor"
          strokeOpacity="0.12"
          strokeWidth={stroke}
        />
        {/* Filled arc. transform/rotate puts the start at 12 o'clock
            rather than 3 o'clock so the visual progress reads
            clockwise from the top, matching every clock face the
            child has ever seen. */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={isHit ? BRAND_ARROW_COLORS.green : BRAND_ARROW_COLORS.navy}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference - filled}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center leading-none">
        <span className="font-display text-2xl font-semibold tabular-nums">
          {count}
        </span>
        <span className="text-[10px] text-(--color-muted-foreground)">
          of {target}
        </span>
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- */
/* One-line summary                                                  */
/* ----------------------------------------------------------------- */

function SummaryLine({ data }: { data: PracticeSummary }) {
  const remaining = Math.max(0, data.target_days - data.practice_days_count_this_week);
  if (data.weekly_goal_met) {
    return (
      <p className="text-sm leading-relaxed text-(--color-foreground)">
        You hit your weekly goal —{" "}
        <strong>{data.practice_days_count_this_week}</strong> practice days this
        week. Any more is a bonus.
      </p>
    );
  }
  if (data.practice_days_count_this_week === 0) {
    return (
      <p className="text-sm leading-relaxed text-(--color-foreground)">
        Fresh week. <strong>{data.target_days}</strong> practice days ahead —
        one quiz a day is all it takes.
      </p>
    );
  }
  return (
    <p className="text-sm leading-relaxed text-(--color-foreground)">
      <strong>{remaining}</strong>{" "}
      {remaining === 1 ? "more practice day" : "more practice days"} to hit
      your weekly goal. You've done{" "}
      <strong>{data.practice_days_count_this_week}</strong> so far.
    </p>
  );
}

/* ----------------------------------------------------------------- */
/* Weekly-goal editor                                                */
/* ----------------------------------------------------------------- */

function WeeklyGoalEditor({ target }: { target: number }) {
  // `editing` flips on user intent; `draft` is the in-progress
  // pick. We seed draft from target on every editor-open via the
  // "Open" handler below — no useEffect, no setState-in-effect.
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(target);
  const setGoal = useSetWeeklyGoal();

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => {
          // Re-seed draft from the (possibly newly-updated) target
          // each time the editor opens, so the picker always shows
          // the current value.
          setDraft(target);
          setEditing(true);
        }}
        className="inline-flex items-center gap-1 text-xs text-(--color-muted-foreground) hover:text-(--color-foreground)"
      >
        <Pencil className="h-3 w-3" />
        Goal: {target} days/week
      </button>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="text-(--color-muted-foreground)">Aim for</span>
      <div className="inline-flex overflow-hidden rounded-md border border-(--color-border)">
        {[2, 3, 4, 5, 6, 7].map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDraft(d)}
            className={cn(
              "px-2.5 py-1 text-xs tabular-nums",
              draft === d
                ? "bg-(--color-primary) text-(--color-primary-foreground)"
                : "hover:bg-(--color-muted)",
            )}
          >
            {d}
          </button>
        ))}
      </div>
      <span className="text-(--color-muted-foreground)">days a week</span>
      <Button
        size="sm"
        onClick={() => {
          setGoal.mutate(draft, { onSuccess: () => setEditing(false) });
        }}
        disabled={setGoal.isPending || draft === target}
      >
        {setGoal.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
        Save
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => {
          setDraft(target);
          setEditing(false);
        }}
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  );
}

/* ----------------------------------------------------------------- */
/* Stamps strip                                                      */
/* ----------------------------------------------------------------- */

function StampsStrip({ stamps }: { stamps: LearnerStamp[] }) {
  // Use the practice-summary's embedded recent stamps; falling back to
  // the dedicated stamps query would double-fetch on first load.
  // useMyStamps is the full collection — referenced here only to wake
  // up the react-query cache for the /me/stamps page so navigating
  // there is instant. Suppress its result; we only render the embedded
  // strip.
  useMyStamps(20);

  if (stamps.length === 0) {
    return (
      <div className="text-xs text-(--color-muted-foreground) md:max-w-[10rem] md:text-right">
        Stamps you earn for practising land here.
        <Button asChild variant="link" size="sm" className="block px-0">
          <Link to="/me/stamps">View stamp book</Link>
        </Button>
      </div>
    );
  }
  // Show up to 5 newest stamps as small chips, then a "+N" overflow.
  const preview = stamps.slice(0, 5);
  const overflow = Math.max(0, stamps.length - preview.length);
  return (
    <div className="md:max-w-[12rem] md:text-right">
      <div className="flex flex-wrap items-center gap-1.5 md:justify-end">
        {preview.map((s) => (
          <StampChip key={s.id} stamp={s} />
        ))}
        {overflow > 0 && (
          <span className="text-[11px] text-(--color-muted-foreground)">
            +{overflow}
          </span>
        )}
      </div>
      <Button
        asChild
        variant="link"
        size="sm"
        className="mt-1 inline-flex h-auto items-center gap-1 px-0 text-xs"
      >
        <Link to="/me/stamps">
          Stamp book <ArrowRight className="h-3 w-3" />
        </Link>
      </Button>
    </div>
  );
}

/**
 * Per-stamp colour + label. Falls through to a generic outline chip
 * for unknown kinds so adding a new kind on the backend never crashes
 * the UI.
 */
function StampChip({ stamp }: { stamp: LearnerStamp }) {
  const meta = STAMP_PRESENTATION[stamp.kind as StampKind];
  if (!meta) {
    return (
      <Badge variant="outline" className="text-[10px]">
        Stamp
      </Badge>
    );
  }
  return (
    <span
      className="inline-flex h-7 w-7 items-center justify-center rounded-full border text-base"
      style={{
        backgroundColor: `${meta.color}1a`, // hex + alpha
        borderColor: meta.color,
        color: meta.color,
      }}
      title={meta.label}
      aria-label={meta.label}
    >
      <Award className="h-3.5 w-3.5" />
    </span>
  );
}

// STAMP_PRESENTATION lives in @/lib/stamps so both PracticeCard and
// StampBook can import it without violating react-refresh's
// "components-only export" rule for .tsx files.
