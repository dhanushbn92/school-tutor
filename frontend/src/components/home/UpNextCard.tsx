import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { MascotFigure } from "@/components/mascot/MascotFigure";
import { GREETING_POSE } from "@/lib/mascotPoses";
import { Skeleton } from "@/components/ui/skeleton";
import type { OutcomePick } from "@/lib/progress";
import { cn } from "@/lib/utils";

interface Step {
  key: string;
  title: string;
  hint: string;
  cta: string;
  to: string;
}

const STEP_WORDS = ["One", "Two", "Three"];

/**
 * The one thing to do next, with the lesson broken into numbered steps:
 * watch the lesson (only when the chapter has videos), read the summary,
 * then practise it. Each step opens the chapter on the matching tab.
 */
export function UpNextCard({
  loading = false,
  pick,
  hasChapters,
  hasVideo,
  quizHref,
  quizLabel,
}: {
  /** True while the mastery grid is still loading. */
  loading?: boolean;
  pick: OutcomePick | null;
  /** False when the learner's syllabus has no chapters to roll up yet. */
  hasChapters: boolean;
  hasVideo: boolean;
  quizHref: string;
  quizLabel: string;
}) {
  if (loading) {
    return (
      <Card className="rounded-2xl p-6 md:p-8" aria-busy="true">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="mt-4 h-8 w-3/4" />
        <Skeleton className="mt-6 h-20 w-full rounded-2xl" />
        <Skeleton className="mt-3 h-20 w-full rounded-2xl" />
      </Card>
    );
  }

  if (!pick) {
    return (
      <Card className="flex items-center gap-6 rounded-2xl p-6 md:p-8">
        <MascotFigure
          pose={GREETING_POSE}
          className="hidden h-36 w-auto shrink-0 sm:block"
        />
        <div>
          <h2 className="font-display text-xl font-bold tracking-tight md:text-2xl">
            {hasChapters ? "Everything here is mastered" : "Start with a quiz"}
          </h2>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-(--color-muted-foreground)">
            {hasChapters
              ? "Great work. A quick quiz keeps it fresh."
              : "Take your first quiz and your next lesson shows up here."}
          </p>
          <Button asChild size="lg" className="mt-5 rounded-xl">
            <Link to={quizHref}>
              <Sparkles className="h-4 w-4" />
              {quizLabel}
            </Link>
          </Button>
        </div>
      </Card>
    );
  }

  const base = `/learn/chapters/${pick.chapter_id}`;
  const steps: Step[] = [
    ...(hasVideo
      ? [
          {
            key: "watch",
            title: "Watch the lesson",
            hint: "Start here. Pause and replay as often as you like.",
            cta: "Watch",
            to: `${base}?tab=videos`,
          },
        ]
      : []),
    {
      key: "read",
      title: "Read the summary",
      hint: "The key ideas in one short page.",
      cta: "Read",
      to: `${base}?tab=summary`,
    },
    {
      key: "practise",
      title: "Practise it",
      hint: "Worksheet and quiz. Mistakes teach the most.",
      cta: "Practise",
      to: `${base}?tab=worksheets`,
    },
  ];

  return (
    <Card className="rounded-2xl p-6 md:p-8">
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="rounded-full bg-(--color-primary)/10 px-3 py-1 text-xs font-semibold text-(--color-primary)">
          Up next
        </span>
        {pick.subject_name && (
          <span className="text-sm text-(--color-muted-foreground)">
            {pick.subject_name}
          </span>
        )}
      </div>
      <h2 className="mt-3 font-display text-xl font-bold tracking-tight md:text-2xl">
        Chapter {pick.chapter_number} · {pick.chapter_title}
      </h2>
      <p className="mt-1.5 text-sm leading-relaxed text-(--color-muted-foreground)">
        {STEP_WORDS[steps.length - 1]} {steps.length === 1 ? "step" : "steps"}. Do
        them in order and the quiz will feel easy.
      </p>

      <ol className="mt-5 space-y-3">
        {steps.map((s, i) => (
          <li
            key={s.key}
            className={cn(
              "flex flex-wrap items-center gap-3 rounded-2xl border p-4 sm:gap-4",
              i === 0
                ? "border-transparent bg-(--color-primary)/8"
                : "border-(--color-border)",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "grid h-9 w-9 shrink-0 place-items-center rounded-full font-display text-sm font-bold",
                i === 0
                  ? "bg-(--color-primary) text-(--color-primary-foreground)"
                  : "bg-(--color-muted) text-(--color-muted-foreground)",
              )}
            >
              {i + 1}
            </span>
            <div className="min-w-0 flex-1 basis-48">
              <div className="font-semibold">{s.title}</div>
              <div className="mt-0.5 text-sm text-(--color-muted-foreground)">
                {s.hint}
              </div>
            </div>
            <Button
              asChild
              size="lg"
              variant={i === 0 ? "default" : "secondary"}
              className="rounded-xl"
            >
              <Link to={s.to}>{s.cta}</Link>
            </Button>
          </li>
        ))}
      </ol>
    </Card>
  );
}
