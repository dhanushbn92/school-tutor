import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Dices,
  Eye,
  Layers,
  Loader2,
  RefreshCw,
  Shuffle,
  Timer,
  Trophy,
} from "lucide-react";
import { toast } from "sonner";
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
import { api, humanError } from "@/lib/api";
import { useSurpriseQuestion } from "@/lib/queries";
import { BRAND_ARROW_COLORS } from "@/lib/brand";
import { useMascot } from "@/lib/mascotContext";
import type { PracticeCardQuestion } from "@/lib/queries";

/**
 * Practice variety hub — Stage 7 of the child-centric roadmap.
 *
 * Three modes that complement the main quick-quiz flow:
 *   1. Speedrun     — 5 questions, ~3 minutes. Reuses /me/quick-quiz
 *                     under the hood; this page just configures and
 *                     launches it.
 *   2. Surprise me  — one random question with answer-reveal. No
 *                     grading, no submission — pure curiosity.
 *   3. Flashcards   — N factual cards with a flip UX. Lives on its
 *                     own route (/practice/flashcards) because the
 *                     flow runs across many cards.
 *
 * Quiz fatigue is real; the goal here is to give a learner who
 * doesn't feel like a "full quiz" something else to chew on for 30
 * seconds. The mascot reacts to each mode with a quick context
 * line so the hub feels alive.
 */
export function PracticePage() {
  const navigate = useNavigate();
  const mascot = useMascot();
  const [launching, setLaunching] = useState(false);

  async function launchSpeedrun() {
    if (launching) return;
    setLaunching(true);
    mascot.reactWith("DRAWN", {
      message: "5 questions, 3 minutes — go!",
      autoResetMs: 4000,
    });
    try {
      // Reuse the existing quick-quiz endpoint. We need a chapter_id
      // and the easiest way is to grab the first one the learner has
      // access to — fetch surprise once just to find a chapter.
      // (A future iteration could let the learner pick the chapter
      // from a dropdown here; for v1 we use the syllabus default.)
      const seed = await api.get<PracticeCardQuestion>("/me/practice/surprise");
      const chapter_id = seed.data.chapter_id;
      if (!chapter_id) {
        throw new Error("No chapter available for your syllabus yet.");
      }
      const { data } = await api.post<{ id: number }>("/me/quick-quiz", {
        chapter_id,
        question_count: 5,
        kind: "objective",
        duration_minutes: 3,
        title: "Speedrun · 5 questions",
      });
      navigate(`/assessments/${data.id}/take`);
    } catch (err) {
      toast.error(humanError(err));
    } finally {
      setLaunching(false);
    }
  }

  return (
    <ThemedPage>
      <PageHeader
        title="Practice your way"
        description="Three quick modes for the days a full quiz feels like too much. None of these break your streak — they make it."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <ModeCard
          title="Speedrun"
          tagline="5 questions · 3 minutes"
          description="A tight burst of objective questions. Auto-submits when the timer hits zero."
          accentColor={BRAND_ARROW_COLORS.orange}
          icon={<Timer className="h-5 w-5" />}
          cta={launching ? "Launching…" : "Start speedrun"}
          ctaDisabled={launching}
          onClick={launchSpeedrun}
        />

        <ModeCard
          title="Surprise me"
          tagline="One random question"
          description="Don't know where to start? Tap the dice. We'll pull one question from your whole syllabus."
          accentColor={BRAND_ARROW_COLORS.purple}
          icon={<Dices className="h-5 w-5" />}
          cta="Roll the dice"
          ctaDisabled={false}
          // Surprise renders inline below, so the card's CTA is a
          // visual cue — actual rendering happens in <SurpriseSection />.
          // Scroll to the section on click so a small-screen learner
          // doesn't have to hunt for it.
          onClick={() => {
            const el = document.getElementById("surprise-section");
            el?.scrollIntoView({ behavior: "smooth", block: "start" });
          }}
        />

        <ModeCard
          title="Flashcards"
          tagline="Flip · got it · tricky"
          description="A deck of factual cards with the answer on the back. Mark each as 'got it' or 'tricky' as you go."
          accentColor={BRAND_ARROW_COLORS.teal}
          icon={<Layers className="h-5 w-5" />}
          cta="Open flashcards"
          ctaDisabled={false}
          asLink="/practice/flashcards"
        />
      </div>

      <SurpriseSection />
    </ThemedPage>
  );
}

/* ----------------------------------------------------------------- */
/* Mode card                                                         */
/* ----------------------------------------------------------------- */

function ModeCard({
  title,
  tagline,
  description,
  icon,
  accentColor,
  cta,
  ctaDisabled,
  onClick,
  asLink,
}: {
  title: string;
  tagline: string;
  description: string;
  icon: React.ReactNode;
  accentColor: string;
  cta: string;
  ctaDisabled: boolean;
  onClick?: () => void;
  asLink?: string;
}) {
  return (
    <Card className="overflow-hidden transition-shadow hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <span
            className="inline-flex h-10 w-10 items-center justify-center rounded-full"
            style={{
              backgroundColor: `${accentColor}1a`,
              color: accentColor,
              border: `1px solid ${accentColor}40`,
            }}
          >
            {icon}
          </span>
          <div>
            <CardTitle className="font-display text-lg">{title}</CardTitle>
            <CardDescription className="text-[11px] uppercase tracking-wide">
              {tagline}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm leading-relaxed text-(--color-muted-foreground)">
          {description}
        </p>
        {asLink ? (
          <Button asChild className="w-full" disabled={ctaDisabled}>
            <Link to={asLink}>
              {cta} <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        ) : (
          <Button onClick={onClick} disabled={ctaDisabled} className="w-full">
            {ctaDisabled ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : null}
            {cta}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

/* ----------------------------------------------------------------- */
/* Surprise me — inline reveal                                       */
/* ----------------------------------------------------------------- */

function SurpriseSection() {
  const [active, setActive] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const mascot = useMascot();
  const q = useSurpriseQuestion(active);

  function rollAgain() {
    setRevealed(false);
    setActive(true);
    mascot.reactWith("DRAWN", {
      message: "Just look at it. No pressure.",
      autoResetMs: 3500,
    });
    q.refetch();
  }

  function reveal() {
    setRevealed(true);
    mascot.reactWith("FIRES", {
      message: "Mystery solved!",
      autoResetMs: 3000,
    });
  }

  if (!active) {
    return (
      <div id="surprise-section" className="mt-8 scroll-mt-20">
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
            <Shuffle className="h-8 w-8 text-(--color-muted-foreground)" />
            <div className="font-display text-base">Roll the dice when you're ready</div>
            <p className="max-w-md text-xs text-(--color-muted-foreground)">
              One random question from your whole syllabus appears here. No
              grading, no streak risk — just a quick wonder.
            </p>
            <Button
              onClick={() => {
                setActive(true);
                mascot.reactWith("DRAWN", {
                  message: "Just look at it. No pressure.",
                  autoResetMs: 3500,
                });
              }}
            >
              <Dices className="h-4 w-4" /> Roll the dice
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div id="surprise-section" className="mt-8 scroll-mt-20">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Dices className="h-4 w-4 text-(--color-primary)" />
              Surprise me
            </CardTitle>
            <Button size="sm" variant="outline" onClick={rollAgain} disabled={q.isFetching}>
              {q.isFetching ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              Another one
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {q.isLoading ? (
            <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
              <Loader2 className="h-4 w-4 animate-spin" /> Picking one…
            </div>
          ) : q.error || !q.data ? (
            <div className="text-sm text-(--color-destructive)">
              Couldn't pick a surprise right now. Try again in a moment.
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-xs text-(--color-muted-foreground)">
                <Badge variant="outline">{q.data.type}</Badge>
                <Badge variant="outline">{q.data.difficulty}</Badge>
                {q.data.outcome_code && (
                  <Badge variant="secondary">{q.data.outcome_code}</Badge>
                )}
              </div>
              <p className="text-base leading-relaxed">{q.data.text}</p>
              {q.data.type === "MCQ" && q.data.options?.choices && (
                <ul className="ml-4 list-disc text-sm text-(--color-foreground)">
                  {q.data.options.choices.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              )}
              {!revealed ? (
                <Button onClick={reveal} variant="outline">
                  <Eye className="h-4 w-4" /> Show the answer
                </Button>
              ) : (
                <div className="rounded-md border border-(--color-success) bg-[color-mix(in_oklab,var(--color-success)_8%,transparent)] p-3 text-sm">
                  <div className="flex items-center gap-2 font-medium">
                    <Trophy className="h-4 w-4 text-(--color-success)" />
                    Answer
                  </div>
                  <div className="mt-1 whitespace-pre-wrap">{q.data.correct_answer}</div>
                  {q.data.explanation && (
                    <div className="mt-3 border-t border-(--color-border) pt-2 text-xs text-(--color-muted-foreground)">
                      <span className="font-medium text-(--color-foreground)">Why:</span>{" "}
                      {q.data.explanation}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

