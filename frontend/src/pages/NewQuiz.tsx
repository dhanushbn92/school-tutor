import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Loader2, Sparkles } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useChapterDetail,
  useChapters,
  useCreateAssessmentFromBank,
  useMySections,
} from "@/lib/queries";
import { useAvailableSubjects } from "@/lib/scope";
import { BoardContextBar, labelForSubject } from "@/components/BoardContextBar";
import { humanError } from "@/lib/api";

const DIFFICULTY_PRESETS: { label: string; mix: Record<string, number> }[] = [
  { label: "Balanced (E:M:H = 1:2:1)", mix: { EASY: 2, MEDIUM: 4, HARD: 2 } },
  { label: "Easy-leaning (E:M:H = 2:2:1)", mix: { EASY: 4, MEDIUM: 4, HARD: 2 } },
  { label: "Challenging (E:M:H = 1:2:2)", mix: { EASY: 2, MEDIUM: 4, HARD: 4 } },
  { label: "All medium", mix: { EASY: 0, MEDIUM: 8, HARD: 0 } },
];

const COGNITIVE_PRESETS: { label: string; mix: Record<string, number> }[] = [
  {
    label: "Balanced (Factual : Understanding : Application = 1:1:1)",
    mix: { FACTUAL: 1, UNDERSTANDING: 1, APPLICATION: 1 },
  },
  {
    label: "Recall-heavy (Factual 2 : Understanding 1 : Application 1)",
    mix: { FACTUAL: 2, UNDERSTANDING: 1, APPLICATION: 1 },
  },
  {
    label: "Skill-building (Factual 1 : Understanding 2 : Application 1)",
    mix: { FACTUAL: 1, UNDERSTANDING: 2, APPLICATION: 1 },
  },
  {
    label: "Application-heavy (Factual 1 : Understanding 1 : Application 2)",
    mix: { FACTUAL: 1, UNDERSTANDING: 1, APPLICATION: 2 },
  },
];

export function NewQuizPage() {
  const navigate = useNavigate();
  const sectionsQ = useMySections();
  const [sectionId, setSectionId] = useState<number | undefined>(undefined);
  const section = sectionsQ.data?.find((s) => s.id === sectionId);
  // For teachers this is intersected with their explicit subject assignments,
  // so they can't accidentally create a quiz for a subject they don't teach.
  // For school admins it returns every subject of the class.
  const subjectsScope = useAvailableSubjects(section?.class_level ?? undefined);
  const [subjectId, setSubjectId] = useState<number | undefined>(undefined);
  const chaptersQ = useChapters({
    class_level: section?.class_level ?? undefined,
    subject_id: subjectId,
  });
  const [chapterId, setChapterId] = useState<number | undefined>(undefined);
  const chapterDetailQ = useChapterDetail(chapterId);
  const [topicId, setTopicId] = useState<number | undefined>(undefined);

  const [title, setTitle] = useState("");
  const [questionCount, setQuestionCount] = useState(8);
  // Time-bound is the platform default — a finite-time quiz is closer to
  // a real exam — but the user can flip it off for an untimed practice
  // session. When `timed` is false we send duration_minutes: null to
  // the backend, which stores it and the take-quiz page renders no timer.
  const [timed, setTimed] = useState(true);
  const [duration, setDuration] = useState(20);
  const [presetIndex, setPresetIndex] = useState<string>("0");
  const [useDifficultyMix, setUseDifficultyMix] = useState(true);
  const [cognitivePresetIndex, setCognitivePresetIndex] = useState<string>("0");
  const [useCognitiveMix, setUseCognitiveMix] = useState(false);

  const createMutation = useCreateAssessmentFromBank();

  // Auto-select sensible defaults as the data arrives.
  useEffect(() => {
    if (!sectionId && sectionsQ.data?.length) {
      setSectionId(sectionsQ.data[0].id);
    }
  }, [sectionId, sectionsQ.data]);
  useEffect(() => {
    setSubjectId(undefined);
    setChapterId(undefined);
    setTopicId(undefined);
  }, [sectionId]);
  useEffect(() => {
    const subjects = subjectsScope.subjects;
    if (subjects.length === 0) return;
    // Reset if the picked subject no longer belongs to the (possibly newly
    // scoped) list — happens when teacher's assignments shift, or when
    // section changes and the new class has different subjects.
    const stillValid =
      subjectId !== undefined && subjects.some((s) => s.id === subjectId);
    if (stillValid) return;
    const science =
      subjects.find((s) => s.name === "Science") ?? subjects[0];
    setSubjectId(science.id);
  }, [subjectId, subjectsScope.subjects]);
  useEffect(() => {
    if (!chapterId && chaptersQ.data?.length) {
      setChapterId(chaptersQ.data[0].id);
    }
  }, [chapterId, chaptersQ.data]);
  useEffect(() => {
    setTopicId(undefined);
  }, [chapterId]);

  const presetMix = DIFFICULTY_PRESETS[Number(presetIndex)].mix;
  const scaledMix = scaleMix(presetMix, questionCount);
  const cognitivePresetMix = COGNITIVE_PRESETS[Number(cognitivePresetIndex)].mix;
  const scaledCognitiveMix = scaleMix(cognitivePresetMix, questionCount);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!sectionId || !subjectId || !chapterId) {
      toast.error("Pick a section, subject, and chapter");
      return;
    }
    if (!title.trim()) {
      toast.error("Give the quiz a title");
      return;
    }
    try {
      const created = await createMutation.mutateAsync({
        section_id: sectionId,
        subject_id: subjectId,
        chapter_id: chapterId,
        topic_id: topicId ?? null,
        type: "QUIZ",
        title: title.trim(),
        // null when the admin chose "untimed" — backend stores it as
        // NULL and the take-quiz page renders no timer banner.
        duration_minutes: timed ? duration : null,
        question_count: questionCount,
        difficulty_mix: useDifficultyMix ? scaledMix : undefined,
        cognitive_mix: useCognitiveMix ? scaledCognitiveMix : undefined,
      });
      toast.success(
        `Quiz ready (#${created.id}) · ${created.questions.length} questions sampled. ` +
          `Tap Publish on the next page to share it with the section.`,
      );
      navigate(`/assessments/${created.id}`);
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <ThemedPage>
      <PageHeader
        title="New quiz from bank"
        description="Sample approved questions from the global question bank to build a fresh quiz for one of your sections. No AI call at this step — questions are drawn instantly from the pool the platform team has curated."
        actions={
          <Button asChild variant="outline">
            <Link to="/assessments">
              <ArrowLeft className="h-4 w-4" />
              Cancel
            </Link>
          </Button>
        }
      />

      {/* Board context — once a subject is picked, surface the resolved
          board so a teacher who teaches both CBSE and NIOS Maths can
          tell which question bank they're sampling from. The selected
          section's class info already appears in the dropdown beside
          this strip, so we don't repeat the class level here. */}
      <BoardContextBar
        subjectName={subjectsScope.subjects.find((s) => s.id === subjectId)?.name}
        board={subjectsScope.subjects.find((s) => s.id === subjectId)?.board}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Build your quiz</CardTitle>
            <CardDescription>
              Pick a chapter, choose how many questions you want, and we'll randomly sample
              from the approved bank. The same form lands you at the gradebook ready to
              publish to the section.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label>Section</Label>
                <Select
                  value={sectionId !== undefined ? String(sectionId) : ""}
                  onValueChange={(v) => setSectionId(Number(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Pick a section" />
                  </SelectTrigger>
                  <SelectContent>
                    {sectionsQ.data?.map((s) => (
                      <SelectItem key={s.id} value={String(s.id)}>
                        {s.class_display_name} · {s.name} ({s.academic_year})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Subject</Label>
                  <Select
                    value={subjectId !== undefined ? String(subjectId) : ""}
                    onValueChange={(v) => setSubjectId(Number(v))}
                    disabled={subjectsScope.subjects.length === 0}
                  >
                    <SelectTrigger>
                      <SelectValue
                        placeholder={
                          subjectsScope.isScoped &&
                          subjectsScope.subjects.length === 0
                            ? "No subjects assigned to you"
                            : "Subject"
                        }
                      />
                    </SelectTrigger>
                    <SelectContent>
                      {subjectsScope.subjects.map((s) => (
                        <SelectItem key={s.id} value={String(s.id)}>
                          {labelForSubject(s)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Chapter</Label>
                  <Select
                    value={chapterId !== undefined ? String(chapterId) : ""}
                    onValueChange={(v) => setChapterId(Number(v))}
                    disabled={!chaptersQ.data?.length}
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
              </div>

              <div className="space-y-1.5">
                <Label>Topic (optional)</Label>
                <Select
                  value={topicId !== undefined ? String(topicId) : ""}
                  onValueChange={(v) => setTopicId(v === "" ? undefined : Number(v))}
                  disabled={!chapterDetailQ.data?.topics.length}
                >
                  <SelectTrigger>
                    <SelectValue
                      placeholder={
                        chapterDetailQ.data?.topics.length
                          ? "All topics in this chapter"
                          : "No topics tagged for this chapter"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {chapterDetailQ.data?.topics.map((t) => (
                      <SelectItem key={t.id} value={String(t.id)}>
                        {t.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="title">Quiz title</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Friday quick check — Ch 5"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="qcount">Questions</Label>
                  <Input
                    id="qcount"
                    type="number"
                    min={3}
                    max={30}
                    value={questionCount}
                    onChange={(e) => setQuestionCount(Number(e.target.value))}
                  />
                </div>
                <div className="space-y-1.5">
                  {/* Time-bound toggle + conditional duration input.
                      The toggle is what the teacher reaches for first
                      ("is this an exam-style quiz or open practice?");
                      the duration field only appears when relevant so
                      the form doesn't carry a dead field for untimed
                      quizzes. */}
                  <Label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={timed}
                      onChange={(e) => setTimed(e.target.checked)}
                      className="h-4 w-4 rounded border-(--color-input) accent-(--color-primary)"
                    />
                    Time-bound
                  </Label>
                  {timed ? (
                    <Input
                      id="duration"
                      type="number"
                      min={1}
                      max={180}
                      value={duration}
                      onChange={(e) => setDuration(Number(e.target.value))}
                      aria-label="Duration in minutes"
                    />
                  ) : (
                    <p className="text-xs text-(--color-muted-foreground)">
                      Untimed — students can take as long as they like.
                    </p>
                  )}
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label>Difficulty mix</Label>
                  <label className="flex items-center gap-2 text-xs text-(--color-muted-foreground)">
                    <input
                      type="checkbox"
                      checked={useDifficultyMix}
                      onChange={(e) => setUseDifficultyMix(e.target.checked)}
                    />
                    Apply mix
                  </label>
                </div>
                <Select
                  value={presetIndex}
                  onValueChange={setPresetIndex}
                  disabled={!useDifficultyMix}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DIFFICULTY_PRESETS.map((p, i) => (
                      <SelectItem key={i} value={String(i)}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {useDifficultyMix && (
                  <div className="text-xs text-(--color-muted-foreground)">
                    Will draw: {Object.entries(scaledMix).map(([k, v]) => `${v} ${k}`).join(" · ")}
                  </div>
                )}
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label>Cognitive (Bloom) mix</Label>
                  <label className="flex items-center gap-2 text-xs text-(--color-muted-foreground)">
                    <input
                      type="checkbox"
                      checked={useCognitiveMix}
                      onChange={(e) => setUseCognitiveMix(e.target.checked)}
                    />
                    Apply mix
                  </label>
                </div>
                <Select
                  value={cognitivePresetIndex}
                  onValueChange={setCognitivePresetIndex}
                  disabled={!useCognitiveMix}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {COGNITIVE_PRESETS.map((p, i) => (
                      <SelectItem key={i} value={String(i)}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {useCognitiveMix && (
                  <div className="text-xs text-(--color-muted-foreground)">
                    Will draw: {Object.entries(scaledCognitiveMix).map(([k, v]) => `${v} ${k}`).join(" · ")}
                    <span className="ml-2 italic">
                      (Factual = recall · Understanding = explain · Application = use & analyse)
                    </span>
                  </div>
                )}
              </div>

              <Button type="submit" className="w-full" disabled={createMutation.isPending}>
                {createMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Sample {questionCount} questions and create quiz
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>How sampling works</CardTitle>
            <CardDescription>What you'll get and what to do if the bank is thin.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-relaxed">
            <p>
              The platform team curates a global question bank, organised by class, subject,
              chapter, learning outcome, and difficulty. When you build a quiz here, we draw
              random APPROVED questions matching your filters — instantly, no AI call.
            </p>
            <p>
              If you ask for more questions than the bank has for your scope (e.g., 30 HARD
              questions on Chapter 9 when only 8 are approved), the request is rejected with a{" "}
              <strong>409 Bank coverage insufficient</strong> response. Either lower the
              count, drop a filter, or ping the platform team to expand that area of the bank.
            </p>
            <p>
              After creation the quiz lands in <strong>DRAFT</strong> and is invisible
              to students. The detail page that opens next has a{" "}
              <strong>Publish to section</strong> button — one click and the quiz
              becomes visible to everyone in the section. You can also publish from the{" "}
              <Link to="/assessments" className="text-(--color-primary) underline-offset-4 hover:underline">
                Assessments
              </Link>{" "}
              list using the inline Publish action.
            </p>
            <p className="rounded-md bg-(--color-muted) px-3 py-2 text-xs text-(--color-muted-foreground)">
              <ArrowRight className="mr-1 inline h-3 w-3" />
              Tip: questions can repeat across quizzes. The sampler does not yet exclude
              questions a student has seen recently — that's on the roadmap.
            </p>
          </CardContent>
        </Card>
      </div>
    </ThemedPage>
  );
}

/** Re-scale a preset mix to sum to `total`. Rounds while preserving total exactly. */
function scaleMix(mix: Record<string, number>, total: number): Record<string, number> {
  const presetTotal = Object.values(mix).reduce((s, v) => s + v, 0);
  if (presetTotal === 0) return mix;
  const ratios = Object.fromEntries(
    Object.entries(mix).map(([k, v]) => [k, (v * total) / presetTotal]),
  );
  // Floor each, then distribute the remainder by largest fractional part.
  const floors = Object.fromEntries(
    Object.entries(ratios).map(([k, v]) => [k, Math.floor(v)]),
  );
  let remaining = total - Object.values(floors).reduce((s, v) => s + v, 0);
  const remainders = Object.entries(ratios)
    .map(([k, v]) => [k, v - Math.floor(v)] as [string, number])
    .sort((a, b) => b[1] - a[1]);
  for (const [k] of remainders) {
    if (remaining <= 0) break;
    floors[k] += 1;
    remaining -= 1;
  }
  return floors;
}
