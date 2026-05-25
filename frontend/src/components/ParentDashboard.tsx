import { useState } from "react";
import {
  Award,
  BookOpenCheck,
  Compass,
  Flame,
  HeartHandshake,
  Loader2,
  Send,
  Sprout,
  Star,
  Target,
  Trophy,
} from "lucide-react";
import { BRAND_ARROW_COLORS } from "@/lib/brand";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Empty } from "@/components/ui/empty";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import {
  useChildWeeklySummary,
  useMyChildren,
  useSendEncouragement,
} from "@/lib/queries";

/**
 * Parent / guardian dashboard — Stage 6 of the child-centric
 * roadmap.
 *
 * Design intent (per the roadmap): "open the window to parents but
 * only the encouraging view, not surveillance". This dashboard
 * therefore shows:
 *   ✓ Weekly practice rhythm (days this week vs. target)
 *   ✓ Login streak + longest
 *   ✓ Points + current level
 *   ✓ Weeks-goal-met run
 *   ✓ Recent stamps (the celebratory wins)
 *
 * It DOES NOT show:
 *   ✗ Mistake detail (that's the learner's private review pool)
 *   ✗ Per-quiz scores / per-assessment grades
 *   ✗ The mastery heatmap
 *
 * The parent can send a short encouragement note to the child via
 * the inline composer at the bottom of each child card. Notes land
 * on the child's dashboard until they dismiss them.
 *
 * Multi-child support: a parent can have multiple APPROVED links
 * (one per code consumed). Each renders as its own card; the
 * encouragement composer is per-child.
 */
export function ParentDashboard() {
  const { user } = useAuth();
  const childrenQ = useMyChildren();

  const firstName = (user?.full_name ?? "").split(/\s+/)[0] || "there";

  return (
    <ThemedPage>
      <PageHeader
        title={`Hello, ${firstName}`}
        description="A gentle window into your child's practice. Drop a note any time — they'll see it on their dashboard."
      />

      {childrenQ.isLoading ? (
        <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading your children…
        </div>
      ) : !childrenQ.data || childrenQ.data.length === 0 ? (
        <Empty
          icon={<HeartHandshake className="h-6 w-6" />}
          title="No children linked yet"
          description={
            "Ask your child to generate an invite code from their dashboard and share it with you. " +
            "Then sign out and sign up again with the code, or contact support if you need help."
          }
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {childrenQ.data.map((child) => (
            <ChildCard
              key={child.user_id}
              childUserId={child.user_id}
              childName={child.full_name}
            />
          ))}
        </div>
      )}
    </ThemedPage>
  );
}

/* ----------------------------------------------------------------- */
/* ChildCard — one child's weekly summary + send composer            */
/* ----------------------------------------------------------------- */

function ChildCard({
  childUserId,
  childName,
}: {
  childUserId: number;
  childName: string;
}) {
  const summaryQ = useChildWeeklySummary(childUserId);
  const summary = summaryQ.data;

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <CardTitle className="font-display text-xl">{childName}</CardTitle>
            <CardDescription>
              {summary
                ? `${summary.practice_days_count_this_week} of ${summary.target_days} practice days this week${summary.subject_name ? ` · ${summary.subject_name}` : ""}`
                : "Loading their week…"}
            </CardDescription>
          </div>
          {summary && summary.weekly_goal_met && (
            <Badge variant="success" className="gap-1">
              <Target className="h-3 w-3" /> Goal hit!
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {summaryQ.isLoading || !summary ? (
          <div className="flex items-center gap-2 py-4 text-sm text-(--color-muted-foreground)">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : (
          <>
            {/* Top: stat strip + level progress bar. */}
            <StatStrip summary={summary} />
            <LevelProgressBar summary={summary} />

            {/* Mid: 3-tile chapter rollup mirroring the learner's
                own narrative tiles. Always shows zeros for fresh
                accounts so the parent sees the framing even before
                practice starts. */}
            <ChapterRollup rollup={summary.chapter_rollup} />

            {/* Strengths + Growing in — the two big "what does this
                mean?" payloads the parent asked for. Framed
                positively in both cases; "growing in" is the
                same data the learner sees on "Areas to focus on". */}
            <div className="grid gap-3 md:grid-cols-2">
              <OutcomeList
                title="What they're doing well"
                icon={<Trophy className="h-4 w-4 text-(--color-success)" />}
                items={summary.strengths}
                empty="As your child practises, their strongest concepts will show up here."
                tone="strength"
              />
              <OutcomeList
                title="Growing in"
                icon={<Sprout className="h-4 w-4 text-(--color-warning)" />}
                items={summary.growing_in}
                empty="Nothing flagged for extra practice right now."
                tone="growing"
              />
            </div>

            {/* 12-week consistency heatmap — single most visual
                "are they showing up?" answer. */}
            <ConsistencyStrip heatmap={summary.heatmap} />

            {/* Stamps tally — small celebratory footer. */}
            <StampsTally
              byKind={summary.stamps_by_kind}
              recentStamps={summary.recent_stamps}
            />
          </>
        )}
        <EncouragementComposer childUserId={childUserId} childName={childName} />
      </CardContent>
    </Card>
  );
}

/* --- Stat strip: streak / level / weekly goal --- */

function StatStrip({
  summary,
}: {
  summary: NonNullable<ReturnType<typeof useChildWeeklySummary>["data"]>;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <StatTile
        icon={<Flame className="h-4 w-4 text-orange-500" />}
        label="Streak"
        value={`${summary.streak.current} day${summary.streak.current === 1 ? "" : "s"}`}
        sub={`Longest: ${summary.streak.longest}`}
      />
      <StatTile
        icon={<Star className="h-4 w-4 text-amber-500" />}
        label="Level"
        value={summary.level.name}
        sub={`${summary.points_total} pts`}
      />
      <StatTile
        icon={<Target className="h-4 w-4 text-emerald-600" />}
        label="Weekly goal"
        value={`${summary.weekly_goal_progress.weeks_met_total} weeks`}
        sub={
          summary.weekly_goal_progress.weeks_met_run > 1
            ? `${summary.weekly_goal_progress.weeks_met_run} in a row`
            : summary.weekly_goal_met
              ? "Hit it this week"
              : "Working on this week"
        }
      />
    </div>
  );
}

function StatTile({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="rounded-md border border-(--color-border) p-3">
      <div className="flex items-center gap-2 text-xs text-(--color-muted-foreground)">
        {icon}
        <span>{label}</span>
      </div>
      <div className="mt-1 font-display text-lg font-semibold leading-none">
        {value}
      </div>
      <div className="mt-1 text-[11px] text-(--color-muted-foreground)">{sub}</div>
    </div>
  );
}

/* --- Level progress bar --- */

function LevelProgressBar({
  summary,
}: {
  summary: NonNullable<ReturnType<typeof useChildWeeklySummary>["data"]>;
}) {
  const { level, points_total } = summary;
  const ratio =
    level.next_min_points !== null && level.next_min_points > level.min_points
      ? Math.min(
          1,
          Math.max(
            0,
            (points_total - level.min_points) /
              (level.next_min_points - level.min_points),
          ),
        )
      : 1;
  return (
    <div className="rounded-md border border-(--color-border) bg-(--color-muted)/40 p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex items-center gap-2 text-sm">
          <Star className="h-4 w-4 text-amber-500" />
          <span className="font-display font-semibold">{level.name}</span>
          <span className="text-xs text-(--color-muted-foreground)">
            · {level.blurb}
          </span>
        </div>
        <span className="text-xs tabular-nums text-(--color-muted-foreground)">
          {points_total} points total
        </span>
      </div>
      <div
        className="mt-2 h-2 w-full overflow-hidden rounded-full bg-(--color-border)"
        aria-hidden="true"
      >
        <div
          className="h-full rounded-full bg-amber-500 transition-[width]"
          style={{ width: `${ratio * 100}%` }}
        />
      </div>
      <div className="mt-1 text-xs text-(--color-muted-foreground)">
        {level.points_to_next === null
          ? "Top tier — every point now is a victory lap."
          : `${level.points_to_next} pts to ${level.next_name}.`}
      </div>
    </div>
  );
}

/* --- Chapter rollup (3 mini-tiles) --- */

function ChapterRollup({
  rollup,
}: {
  rollup: NonNullable<
    ReturnType<typeof useChildWeeklySummary>["data"]
  >["chapter_rollup"];
}) {
  const tiles: { label: string; count: number; color: string; icon: React.ReactNode; blurb: string }[] = [
    {
      label: "Chapters mastered",
      count: rollup.mastered,
      color: BRAND_ARROW_COLORS.green,
      icon: <Star className="h-4 w-4" />,
      blurb: rollup.mastered === 0 ? "Their first mastered chapter is a few quizzes away." : "Chapters they're consistently strong on.",
    },
    {
      label: "In practice",
      count: rollup.in_practice,
      color: BRAND_ARROW_COLORS.orange,
      icon: <HeartHandshake className="h-4 w-4" />,
      blurb: rollup.in_practice === 0 ? "Nothing in progress this week." : "Where the effort is currently going.",
    },
    {
      label: "To explore",
      count: rollup.to_explore,
      color: BRAND_ARROW_COLORS.navy,
      icon: <Compass className="h-4 w-4" />,
      blurb: rollup.to_explore === 0 ? "Every chapter touched. Well done." : "Fresh ground still ahead.",
    },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {tiles.map((t) => (
        <div key={t.label} className="rounded-md border border-(--color-border) p-3">
          <div className="flex items-center gap-2">
            <span
              className="inline-flex h-7 w-7 items-center justify-center rounded-full border"
              style={{
                backgroundColor: `${t.color}1a`,
                borderColor: t.color,
                color: t.color,
              }}
            >
              {t.icon}
            </span>
            <div className="min-w-0">
              <div className="font-display text-xl font-semibold leading-none tabular-nums">
                {t.count}
              </div>
              <div className="text-[11px] text-(--color-muted-foreground)">
                {t.label}
              </div>
            </div>
          </div>
          <div className="mt-1.5 text-[11px] text-(--color-muted-foreground)">
            {t.blurb}
          </div>
        </div>
      ))}
    </div>
  );
}

/* --- Outcome list (strengths + growing-in) --- */

function OutcomeList({
  title,
  icon,
  items,
  empty,
  tone,
}: {
  title: string;
  icon: React.ReactNode;
  items: NonNullable<
    ReturnType<typeof useChildWeeklySummary>["data"]
  >["strengths"];
  empty: string;
  tone: "strength" | "growing";
}) {
  return (
    <div className="rounded-md border border-(--color-border) p-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        {icon}
        <span>{title}</span>
      </div>
      {items.length === 0 ? (
        <p className="mt-2 text-xs text-(--color-muted-foreground)">{empty}</p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {items.map((o) => (
            <li key={`${o.chapter_id}-${o.code}`} className="text-xs">
              <div className="flex items-center gap-2">
                <Badge
                  variant={tone === "strength" ? "success" : "warning"}
                  className="text-[10px]"
                >
                  {Math.round((o.mastery ?? 0) * 100)}%
                </Badge>
                <span className="truncate font-medium">{o.description}</span>
              </div>
              {o.chapter_title && (
                <div className="ml-1 mt-0.5 text-[10px] text-(--color-muted-foreground)">
                  Ch {o.chapter_number}. {o.chapter_title} ·{" "}
                  {o.attempts} attempt{o.attempts === 1 ? "" : "s"}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* --- 12-week consistency strip --- */

function ConsistencyStrip({
  heatmap,
}: {
  heatmap: NonNullable<ReturnType<typeof useChildWeeklySummary>["data"]>["heatmap"];
}) {
  if (!heatmap || heatmap.length === 0) return null;
  const today = new Date().toISOString().slice(0, 10);
  const visible = heatmap.filter((c) => c.day <= today);
  const weeks: typeof heatmap[] = [];
  visible.forEach((c, idx) => {
    const wi = Math.floor(idx / 7);
    if (!weeks[wi]) weeks[wi] = [];
    weeks[wi].push(c);
  });
  return (
    <div className="rounded-md border border-(--color-border) p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium text-(--color-muted-foreground)">
          <BookOpenCheck className="h-3.5 w-3.5" /> Last {weeks.length} weeks of practice
        </div>
        <div className="text-[10px] text-(--color-muted-foreground)">
          <span className="mr-2 inline-flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-(--color-muted)" /> quiet
          </span>
          <span className="inline-flex items-center gap-1">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: BRAND_ARROW_COLORS.green }}
            />{" "}
            practised
          </span>
        </div>
      </div>
      <div className="flex gap-1 overflow-x-auto">
        {weeks.map((wk, wi) => (
          <div key={wi} className="flex flex-col gap-1">
            {wk.map((c) => (
              <span
                key={c.day}
                title={`${c.day} - ${c.practiced ? "practised" : "no practice"}`}
                className="h-3 w-3 rounded-sm"
                style={{
                  backgroundColor: c.practiced
                    ? BRAND_ARROW_COLORS.green
                    : "color-mix(in srgb, currentColor 10%, transparent)",
                }}
                aria-label={`${c.day} ${c.practiced ? "practised" : "no practice"}`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/* --- Stamps tally (replaces the old recent-stamps strip) --- */

function StampsTally({
  byKind,
  recentStamps,
}: {
  byKind: Record<string, number>;
  recentStamps: NonNullable<
    ReturnType<typeof useChildWeeklySummary>["data"]
  >["recent_stamps"];
}) {
  const total = Object.values(byKind).reduce((a, b) => a + b, 0);
  if (total === 0 && recentStamps.length === 0) return null;
  const tiles: { key: string; label: string }[] = [
    { key: "QUIZ_COMPLETED", label: "Quizzes done" },
    { key: "PERFECT_SCORE", label: "Perfect scores" },
    { key: "PRACTICE_DAY", label: "Practice days" },
    { key: "WEEKLY_GOAL_MET", label: "Weekly goals hit" },
  ];
  return (
    <div className="rounded-md border border-(--color-border) p-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-(--color-muted-foreground)">
        <Award className="h-3.5 w-3.5 text-amber-500" /> Stamps earned
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {tiles.map((t) => (
          <div
            key={t.key}
            className="rounded-md border border-(--color-border) bg-(--color-muted)/40 px-2 py-1.5 text-center"
          >
            <div className="font-display text-base font-semibold leading-none tabular-nums">
              {byKind[t.key] ?? 0}
            </div>
            <div className="mt-0.5 text-[10px] text-(--color-muted-foreground)">
              {t.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* --- Encouragement composer --- */

const PRESET_MESSAGES: string[] = [
  "Proud of you — keep going!",
  "Saw your streak — that's discipline. Well done.",
  "One step at a time. You've got this.",
  "Take a break too — practice matters, rest matters more.",
];

function EncouragementComposer({
  childUserId,
  childName,
}: {
  childUserId: number;
  childName: string;
}) {
  const [message, setMessage] = useState("");
  const send = useSendEncouragement();

  function handleSend(text?: string) {
    const content = (text ?? message).trim();
    if (!content) return;
    send.mutate(
      { child_user_id: childUserId, message: content },
      {
        onSuccess: () => {
          toast.success(`Sent to ${childName.split(/\s+/)[0]} — they'll see it on their dashboard.`);
          setMessage("");
        },
        onError: (err) => {
          const detail =
            (err as { response?: { data?: { detail?: string } } })?.response
              ?.data?.detail;
          toast.error(typeof detail === "string" ? detail : "Couldn't send. Try again.");
        },
      },
    );
  }

  return (
    <div className="rounded-md border border-dashed border-(--color-border) p-3">
      <Label className="text-xs font-medium">Send a quick note</Label>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {PRESET_MESSAGES.map((p) => (
          <Button
            key={p}
            size="sm"
            variant="outline"
            className="text-[11px]"
            onClick={() => handleSend(p)}
            disabled={send.isPending}
          >
            {p}
          </Button>
        ))}
      </div>
      <div className="mt-2 grid gap-2">
        <textarea
          rows={2}
          maxLength={280}
          placeholder="Or write your own (max 280 chars)…"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={send.isPending}
          className="w-full rounded-md border border-(--color-border) bg-(--color-background) px-3 py-2 text-sm shadow-sm placeholder:text-(--color-muted-foreground) focus:outline-none focus:ring-2 focus:ring-(--color-primary)/40 disabled:opacity-60"
        />
        <div className="flex items-center justify-between text-[11px] text-(--color-muted-foreground)">
          <span>{message.length}/280</span>
          <Button
            size="sm"
            onClick={() => handleSend()}
            disabled={!message.trim() || send.isPending}
          >
            {send.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}

