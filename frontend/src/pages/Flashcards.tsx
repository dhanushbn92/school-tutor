import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  HelpCircle,
  Layers,
  Loader2,
  RotateCw,
  Sparkles,
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
import { useAudioPreferences, useFlashcards } from "@/lib/queries";
import { BRAND_ARROW_COLORS } from "@/lib/brand";
import { useMascot } from "@/lib/mascotContext";
import { ReadAloudButton } from "@/components/ReadAloudButton";

/**
 * Flashcards mode — Stage 7 of the child-centric roadmap.
 *
 * A deck of factual / REMEMBER-bucket questions, one card at a time.
 * Card front is the question text; tap to flip to the answer; mark
 * each card as "got it" or "tricky" before advancing.
 *
 * Design intent: zero grading. No streak risk, no points, no
 * mistakes table. The "tricky" tally lives in component state only —
 * a future iteration can persist a `flashcard_tricky` table to power
 * a "revisit your tricky cards" surface. For v1 the tally just feeds
 * the end-of-deck summary screen.
 */

type CardVerdict = "got_it" | "tricky" | null;

export function FlashcardsPage() {
  const cardsQ = useFlashcards({ count: 10 });
  const audioPrefs = useAudioPreferences();
  const autoplay = audioPrefs.data?.autoplay_questions ?? false;
  const mascot = useMascot();
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [verdicts, setVerdicts] = useState<Record<number, CardVerdict>>({});

  const cards = cardsQ.data ?? [];
  const total = cards.length;
  const finished = total > 0 && index >= total;
  const current = !finished ? cards[index] : null;

  // Tally for the end-screen
  const tally = useMemo(() => {
    let got = 0;
    let tricky = 0;
    for (const v of Object.values(verdicts)) {
      if (v === "got_it") got += 1;
      else if (v === "tricky") tricky += 1;
    }
    return { got, tricky };
  }, [verdicts]);

  function flip() {
    setFlipped((f) => !f);
  }

  function mark(verdict: CardVerdict) {
    if (!current) return;
    setVerdicts((v) => ({ ...v, [current.id]: verdict }));
    if (verdict === "got_it") {
      mascot.reactWith("FIRES", {
        message: "Locked in!",
        autoResetMs: 1500,
      });
    } else if (verdict === "tricky") {
      mascot.reactWith("RESTRING", {
        message: "Worth a second look.",
        autoResetMs: 2000,
      });
    }
    // Advance to the next card. Reset the flip state so the next
    // card opens question-side up.
    setIndex((i) => i + 1);
    setFlipped(false);
  }

  function restart() {
    setIndex(0);
    setFlipped(false);
    setVerdicts({});
    cardsQ.refetch();
  }

  return (
    <ThemedPage>
      <PageHeader
        title="Flashcards"
        description="Flip each card to see the answer. Mark how it felt — no scores, no streak risk."
        actions={
          <Button asChild variant="outline">
            <Link to="/practice">
              <ArrowLeft className="h-4 w-4" /> Back to practice
            </Link>
          </Button>
        }
      />

      {cardsQ.isLoading ? (
        <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
          <Loader2 className="h-4 w-4 animate-spin" /> Picking your deck…
        </div>
      ) : cardsQ.error ? (
        <Empty
          icon={<Layers className="h-6 w-6" />}
          title="Couldn't load cards"
          description="Try again in a moment. If this keeps happening, your syllabus might not have factual questions yet."
          action={
            <Button onClick={() => cardsQ.refetch()}>
              <RotateCw className="h-4 w-4" /> Retry
            </Button>
          }
        />
      ) : total === 0 ? (
        <Empty
          icon={<Layers className="h-6 w-6" />}
          title="No flashcards yet"
          description="Your syllabus doesn't have factual cards available right now. Check back after more questions land in the bank."
        />
      ) : finished ? (
        <DeckSummary tally={tally} total={total} onRestart={restart} />
      ) : current ? (
        <div className="mx-auto max-w-2xl">
          <div className="mb-3 flex items-center justify-between text-xs text-(--color-muted-foreground)">
            <span>
              Card {index + 1} of {total}
            </span>
            <span className="flex items-center gap-2">
              <Badge variant="success" className="text-[10px]">
                Got it: {tally.got}
              </Badge>
              <Badge variant="warning" className="text-[10px]">
                Tricky: {tally.tricky}
              </Badge>
            </span>
          </div>

          <Flashcard
            // Key on the card id so autoStart re-fires per new card.
            key={current.id}
            question={current.text}
            answer={current.correct_answer}
            explanation={current.explanation}
            outcomeCode={current.outcome_code}
            flipped={flipped}
            onFlip={flip}
            autoplay={autoplay}
          />

          <div className="mt-4 grid grid-cols-2 gap-3">
            <Button
              variant="outline"
              className="border-(--color-warning) text-(--color-warning) hover:bg-[color-mix(in_oklab,var(--color-warning)_10%,transparent)]"
              onClick={() => mark("tricky")}
            >
              <HelpCircle className="h-4 w-4" /> Tricky
            </Button>
            <Button
              className="bg-(--color-success) text-white hover:bg-[color-mix(in_oklab,var(--color-success)_85%,black)]"
              onClick={() => mark("got_it")}
            >
              <CheckCircle2 className="h-4 w-4" /> Got it
            </Button>
          </div>
          <p className="mt-3 text-center text-xs text-(--color-muted-foreground)">
            Tip: tap the card to flip it before deciding.
          </p>
        </div>
      ) : null}
    </ThemedPage>
  );
}

/* ----------------------------------------------------------------- */
/* Flippable card                                                    */
/* ----------------------------------------------------------------- */

function Flashcard({
  question,
  answer,
  explanation,
  outcomeCode,
  flipped,
  onFlip,
  autoplay,
}: {
  question: string;
  answer: string;
  explanation: string | null;
  outcomeCode: string | null;
  flipped: boolean;
  onFlip: () => void;
  autoplay: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onFlip}
      // The card uses CSS 3D transform to flip in place. We use a
      // simple `aria-pressed` flag plus a visual rotate to keep
      // the markup minimal — front and back are stacked absolute
      // children inside a single perspective container.
      aria-pressed={flipped}
      aria-label={flipped ? "Show question" : "Show answer"}
      className="relative block w-full text-left"
      style={{ perspective: "1200px", height: "320px" }}
    >
      <div
        className="absolute inset-0 transition-transform duration-500"
        style={{
          transformStyle: "preserve-3d",
          transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)",
        }}
      >
        {/* Front — question */}
        <div
          className="absolute inset-0 flex flex-col rounded-xl border border-(--color-border) bg-(--color-card) p-6 shadow-sm"
          style={{ backfaceVisibility: "hidden" }}
        >
          <div className="mb-2 flex items-center justify-between text-xs text-(--color-muted-foreground)">
            <span className="flex items-center gap-1">
              <Layers className="h-3.5 w-3.5" /> Question
            </span>
            <div className="flex items-center gap-2">
              {outcomeCode && (
                <Badge variant="secondary" className="text-[10px]">
                  {outcomeCode}
                </Badge>
              )}
              {/* Stop click-propagation so tapping 🔊 doesn't also
                  flip the card. */}
              <span onClick={(e) => e.stopPropagation()}>
                <ReadAloudButton
                  text={question}
                  autoStart={autoplay}
                  label="Read the question"
                />
              </span>
            </div>
          </div>
          <div className="flex flex-1 items-center justify-center">
            <p className="font-display text-lg leading-relaxed text-(--color-foreground)">
              {question}
            </p>
          </div>
          <div className="mt-2 text-center text-xs text-(--color-muted-foreground)">
            Tap to flip
          </div>
        </div>

        {/* Back — answer + explanation */}
        <div
          className="absolute inset-0 flex flex-col rounded-xl border border-(--color-border) p-6 shadow-sm"
          style={{
            backfaceVisibility: "hidden",
            transform: "rotateY(180deg)",
            backgroundColor: `color-mix(in oklab, ${BRAND_ARROW_COLORS.green} 6%, var(--color-card))`,
          }}
        >
          <div className="mb-2 flex items-center justify-between gap-2 text-xs font-medium text-(--color-success)">
            <span className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5" /> Answer
            </span>
            <span onClick={(e) => e.stopPropagation()}>
              <ReadAloudButton
                text={answer + (explanation ? `. ${explanation}` : "")}
                label="Read the answer"
              />
            </span>
          </div>
          <div className="flex-1 overflow-auto">
            <p className="font-display text-base leading-relaxed text-(--color-foreground)">
              {answer}
            </p>
            {explanation && (
              <p className="mt-3 border-t border-(--color-border) pt-3 text-xs leading-relaxed text-(--color-muted-foreground)">
                <span className="font-medium text-(--color-foreground)">Why:</span>{" "}
                {explanation}
              </p>
            )}
          </div>
          <div className="mt-2 text-center text-xs text-(--color-muted-foreground)">
            Tap to flip back
          </div>
        </div>
      </div>
    </button>
  );
}

/* ----------------------------------------------------------------- */
/* Deck-finished summary                                             */
/* ----------------------------------------------------------------- */

function DeckSummary({
  tally,
  total,
  onRestart,
}: {
  tally: { got: number; tricky: number };
  total: number;
  onRestart: () => void;
}) {
  return (
    <Card className="mx-auto max-w-xl">
      <CardHeader>
        <CardTitle className="font-display text-xl">Deck done!</CardTitle>
        <CardDescription>
          {tally.tricky === 0
            ? "Clean run. Want a fresh deck?"
            : `${tally.tricky} card${tally.tricky === 1 ? "" : "s"} flagged as tricky — worth circling back tomorrow.`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-center">
          <div className="rounded-md border border-(--color-success) bg-[color-mix(in_oklab,var(--color-success)_8%,transparent)] p-4">
            <div className="font-display text-3xl font-semibold leading-none">
              {tally.got}
            </div>
            <div className="mt-1 text-xs text-(--color-muted-foreground)">
              Got it
            </div>
          </div>
          <div className="rounded-md border border-(--color-warning) bg-[color-mix(in_oklab,var(--color-warning)_10%,transparent)] p-4">
            <div className="font-display text-3xl font-semibold leading-none">
              {tally.tricky}
            </div>
            <div className="mt-1 text-xs text-(--color-muted-foreground)">
              Tricky
            </div>
          </div>
        </div>
        <div className="text-center text-xs text-(--color-muted-foreground)">
          {total} cards · {tally.got + tally.tricky} marked
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={onRestart} className="flex-1">
            <RotateCw className="h-4 w-4" /> Fresh deck
          </Button>
          <Button asChild variant="outline" className="flex-1">
            <Link to="/practice">
              Back to practice <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
