import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { BrandLogo } from "@/components/BrandLogo";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { BRAND_NAVY, BRAND_ORANGE } from "@/lib/brand";
import { useFeaturedVideos, useMyMistakes, usePracticeSummary } from "@/lib/queries";
import type { OutcomePick } from "@/lib/progress";

/** The navy card: the platform's purpose, and the one big action. */
function PurposeCard({ quizHref, quizLabel }: { quizHref: string; quizLabel: string }) {
  return (
    <div
      className="flex flex-col gap-3.5 rounded-2xl p-6 text-white"
      style={{ background: BRAND_NAVY }}
    >
      <span className="inline-flex self-start rounded-xl bg-white p-1.5">
        <BrandLogo size={40} />
      </span>
      <h2 className="font-display text-xl font-extrabold leading-tight tracking-tight">
        Practice. Again. And again.
      </h2>
      <p className="text-sm leading-relaxed text-white/75">
        Each quiz is another arrow drawn toward mastery.
      </p>
      <Button
        asChild
        size="lg"
        className="mt-1 rounded-xl text-[#2B1700] hover:opacity-90"
        style={{ background: BRAND_ORANGE }}
      >
        <Link to={quizHref}>
          <Sparkles className="h-4 w-4" />
          {quizLabel}
        </Link>
      </Button>
    </div>
  );
}

function WeekCard() {
  const { data } = usePracticeSummary();
  if (!data) return null;
  const pct = Math.min(
    100,
    Math.round((data.practice_days_count_this_week / Math.max(1, data.target_days)) * 100),
  );
  return (
    <Card className="rounded-2xl p-5">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="font-display text-base font-bold">This week</h2>
        {data.weekly_goal_met && (
          <span className="rounded-full bg-(--color-success)/12 px-2.5 py-0.5 text-xs font-semibold text-(--color-success)">
            Goal hit
          </span>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="font-display text-3xl font-extrabold tabular-nums">
          {data.practice_days_count_this_week}
        </span>
        <span className="text-sm text-(--color-muted-foreground)">
          of {data.target_days} practice days
        </span>
      </div>
      <div
        className="mt-3 h-2.5 overflow-hidden rounded-full bg-(--color-muted)"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={data.target_days}
        aria-valuenow={data.practice_days_count_this_week}
        aria-label="Practice days this week"
      >
        <div
          className="h-full rounded-full bg-(--color-primary)"
          style={{ width: `${pct}%` }}
        />
      </div>
    </Card>
  );
}

function LinkCard({
  to,
  title,
  cta,
  children,
}: {
  to: string;
  title: string;
  cta: string;
  children: ReactNode;
}) {
  return (
    <Card className="rounded-2xl transition-shadow hover:shadow-md">
      <Link to={to} className="flex flex-col gap-1.5 rounded-2xl p-5">
        <h3 className="font-display text-base font-bold">{title}</h3>
        <div className="text-sm leading-relaxed text-(--color-muted-foreground)">
          {children}
        </div>
        <span className="mt-2 text-sm font-semibold text-(--color-primary)">{cta}</span>
      </Link>
    </Card>
  );
}

function VideoCard() {
  const { data } = useFeaturedVideos();
  if (!data || data.total_videos === 0 || data.chapters.length === 0) return null;
  const subjects = [...new Set(data.chapters.map((c) => c.subject_name))];
  const where =
    subjects.length === 1
      ? ` in ${subjects[0]}`
      : subjects.length <= 3
        ? ` in ${subjects.slice(0, -1).join(", ")} and ${subjects[subjects.length - 1]}`
        : ` in ${subjects.length} subjects`;
  return (
    <LinkCard to="/videos" title="Video lessons" cta="Browse video lessons">
      {data.total_videos} {data.total_videos === 1 ? "video" : "videos"} across{" "}
      {data.total_chapters} {data.total_chapters === 1 ? "chapter" : "chapters"}
      {where}. Watch a chapter, then practise it.
    </LinkCard>
  );
}

function StrongestCard({
  strongest,
  isIndividual,
}: {
  strongest: OutcomePick | null;
  isIndividual: boolean;
}) {
  if (!strongest) return null;
  return (
    <LinkCard
      to={
        isIndividual
          ? `/quick-quiz?chapter=${strongest.chapter_id}`
          : `/learn/chapters/${strongest.chapter_id}`
      }
      title="Your strongest topic"
      cta={isIndividual ? "Practise it" : "Open the chapter"}
    >
      <span className="line-clamp-2">{strongest.description}</span>
      <span className="mt-1 block text-xs">
        Chapter {strongest.chapter_number} · {Math.round((strongest.mastery ?? 0) * 100)}%
      </span>
    </LinkCard>
  );
}

function MistakesCard() {
  const { data } = useMyMistakes({ limit: 1 });
  const n = data?.total_active ?? 0;
  if (n === 0) return null;
  return (
    <LinkCard to="/me/mistakes" title="Mistakes to review" cta="Review mistakes">
      {n} {n === 1 ? "question is" : "questions are"} waiting. Fixing them is the
      fastest way to improve.
    </LinkCard>
  );
}

/** The right-hand column of the learner home page (see the ordering note below). */
export function HomeAside({
  strongest,
  isIndividual,
  quizHref,
  quizLabel,
}: {
  strongest: OutcomePick | null;
  isIndividual: boolean;
  quizHref: string;
  quizLabel: string;
}) {
  // Two groups with explicit `order`, so on a phone (where the page is a
  // single column) the purpose card and weekly goal come right after the
  // "Up next" card, and the info cards come after the subjects. From the
  // large breakpoint up they simply stack in the side column.
  return (
    <>
      <div className="order-2 space-y-5 lg:order-none">
        <PurposeCard quizHref={quizHref} quizLabel={quizLabel} />
        <WeekCard />
      </div>
      <div className="order-4 space-y-5 lg:order-none">
        <VideoCard />
        <StrongestCard strongest={strongest} isIndividual={isIndividual} />
        <MistakesCard />
      </div>
    </>
  );
}
