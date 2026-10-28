import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2 } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Disclosure } from "@/components/Disclosure";
import { MasteryHeatmap } from "@/components/MasteryHeatmap";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { useAuth } from "@/lib/auth";
import {
  useMyAssessments,
  useMySections,
  useMyStudents,
  usePracticeSummary,
  useStudentMastery,
  useStudentTrend,
  useSubjects,
} from "@/lib/queries";
import { pickBestPlace, rollupChapters, rollupSubjects } from "@/lib/progress";
import { cn, formatDateTime, formatPercent } from "@/lib/utils";
import { BUCKET_LABEL } from "@/lib/types";
import type { CognitiveBucket } from "@/lib/types";

const BUCKET_COLOUR: Record<CognitiveBucket, string> = {
  FACTUAL: "#2E9E5B",
  UNDERSTANDING: "#1668D8",
  APPLICATION: "#F7931E",
};

export function ReportCardPage() {
  const { user } = useAuth();
  const isIndividual = user?.role === "individual_learner";
  const firstName = (user?.full_name ?? "").split(/\s+/)[0];

  const sectionsQ = useMySections();
  const section = sectionsQ.data?.[0];
  const subjectsQ = useSubjects(section?.class_level ?? undefined);
  const studentsQ = useMyStudents(section?.id);
  const myStudent = studentsQ.data?.find((s) => s.user_id === user?.id);

  // The whole-syllabus grid decides which subject to open first (the one the
  // learner has practised most) and powers the friendly summary line.
  const allQ = useStudentMastery({
    student_id: myStudent?.id,
    class_level: section?.class_level ?? undefined,
    allSubjects: true,
  });
  const subjectRollups = useMemo(
    () => rollupSubjects(rollupChapters(allQ.data)),
    [allQ.data],
  );
  const practiceQ = usePracticeSummary();

  const [pickedSubject, setPickedSubject] = useState<number | undefined>();
  const mostPractised = useMemo(() => {
    let best: { id: number; attempted: number } | null = null;
    for (const r of subjectRollups) {
      if (r.subject_id === null) continue;
      const attempted = r.chapters.reduce((n, c) => n + c.outcomes_attempted, 0);
      if (attempted > 0 && (best === null || attempted > best.attempted)) {
        best = { id: r.subject_id, attempted };
      }
    }
    return best?.id;
  }, [subjectRollups]);
  const chosenSubject = pickedSubject ?? mostPractised ?? subjectsQ.data?.[0]?.id;

  const masteryQ = useStudentMastery({
    student_id: myStudent?.id,
    class_level: section?.class_level ?? undefined,
    subject_id: chosenSubject,
  });
  const trendQ = useStudentTrend({
    student_id: myStudent?.id,
    subject_id: chosenSubject,
  });
  const assessmentsQ = useMyAssessments();

  const nextStep = useMemo(
    () => pickBestPlace(rollupChapters(masteryQ.data)),
    [masteryQ.data],
  );

  if (sectionsQ.isLoading || studentsQ.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading…
      </div>
    );
  }

  const summary = masteryQ.data?.summary;
  const trend = trendQ.data;
  const evaluatedAssessments = (assessmentsQ.data ?? []).filter((a) => {
    if (chosenSubject !== undefined && a.subject_id !== chosenSubject) return false;
    return a.status === "PUBLISHED" || a.status === "CLOSED";
  });

  const { strengths, weaknesses } = pickHighlights(masteryQ.data);
  const grade = computeGrade(trend?.summary.average_percentage ?? null);
  const bestScore = trend?.series.length
    ? Math.max(...trend.series.map((p) => p.percentage))
    : null;
  const covered =
    summary && summary.outcomes_total > 0
      ? Math.round((summary.outcomes_attempted / summary.outcomes_total) * 100)
      : 0;
  const practiseHref = (chapterId: number) =>
    isIndividual
      ? `/quick-quiz?chapter=${chapterId}`
      : `/learn/chapters/${chapterId}?tab=worksheets`;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight">Report card</h1>
        <p className="mt-1.5 text-base text-(--color-muted-foreground)">
          {section ? `Class ${section.class_level} · ${section.academic_year}` : "Your academic report card."}
        </p>
        <p className="mt-3 max-w-3xl text-lg leading-relaxed">
          {friendlySummary({
            firstName,
            average: allQ.data?.summary.average_mastery ?? null,
            practiceDays: practiceQ.data?.practice_days_count_this_week,
            strongestSubject: strongestSubjectName(subjectRollups),
          })}
        </p>
      </div>

      {subjectsQ.data && subjectsQ.data.length > 1 && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Choose a subject">
          {subjectsQ.data.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setPickedSubject(s.id)}
              aria-pressed={chosenSubject === s.id}
              className={cn(
                "rounded-full border px-4 py-2 text-sm font-semibold transition-colors",
                chosenSubject === s.id
                  ? "border-(--color-foreground) bg-(--color-foreground) text-(--color-background)"
                  : "border-(--color-border) bg-(--color-card) text-(--color-muted-foreground) hover:text-(--color-foreground)",
              )}
            >
              {s.name}
            </button>
          ))}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="rounded-2xl p-6">
          <div className="text-sm text-(--color-muted-foreground)">Outcomes covered</div>
          <div className="mt-1 font-display text-3xl font-extrabold">
            {summary ? summary.outcomes_attempted : "—"}
            <span className="text-base font-medium text-(--color-muted-foreground)">
              {summary ? ` / ${summary.outcomes_total}` : ""}
            </span>
          </div>
          <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-(--color-muted)">
            <div className="h-full rounded-full bg-(--color-primary)" style={{ width: `${covered}%` }} />
          </div>
        </Card>
        <Card className="rounded-2xl p-6">
          <div className="text-sm text-(--color-muted-foreground)">Average mastery</div>
          <div className="mt-1 flex items-center gap-3">
            <span className="font-display text-3xl font-extrabold">
              {formatPercent(summary?.average_mastery)}
            </span>
            {grade.label !== "—" && (
              <Badge variant={grade.intent === "danger" ? "destructive" : grade.intent === "warning" ? "warning" : "success"}>
                {grade.label.length === 1 ? `Grade ${grade.label}` : grade.label}
              </Badge>
            )}
          </div>
          <div className="mt-3 text-sm text-(--color-muted-foreground)">{grade.note}</div>
        </Card>
        <Card className="rounded-2xl p-6">
          <div className="text-sm text-(--color-muted-foreground)">Quizzes taken</div>
          <div className="mt-1 font-display text-3xl font-extrabold">
            {trend?.summary.tests_evaluated ?? 0}
          </div>
          <div className="mt-3 text-sm text-(--color-muted-foreground)">
            {bestScore !== null ? `Best score ${bestScore}%` : "No tests taken yet"}
          </div>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-3 rounded-2xl bg-[#0E2A4D] p-6 text-white">
          <span className="self-start rounded-full bg-white/15 px-3 py-1 text-xs font-semibold">
            Best next step
          </span>
          {nextStep ? (
            <>
              <h2 className="font-display text-xl font-extrabold leading-snug">
                Practise {nextStep.chapter_title}
              </h2>
              <p className="text-sm leading-relaxed text-white/75">
                {nextStep.mastery !== null
                  ? `Your score here is ${Math.round(nextStep.mastery * 100)}%. One short quiz will lift it fastest.`
                  : "You have not tried this one yet. A short quiz is a good start."}
              </p>
              <Button
                asChild
                size="lg"
                className="mt-auto rounded-xl bg-[#F7931E] text-[#2B1700] hover:opacity-90"
              >
                <Link to={practiseHref(nextStep.chapter_id)}>
                  {isIndividual ? "Start a quiz" : "Practise"}
                </Link>
              </Button>
            </>
          ) : (
            <>
              <h2 className="font-display text-xl font-extrabold leading-snug">Take your first quiz</h2>
              <p className="text-sm leading-relaxed text-white/75">
                Your best next step shows up here once you have some results.
              </p>
              <Button
                asChild
                size="lg"
                className="mt-auto rounded-xl bg-[#F7931E] text-[#2B1700] hover:opacity-90"
              >
                <Link to={isIndividual ? "/quick-quiz" : "/assessments"}>
                  {isIndividual ? "Start a quiz" : "My quizzes"}
                </Link>
              </Button>
            </>
          )}
        </div>

        <Card className="rounded-2xl p-6 lg:col-span-2">
          <h2 className="font-display text-lg font-bold">How you think</h2>
          <p className="mt-0.5 text-sm text-(--color-muted-foreground)">
            Average mastery by kind of question
          </p>
          <div className="mt-5 space-y-4">
            {(["FACTUAL", "UNDERSTANDING", "APPLICATION"] as CognitiveBucket[]).map((b) => {
              const stats = summary?.by_bucket?.[b];
              const value = stats?.average_mastery ?? null;
              return (
                <div key={b}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="font-semibold">{BUCKET_LABEL[b]}</span>
                    <span className="text-(--color-muted-foreground)">
                      {value === null ? "No attempts yet" : formatPercent(value)}
                    </span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-(--color-muted)">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.round((value ?? 0) * 100)}%`,
                        background: BUCKET_COLOUR[b],
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="rounded-2xl p-6">
          <h2 className="font-display text-lg font-bold">Strengths</h2>
          <p className="mt-0.5 text-sm text-(--color-muted-foreground)">
            Topics you are consistently scoring 75% or more on.
          </p>
          {strengths.length === 0 ? (
            <Empty
              title="Not enough data yet"
              description="Take a few more quizzes and your strongest topics will appear here."
              className="border-0 py-4"
            />
          ) : (
            <ul className="mt-3 divide-y divide-(--color-border)">
              {strengths.map((o) => (
                <li key={`${o.chapter_id}-${o.code}`} className="flex items-center gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{o.description}</div>
                    <div className="text-xs text-(--color-muted-foreground)">
                      Chapter {o.chapter_number} · {o.chapter_title}
                    </div>
                  </div>
                  <b className="text-sm text-(--color-success)">{Math.round((o.mastery ?? 0) * 100)}%</b>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="rounded-2xl p-6">
          <h2 className="font-display text-lg font-bold">To improve</h2>
          <p className="mt-0.5 text-sm text-(--color-muted-foreground)">
            Mastery below 60%. Focus your next quizzes here.
          </p>
          {weaknesses.length === 0 ? (
            <Empty
              title="Nothing flagged"
              description="You are holding above 60% on every attempted topic. Keep going!"
              className="border-0 py-4"
            />
          ) : (
            <ul className="mt-3 divide-y divide-(--color-border)">
              {weaknesses.map((o) => (
                <li key={`${o.chapter_id}-${o.code}`} className="flex items-center gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{o.description}</div>
                    <div className="text-xs text-(--color-muted-foreground)">
                      Chapter {o.chapter_number} · {o.chapter_title}
                    </div>
                  </div>
                  <b className="text-sm text-(--color-warning)">{Math.round((o.mastery ?? 0) * 100)}%</b>
                  <Button asChild size="sm" variant="secondary" className="rounded-lg">
                    <Link to={practiseHref(o.chapter_id)}>Practise</Link>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Disclosure title="Topic map, score trend and test history">
        <div className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              {masteryQ.data ? (
                <MasteryHeatmap
                  title="Topic mastery map"
                  description="Colour shows your running mastery per learning outcome."
                  chapters={masteryQ.data.chapters.map((ch) => ({
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
                  <CardContent className="py-8">
                    <Empty title="No mastery data yet" />
                  </CardContent>
                </Card>
              )}
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Score trend</CardTitle>
                <CardDescription>Evaluated tests over time.</CardDescription>
              </CardHeader>
              <CardContent className="h-64">
                {trend && trend.series.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={trend.series.map((p, i) => ({
                        index: i + 1,
                        name: p.assessment_title,
                        percentage: p.percentage,
                      }))}
                      margin={{ top: 8, right: 12, bottom: 0, left: -12 }}
                    >
                      <CartesianGrid stroke="oklch(90% 0.008 260)" strokeDasharray="3 3" />
                      <XAxis dataKey="index" tickLine={false} axisLine={false} fontSize={11} />
                      <YAxis domain={[0, 100]} tickLine={false} axisLine={false} fontSize={11} unit="%" />
                      <Tooltip
                        contentStyle={{ borderRadius: 8, border: "1px solid oklch(90% 0.008 260)" }}
                        labelFormatter={(_, p) => p[0]?.payload?.name ?? ""}
                        formatter={(v) => [`${v}%`, "Score"] as [string, string]}
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
                  <Empty title="No tests evaluated yet" className="border-0 py-6" />
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Test history</CardTitle>
              <CardDescription>
                All published or closed assessments in this subject. Scores show as percentages.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {evaluatedAssessments.length === 0 ? (
                <Empty title="No tests yet" className="border-0 py-6" />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs uppercase tracking-wide text-(--color-muted-foreground)">
                      <tr>
                        <th className="pb-2 pr-3">Title</th>
                        <th className="pb-2 pr-3">Type</th>
                        <th className="pb-2 pr-3">Total marks</th>
                        <th className="pb-2 pr-3">Date</th>
                        <th className="pb-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evaluatedAssessments.map((a) => (
                        <tr key={a.id} className="border-t border-(--color-border)">
                          <td className="py-2 pr-3">
                            <Link
                              to={`/assessments/${a.id}/take`}
                              className="text-(--color-primary) hover:underline"
                            >
                              {a.title}
                            </Link>
                          </td>
                          <td className="py-2 pr-3">
                            <Badge variant="outline">{a.type}</Badge>
                          </td>
                          <td className="py-2 pr-3">{a.total_marks}</td>
                          <td className="py-2 pr-3 text-(--color-muted-foreground)">
                            {formatDateTime(a.published_at)}
                          </td>
                          <td className="py-2">
                            <Badge
                              variant={
                                a.status === "PUBLISHED" ? "success" : a.status === "CLOSED" ? "secondary" : "warning"
                              }
                            >
                              {a.status}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </Disclosure>
    </div>
  );
}

/** One friendly line that opens the page, based on what the learner has done. */
function friendlySummary({
  firstName,
  average,
  practiceDays,
  strongestSubject,
}: {
  firstName: string;
  average: number | null;
  practiceDays: number | undefined;
  strongestSubject: string | null;
}): string {
  const name = firstName ? `, ${firstName}` : "";
  if (average === null) {
    return `Welcome${name}. Take a quiz and your report card will start to fill in.`;
  }
  const head = average >= 0.6 ? `You are doing well${name}.` : `Keep going${name}.`;
  const bits: string[] = [];
  if (practiceDays !== undefined) {
    bits.push(`you practised ${practiceDays} ${practiceDays === 1 ? "day" : "days"} this week`);
  }
  bits.push(`your average mastery is ${Math.round(average * 100)}%`);
  const joined = bits.join(" and ");
  const sentence = `${joined.charAt(0).toUpperCase()}${joined.slice(1)}.`;
  const strongest = strongestSubject ? ` ${strongestSubject} is your strongest subject.` : "";
  return `${head} ${sentence}${strongest}`;
}

/** The subject whose attempted chapters have the highest average mastery. */
function strongestSubjectName(
  subjects: { subject_name: string; chapters: { average_mastery: number | null }[] }[],
): string | null {
  let best: { name: string; avg: number } | null = null;
  for (const s of subjects) {
    const vals = s.chapters
      .map((c) => c.average_mastery)
      .filter((v): v is number => v !== null);
    if (vals.length === 0) continue;
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    if (best === null || avg > best.avg) best = { name: s.subject_name, avg };
  }
  return best?.name ?? null;
}

interface OutcomeHighlight {
  chapter_id: number;
  chapter_number: number;
  chapter_title: string;
  code: string;
  description: string;
  mastery: number | null;
}

function pickHighlights(
  grid:
    | {
        chapters: {
          chapter_id: number;
          chapter_number: number;
          chapter_title: string;
          outcomes: { code: string; description: string; mastery: number | null; attempts: number }[];
        }[];
      }
    | undefined,
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
        });
      }
    }
  }
  const strengths = attempted
    .filter((o) => (o.mastery ?? 0) >= 0.75)
    .sort((a, b) => (b.mastery ?? 0) - (a.mastery ?? 0))
    .slice(0, 5);
  const weaknesses = attempted
    .filter((o) => (o.mastery ?? 1) < 0.6)
    .sort((a, b) => (a.mastery ?? 1) - (b.mastery ?? 1))
    .slice(0, 5);
  return { strengths, weaknesses };
}

function computeGrade(
  averagePercent: number | null,
): { label: string; note: string; intent: "default" | "success" | "warning" | "danger" } {
  if (averagePercent === null || averagePercent === undefined) {
    return { label: "—", note: "Take a few quizzes to see your grade.", intent: "default" };
  }
  if (averagePercent >= 85) return { label: "A", note: "Excellent. Keep it up!", intent: "success" };
  if (averagePercent >= 70) return { label: "B", note: "Strong. Push for an A!", intent: "success" };
  if (averagePercent >= 55) return { label: "C", note: "On track. Focus areas help.", intent: "default" };
  if (averagePercent >= 40) return { label: "D", note: "Practise weak topics this week.", intent: "warning" };
  return { label: "Needs focus", note: "Schedule daily practice quizzes.", intent: "danger" };
}
