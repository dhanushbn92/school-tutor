import { useState } from "react";
import {
  Award,
  Flame,
  HeartHandshake,
  Loader2,
  Send,
  Star,
  Target,
} from "lucide-react";
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
        <CardTitle className="font-display text-lg">{childName}</CardTitle>
        <CardDescription>
          {summary
            ? `Week of ${summary.week_start} — ${summary.practice_days_count_this_week} of ${summary.target_days} practice days so far.`
            : "Loading their week…"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {summaryQ.isLoading || !summary ? (
          <div className="flex items-center gap-2 py-4 text-sm text-(--color-muted-foreground)">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : (
          <>
            <StatStrip summary={summary} />
            <StampStrip stamps={summary.recent_stamps} />
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

/* --- Recent stamps strip --- */

function StampStrip({
  stamps,
}: {
  stamps: NonNullable<
    ReturnType<typeof useChildWeeklySummary>["data"]
  >["recent_stamps"];
}) {
  if (!stamps || stamps.length === 0) return null;
  return (
    <div>
      <div className="mb-1.5 text-xs font-medium text-(--color-muted-foreground)">
        Recent stamps
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {stamps.slice(0, 6).map((s) => (
          <Badge key={s.id} variant="outline" className="gap-1 text-[10px]">
            <Award className="h-3 w-3" />
            {humanStampKind(s.kind)}
          </Badge>
        ))}
      </div>
    </div>
  );
}

function humanStampKind(kind: string): string {
  switch (kind) {
    case "QUIZ_COMPLETED":
      return "Quiz done";
    case "PERFECT_SCORE":
      return "Perfect score";
    case "PRACTICE_DAY":
      return "Practice day";
    case "WEEKLY_GOAL_MET":
      return "Weekly goal";
    default:
      return kind;
  }
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

