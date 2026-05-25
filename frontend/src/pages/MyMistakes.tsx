import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  HelpCircle,
  Loader2,
  PartyPopper,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { TellMeMore } from "@/components/TellMeMore";
import { ReadAloudButton } from "@/components/ReadAloudButton";
import { useExplainTier, useMyMistakes, useRetryMistake } from "@/lib/queries";
import { useMascot } from "@/lib/mascotContext";
import {
  maybePlay,
  playCorrectChime,
  playNotYetChime,
  playStruggleSuccessChime,
} from "@/lib/speech";
import type { LearnerMistakeEntry, MistakeRetryResult } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

/**
 * "Things I got wrong" — the learner's personal review pool, Stage 2
 * of the child-centric roadmap.
 *
 * Lists every question the learner has answered incorrectly across
 * any quiz / worksheet (auto-gradable types only — subjective answers
 * don't have an objective verdict to key off). Each card offers a
 * single-question retry that grades inline and either resets or
 * advances the "consecutive corrects" counter. Two correct answers
 * in a row (the twice-right rule) resolve the row and it drops out
 * of the active list — a small guard against lucky guesses
 * prematurely retiring a question from review.
 *
 * No filters yet; if the active list ever grows beyond a screenful
 * we'll bolt on chapter / subject filter chips (the GET endpoint
 * already accepts both).
 */
export function MyMistakesPage() {
  const mistakesQ = useMyMistakes({ limit: 200 });

  if (mistakesQ.isLoading) {
    return (
      <ThemedPage>
        <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading your mistakes…
        </div>
      </ThemedPage>
    );
  }

  const data = mistakesQ.data;
  const items = data?.items ?? [];
  const total = data?.total_active ?? 0;

  return (
    <ThemedPage>
      <PageHeader
        title="Things I got wrong"
        description={
          total === 0
            ? "Nothing to review right now — you're all caught up."
            : `${total} question${total === 1 ? "" : "s"} waiting for another try. Two in a row gets them off the list.`
        }
        actions={
          <Button asChild variant="outline">
            <Link to="/">
              <ArrowLeft className="h-4 w-4" /> Back to dashboard
            </Link>
          </Button>
        }
      />

      {items.length === 0 ? (
        <Empty
          icon={<Sparkles className="h-6 w-6" />}
          title="No active mistakes"
          description="When you get something wrong, it'll show up here for a retry. Two correct retries in a row clear it."
          action={
            <Button asChild>
              <Link to="/quick-quiz">Start a quiz</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4">
          {items.map((entry) => (
            <MistakeCard key={entry.question_id} entry={entry} />
          ))}
        </div>
      )}
    </ThemedPage>
  );
}

/** One question card with inline retry. State is local to the card so
 *  the learner can be mid-retry on N cards without anything stomping
 *  on each other. */
function MistakeCard({ entry }: { entry: LearnerMistakeEntry }) {
  const retry = useRetryMistake();
  const mascot = useMascot();
  const [answer, setAnswer] = useState<string>("");
  const [verdict, setVerdict] = useState<MistakeRetryResult | null>(null);

  const choices = useMemo<string[] | null>(() => {
    if (entry.question_type === "MCQ" && entry.options) return entry.options;
    if (entry.question_type === "TRUE_FALSE") return ["True", "False"];
    return null;
  }, [entry.question_type, entry.options]);

  const isAnswered = verdict !== null;

  function submit() {
    if (retry.isPending) return;
    const text = answer.trim();
    if (!text) return; // backend treats empty as wrong; force a deliberate click
    retry.mutate(
      { question_id: entry.question_id, answer_text: text },
      {
        onSuccess: (res) => {
          setVerdict(res);
          // Stage 5 — mascot reactions for the retry verdict.
          // Stage 9 — louder celebration on success-after-struggle.
          if (res.resolved) {
            mascot.reactWith("VICTORY", {
              message: "Cleared! That mistake is off your list.",
              autoResetMs: 7000,
            });
            maybePlay(playStruggleSuccessChime);
          } else if (res.was_struggling) {
            // Correct after a wrong streak — the biggest emotional
            // moment on this page. The verdict panel shows the
            // celebration banner; we double up the mascot mood.
            mascot.reactWith("VICTORY", {
              message: "You stuck with it. That's mastery.",
              autoResetMs: 7000,
            });
            maybePlay(playStruggleSuccessChime);
          } else if (res.correct) {
            mascot.reactWith("FIRES", {
              message: "Right! One more in a row and it's gone.",
              autoResetMs: 6000,
            });
            maybePlay(playCorrectChime);
          } else {
            mascot.reactWith("RESTRING", {
              message: "Same question, fresh try — that's how mastery is built.",
              autoResetMs: 6000,
            });
            maybePlay(playNotYetChime);
          }
        },
      },
    );
  }

  function tryAgain() {
    // Reset the card to its pristine state. The next attempt is a
    // fresh round-trip — the previous verdict is gone from local
    // state, the input is empty, and the row in the active list has
    // already been refreshed by the mutation's onSuccess.
    setVerdict(null);
    setAnswer("");
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2 text-xs text-(--color-muted-foreground)">
          {entry.subject_name && <Badge variant="secondary">{entry.subject_name}</Badge>}
          {entry.chapter_title && (
            <span>
              Ch {entry.chapter_number ?? "?"} · {entry.chapter_title}
            </span>
          )}
          <span>·</span>
          <span>{entry.question_type}</span>
          <span>·</span>
          <span>{entry.marks} marks</span>
        </div>
        <CardTitle className="mt-2 text-base font-normal leading-relaxed">
          <span className="inline-flex items-start gap-2">
            <span>{entry.question_text}</span>
            <ReadAloudButton text={entry.question_text} label="Read the question" />
          </span>
        </CardTitle>
        <CardDescription>
          First missed {formatDateTime(entry.first_wrong_at)}
          {entry.consecutive_corrects > 0 && (
            <>
              {" · "}
              <span className="text-(--color-primary)">
                {entry.consecutive_corrects} correct in a row — one more clears it
              </span>
            </>
          )}
        </CardDescription>
      </CardHeader>

      <CardContent>
        {choices ? (
          <ul className="grid gap-2">
            {choices.map((choice) => {
              const selected = answer === choice;
              return (
                <li key={choice}>
                  <button
                    type="button"
                    disabled={isAnswered || retry.isPending}
                    onClick={() => setAnswer(choice)}
                    className={
                      "w-full rounded-md border px-3 py-2 text-left text-sm transition " +
                      (selected
                        ? "border-(--color-primary) bg-(--color-primary)/10"
                        : "border-(--color-border) hover:bg-(--color-muted)")
                    }
                  >
                    {choice}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <Input
            placeholder="Type your answer"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={isAnswered || retry.isPending}
          />
        )}

        {verdict && <VerdictPanel verdict={verdict} />}

        {/* Stage 9 — Hint banner. Surfaces once the wrong-streak
            has crossed the server's threshold (3 by default) OR
            the latest retry verdict says hint_available. Stays
            visible across reloads since it reads entry.hint_available
            from the persisted server state. */}
        {(entry.hint_available || verdict?.hint_available) &&
          !verdict?.correct && (
            <HintBanner questionId={entry.question_id} />
          )}

        {/* Stage 3 — "Tell me more" chain. Shown after a retry so the
            learner has seen the verdict + correct answer first. */}
        {verdict && <TellMeMore questionId={entry.question_id} />}
      </CardContent>

      <CardFooter className="justify-end gap-2">
        {!isAnswered ? (
          <Button
            onClick={submit}
            disabled={!answer.trim() || retry.isPending}
          >
            {retry.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Checking…
              </>
            ) : (
              <>
                <RotateCcw className="h-4 w-4" /> Try this again
              </>
            )}
          </Button>
        ) : (
          <Button variant="outline" onClick={tryAgain} disabled={verdict.resolved}>
            {verdict.resolved ? "Cleared!" : "Have another go"}
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

/** Inline feedback after a retry. Shows the verdict, the correct
 *  answer (always — the learner has just tried this, no point hiding
 *  it), and the explanation if the question has one. */
function VerdictPanel({ verdict }: { verdict: MistakeRetryResult }) {
  // Stage 9 — escalating celebration for success-after-struggle.
  // Same color palette as the regular "Right!" panel but with a
  // bigger headline and a PartyPopper icon to make the "you stuck
  // with it" moment visually distinct from a casual first-try win.
  if (verdict.correct && verdict.was_struggling) {
    return (
      <div className="mt-4 overflow-hidden rounded-md border-2 border-emerald-400 bg-gradient-to-br from-emerald-100 to-emerald-50 p-4 text-sm text-emerald-950 shadow-sm dark:from-emerald-950/60 dark:to-emerald-950/20 dark:text-emerald-100">
        <div className="flex items-center gap-2 font-display text-base font-semibold">
          <PartyPopper className="h-5 w-5 animate-bounce" />
          You stuck with it. That's mastery.
        </div>
        <div className="mt-1 text-xs opacity-90">
          {verdict.resolved
            ? "And that's two in a row — clearing this from your list."
            : "One more correct retry and it's off your list for good."}
        </div>
        <VerdictAnswerRow verdict={verdict} />
      </div>
    );
  }

  return (
    <div
      className={
        "mt-4 rounded-md border p-3 text-sm " +
        (verdict.correct
          ? "border-emerald-300 bg-emerald-50 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100"
          : "border-amber-300 bg-amber-50 text-amber-900 dark:bg-amber-950/40 dark:text-amber-100")
      }
    >
      <div className="flex items-center gap-2 font-medium">
        {verdict.correct ? (
          <>
            <CheckCircle2 className="h-4 w-4" />
            Right!
            {verdict.resolved
              ? " That's two in a row — clearing this from your list."
              : " One more correct and it's off the list."}
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            Not yet — have another look.
          </>
        )}
      </div>
      <VerdictAnswerRow verdict={verdict} />
    </div>
  );
}


/** Answer + explanation block used by both the regular verdict
 *  panel and the bigger "success after struggle" celebration. */
function VerdictAnswerRow({ verdict }: { verdict: MistakeRetryResult }) {
  return (
    <>
      <div className="mt-2 flex items-start justify-between gap-2 text-xs">
        <div>
          <span className="font-medium">Correct answer:</span> {verdict.correct_answer}
        </div>
        <ReadAloudButton
          text={
            verdict.correct_answer +
            (verdict.explanation ? `. ${verdict.explanation}` : "")
          }
          label="Read the answer"
        />
      </div>
      {verdict.explanation && (
        <div className="mt-1 text-xs">
          <span className="font-medium">Why:</span> {verdict.explanation}
        </div>
      )}
    </>
  );
}


/* ----------------------------------------------------------------- */
/* Stage 9 — Hint banner                                             */
/* ----------------------------------------------------------------- */

/** Surfaces once a learner has gotten the same question wrong three
 *  times in a row. One tap fetches the ANALOGY tier from Stage 3
 *  (the gentlest of the three "Tell me more" tiers — a relatable
 *  parallel rather than a worked solution). Inline reveal, no
 *  navigation away.
 *
 *  Deliberately a separate component from <TellMeMore /> because the
 *  framing here is "help me get unstuck", not "go deeper". Same
 *  endpoint under the hood.
 */
function HintBanner({ questionId }: { questionId: number }) {
  // Lazy import to keep the file lean; useExplainTier already lives
  // in queries.ts and is exercised by TellMeMore.
  const explain = useExplainTier();
  const [hintText, setHintText] = useState<string | null>(null);

  function fetchHint() {
    if (explain.isPending) return;
    explain.mutate(
      { question_id: questionId, tier: "ANALOGY" },
      {
        onSuccess: (res) => setHintText(res.text),
      },
    );
  }

  return (
    <div className="mt-4 rounded-md border border-(--color-primary) bg-[color-mix(in_oklab,var(--color-primary)_8%,transparent)] p-3">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-(--color-primary) text-(--color-primary-foreground)">
          <HelpCircle className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-medium text-(--color-foreground)">
            Stuck? Try an analogy.
          </div>
          <div className="mt-0.5 text-xs text-(--color-muted-foreground)">
            We'll pull a kinder explanation that maps this concept onto
            something familiar.
          </div>
          {!hintText && (
            <Button
              size="sm"
              variant="outline"
              className="mt-2"
              onClick={fetchHint}
              disabled={explain.isPending}
            >
              {explain.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              {explain.isPending ? "Thinking…" : "Show me a hint"}
            </Button>
          )}
          {hintText && (
            <div className="mt-2 rounded-md border border-(--color-border) bg-(--color-card) p-3 text-sm leading-relaxed">
              <div className="flex items-start gap-2">
                <div className="flex-1 whitespace-pre-line">{hintText}</div>
                <ReadAloudButton text={hintText} label="Read the hint" />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
