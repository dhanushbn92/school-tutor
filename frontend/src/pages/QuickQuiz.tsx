import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { humanError } from "@/lib/api";
import {
  useChapterDetail,
  useChapters,
  useMySections,
  useQuickQuiz,
  useSubjects,
} from "@/lib/queries";
import { labelForSubject } from "@/components/BoardContextBar";

type QuizKind = "mixed" | "subjective" | "objective";

const DEFAULT_COUNT_BY_KIND: Record<QuizKind, number> = {
  mixed: 10,
  subjective: 5,
  objective: 10,
};

const KIND_LABEL: Record<QuizKind, string> = {
  mixed: "Mixed quiz",
  subjective: "Subjective test",
  objective: "Objective only",
};

const KIND_DESCRIPTION: Record<QuizKind, string> = {
  mixed: "10 questions of all types — MCQ, fill-in-the-blanks, short and long answer.",
  subjective: "5 short and long-answer questions. You'll see the model answer after submitting.",
  objective: "10 MCQ, true/false, and fill-in-the-blank questions. Auto-graded as soon as you submit.",
};

export function QuickQuizPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const presetChapterId = (() => {
    const v = searchParams.get("chapter");
    const n = v ? Number(v) : NaN;
    return Number.isFinite(n) && n > 0 ? n : undefined;
  })();
  const sectionsQ = useMySections();
  const classLevel = sectionsQ.data?.[0]?.class_level ?? undefined;
  // Arriving from a chapter page (?chapter=N): the subject comes from that
  // chapter, which may not be in the learner's own class, so list every
  // subject they can see rather than just one class.
  const subjectsQ = useSubjects(presetChapterId ? undefined : classLevel, {
    fetchAllWhenUndefined: presetChapterId !== undefined,
  });
  const presetQ = useChapterDetail(presetChapterId);
  const [pickedSubjectId, setPickedSubjectId] = useState<number | undefined>();
  const defaultSubjectId =
    presetChapterId !== undefined
      ? (presetQ.data?.subject_id ?? undefined)
      : (subjectsQ.data?.find((s) => s.name === "Science") ?? subjectsQ.data?.[0])?.id;
  const subjectId = pickedSubjectId ?? defaultSubjectId;
  const chaptersQ = useChapters({ class_level: subjectId ? undefined : classLevel, subject_id: subjectId });
  const [pickedChapterId, setPickedChapterId] = useState<number | undefined>(presetChapterId);
  // Until a chapter is picked, the first one of the subject is selected.
  const chapterId = pickedChapterId ?? chaptersQ.data?.[0]?.id;
  const [mode, setMode] = useState<"single" | "cumulative">("single");
  const [kind, setKind] = useState<QuizKind>("mixed");
  const [selectedChapters, setSelectedChapters] = useState<number[]>([]);
  // Time-bound is ON by default. Earlier this was opt-in (off by
  // default) on the theory that self-directed practice should be
  // relaxed, but learners consistently expected to see a timer the
  // moment they hit Start — flipping the default removes the
  // "where's my timer?" confusion. Untick it explicitly for an
  // open-book / untimed session.
  const [timed, setTimed] = useState(true);
  const [duration, setDuration] = useState(15);

  const quick = useQuickQuiz();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (mode === "single" && !chapterId) {
      toast.error("Pick a chapter");
      return;
    }
    if (mode === "cumulative" && selectedChapters.length < 2) {
      toast.error("Pick at least 2 chapters for a cumulative test");
      return;
    }
    try {
      const created = await quick.mutateAsync({
        chapter_id: mode === "single" ? chapterId : undefined,
        chapter_ids: mode === "cumulative" ? selectedChapters : undefined,
        question_count: DEFAULT_COUNT_BY_KIND[kind],
        kind,
        // null when the learner left the quiz untimed; an integer
        // when they want the countdown + auto-submit.
        duration_minutes: timed ? duration : null,
      });
      // Belt-and-braces: also stash the chosen duration in localStorage
      // keyed by the returned assessment id. The take-quiz page reads
      // this as a fallback when assessment.duration_minutes comes back
      // null (which can happen if the running backend hasn't reloaded
      // the QuickQuizRequest schema and silently dropped the field).
      // Teacher-assigned quizzes — where duration is set server-side
      // by NewQuiz / from-bank — don't need this; the take page
      // prefers the server value when it's present.
      try {
        if (timed && duration > 0) {
          window.localStorage.setItem(
            `dhananjaya:quiz-duration:${created.id}`,
            String(duration),
          );
        } else {
          // Explicit "untimed" — overwrite any leftover entry so a
          // re-creation with the same id can't inherit a stale timer.
          window.localStorage.removeItem(
            `dhananjaya:quiz-duration:${created.id}`,
          );
        }
      } catch {
        /* private mode / disabled storage — non-fatal */
      }
      toast.success("Quiz ready — get started!");
      navigate(`/assessments/${created.id}/take`);
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <ThemedPage>
      <PageHeader
        title="Start a quiz"
        description="Pick a chapter and tap Start. We'll draw a fresh set of questions from the chapter bank — no two attempts look exactly the same."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick quiz</CardTitle>
            <CardDescription>{KIND_DESCRIPTION[kind]}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Subject</Label>
                  <Select
                    value={subjectId !== undefined ? String(subjectId) : ""}
                    onValueChange={(v) => {
                      // Radix reports "" while its item list is still settling.
                      if (!v) return;
                      setPickedSubjectId(Number(v));
                      // The old chapter belongs to the previous subject.
                      setPickedChapterId(undefined);
                      setSelectedChapters([]);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Subject" />
                    </SelectTrigger>
                    <SelectContent>
                      {subjectsQ.data?.map((s) => (
                        <SelectItem key={s.id} value={String(s.id)}>
                          {labelForSubject(s)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Mode</Label>
                  <Select
                    value={mode}
                    onValueChange={(v) => setMode(v as "single" | "cumulative")}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="single">Single chapter</SelectItem>
                      <SelectItem value="cumulative">
                        Cumulative · multi-chapter
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label>Test type</Label>
                <Select
                  value={kind}
                  onValueChange={(v) => setKind(v as QuizKind)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="mixed">{KIND_LABEL.mixed}</SelectItem>
                    <SelectItem value="subjective">
                      {KIND_LABEL.subjective}
                    </SelectItem>
                    <SelectItem value="objective">
                      {KIND_LABEL.objective}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {mode === "single" ? (
                <div className="space-y-1.5">
                  <Label>Chapter</Label>
                  <Select
                    value={chapterId !== undefined ? String(chapterId) : ""}
                    onValueChange={(v) => v && setPickedChapterId(Number(v))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Chapter" />
                    </SelectTrigger>
                    <SelectContent>
                      {chaptersQ.data?.map((c) => (
                        <SelectItem key={c.id} value={String(c.id)}>
                          Ch {c.chapter_number}. {c.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : (
                <div className="space-y-1.5">
                  <Label>Chapters to include (pick 2 or more)</Label>
                  <div className="rounded-md border border-(--color-border) p-3 max-h-56 overflow-y-auto space-y-1">
                    {chaptersQ.data?.length ? (
                      chaptersQ.data.map((c) => {
                        const checked = selectedChapters.includes(c.id);
                        return (
                          <label
                            key={c.id}
                            className="flex items-center gap-2 text-sm cursor-pointer rounded-md px-2 py-1 hover:bg-(--color-muted)"
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() =>
                                setSelectedChapters((prev) =>
                                  prev.includes(c.id)
                                    ? prev.filter((id) => id !== c.id)
                                    : [...prev, c.id]
                                )
                              }
                            />
                            <span>
                              <span className="text-(--color-muted-foreground) text-xs mr-1">
                                Ch {c.chapter_number}
                              </span>
                              {c.title}
                            </span>
                          </label>
                        );
                      })
                    ) : (
                      <div className="text-xs text-(--color-muted-foreground)">
                        No chapters available.
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-(--color-muted-foreground)">
                    Selected {selectedChapters.length} of{" "}
                    {chaptersQ.data?.length ?? 0}.
                  </p>
                </div>
              )}

              {/* Time-bound toggle. Off by default for self-directed
                  practice (a learner should be able to pause and
                  think); flipping it on enables the take-page
                  countdown + auto-submit at zero. */}
              <div className="space-y-1.5 rounded-md border border-(--color-border) p-3">
                <Label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={timed}
                    onChange={(e) => setTimed(e.target.checked)}
                    className="h-4 w-4 rounded border-(--color-input) accent-(--color-primary)"
                  />
                  Time-bound — simulate exam conditions
                </Label>
                {timed ? (
                  <div className="flex items-center gap-2 pl-6">
                    <Label htmlFor="qq-duration" className="text-xs text-(--color-muted-foreground)">
                      Minutes
                    </Label>
                    <input
                      id="qq-duration"
                      type="number"
                      min={1}
                      max={180}
                      value={duration}
                      onChange={(e) => setDuration(Number(e.target.value))}
                      className="w-20 rounded-md border border-(--color-input) bg-transparent px-2 py-1 text-sm"
                    />
                    <span className="text-xs text-(--color-muted-foreground)">
                      A countdown appears at the top; the quiz auto-submits at zero.
                    </span>
                  </div>
                ) : (
                  <p className="pl-6 text-xs text-(--color-muted-foreground)">
                    Untimed — take as long as you like to think through each answer.
                  </p>
                )}
              </div>

              <Button
                type="submit"
                size="lg"
                className="w-full"
                disabled={quick.isPending}
              >
                {quick.isPending ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Sparkles className="h-5 w-5" />
                )}
                Start quiz
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>How it works</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-relaxed">
            <p>
              <strong>Mixed quiz</strong> — 10 random questions of all types,
              great for daily revision.
            </p>
            <p>
              <strong>Subjective test</strong> — 5 short and long answer
              questions to practise writing. The model answer (with a detailed
              walk-through where available) appears after you submit so you can
              compare.
            </p>
            <p>
              <strong>Objective only</strong> — 10 MCQ, true/false, and fill-in
              questions, all auto-graded the moment you submit.
            </p>
            <p>
              In <strong>Cumulative · multi-chapter</strong> mode, tick two or
              more chapters and questions are mixed across all of them —
              perfect for a before-the-exam revision.
            </p>
            <p className="rounded-md bg-(--color-muted) px-3 py-2 text-xs text-(--color-muted-foreground)">
              Want a quiz tailored to specific difficulty or Bloom levels? That
              is part of the teacher's view — your teacher can build a custom
              quiz and assign it to your class.
            </p>
          </CardContent>
        </Card>
      </div>
    </ThemedPage>
  );
}
