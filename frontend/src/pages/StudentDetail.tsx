import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Loader2,
  NotebookPen,
  TrendingUp,
} from "lucide-react";
import {
  LineChart,
  Line,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
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
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MasteryHeatmap } from "@/components/MasteryHeatmap";
import type { HeatmapView } from "@/components/MasteryHeatmap";
import { StatCard } from "@/components/StatCard";
import { StudentFocusAreas } from "@/components/StudentFocusAreas";
import { labelForSubject } from "@/components/BoardContextBar";
import {
  useCreateInterventionNote,
  useMySections,
  useStudentInterventionNotes,
  useStudentMastery,
  useStudentTrend,
  useSubjects,
} from "@/lib/queries";
import { humanError } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/utils";

export function StudentDetailPage() {
  const { studentId } = useParams();
  const id = studentId ? Number(studentId) : undefined;

  const sectionsQ = useMySections();
  const classLevel = sectionsQ.data?.[0]?.class_level ?? undefined;
  const subjectsQ = useSubjects(classLevel);
  const [subjectId, setSubjectId] = useState<number | undefined>(undefined);
  const chosenSubject =
    subjectId ??
    subjectsQ.data?.find((s) => s.name === "Science")?.id ??
    subjectsQ.data?.[0]?.id;

  const masteryQ = useStudentMastery({
    student_id: id,
    class_level: classLevel,
    subject_id: chosenSubject,
  });
  const trendQ = useStudentTrend({ student_id: id, subject_id: chosenSubject });
  const notesQ = useStudentInterventionNotes(id);
  const createNote = useCreateInterventionNote();
  const [note, setNote] = useState("");
  const [heatmapView, setHeatmapView] = useState<HeatmapView>("combined");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!id || !note.trim()) return;
    try {
      await createNote.mutateAsync({ student_id: id, note: note.trim() });
      setNote("");
      toast.success("Intervention note saved");
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  const studentName = masteryQ.data?.subject ? undefined : undefined; // served by teacher
  const header = `Student #${id ?? "?"}${studentName ? ` · ${studentName}` : ""}`;

  return (
    <ThemedPage>
      <PageHeader
        title={header}
        description="Mastery map across the syllabus, test trend over time, and intervention history."
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
              <Link to="/sections">
                <ArrowLeft className="h-4 w-4" />
                Back
              </Link>
            </Button>
          </div>
        }
      />

      {masteryQ.isLoading ? (
        <Loader />
      ) : !masteryQ.data ? (
        <Empty
          title="No mastery data"
          description="This student has not attempted any assessments for the selected subject."
        />
      ) : (
        <>
          <div className="mb-6 grid gap-4 md:grid-cols-3">
            <StatCard
              label="Outcomes attempted"
              value={`${masteryQ.data.summary.outcomes_attempted}/${masteryQ.data.summary.outcomes_total}`}
              icon={<BookOpen className="h-5 w-5" />}
              sub={`${masteryQ.data.subject ?? "—"} syllabus`}
            />
            <StatCard
              label="Average mastery"
              value={formatPercent(masteryQ.data.summary.average_mastery)}
              icon={<TrendingUp className="h-5 w-5" />}
              intent="success"
              sub="Across attempted outcomes"
            />
            <StatCard
              label="Tests evaluated"
              value={trendQ.data?.summary.tests_evaluated ?? 0}
              sub={
                trendQ.data?.summary.average_percentage !== null &&
                trendQ.data?.summary.average_percentage !== undefined
                  ? `Avg score ${trendQ.data.summary.average_percentage}%`
                  : undefined
              }
              icon={<NotebookPen className="h-5 w-5" />}
            />
          </div>

          {/* Per-student "weak topics / areas of focus" panel. Lives
              ABOVE the heatmap so the teacher sees the actionable list
              first; the heatmap below provides the full landscape for
              context. */}
          <StudentFocusAreas chapters={masteryQ.data.chapters} limit={5} />

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <MasteryHeatmap
                title="Topic mastery map"
                description="Colour shows the student's running mastery per learning outcome."
                view={heatmapView}
                headerSlot={
                  <div className="w-48">
                    <Select
                      value={heatmapView}
                      onValueChange={(v) => setHeatmapView(v as HeatmapView)}
                    >
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
            </div>
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Score trend</CardTitle>
                  <CardDescription>Evaluated assessments over time.</CardDescription>
                </CardHeader>
                <CardContent className="h-64">
                  {trendQ.data && trendQ.data.series.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={trendQ.data.series.map((p, idx) => ({
                          index: idx + 1,
                          name: p.assessment_title,
                          percentage: p.percentage,
                          date: p.date ? p.date.slice(0, 10) : "",
                        }))}
                        margin={{ top: 8, right: 12, bottom: 0, left: -12 }}
                      >
                        <CartesianGrid stroke="oklch(90% 0.008 260)" strokeDasharray="3 3" />
                        <XAxis
                          dataKey="index"
                          tickLine={false}
                          axisLine={false}
                          fontSize={11}
                        />
                        <YAxis
                          domain={[0, 100]}
                          tickLine={false}
                          axisLine={false}
                          fontSize={11}
                          unit="%"
                        />
                        <Tooltip
                          contentStyle={{ borderRadius: 8, border: "1px solid oklch(90% 0.008 260)" }}
                          labelFormatter={(_, p) =>
                            p[0]?.payload?.name ?? ""
                          }
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
                    <Empty
                      title="No evaluated tests yet"
                      className="border-0 py-8"
                    />
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Intervention notes</CardTitle>
                  <CardDescription>Log follow-up items for this student.</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-2">
                    <Label htmlFor="note" className="sr-only">
                      Note
                    </Label>
                    <textarea
                      id="note"
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      rows={3}
                      placeholder="e.g. Struggling with scientific method — assign remedial quiz."
                      className="flex w-full rounded-md border border-(--color-input) bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-(--color-muted-foreground) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--color-ring) disabled:cursor-not-allowed disabled:opacity-50"
                    />
                    <div className="flex justify-end">
                      <Button
                        type="submit"
                        size="sm"
                        disabled={createNote.isPending || !note.trim()}
                      >
                        {createNote.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                        Save note
                      </Button>
                    </div>
                  </form>
                  <div className="mt-4 space-y-2">
                    {notesQ.data && notesQ.data.length > 0 ? (
                      notesQ.data.map((n) => (
                        <div
                          key={n.id}
                          className="rounded-md border border-(--color-border) p-3 text-sm"
                        >
                          <div className="flex items-center justify-between gap-2 text-xs text-(--color-muted-foreground)">
                            <Badge variant="outline">Teacher #{n.teacher_id}</Badge>
                            <span>{formatDate(n.created_at)}</span>
                          </div>
                          <p className="mt-1">{n.note}</p>
                        </div>
                      ))
                    ) : (
                      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
                        <AlertTriangle className="h-4 w-4" />
                        No notes yet.
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}
    </ThemedPage>
  );
}

function Loader() {
  return (
    <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
      <Loader2 className="h-4 w-4 animate-spin" />
      Loading...
    </div>
  );
}
