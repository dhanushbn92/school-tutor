import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  RotateCcw,
  Sparkles,
  XCircle,
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
import { useMyMistakes, useRetryMistake } from "@/lib/queries";
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
        onSuccess: (res) => setVerdict(res),
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
          {entry.question_text}
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
  return (
    <div
      className={
        "mt-4 rounded-md border p-3 text-sm " +
        (verdict.correct
          ? "border-emerald-300 bg-emerald-50 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100"
          : "border-rose-300 bg-rose-50 text-rose-900 dark:bg-rose-950/40 dark:text-rose-100")
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
            <XCircle className="h-4 w-4" />
            Not quite. Have another look.
          </>
        )}
      </div>
      <div className="mt-2 text-xs">
        <span className="font-medium">Correct answer:</span> {verdict.correct_answer}
      </div>
      {verdict.explanation && (
        <div className="mt-1 text-xs">
          <span className="font-medium">Why:</span> {verdict.explanation}
        </div>
      )}
    </div>
  );
}
