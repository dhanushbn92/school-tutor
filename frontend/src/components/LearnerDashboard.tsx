import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ClipboardList,
  Loader2,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Trophy,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import { DashboardHero } from "@/components/DashboardHero";
import { DashboardPurposePanel } from "@/components/DashboardPurposePanel";
import { PracticeCard } from "@/components/PracticeCard";
import { LearnerProgressNarrative } from "@/components/LearnerProgressNarrative";
import { MascotToggleHint } from "@/components/MascotToggleHint";
import { FamilyNotesCard } from "@/components/FamilyNotesCard";
import { ParentInviteCard } from "@/components/ParentInviteCard";
import { AudioSettingsCard } from "@/components/AudioSettingsCard";
import { AccessibilityCard } from "@/components/AccessibilityCard";
import { MasteryHeatmap } from "@/components/MasteryHeatmap";
import type { HeatmapView } from "@/components/MasteryHeatmap";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { useAuth } from "@/lib/auth";
import {
  useMyAssessments,
  useMySections,
  useMyStudents,
  useStudentMastery,
  useStudentTrend,
  useSubjects,
} from "@/lib/queries";
import { formatDateTime } from "@/lib/utils";

export function LearnerDashboard() {
  const { user } = useAuth();
  const isIndividual = user?.role === "individual_learner";

  const sectionsQ = useMySections();
  const section = sectionsQ.data?.[0];
  const subjectsQ = useSubjects(section?.class_level ?? undefined);
  const subject =
    subjectsQ.data?.find((s) => s.name === "Science") ?? subjectsQ.data?.[0];
  const studentsQ = useMyStudents(section?.id);
  // Find this user's own Student record (works for both school student + individual)
  const myStudent = studentsQ.data?.find((s) => s.user_id === user?.id);

  // Whole-syllabus mastery (every subject in the class). Powers the
  // narrative tiles, the strongest + best-place picks, the syllabus
  // map, AND the strengths/focus lists below — so a learner sees
  // their entire syllabus on the dashboard, not just one subject.
  const masteryQ = useStudentMastery({
    student_id: myStudent?.id,
    class_level: section?.class_level ?? undefined,
    // No subject_id — get all subjects.
  });
  // Subject-scoped mastery (one subject at a time) for the Topic
  // mastery heatmap below; the cognitive-bucket picker on that
  // widget only makes sense per-subject.
  const subjectMasteryQ = useStudentMastery({
    student_id: myStudent?.id,
    class_level: section?.class_level ?? undefined,
    subject_id: subject?.id,
  });
  const trendQ = useStudentTrend({
    student_id: myStudent?.id,
    subject_id: subject?.id,
  });
  const assessmentsQ = useMyAssessments();

  const [view, setView] = useState<HeatmapView>("combined");

  const recent = (assessmentsQ.data ?? []).slice(0, 5);
  const published = recent.filter((a) => a.status === "PUBLISHED");

  if (sectionsQ.isLoading || studentsQ.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading…
      </div>
    );
  }

  const summary = masteryQ.data?.summary;
  // The four headline stat cards (and the per-bucket "Focus area" tile
  // that consumed pickWeakestBucket) were retired in Stage 4 in favour
  // of <LearnerProgressNarrative />. `summary` is still consumed by
  // the lower strengths/weaknesses lists' empty-state copy.
  const { strengths, weaknesses } = pickOutcomeHighlights(masteryQ.data);

  return (
    <ThemedPage>
      <DashboardHero
        role="learner"
        userName={(user?.full_name ?? "").split(/\s+/)[0] || undefined}
      />
      {/* The platform's purpose panel — practice ethos + a primary
          CTA pointing at the next quiz. Sits above the mastery
          widgets so the practice prompt is unmissable. */}
      <DashboardPurposePanel role="learner" />
      {/* "Your practice" card — weekly progress ring + stamp strip.
          Stage 1 of the child-centric roadmap. */}
      <PracticeCard />
      {/* Stage 5 — only renders if the learner has previously turned
          the Vidyārthi mascot off. Gives them a one-click path back
          to enabling the companion so the off switch is reversible. */}
      <MascotToggleHint />
      {/* Stage 6 — "Notes from family" card. Renders nothing if no
          undismissed parent encouragements exist, so it stays
          invisible for learners without a linked parent. */}
      <FamilyNotesCard />
      <PageHeader
        title={`Welcome, ${(user?.full_name ?? "").split(/\s+/)[0]}`}
        description={
          isIndividual
            ? "Your private practice — track your mastery, see your trend, and start a fresh quiz any time."
            : "Your assigned quizzes and progress across the syllabus."
        }
        actions={
          isIndividual ? (
            <Button asChild>
              <Link to="/quick-quiz">
                <Sparkles className="h-4 w-4" />
                Start a quiz
              </Link>
            </Button>
          ) : (
            <Button asChild>
              <Link to="/assessments">
                <ClipboardList className="h-4 w-4" />
                My quizzes
              </Link>
            </Button>
          )
        }
      />

      {/* Stage 4 — Story-shaped progress.
          Replaces the four-card stat row (Outcomes mastered / Average
          mastery / Focus area / Quizzes taken) with a narrative
          rendering: three chapter-state tiles + strongest concept +
          best-place-to-practise + a topic-tree visual. The bare numbers
          aren't gone — they're folded into the dot grid and the
          per-chapter "X/Y outcomes mastered" caption, where they
          finally read as part of a story rather than a report card. */}
      <LearnerProgressNarrative
        data={masteryQ.data}
        subjectName={subject?.name}
        showPracticeLinks={isIndividual}
      />

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Trophy className="h-4 w-4 text-(--color-success)" />
              <CardTitle>Your strengths</CardTitle>
            </div>
            <CardDescription>
              Outcomes where you're scoring 75% or higher across recent attempts.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {strengths.length === 0 ? (
              <Empty
                title="No strong topics yet"
                description="Take a few quizzes — your top topics will show up here once you're consistently above 75%."
                className="border-0 py-4"
              />
            ) : (
              <ul className="space-y-2">
                {strengths.map((o) => (
                  <li
                    key={`${o.chapter_id}-${o.code}`}
                    className="flex items-center justify-between gap-3 rounded-md border border-(--color-border) px-3 py-2 text-sm"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{outcomeShortCode(o.code)}</Badge>
                        <span className="truncate font-medium">{o.description}</span>
                      </div>
                      <div className="mt-1 text-[11px] text-(--color-muted-foreground)">
                        Ch {o.chapter_number}. {o.chapter_title} · {o.attempts} attempt
                        {o.attempts === 1 ? "" : "s"}
                      </div>
                    </div>
                    <Badge variant="success">
                      {Math.round((o.mastery ?? 0) * 100)}%
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-(--color-warning)" />
              <CardTitle>Areas to focus on</CardTitle>
            </div>
            <CardDescription>
              Outcomes where mastery is below 60%. A short focused practice goes a long way.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {weaknesses.length === 0 ? (
              <Empty
                title="Nothing flagged yet"
                description={
                  summary && summary.outcomes_attempted > 0
                    ? "You're holding above 60% on every attempted topic. Keep going!"
                    : "Take a quiz to see which topics need extra work."
                }
                className="border-0 py-4"
              />
            ) : (
              <ul className="space-y-2">
                {weaknesses.map((o) => (
                  <li
                    key={`${o.chapter_id}-${o.code}`}
                    className="flex items-center justify-between gap-3 rounded-md border border-(--color-border) px-3 py-2 text-sm"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{outcomeShortCode(o.code)}</Badge>
                        <span className="truncate font-medium">{o.description}</span>
                      </div>
                      <div className="mt-1 text-[11px] text-(--color-muted-foreground)">
                        Ch {o.chapter_number}. {o.chapter_title} · {o.attempts} attempt
                        {o.attempts === 1 ? "" : "s"}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="warning">
                        {Math.round((o.mastery ?? 0) * 100)}%
                      </Badge>
                      {isIndividual && (
                        <Button asChild size="sm" variant="outline">
                          <Link to={`/quick-quiz?chapter=${o.chapter_id}`}>
                            Practice
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Link>
                        </Button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {subjectMasteryQ.data ? (
            <MasteryHeatmap
              title={
                subject
                  ? `Topic mastery map · ${subject.name}`
                  : "Topic mastery map"
              }
              description="How much of the syllabus you've practised so far. Cells fill in as you submit quizzes."
              view={view}
              headerSlot={
                <div className="w-48">
                  <Select value={view} onValueChange={(v) => setView(v as HeatmapView)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="combined">Combined</SelectItem>
                      <SelectItem value="FACTUAL">Factual only</SelectItem>
                      <SelectItem value="UNDERSTANDING">Understanding only</SelectItem>
                      <SelectItem value="APPLICATION">Application only</SelectItem>
                      <SelectItem value="remember">Bloom · Remember</SelectItem>
                      <SelectItem value="understand">Bloom · Understand</SelectItem>
                      <SelectItem value="apply">Bloom · Apply</SelectItem>
                      <SelectItem value="analyze">Bloom · Analyze</SelectItem>
                      <SelectItem value="evaluate">Bloom · Evaluate</SelectItem>
                      <SelectItem value="create">Bloom · Create</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              }
              chapters={subjectMasteryQ.data.chapters.map((ch) => ({
                chapter_id: ch.chapter_id,
                chapter_number: ch.chapter_number,
                chapter_title: ch.chapter_title,
                outcomes: ch.outcomes.map((o) => ({
                  code: o.code,
                  description: o.description,
                  mastery: o.mastery,
                  attempts: o.attempts,
                  buckets: o.buckets,
                })),
              }))}
            />
          ) : (
            <Card>
              <CardContent className="p-6">
                <Empty
                  icon={<TrendingUp className="h-6 w-6" />}
                  title="No mastery yet"
                  description={
                    isIndividual
                      ? "Take your first quiz to start filling in your map."
                      : "When you take an assigned quiz, your mastery map fills in here."
                  }
                  action={
                    isIndividual ? (
                      <Button asChild>
                        <Link to="/quick-quiz">Start a quiz</Link>
                      </Button>
                    ) : undefined
                  }
                  className="border-0"
                />
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Score trend</CardTitle>
              <CardDescription>Your evaluated quizzes over time.</CardDescription>
            </CardHeader>
            <CardContent className="h-56">
              {trendQ.data && trendQ.data.series.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={trendQ.data.series.map((p, i) => ({
                      index: i + 1,
                      name: p.assessment_title,
                      percentage: p.percentage,
                    }))}
                    margin={{ top: 6, right: 12, bottom: 0, left: -12 }}
                  >
                    <CartesianGrid stroke="oklch(90% 0.008 260)" strokeDasharray="3 3" />
                    <XAxis dataKey="index" tickLine={false} axisLine={false} fontSize={11} />
                    <YAxis
                      domain={[0, 100]}
                      tickLine={false}
                      axisLine={false}
                      fontSize={11}
                      unit="%"
                    />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 8,
                        border: "1px solid oklch(90% 0.008 260)",
                      }}
                      labelFormatter={(_, p) => p[0]?.payload?.name ?? ""}
                      formatter={(value) => [`${value}%`, "Score"] as [string, string]}
                    />
                    <Line
                      type="monotone"
                      dataKey="percentage"
                      stroke="oklch(56% 0.14 257)"
                      strokeWidth={2.5}
                      dot={{ r: 4, strokeWidth: 2 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Empty title="No quizzes evaluated yet" className="border-0 py-6" />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent quizzes</CardTitle>
              <CardDescription>Latest quizzes you can take.</CardDescription>
            </CardHeader>
            <CardContent>
              {published.length === 0 ? (
                <Empty
                  title="No quizzes ready"
                  description={
                    isIndividual
                      ? "Tap Start a quiz to draw fresh questions from the bank."
                      : "Your teacher hasn't published anything yet."
                  }
                  className="border-0 py-6"
                />
              ) : (
                <ul className="space-y-2">
                  {published.map((a) => (
                    <li
                      key={a.id}
                      className="flex items-center justify-between gap-2 rounded-md border border-(--color-border) p-3 text-sm"
                    >
                      <div className="min-w-0">
                        <div className="truncate font-medium">{a.title}</div>
                        <div className="text-[11px] text-(--color-muted-foreground)">
                          <Badge variant="outline" className="mr-1">
                            {a.type}
                          </Badge>
                          {a.total_marks} marks · {formatDateTime(a.published_at)}
                        </div>
                      </div>
                      <Button asChild size="sm">
                        <Link to={`/assessments/${a.id}/take`}>
                          Take
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Stage 8 — audio / read-aloud settings. Sits with the other
          "configure once" affordances at the bottom of the dashboard
          rather than competing with the practice headline. The 🔊
          button itself appears next to every question text across
          the app; this card is just where the learner picks the
          voice + autoplay preference. */}
      <div className="mt-6">
        <AudioSettingsCard />
      </div>

      {/* Stage 10 — accessibility toggles: dyslexia-friendly font,
          high contrast, larger tap targets, take-a-break nudge.
          All four are per-device (localStorage) so a phone can
          have larger targets while the desktop stays normal. */}
      <div className="mt-6">
        <AccessibilityCard />
      </div>

      {/* Stage 6 — invite a parent / guardian. Sits at the bottom of
          the dashboard rather than competing with the practice
          headline; it's a "configure once" affordance, not a
          day-to-day widget. */}
      <div className="mt-6">
        <ParentInviteCard />
      </div>
    </ThemedPage>
  );
}

interface OutcomeHighlight {
  chapter_id: number;
  chapter_number: number;
  chapter_title: string;
  code: string;
  description: string;
  mastery: number | null;
  attempts: number;
}

const STRENGTH_THRESHOLD = 0.75;
const FOCUS_THRESHOLD = 0.6;
const HIGHLIGHTS_PER_LIST = 3;

function pickOutcomeHighlights(
  grid: { chapters: { chapter_id: number; chapter_number: number; chapter_title: string; outcomes: { code: string; description: string; mastery: number | null; attempts: number }[] }[] } | undefined,
): { strengths: OutcomeHighlight[]; weaknesses: OutcomeHighlight[] } {
  if (!grid) return { strengths: [], weaknesses: [] };
  const attempted: OutcomeHighlight[] = [];
  for (const ch of grid.chapters) {
    for (const o of ch.outcomes) {
      if (o.attempts > 0 && o.mastery !== null) {
        attempted.push({
          chapter_id: ch.chapter_id,
          chapter_number: ch.chapter_number,
          chapter_title: ch.chapter_title,
          code: o.code,
          description: o.description,
          mastery: o.mastery,
          attempts: o.attempts,
        });
      }
    }
  }
  const strengths = attempted
    .filter((o) => (o.mastery ?? 0) >= STRENGTH_THRESHOLD)
    .sort((a, b) => (b.mastery ?? 0) - (a.mastery ?? 0))
    .slice(0, HIGHLIGHTS_PER_LIST);
  const weaknesses = attempted
    .filter((o) => (o.mastery ?? 1) < FOCUS_THRESHOLD)
    .sort((a, b) => (a.mastery ?? 1) - (b.mastery ?? 1))
    .slice(0, HIGHLIGHTS_PER_LIST);
  return { strengths, weaknesses };
}

/** "6-SCI-WOS-01" → "WOS-01". Falls back to the full code if format is unexpected. */
function outcomeShortCode(code: string): string {
  const parts = code.split("-");
  return parts.length >= 4 ? parts.slice(-2).join("-") : code;
}
