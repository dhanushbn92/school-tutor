import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ClipboardList,
  GraduationCap,
  Loader2,
  Plus,
  Send,
  Sparkles,
  User as UserIcon,
  X,
} from "lucide-react";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Empty } from "@/components/ui/empty";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { humanError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  useChapters,
  useMyAssessments,
  useMySubmissions,
  usePublishAssessment,
  useSubjects,
} from "@/lib/queries";
import { formatDateTime } from "@/lib/utils";

export function AssessmentsPage() {
  const { user } = useAuth();
  const { data, isLoading } = useMyAssessments();
  const canTake = user?.role === "student" || user?.role === "individual_learner";
  const canBuild = user?.role === "school_admin" || user?.role === "teacher";
  const isIndividual = user?.role === "individual_learner";
  const submissionsQ = useMySubmissions();
  const submissionByAssessment = new Map(
    (submissionsQ.data ?? []).map((s) => [s.assessment_id, s]),
  );
  // Inline publish for teachers / admins. We track the in-flight assessment
  // id so multiple rows can disable independently while one is pending.
  const publishMut = usePublishAssessment();

  // Filter state. Subject + chapter dropdowns let the learner / teacher
  // narrow a long assessment list. Chapter filter is gated on a subject
  // pick because chapters belong to subjects; switching subject resets
  // the chapter pick to avoid showing a stale chapter from a different
  // subject.
  const [pickedSubjectId, setPickedSubjectId] = useState<number | null>(null);
  const [pickedChapterId, setPickedChapterId] = useState<number | null>(null);

  // Subjects / chapters for the dropdown labels. We fetch the full
  // subject catalog (across all classes) so a teacher viewing
  // assessments across several class levels still sees real subject
  // names rather than IDs.
  const subjectsQ = useSubjects(undefined, { fetchAllWhenUndefined: true });
  const chaptersQ = useChapters({
    subject_id: pickedSubjectId ?? undefined,
  });

  // Derive ONLY the subjects + chapters that actually appear in this
  // user's assessment list. No point offering filters that would
  // return zero rows.
  const subjectsInUse = useMemo(() => {
    const ids = new Set<number>();
    (data ?? []).forEach((a) => ids.add(a.subject_id));
    const all = subjectsQ.data ?? [];
    return all
      .filter((s) => ids.has(s.id))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [data, subjectsQ.data]);

  const chaptersInUse = useMemo(() => {
    if (pickedSubjectId === null) return [];
    const ids = new Set<number>();
    (data ?? []).forEach((a) => {
      if (a.subject_id === pickedSubjectId && a.chapter_id !== null) {
        ids.add(a.chapter_id);
      }
    });
    const all = chaptersQ.data ?? [];
    return all
      .filter((c) => ids.has(c.id))
      .sort((a, b) => a.chapter_number - b.chapter_number);
  }, [data, chaptersQ.data, pickedSubjectId]);

  // Apply the filters. Default (no picks) shows everything.
  const filtered = useMemo(() => {
    if (!data) return [];
    return data.filter((a) => {
      if (pickedSubjectId !== null && a.subject_id !== pickedSubjectId) return false;
      if (pickedChapterId !== null && a.chapter_id !== pickedChapterId) return false;
      return true;
    });
  }, [data, pickedSubjectId, pickedChapterId]);

  const hasActiveFilter = pickedSubjectId !== null || pickedChapterId !== null;

  function onSubjectChange(value: string) {
    const next = value === "all" ? null : Number(value);
    setPickedSubjectId(next);
    // Chapters belong to subjects — resetting prevents a stale chapter
    // from a different subject sticking around in the filter.
    setPickedChapterId(null);
  }

  function onChapterChange(value: string) {
    setPickedChapterId(value === "all" ? null : Number(value));
  }

  function clearFilters() {
    setPickedSubjectId(null);
    setPickedChapterId(null);
  }

  return (
    <ThemedPage>
      <PageHeader
        title={canTake ? "My quizzes" : "Assessments"}
        description={
          canTake
            ? "Quizzes assigned to you (or that you've started). Click Take to attempt."
            : "Quizzes, worksheets, and tests you've built from the question bank."
        }
        actions={
          canBuild ? (
            <Button asChild>
              <Link to="/assessments/new">
                <Plus className="h-4 w-4" />
                New quiz from bank
              </Link>
            </Button>
          ) : isIndividual ? (
            <Button asChild>
              <Link to="/quick-quiz">
                <Sparkles className="h-4 w-4" />
                Start a quiz
              </Link>
            </Button>
          ) : undefined
        }
      />
      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading...
        </div>
      ) : !data || data.length === 0 ? (
        <Empty
          icon={<ClipboardList className="h-6 w-6" />}
          title={canTake ? "No quizzes yet" : "No assessments yet"}
          description={
            canTake
              ? isIndividual
                ? "Tap Start a quiz to draw fresh questions from the bank."
                : "Your teacher hasn't assigned anything yet."
              : "Assessments appear here once you create them from approved questions."
          }
          action={
            isIndividual ? (
              <Button asChild>
                <Link to="/quick-quiz">
                  <Sparkles className="h-4 w-4" />
                  Start a quiz
                </Link>
              </Button>
            ) : undefined
          }
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>{canTake ? "My quizzes" : "All assessments"}</CardTitle>
            <CardDescription>
              {canTake
                ? "Click Take to attempt one. Your score updates your mastery map."
                : "Click into one to view questions and the gradebook."}
            </CardDescription>
          </CardHeader>
          {/* Filter row. Only shown when the user has more than a couple
              of assessments — a learner with three quizzes total doesn't
              need a subject filter cluttering the page. Subject options
              are derived from the assessments themselves so we only
              offer filters that would actually return rows. */}
          {subjectsInUse.length > 1 && (
            <div className="border-b border-(--color-border) px-6 py-3">
              <div className="flex flex-wrap items-end gap-3">
                <div className="grid gap-1.5">
                  <Label className="text-xs" htmlFor="assess-subject">
                    Subject
                  </Label>
                  <Select
                    value={
                      pickedSubjectId === null ? "all" : String(pickedSubjectId)
                    }
                    onValueChange={onSubjectChange}
                  >
                    <SelectTrigger id="assess-subject" className="w-[200px]">
                      <SelectValue placeholder="All subjects" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All subjects</SelectItem>
                      {subjectsInUse.map((s) => (
                        <SelectItem key={s.id} value={String(s.id)}>
                          {s.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Chapter dropdown only appears once a subject is picked
                    — "All subjects" with a chapter filter rarely makes
                    sense and would mostly confuse. */}
                {pickedSubjectId !== null && chaptersInUse.length > 0 && (
                  <div className="grid gap-1.5">
                    <Label className="text-xs" htmlFor="assess-chapter">
                      Chapter
                    </Label>
                    <Select
                      value={
                        pickedChapterId === null
                          ? "all"
                          : String(pickedChapterId)
                      }
                      onValueChange={onChapterChange}
                    >
                      <SelectTrigger id="assess-chapter" className="w-[260px]">
                        <SelectValue placeholder="All chapters" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All chapters</SelectItem>
                        {chaptersInUse.map((c) => (
                          <SelectItem key={c.id} value={String(c.id)}>
                            Ch {c.chapter_number}. {c.title}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                {hasActiveFilter && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearFilters}
                    className="self-end"
                  >
                    <X className="h-3.5 w-3.5" /> Clear
                  </Button>
                )}

                <div className="ml-auto self-end text-xs text-(--color-muted-foreground)">
                  Showing {filtered.length} of {data.length}
                </div>
              </div>
            </div>
          )}
          <CardContent className="overflow-x-auto">
            {filtered.length === 0 ? (
              <div className="py-8 text-center text-sm text-(--color-muted-foreground)">
                No quizzes match the current filter.{" "}
                <button
                  type="button"
                  onClick={clearFilters}
                  className="text-(--color-primary) underline-offset-2 hover:underline"
                >
                  Clear filter
                </button>
              </div>
            ) : (
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
                <tr className="border-b border-(--color-border)">
                  <th className="py-2 text-left font-medium">Title</th>
                  <th className="py-2 text-left font-medium">Type</th>
                  {/* Source column distinguishes self-started quizzes (e.g.,
                      via /quick-quiz) from teacher-assigned ones. Only
                      learners see it — for teachers / admins this would
                      mostly read "Self-study" against their own work. */}
                  {canTake && (
                    <th className="py-2 text-left font-medium">Source</th>
                  )}
                  <th className="py-2 text-left font-medium">Status</th>
                  <th className="py-2 text-right font-medium">Marks</th>
                  <th className="py-2 text-right font-medium">Questions</th>
                  <th className="py-2 text-right font-medium">Published</th>
                  <th className="py-2 text-right font-medium" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => {
                  const mySub = submissionByAssessment.get(a.id);
                  const isSelfStarted =
                    user?.id !== undefined && a.created_by_id === user.id;
                  return (
                    <tr
                      key={a.id}
                      // Subtle hover highlight makes scanning a long
                      // assessments list easier — your eye snaps to the
                      // row under the cursor without the noise of a
                      // strong selection treatment.
                      className="border-b border-(--color-border)/60 transition-colors hover:bg-(--color-muted)/40"
                    >
                      <td className="py-2">
                        <Link
                          to={`/assessments/${a.id}`}
                          className="font-medium underline-offset-4 hover:underline"
                        >
                          {a.title}
                        </Link>
                      </td>
                      <td className="py-2 text-(--color-muted-foreground)">{a.type}</td>
                      {canTake && (
                        <td className="py-2">
                          {isSelfStarted ? (
                            <Badge variant="secondary" className="gap-1">
                              <UserIcon className="h-3 w-3" /> Self-study
                            </Badge>
                          ) : (
                            <Badge variant="default" className="gap-1">
                              <GraduationCap className="h-3 w-3" /> Assigned
                            </Badge>
                          )}
                        </td>
                      )}
                      <td className="py-2">
                        {canTake && mySub ? (
                          <Badge
                            variant={
                              mySub.status === "EVALUATED" ? "success" : "warning"
                            }
                          >
                            {mySub.status === "EVALUATED"
                              ? `Done · ${mySub.total_awarded ?? 0}/${mySub.max_marks}`
                              : "Submitted"}
                          </Badge>
                        ) : (
                          <Badge
                            variant={
                              a.status === "PUBLISHED"
                                ? "success"
                                : a.status === "CLOSED"
                                  ? "outline"
                                  : "secondary"
                            }
                          >
                            {a.status}
                          </Badge>
                        )}
                      </td>
                      <td className="py-2 text-right tabular-nums">{a.total_marks}</td>
                      <td className="py-2 text-right tabular-nums">
                        {a.questions?.length ?? 0}
                      </td>
                      <td className="py-2 text-right text-xs text-(--color-muted-foreground)">
                        {formatDateTime(a.published_at)}
                      </td>
                      <td className="py-2 text-right">
                        {canTake && mySub ? (
                          <Button asChild size="sm" variant="outline">
                            <Link to={`/assessments/${a.id}`}>
                              View results
                              <ArrowRight className="h-3.5 w-3.5" />
                            </Link>
                          </Button>
                        ) : canTake && a.status === "PUBLISHED" ? (
                          <Button asChild size="sm">
                            <Link to={`/assessments/${a.id}/take`}>
                              Take
                              <ArrowRight className="h-3.5 w-3.5" />
                            </Link>
                          </Button>
                        ) : canBuild && a.status === "DRAFT" ? (
                          // One-click publish from the list. The disabled
                          // state intentionally guards only the row whose
                          // mutation is currently running, so a teacher can
                          // queue several drafts in quick succession.
                          <Button
                            size="sm"
                            onClick={() =>
                              publishMut.mutate(a.id, {
                                onSuccess: () =>
                                  toast.success(`"${a.title}" published.`),
                                onError: (err) => toast.error(humanError(err)),
                              })
                            }
                            disabled={
                              publishMut.isPending && publishMut.variables === a.id
                            }
                          >
                            {publishMut.isPending && publishMut.variables === a.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Send className="h-3.5 w-3.5" />
                            )}
                            Publish
                          </Button>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            )}
          </CardContent>
        </Card>
      )}
    </ThemedPage>
  );
}
