import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Loader2,
  Send,
  Sparkles,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { formatClock, useQuizTimer } from "@/lib/useQuizTimer";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Empty } from "@/components/ui/empty";
import { humanError } from "@/lib/api";
import {
  useAssessment,
  useMySubmissions,
  useQuestionsByIds,
  useSubmission,
  useSubmitAssessment,
} from "@/lib/queries";
import type {
  CognitiveBucket,
  Question,
  QuestionType,
  Submission,
  SubmissionAnswer,
} from "@/lib/types";
import { BLOOM_TO_BUCKET, BUCKET_LABEL } from "@/lib/types";
import { cn, formatMarks } from "@/lib/utils";
import { RichExplanationView } from "@/components/RichExplanation";
import { TellMeMore } from "@/components/TellMeMore";

const BUCKET_ORDER: CognitiveBucket[] = ["FACTUAL", "UNDERSTANDING", "APPLICATION"];

// Subjective question types are not auto-graded — the student self-evaluates
// against the answer key shown in the results view. AI grading will replace
// this stub later (the previous keyword-rubric grader was retired because
// rule-based scoring of free text was unreliable).
const SUBJECTIVE_TYPES: ReadonlySet<QuestionType> = new Set<QuestionType>([
  "SHORT_ANSWER",
  "LONG_ANSWER",
  "CASE_BASED",
]);

function isSubjectiveType(t: QuestionType | undefined): boolean {
  return t !== undefined && SUBJECTIVE_TYPES.has(t);
}

export function TakeAssessmentPage() {
  const { assessmentId } = useParams();
  const aid = assessmentId ? Number(assessmentId) : undefined;
  const assessmentQ = useAssessment(aid);

  const questionIds = useMemo(
    () =>
      [...(assessmentQ.data?.questions ?? [])]
        .sort((a, b) => a.order - b.order)
        .map((aq) => aq.question_id),
    [assessmentQ.data?.questions],
  );
  const questionsQ = useQuestionsByIds(questionIds);

  const [answers, setAnswers] = useState<Record<number, string>>({});
  const submitMut = useSubmitAssessment();
  const [submission, setSubmission] = useState<Submission | null>(null);

  // If the learner already has a submission for this assessment, load it so
  // we render the results view immediately (no re-take attempt).
  const mySubsQ = useMySubmissions();
  const existingSubId = mySubsQ.data?.find((s) => s.assessment_id === aid)?.id;
  const existingSubQ = useSubmission(existingSubId);

  // When the assessment loads, reset answers if the question set changes.
  useEffect(() => {
    setAnswers({});
    setSubmission(null);
  }, [aid]);

  // Once both the existing submission AND every question has loaded, drop
  // into the results view. Gating on `questionsQ.data` avoids a flash of
  // half-rendered ResultCards (no correct answer, no rich explanation)
  // while questions are still in flight.
  useEffect(() => {
    if (
      existingSubQ.data &&
      submission === null &&
      questionsQ.data &&
      questionsQ.data.length > 0
    ) {
      setSubmission(existingSubQ.data);
    }
  }, [existingSubQ.data, submission, questionsQ.data]);

  // Hooks MUST live above the conditional returns below — moving them
  // down breaks Rules of Hooks (number of hooks differs across renders).
  const questionsById = useMemo(
    () => new Map((questionsQ.data ?? []).map((q) => [q.id, q])),
    [questionsQ.data],
  );

  // Time-bound assessment? duration comes from either the server
  // (assessment.duration_minutes — teacher-assigned quizzes set this
  // at creation) or, as a fallback, from a localStorage entry the
  // QuickQuiz form wrote on creation (for self-started quizzes where
  // the backend dropped the field). Whichever produces a positive
  // value drives the timer.
  const localFallback = (() => {
    if (aid === undefined || typeof window === "undefined") return null;
    try {
      const raw = window.localStorage.getItem(`dhananjaya:quiz-duration:${aid}`);
      const n = raw == null ? NaN : Number(raw);
      return Number.isFinite(n) && n > 0 ? n : null;
    } catch {
      return null;
    }
  })();
  const effectiveDuration =
    assessmentQ.data?.duration_minutes ?? localFallback ?? null;
  // isTimed says "we have a countdown deadline"; the elapsed-time
  // display is shown for both timed AND untimed attempts so every
  // learner sees a working clock at the top of the page. The timer
  // runs as long as the quiz is being taken (no submission yet)
  // and an assessment has loaded — totalSeconds will be 0 on
  // untimed attempts, which the banner detects to switch from
  // countdown mode to elapsed-time mode.
  const isTimed = effectiveDuration !== null && submission === null;
  const timerEnabled = assessmentQ.data !== undefined && submission === null;
  const {
    secondsLeft,
    totalSeconds,
    elapsedSeconds,
    clear: clearTimer,
  } = useQuizTimer({
    assessmentId: aid,
    durationMinutes: effectiveDuration,
    enabled: timerEnabled,
  });

  // Auto-submit guard — fire at most once per page lifetime. Without
  // this, a transient failure on the auto-submit could re-fire the
  // effect every tick.
  const autoSubmitFiredRef = useRef(false);

  // handleSubmit is declared as a function declaration (hoisted) so the
  // auto-submit useEffect below can reference it even though it lives
  // earlier in source order. Function declarations are hoisted; const
  // arrow functions are not — keeping this as a declaration is
  // deliberate.
  async function handleSubmit(e?: FormEvent) {
    if (e) e.preventDefault();
    if (!assessmentQ.data) return;
    const stringified: Record<string, string> = {};
    for (const [k, v] of Object.entries(answers)) {
      if (v && v.trim()) stringified[k] = v;
    }
    try {
      const sub = await submitMut.mutateAsync({
        assessment_id: assessmentQ.data.id,
        answers: stringified,
      });
      setSubmission(sub);
      // Backend always evaluates objective questions immediately;
      // subjective ones are left for student self-review against the
      // answer key. The toast surfaces only the auto-scored portion.
      const hasSubjective = sub.answers.some((sa) => sa.marks_awarded === null);
      toast.success(
        hasSubjective
          ? `Submitted — review your subjective answers below`
          : `Submitted — ${sub.total_awarded}/${sub.max_marks}`,
      );
      // Clear the persisted start time so a future re-open doesn't race
      // a fresh countdown against the existing submission.
      clearTimer();
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  // Auto-submit when the timer hits zero. Runs only if (a) the quiz is
  // time-bound, (b) it hasn't fired yet, (c) the user hasn't already
  // submitted, and (d) the submit mutation isn't already in flight.
  // The toast warns the learner so the submission doesn't feel sudden.
  useEffect(() => {
    if (!isTimed) return;
    if (autoSubmitFiredRef.current) return;
    if (submission) return;
    if (submitMut.isPending) return;
    if (secondsLeft > 0) return;
    autoSubmitFiredRef.current = true;
    toast.warning("Time's up — submitting your answers now.");
    // Intentional setState-in-effect: this effect is the bridge
    // between the timer (external state) and the submission. Calling
    // handleSubmit (which mutates state) is the whole point. The ref
    // guards against repeated firing.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void handleSubmit();
    // We omit handleSubmit / submission / submitMut.isPending from
    // the deps array because re-running on those changes would either
    // no-op (ref guard) or cause a double submit we explicitly want
    // to avoid.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [secondsLeft, isTimed]);

  // The existing-submission auto-resume flow needs both questions and
  // the submission detail. Show "Loading your results…" while those
  // finish so the user doesn't see the take form flash before the
  // results view.
  const resumingExisting = existingSubId !== undefined && submission === null;
  if (
    assessmentQ.isLoading ||
    questionsQ.isLoading ||
    (resumingExisting && (existingSubQ.isLoading || mySubsQ.isLoading))
  ) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" />
        {resumingExisting ? "Loading your results…" : "Loading the quiz…"}
      </div>
    );
  }
  if (!assessmentQ.data || !questionsQ.data) {
    return (
      <Empty
        title="Quiz not found"
        action={
          <Button asChild variant="outline">
            <Link to="/assessments">
              <ArrowLeft className="h-4 w-4" /> Back to assessments
            </Link>
          </Button>
        }
      />
    );
  }

  const a = assessmentQ.data;

  // Results view (after submit)
  if (submission) {
    // Split answers by who grades them. Objective questions are auto-scored
    // and contribute to the displayed score; subjective ones are left for
    // student self-evaluation against the answer key.
    const objectiveAnswers = submission.answers.filter(
      (sa) => sa.marks_awarded !== null,
    );
    const subjectiveAnswers = submission.answers.filter(
      (sa) => sa.marks_awarded === null,
    );
    const objectiveAwarded = objectiveAnswers.reduce(
      (sum, sa) => sum + (sa.marks_awarded ?? 0),
      0,
    );
    const objectiveMax = objectiveAnswers.reduce(
      (sum, sa) => sum + sa.max_marks,
      0,
    );
    return (
      <ThemedPage>
        <PageHeader
          title={a.title}
          description="Your results."
          actions={
            <Button asChild variant="outline">
              <Link to="/assessments">
                <ArrowLeft className="h-4 w-4" /> All assessments
              </Link>
            </Button>
          }
        />
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>
              {objectiveAnswers.length > 0 ? (
                <>
                  Auto-scored:{" "}
                  <span className="tabular-nums">
                    {objectiveAwarded}/{objectiveMax}
                  </span>
                </>
              ) : (
                <>Self-review</>
              )}
            </CardTitle>
            <CardDescription>
              {subjectiveAnswers.length > 0 ? (
                <span className="inline-flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-(--color-primary)" />
                  {subjectiveAnswers.length} subjective{" "}
                  {subjectiveAnswers.length === 1 ? "question" : "questions"}{" "}
                  for self-review · AI grading coming soon
                  <Badge variant="outline" className="ml-1">Beta</Badge>
                </span>
              ) : (
                <>All questions auto-graded.</>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BucketBreakdown answers={submission.answers} questionsById={questionsById} />
          </CardContent>
        </Card>

        <div className="space-y-3">
          {submission.answers
            .map((a, i) => ({ ...a, __index: i + 1 }))
            .map((sa) => {
              const q = questionsById.get(sa.question_id);
              return (
                <ResultCard key={sa.id} q={q} sa={sa} />
              );
            })}
        </div>
      </ThemedPage>
    );
  }

  // Take-quiz view
  //
  // Timer styling buckets — the banner gets progressively more urgent
  // as the deadline approaches. The thresholds are proportional to
  // the full duration rather than absolute seconds so a 5-minute quiz
  // and a 90-minute quiz both have a sensible warning band.
  const fractionLeft = totalSeconds > 0 ? secondsLeft / totalSeconds : 1;
  const timerIntent: "ok" | "warning" | "critical" =
    !isTimed
      ? "ok"
      : fractionLeft <= 0.1 || secondsLeft <= 30
        ? "critical"
        : fractionLeft <= 0.33
          ? "warning"
          : "ok";

  return (
    <ThemedPage>
      <PageHeader
        title={a.title}
        // PageHeader wraps `description` in a <p>, so we keep the
        // children inline-only (spans, not Badges/<p>). React was
        // logging DOM-nesting warnings (Badge → div inside p, then
        // <p> inside <p>) — those don't break rendering but they
        // were the real chatter in the console. Using spans with
        // badge-ish styling sidesteps both warnings without losing
        // the visual treatment.
        description={
          <>
            <span className="mr-2 inline-flex items-center rounded-full border border-(--color-border) px-2.5 py-0.5 text-xs font-medium text-(--color-foreground)">
              {a.type}
            </span>
            {a.instructions && (
              <span className="text-sm text-(--color-muted-foreground)">
                {a.instructions}
              </span>
            )}
          </>
        }
        actions={
          <Button asChild variant="outline">
            <Link to="/assessments">
              <ArrowLeft className="h-4 w-4" /> Cancel
            </Link>
          </Button>
        }
      />

      {/* Live timer banner — always visible while the quiz is being
          taken. Two modes:
            - Timed (effectiveDuration set): shows a countdown.
              Colour shifts ok → warning → critical as the deadline
              approaches; critical state pulses.
            - Untimed: shows elapsed time so the learner has a sense
              of how long they've been at it. No colour shift, no
              auto-submit.
          Either way the banner is unmistakable at the top of the
          page — no more "where's my timer?" confusion. */}
      <div
        className={cn(
          "sticky top-14 z-10 mb-4 flex items-center justify-between gap-3 rounded-md border px-4 py-2.5 text-sm shadow-sm backdrop-blur",
          isTimed && timerIntent === "ok" &&
            "border-(--color-border) bg-(--color-card)/95 text-(--color-foreground)",
          isTimed && timerIntent === "warning" &&
            "border-(--color-warning) bg-[color-mix(in_oklab,var(--color-warning)_14%,var(--color-card))] text-(--color-foreground)",
          isTimed && timerIntent === "critical" &&
            "border-(--color-destructive) bg-[color-mix(in_oklab,var(--color-destructive)_14%,var(--color-card))] text-(--color-foreground)",
          isTimed && timerIntent === "critical" && "animate-pulse",
          !isTimed &&
            "border-(--color-border) bg-(--color-card)/95 text-(--color-foreground)",
        )}
        role="status"
        aria-live="polite"
      >
        <span className="inline-flex items-center gap-2 font-medium">
          <Clock className="h-4 w-4" />
          {isTimed ? "Time remaining" : "Elapsed time"}
        </span>
        <span className="flex items-center gap-3">
          <span className="text-lg font-semibold tabular-nums leading-none">
            {isTimed ? formatClock(secondsLeft) : formatClock(elapsedSeconds)}
          </span>
          <span className="hidden text-xs text-(--color-muted-foreground) sm:inline">
            {isTimed
              ? `of ${effectiveDuration} min total`
              : "Untimed — take as long as you need"}
          </span>
        </span>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        {questionIds.map((qid, idx) => {
          const q = questionsById.get(qid);
          if (!q) return null;
          return (
            <QuestionInput
              key={qid}
              index={idx + 1}
              question={q}
              value={answers[qid] ?? ""}
              onChange={(v) => setAnswers((prev) => ({ ...prev, [qid]: v }))}
            />
          );
        })}

        <div className="sticky bottom-4 flex justify-end gap-2">
          <Button
            type="submit"
            disabled={submitMut.isPending}
            className="shadow-lg"
            size="lg"
          >
            {submitMut.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Submit quiz
          </Button>
        </div>
      </form>
    </ThemedPage>
  );
}

function QuestionInput({
  index,
  question,
  value,
  onChange,
}: {
  index: number;
  question: Question;
  value: string;
  onChange: (v: string) => void;
}) {
  const choices = question.options?.choices ?? [];

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2 text-xs text-(--color-muted-foreground)">
          <Badge variant="outline">{question.type}</Badge>
          <Badge variant="secondary">{question.difficulty}</Badge>
          <span>{question.marks} marks</span>
          {question.outcome_code && <Badge variant="outline">{question.outcome_code}</Badge>}
        </div>
        <CardTitle className="mt-2 text-base font-medium leading-snug">
          Q{index}. {question.text}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {(question.type === "MCQ" || question.type === "TRUE_FALSE") && choices.length > 0 ? (
          <div className="space-y-2">
            {choices.map((choice) => (
              <label
                key={choice}
                className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-md border border-(--color-border) px-3 py-2 text-sm transition-colors",
                  value === choice
                    ? "border-(--color-primary) bg-[color-mix(in_oklab,var(--color-primary)_10%,transparent)]"
                    : "hover:bg-(--color-muted)",
                )}
              >
                <input
                  type="radio"
                  name={`q-${question.id}`}
                  value={choice}
                  checked={value === choice}
                  onChange={(e) => onChange(e.target.value)}
                />
                {choice}
              </label>
            ))}
          </div>
        ) : question.type === "FILL_BLANK" ? (
          <div className="space-y-1.5">
            <Label htmlFor={`q-${question.id}`} className="sr-only">
              Your answer
            </Label>
            <Input
              id={`q-${question.id}`}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder="Fill in the blank…"
            />
          </div>
        ) : (
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            rows={question.type === "LONG_ANSWER" ? 6 : 3}
            placeholder="Your answer…"
            className="flex w-full rounded-md border border-(--color-input) bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-(--color-muted-foreground) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--color-ring)"
          />
        )}
      </CardContent>
    </Card>
  );
}

function ResultCard({ q, sa }: { q: Question | undefined; sa: SubmissionAnswer & { __index: number } }) {
  const subjective = isSubjectiveType(q?.type);
  // Auto-graded objective verdicts. For subjective questions the platform
  // doesn't compute correctness — the student self-evaluates below.
  const correct =
    !subjective && q && sa.marks_awarded !== null && sa.marks_awarded === sa.max_marks;
  const wrong =
    !subjective && sa.marks_awarded !== null && sa.marks_awarded === 0;
  const partial =
    !subjective &&
    sa.marks_awarded !== null &&
    sa.marks_awarded > 0 &&
    sa.marks_awarded < sa.max_marks;

  const choices = q?.options?.choices ?? [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2 text-xs text-(--color-muted-foreground)">
            {q && <Badge variant="outline">{q.type}</Badge>}
            {q && <Badge variant="secondary">{q.difficulty}</Badge>}
            {q?.outcome_code && <Badge variant="outline">{q.outcome_code}</Badge>}
          </div>
          <div className="flex items-center gap-2 text-sm">
            {subjective ? (
              <Badge variant="outline" className="gap-1">
                <Sparkles className="h-3 w-3" /> Self-review
              </Badge>
            ) : correct ? (
              <Badge variant="success" className="gap-1">
                <CheckCircle2 className="h-3 w-3" /> Correct
              </Badge>
            ) : wrong ? (
              <Badge variant="destructive" className="gap-1">
                <XCircle className="h-3 w-3" /> Wrong
              </Badge>
            ) : partial ? (
              <Badge variant="warning">Partial</Badge>
            ) : null}
            {!subjective && (
              <span className="text-sm tabular-nums">
                {formatMarks(sa.marks_awarded, sa.max_marks)}
              </span>
            )}
            {subjective && (
              <span className="text-xs text-(--color-muted-foreground) tabular-nums">
                worth {sa.max_marks} {sa.max_marks === 1 ? "mark" : "marks"}
              </span>
            )}
          </div>
        </div>
        <CardTitle className="mt-2 text-base font-medium leading-snug">
          Q{sa.__index}. {q?.text ?? `Question #${sa.question_id}`}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div>
          <span className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
            Your answer
          </span>
          <div className="mt-1 rounded-md bg-(--color-muted) p-3 whitespace-pre-wrap">
            {sa.answer_text || <span className="italic text-(--color-muted-foreground)">(blank)</span>}
          </div>
        </div>
        {q && (
          <div>
            <span className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
              {subjective ? "Answer key" : "Correct answer"}
            </span>
            <div className="mt-1 rounded-md border border-(--color-success) bg-[color-mix(in_oklab,var(--color-success)_8%,transparent)] p-3 whitespace-pre-wrap">
              {q.correct_answer}
            </div>
          </div>
        )}
        {subjective && (
          // We deliberately don't try to score subjective answers right now —
          // the previous keyword-rubric grader was unreliable. Comparing
          // their answer with the key trains the student's self-assessment;
          // AI grading will replace this stub later.
          <div className="rounded-md border border-(--color-primary)/40 bg-[color-mix(in_oklab,var(--color-primary)_6%,transparent)] p-3 text-xs">
            <div className="flex items-center gap-1.5 font-medium text-(--color-foreground)">
              <Sparkles className="h-3.5 w-3.5 text-(--color-primary)" />
              Compare your answer with the key above
              <Badge variant="outline" className="ml-1">Beta</Badge>
            </div>
            <p className="mt-1 text-(--color-muted-foreground)">
              Subjective answers aren't auto-scored yet. AI-based evaluation
              is coming soon — for now, use the answer key to self-assess
              what you got right and where to revise.
            </p>
          </div>
        )}
        {q?.explanation && (
          <div className="rounded-md border border-(--color-border) bg-(--color-muted)/40 p-3 text-xs text-(--color-muted-foreground)">
            <span className="font-medium">Explanation: </span>
            {q.explanation}
          </div>
        )}
        {q?.explanation_rich && (
          <div className="rounded-md border border-(--color-border) bg-(--color-card) p-3">
            <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground) mb-2">
              Detailed walk-through
            </div>
            <RichExplanationView data={q.explanation_rich} />
          </div>
        )}
        {/* Stage 3 — "Tell me more" chain. Shown on every results card
            so the learner can dig deeper into any question they just
            saw the answer for, win or lose. */}
        {q && <TellMeMore questionId={q.id} />}
        {sa.teacher_remark && (
          <div className="rounded-md border border-(--color-warning) bg-[color-mix(in_oklab,var(--color-warning)_10%,transparent)] p-3 text-sm">
            <span className="font-medium">Teacher remark: </span>
            {sa.teacher_remark}
          </div>
        )}
        {choices.length > 0 && q?.type === "MCQ" && (
          <div className="text-xs text-(--color-muted-foreground)">
            Options were: {choices.join(" · ")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function BucketBreakdown({
  answers,
  questionsById,
}: {
  answers: SubmissionAnswer[];
  questionsById: Map<number, Question>;
}) {
  // For each bucket, `awarded`/`max` reflect only auto-graded objective
  // questions — including subjective max marks in the denominator would
  // understate the student's auto-scored performance. Subjective questions
  // are surfaced separately via `selfReview`.
  const buckets: Record<
    CognitiveBucket,
    { awarded: number; max: number; count: number; selfReview: number }
  > = {
    FACTUAL: { awarded: 0, max: 0, count: 0, selfReview: 0 },
    UNDERSTANDING: { awarded: 0, max: 0, count: 0, selfReview: 0 },
    APPLICATION: { awarded: 0, max: 0, count: 0, selfReview: 0 },
  };
  for (const a of answers) {
    const q = questionsById.get(a.question_id);
    if (!q) continue;
    const b = BLOOM_TO_BUCKET[q.cognitive_level];
    buckets[b].count += 1;
    if (a.marks_awarded === null) {
      // Subjective — left for self-review, not counted against the bucket %.
      buckets[b].selfReview += 1;
    } else {
      buckets[b].awarded += a.marks_awarded;
      buckets[b].max += a.max_marks;
    }
  }
  const anyData = BUCKET_ORDER.some((b) => buckets[b].count > 0);
  if (!anyData) return null;
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground) mb-2">
        Score by cognitive level
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {BUCKET_ORDER.map((b) => {
          const stats = buckets[b];
          if (stats.count === 0) {
            return (
              <div
                key={b}
                className="rounded-md border border-dashed border-(--color-border) px-3 py-2 text-xs text-(--color-muted-foreground)"
              >
                <div className="font-medium">{BUCKET_LABEL[b]}</div>
                <div>No questions</div>
              </div>
            );
          }
          const pct = stats.max > 0 ? Math.round((stats.awarded / stats.max) * 100) : 0;
          // All questions in this bucket are subjective — show a self-review
          // tile instead of a 0/0 score.
          const allSelfReview = stats.max === 0 && stats.selfReview > 0;
          return (
            <div
              key={b}
              className="rounded-md border border-(--color-border) bg-(--color-muted) px-3 py-2"
            >
              <div className="text-xs text-(--color-muted-foreground)">{BUCKET_LABEL[b]}</div>
              {allSelfReview ? (
                <div className="text-lg font-medium">
                  Self-review
                </div>
              ) : (
                <div className="text-lg font-medium">
                  {stats.awarded}
                  <span className="text-(--color-muted-foreground)">/{stats.max}</span>
                  <span className="ml-2 text-sm text-(--color-muted-foreground)">{pct}%</span>
                </div>
              )}
              <div className="text-[11px] text-(--color-muted-foreground)">
                {stats.count} {stats.count === 1 ? "question" : "questions"}
                {stats.selfReview > 0 && ` · ${stats.selfReview} self-review`}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
