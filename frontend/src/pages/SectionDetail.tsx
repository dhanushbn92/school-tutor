import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ClipboardList,
  Loader2,
  TrendingDown,
  Users,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { MasteryHeatmap } from "@/components/MasteryHeatmap";
import { StatCard } from "@/components/StatCard";
import { labelForSubject } from "@/components/BoardContextBar";
import {
  useMyAssessments,
  useMySections,
  useMyStudents,
  useSectionLeaderboard,
  useSectionPerformance,
  useSectionTopicAverages,
  useSectionWeakestTopics,
  useSubjects,
} from "@/lib/queries";
import { cn, formatDateTime, formatMarks } from "@/lib/utils";

export function SectionDetailPage() {
  const { sectionId } = useParams();
  const sid = sectionId ? Number(sectionId) : undefined;

  const sectionsQ = useMySections();
  const section = sectionsQ.data?.find((s) => s.id === sid);

  const subjectsQ = useSubjects(section?.class_level ?? undefined);
  const [subjectId, setSubjectId] = useState<number | undefined>(undefined);
  const chosenSubject =
    subjectId ??
    subjectsQ.data?.find((s) => s.name === "Science")?.id ??
    subjectsQ.data?.[0]?.id;

  const studentsQ = useMyStudents(sid);
  const assessmentsQ = useMyAssessments();
  const sectionAssessments = useMemo(
    () => (assessmentsQ.data ?? []).filter((a) => a.section_id === sid),
    [assessmentsQ.data, sid],
  );
  const [assessmentId, setAssessmentId] = useState<number | undefined>(undefined);
  const activeAssessment = assessmentId ?? sectionAssessments[0]?.id;

  const perfQ = useSectionPerformance(sid ?? 0, activeAssessment);
  const topicQ = useSectionTopicAverages({
    section_id: sid,
    class_level: section?.class_level ?? undefined,
    subject_id: chosenSubject,
  });
  const weakestQ = useSectionWeakestTopics({
    section_id: sid,
    class_level: section?.class_level ?? undefined,
    subject_id: chosenSubject,
    limit: 5,
  });
  const leaderboardQ = useSectionLeaderboard({
    section_id: sid,
    subject_id: chosenSubject,
  });

  if (sectionsQ.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading...
      </div>
    );
  }
  if (!section) {
    return (
      <Empty
        title="Section not found"
        description="You may not have access to this section, or the ID is invalid."
        action={
          <Button asChild variant="outline">
            <Link to="/sections">
              <ArrowLeft className="h-4 w-4" />
              Back to classes
            </Link>
          </Button>
        }
      />
    );
  }

  return (
    <ThemedPage>
      <PageHeader
        title={`${section.class_display_name} · ${section.name}`}
        description={
          <>
            Academic year {section.academic_year ?? "—"} &middot;{" "}
            {studentsQ.data?.length ?? "…"} students
          </>
        }
        actions={
          <Button asChild variant="outline">
            <Link to="/sections">
              <ArrowLeft className="h-4 w-4" />
              All classes
            </Link>
          </Button>
        }
      />

      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <StatCard
          label="Students enrolled"
          value={studentsQ.data?.length ?? 0}
          icon={<Users className="h-5 w-5" />}
        />
        <StatCard
          label="Assessments"
          value={sectionAssessments.length}
          sub={`${sectionAssessments.filter((a) => a.status === "PUBLISHED").length} published`}
          icon={<ClipboardList className="h-5 w-5" />}
          intent="success"
        />
        <StatCard
          label="Outcomes attempted"
          value={
            topicQ.data
              ? topicQ.data.chapters.reduce(
                  (sum, ch) =>
                    sum + ch.outcomes.filter((o) => o.average_mastery !== null).length,
                  0,
                )
              : 0
          }
          sub={
            topicQ.data
              ? `of ${topicQ.data.chapters.reduce((sum, ch) => sum + ch.outcomes.length, 0)} total`
              : undefined
          }
          icon={<TrendingDown className="h-5 w-5" />}
          intent="warning"
        />
        <StatCard
          label="Class average"
          value={
            perfQ.data?.summary.average !== null && perfQ.data?.summary.average !== undefined
              ? `${perfQ.data.summary.average}/${perfQ.data.total_marks}`
              : "—"
          }
          sub={perfQ.data ? `Latest: ${perfQ.data.assessment_title}` : "Pick an assessment"}
          icon={<ClipboardList className="h-5 w-5" />}
        />
      </div>

      {/* Gradebook */}
      <Card className="mb-6">
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Gradebook</CardTitle>
            <CardDescription>Per-student results for one assessment.</CardDescription>
          </div>
          <div className="w-64">
            {sectionAssessments.length > 0 && activeAssessment ? (
              <Select
                value={String(activeAssessment)}
                onValueChange={(v) => setAssessmentId(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {sectionAssessments.map((a) => (
                    <SelectItem key={a.id} value={String(a.id)}>
                      {a.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : null}
          </div>
        </CardHeader>
        <CardContent>
          {sectionAssessments.length === 0 ? (
            <Empty
              icon={<ClipboardList className="h-6 w-6" />}
              title="No assessments yet"
              description="Create an assessment to see a gradebook."
              action={
                <Button asChild>
                  <Link to="/assessments">Go to assessments</Link>
                </Button>
              }
            />
          ) : perfQ.isLoading ? (
            <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading...
            </div>
          ) : perfQ.data ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
                  <tr className="border-b border-(--color-border)">
                    <th className="py-2 text-left font-medium">Roll</th>
                    <th className="py-2 text-left font-medium">Student</th>
                    <th className="py-2 text-left font-medium">Status</th>
                    <th className="py-2 text-right font-medium">Score</th>
                    <th className="py-2 text-right font-medium">Submitted</th>
                  </tr>
                </thead>
                <tbody>
                  {perfQ.data.students.map((s) => (
                    <tr key={s.student_id} className="border-b border-(--color-border)/60">
                      <td className="py-2 pr-2 text-(--color-muted-foreground)">
                        {s.roll_number ?? "—"}
                      </td>
                      <td className="py-2">
                        <Link
                          to={`/students/${s.student_id}`}
                          className="font-medium underline-offset-4 hover:underline"
                        >
                          {s.full_name ?? `Student #${s.student_id}`}
                        </Link>
                      </td>
                      <td className="py-2">
                        <StatusBadge status={s.status} />
                      </td>
                      <td
                        className={cn(
                          "py-2 text-right tabular-nums",
                          scoreClass(s.total_awarded, s.max_marks),
                        )}
                      >
                        {formatMarks(s.total_awarded, s.max_marks)}
                      </td>
                      <td className="py-2 pl-2 text-right text-xs text-(--color-muted-foreground)">
                        {formatDateTime(s.submitted_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Subject toggle + topic heatmap */}
      <div className="mb-6 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Class mastery</h2>
        <div className="w-52">
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
      </div>

      {topicQ.data ? (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <MasteryHeatmap
              title="Topic mastery heatmap"
              description="Average mastery across enrolled students, per learning outcome."
              chapters={topicQ.data.chapters.map((ch) => ({
                chapter_id: ch.chapter_id,
                chapter_number: ch.chapter_number,
                chapter_title: ch.chapter_title,
                outcomes: ch.outcomes.map((o) => ({
                  code: o.code,
                  description: o.description,
                  mastery: o.average_mastery,
                  students_attempted: o.students_attempted,
                })),
              }))}
            />
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Weakest outcomes</CardTitle>
              <CardDescription>Where remediation will have the biggest impact.</CardDescription>
            </CardHeader>
            <CardContent>
              {weakestQ.data && weakestQ.data.weakest.length > 0 ? (
                <ul className="space-y-3">
                  {weakestQ.data.weakest.map((w) => (
                    <li
                      key={w.code}
                      className="rounded-md border border-(--color-border) p-3 text-sm"
                    >
                      <div className="flex items-center justify-between gap-2 text-xs text-(--color-muted-foreground)">
                        <Badge variant="outline">{w.code}</Badge>
                        <span>Ch {w.chapter_number}</span>
                      </div>
                      <div className="mt-1 line-clamp-2">{w.description}</div>
                      <div className="mt-2 flex items-center justify-between text-xs">
                        <span className="text-(--color-muted-foreground)">
                          {w.students_attempted} attempted
                        </span>
                        <span className="font-semibold">
                          {((w.average_mastery ?? 0) * 100).toFixed(0)}% avg
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty
                  title="No data yet"
                  description="Once students submit assessments, weakest outcomes will surface here."
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Class leaderboard</CardTitle>
              <CardDescription>
                Average score across all evaluated assessments in this subject. Use this to spot top performers and students who need extra support.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {leaderboardQ.isLoading ? (
                <div className="text-sm text-(--color-muted-foreground)">Loading…</div>
              ) : leaderboardQ.data && leaderboardQ.data.students.length > 0 ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground) mb-2">
                      Top performers
                    </div>
                    <ol className="space-y-1 text-sm">
                      {leaderboardQ.data.students
                        .filter((s) => s.average_percentage !== null)
                        .slice(0, 5)
                        .map((s, i) => (
                          <li
                            key={s.student_id}
                            className="flex items-center justify-between rounded-md border border-(--color-border) px-3 py-2"
                          >
                            <span className="flex items-center gap-2 min-w-0">
                              <Badge variant={i === 0 ? "success" : "outline"}>
                                {i + 1}
                              </Badge>
                              <Link
                                to={`/students/${s.student_id}`}
                                className="truncate text-(--color-primary) hover:underline"
                              >
                                {s.full_name ?? `#${s.student_id}`}
                              </Link>
                            </span>
                            <span className="font-medium">
                              {s.average_percentage !== null ? `${s.average_percentage}%` : "—"}
                            </span>
                          </li>
                        ))}
                    </ol>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground) mb-2">
                      Needs support
                    </div>
                    <ol className="space-y-1 text-sm">
                      {leaderboardQ.data.students
                        .filter((s) => s.average_percentage !== null)
                        .slice()
                        .reverse()
                        .slice(0, 5)
                        .map((s) => (
                          <li
                            key={s.student_id}
                            className="flex items-center justify-between rounded-md border border-(--color-border) px-3 py-2"
                          >
                            <Link
                              to={`/students/${s.student_id}`}
                              className="truncate text-(--color-primary) hover:underline"
                            >
                              {s.full_name ?? `#${s.student_id}`}
                            </Link>
                            <span className={cn("font-medium", scoreClass(Math.round((s.average_percentage ?? 0)), 100))}>
                              {s.average_percentage !== null ? `${s.average_percentage}%` : "—"}
                            </span>
                          </li>
                        ))}
                    </ol>
                  </div>
                </div>
              ) : (
                <Empty
                  title="No leaderboard data yet"
                  description="Once students submit and have evaluated assessments, the leaderboard fills in."
                />
              )}
            </CardContent>
          </Card>
        </div>
      ) : null}
    </ThemedPage>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { variant: "default" | "secondary" | "success" | "warning" | "outline"; label: string }> = {
    EVALUATED: { variant: "success", label: "Evaluated" },
    SUBMITTED: { variant: "warning", label: "Submitted" },
    LATE: { variant: "warning", label: "Late" },
    DRAFT: { variant: "secondary", label: "Draft" },
    NOT_SUBMITTED: { variant: "outline", label: "Not submitted" },
  };
  const cfg = map[status] ?? { variant: "outline" as const, label: status };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

function scoreClass(awarded: number | null | undefined, max: number): string {
  if (awarded === null || awarded === undefined) return "text-(--color-muted-foreground)";
  const pct = awarded / Math.max(1, max);
  if (pct >= 0.75) return "text-(--color-success) font-semibold";
  if (pct < 0.4) return "text-(--color-destructive)";
  return "";
}
