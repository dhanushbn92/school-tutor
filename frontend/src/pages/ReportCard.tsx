import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Award,
  ClipboardCheck,
  Loader2,
  Target,
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
import { StatCard } from "@/components/StatCard";
import { MasteryHeatmap } from "@/components/MasteryHeatmap";
import { labelForSubject } from "@/components/BoardContextBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { formatDateTime, formatPercent } from "@/lib/utils";
import { BUCKET_LABEL } from "@/lib/types";
import type { CognitiveBucket } from "@/lib/types";

export function ReportCardPage() {
  const { user } = useAuth();
  const sectionsQ = useMySections();
  const section = sectionsQ.data?.[0];
  const subjectsQ = useSubjects(section?.class_level ?? undefined);
  const [subjectId, setSubjectId] = useState<number | undefined>();
  const chosenSubject =
    subjectId ??
    subjectsQ.data?.find((s) => s.name === "Science")?.id ??
    subjectsQ.data?.[0]?.id;

  const studentsQ = useMyStudents(section?.id);
  const myStudent = studentsQ.data?.find((s) => s.user_id === user?.id);

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

  return (
    <ThemedPage>
      <PageHeader
        title={`Report card · ${user?.full_name ?? "Student"}`}
        description={
          section
            ? `Class ${section.class_level} · ${section.academic_year}`
            : "Your academic report card."
        }
        actions={
          <div className="flex items-center gap-2">
            <div className="w-44">
              {subjectsQ.data && subjectsQ.data.length > 0 ? (
                <Select
                  value={String(chosenSubject ?? "")}
                  onValueChange={(v) => setSubjectId(Number(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Subject" />
                  </SelectTrigger>
                  <SelectContent>
                    {subjectsQ.data.map((s) => (
                      <SelectItem key={s.id} value={String(s.id)}>
                        {labelForSubject(s)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : null}
            </div>
            <Button asChild variant="outline">
              <Link to="/">
                <ArrowLeft className="h-4 w-4" />
                Back
              </Link>
            </Button>
          </div>
        }
      />

      <div className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Outcomes covered"
          value={
            summary
              ? `${summary.outcomes_attempted}/${summary.outcomes_total}`
              : "—"
          }
          sub={`${masteryQ.data?.subject ?? "—"} syllabus`}
          icon={<Award className="h-5 w-5" />}
        />
        <StatCard
          label="Average mastery"
          value={formatPercent(summary?.average_mastery)}
          sub="Across attempted topics"
          icon={<TrendingUp className="h-5 w-5" />}
          intent="success"
        />
        <StatCard
          label="Tests evaluated"
          value={trend?.summary.tests_evaluated ?? 0}
          sub={
            trend?.summary.average_percentage !== null &&
            trend?.summary.average_percentage !== undefined
              ? `Average score ${trend.summary.average_percentage}%`
              : "No tests taken yet"
          }
          icon={<ClipboardCheck className="h-5 w-5" />}
        />
        <StatCard
          label="Overall grade"
          value={grade.label}
          sub={grade.note}
          icon={<Target className="h-5 w-5" />}
          intent={grade.intent}
        />
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        {(["FACTUAL", "UNDERSTANDING", "APPLICATION"] as CognitiveBucket[]).map((b) => {
          const stats = summary?.by_bucket?.[b];
          return (
            <Card key={b}>
              <CardHeader className="pb-1">
                <CardTitle className="text-base">{BUCKET_LABEL[b]}</CardTitle>
                <CardDescription className="text-xs">
                  {stats?.outcomes_attempted
                    ? `${stats.outcomes_attempted} outcomes attempted`
                    : "No attempts yet"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">
                  {formatPercent(stats?.average_mastery ?? null)}
                </div>
                <div className="mt-1 text-xs text-(--color-muted-foreground)">
                  Average mastery in {BUCKET_LABEL[b].toLowerCase()} questions
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Trophy className="h-4 w-4 text-(--color-success)" />
              <CardTitle>Strengths</CardTitle>
            </div>
            <CardDescription>Topics you're consistently scoring 75%+ on.</CardDescription>
          </CardHeader>
          <CardContent>
            {strengths.length === 0 ? (
              <Empty
                title="Not enough data yet"
                description="Take a few more quizzes and your strongest topics will appear here."
                className="border-0 py-4"
              />
            ) : (
              <ul className="space-y-2 text-sm">
                {strengths.map((o) => (
                  <li
                    key={`${o.chapter_id}-${o.code}`}
                    className="flex items-center justify-between gap-3 rounded-md border border-(--color-border) px-3 py-2"
                  >
                    <div className="min-w-0">
                      <div className="font-medium truncate">{o.description}</div>
                      <div className="text-[11px] text-(--color-muted-foreground)">
                        Ch {o.chapter_number}. {o.chapter_title}
                      </div>
                    </div>
                    <Badge variant="success">{Math.round((o.mastery ?? 0) * 100)}%</Badge>
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
              <CardTitle>Improvement topics</CardTitle>
            </div>
            <CardDescription>Mastery below 60%. Focus your next quizzes here.</CardDescription>
          </CardHeader>
          <CardContent>
            {weaknesses.length === 0 ? (
              <Empty
                title="Nothing flagged"
                description="You're holding above 60% on every attempted topic. Keep going!"
                className="border-0 py-4"
              />
            ) : (
              <ul className="space-y-2 text-sm">
                {weaknesses.map((o) => (
                  <li
                    key={`${o.chapter_id}-${o.code}`}
                    className="flex items-center justify-between gap-3 rounded-md border border-(--color-border) px-3 py-2"
                  >
                    <div className="min-w-0">
                      <div className="font-medium truncate">{o.description}</div>
                      <div className="text-[11px] text-(--color-muted-foreground)">
                        Ch {o.chapter_number}. {o.chapter_title}
                      </div>
                    </div>
                    <Badge variant="warning">{Math.round((o.mastery ?? 0) * 100)}%</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-3">
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
  if (averagePercent >= 85) return { label: "A", note: "Excellent — keep it up!", intent: "success" };
  if (averagePercent >= 70) return { label: "B", note: "Strong — push for an A!", intent: "success" };
  if (averagePercent >= 55) return { label: "C", note: "On track — focus areas help.", intent: "default" };
  if (averagePercent >= 40) return { label: "D", note: "Practise weak topics this week.", intent: "warning" };
  return { label: "Needs focus", note: "Schedule daily practice quizzes.", intent: "danger" };
}
