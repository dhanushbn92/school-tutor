import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle2, Loader2, Lock, Send, Sparkles } from "lucide-react";
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
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { humanError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  useAssessment,
  useAssessmentSubmissions,
  useCloseAssessment,
  useMySubmissions,
  usePublishAssessment,
} from "@/lib/queries";
import { formatDateTime, formatMarks } from "@/lib/utils";

export function AssessmentDetailPage() {
  const { user } = useAuth();
  const { assessmentId } = useParams();
  const id = assessmentId ? Number(assessmentId) : undefined;
  const assessmentQ = useAssessment(id);
  const isLearner =
    user?.role === "student" || user?.role === "individual_learner";
  const isTeacherOrAdmin =
    user?.role === "teacher" || user?.role === "school_admin";

  // Teacher / admin view → list every student's submission.
  // Student / individual_learner → list of just their own submission(s).
  const teacherSubsQ = useAssessmentSubmissions(isTeacherOrAdmin ? id : undefined);
  const mySubsQ = useMySubmissions();
  const mySubmission = (mySubsQ.data ?? []).find((s) => s.assessment_id === id);

  const publishMut = usePublishAssessment();
  const closeMut = useCloseAssessment();

  if (assessmentQ.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading...
      </div>
    );
  }
  if (!assessmentQ.data) {
    return (
      <Empty
        title="Assessment not found"
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
  const orderedQuestions = [...a.questions].sort((x, y) => x.order - y.order);

  const handlePublish = () => {
    publishMut.mutate(a.id, {
      onSuccess: () =>
        toast.success(`"${a.title}" is now published — students in section #${a.section_id} can see it.`),
      onError: (err) => toast.error(humanError(err)),
    });
  };

  const handleClose = () => {
    closeMut.mutate(a.id, {
      onSuccess: () =>
        toast.success(`"${a.title}" is closed — no further submissions.`),
      onError: (err) => toast.error(humanError(err)),
    });
  };

  return (
    <ThemedPage>
      <PageHeader
        title={a.title}
        description={
          <>
            <Badge variant="outline" className="mr-2">
              {a.type}
            </Badge>
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
            <span className="ml-3 text-sm text-(--color-muted-foreground)">
              {a.total_marks} marks &middot; {a.questions.length} questions
              {!isLearner && <> &middot; Section #{a.section_id}</>}
            </span>
          </>
        }
        actions={
          <div className="flex items-center gap-2">
            {isTeacherOrAdmin && a.status === "DRAFT" && (
              <Button
                size="sm"
                onClick={handlePublish}
                disabled={publishMut.isPending}
              >
                {publishMut.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Publish
              </Button>
            )}
            {isTeacherOrAdmin && a.status === "PUBLISHED" && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleClose}
                disabled={closeMut.isPending}
              >
                {closeMut.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Lock className="h-4 w-4" />
                )}
                Close
              </Button>
            )}
            <Button asChild variant="outline">
              <Link to="/assessments">
                <ArrowLeft className="h-4 w-4" /> All assessments
              </Link>
            </Button>
          </div>
        }
      />

      {a.instructions && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Instructions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed">{a.instructions}</p>
          </CardContent>
        </Card>
      )}

      {/*
       * Teacher / admin status panel.
       *
       * Quizzes from /assessments/from-bank land in DRAFT and stay invisible
       * to students until published — easy to forget. This card is the loud
       * primary affordance: it tells the teacher exactly which side of the
       * publish line they are on, what the next move is, and what publishing
       * does. The header button is a secondary shortcut for return visits.
       *
       * State machine surfaced here matches the backend (assessments.py):
       *   DRAFT     → "Publish" call-to-action (primary)
       *   PUBLISHED → "Close" (outline, less prominent)
       *   CLOSED    → terminal, just a confirmation message.
       */}
      {isTeacherOrAdmin && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Status &amp; visibility</CardTitle>
            <CardDescription>
              {a.status === "DRAFT" &&
                "Only you can see this quiz right now. Publish to share it with the section."}
              {a.status === "PUBLISHED" &&
                `Live since ${formatDateTime(a.published_at)}. Close it once everyone has had a chance to submit.`}
              {a.status === "CLOSED" &&
                "Closed — no new submissions accepted. Existing submissions stay available for grading and review."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-3">
              {a.status === "DRAFT" && (
                <Button
                  size="lg"
                  onClick={handlePublish}
                  disabled={publishMut.isPending}
                >
                  {publishMut.isPending ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Send className="h-5 w-5" />
                  )}
                  Publish to section
                </Button>
              )}
              {a.status === "PUBLISHED" && (
                <Button
                  size="lg"
                  variant="outline"
                  onClick={handleClose}
                  disabled={closeMut.isPending}
                >
                  {closeMut.isPending ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Lock className="h-5 w-5" />
                  )}
                  Close quiz
                </Button>
              )}
              {a.status === "CLOSED" && (
                <Badge variant="outline" className="gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Closed
                </Badge>
              )}
              {a.status !== "DRAFT" && a.published_at && (
                <span className="text-xs text-(--color-muted-foreground)">
                  Published {formatDateTime(a.published_at)}
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Learner-only: their own status / score and the right CTA. */}
      {isLearner && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Your status</CardTitle>
            <CardDescription>
              {mySubmission
                ? "You have already taken this quiz. Your score and breakdown are below."
                : "You haven't taken this quiz yet. Tap Take quiz to begin."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {mySubmission ? (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <Badge
                    variant={
                      mySubmission.status === "EVALUATED" ? "success" : "warning"
                    }
                  >
                    {mySubmission.status}
                  </Badge>
                  <span className="ml-3 text-2xl font-semibold tabular-nums">
                    {formatMarks(mySubmission.total_awarded, mySubmission.max_marks)}
                  </span>
                  <span className="ml-3 text-xs text-(--color-muted-foreground)">
                    Submitted {formatDateTime(mySubmission.submitted_at)}
                  </span>
                </div>
                <Button asChild>
                  <Link to={`/assessments/${a.id}/take`}>
                    View results
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            ) : a.status === "PUBLISHED" ? (
              <Button asChild size="lg">
                <Link to={`/assessments/${a.id}/take`}>
                  <Sparkles className="h-5 w-5" />
                  Take quiz
                </Link>
              </Button>
            ) : (
              <span className="text-sm text-(--color-muted-foreground)">
                This quiz isn't open right now.
              </span>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Questions</CardTitle>
            <CardDescription>
              {a.questions.length} questions, in order. Total {a.total_marks} marks.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="space-y-2 text-sm">
              {orderedQuestions.map((q, i) => (
                <li
                  key={q.id}
                  className="rounded-md border border-(--color-border) p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="min-w-0">
                      <span className="text-(--color-muted-foreground) mr-2">
                        Q{i + 1}.
                      </span>
                      {q.question_text ?? `Question #${q.question_id}`}
                    </span>
                    <span className="flex shrink-0 items-center gap-2">
                      {q.question_type && (
                        <Badge variant="outline" className="text-[10px]">
                          {q.question_type}
                        </Badge>
                      )}
                      <Badge variant="secondary">{q.marks} mk</Badge>
                    </span>
                  </div>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>

        {/* Teacher / admin: full submissions table. */}
        {isTeacherOrAdmin && (
          <Card>
            <CardHeader>
              <CardTitle>Submissions</CardTitle>
              <CardDescription>Student submissions for this assessment.</CardDescription>
            </CardHeader>
            <CardContent>
              {teacherSubsQ.isLoading ? (
                <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading...
                </div>
              ) : !teacherSubsQ.data || teacherSubsQ.data.length === 0 ? (
                <Empty
                  title="No submissions yet"
                  description="Students will appear here as they submit."
                />
              ) : (
                <table className="w-full text-sm">
                  <thead className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
                    <tr className="border-b border-(--color-border)">
                      <th className="py-2 text-left font-medium">Student</th>
                      <th className="py-2 text-left font-medium">Status</th>
                      <th className="py-2 text-right font-medium">Score</th>
                      <th className="py-2 text-right font-medium">Submitted</th>
                    </tr>
                  </thead>
                  <tbody>
                    {teacherSubsQ.data.map((s) => (
                      <tr key={s.id} className="border-b border-(--color-border)/60">
                        <td className="py-2">
                          <Link
                            to={`/students/${s.student_id}`}
                            className="underline-offset-4 hover:underline"
                          >
                            #{s.student_id}
                          </Link>
                        </td>
                        <td className="py-2">
                          <Badge
                            variant={
                              s.status === "EVALUATED"
                                ? "success"
                                : s.status === "SUBMITTED"
                                  ? "warning"
                                  : "outline"
                            }
                          >
                            {s.status}
                          </Badge>
                        </td>
                        <td className="py-2 text-right tabular-nums">
                          {formatMarks(s.total_awarded, s.max_marks)}
                        </td>
                        <td className="py-2 text-right text-xs text-(--color-muted-foreground)">
                          {formatDateTime(s.submitted_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        )}

        {/* Learner-only: a hint card on the right side instead of submissions. */}
        {isLearner && (
          <Card>
            <CardHeader>
              <CardTitle>How this is graded</CardTitle>
              <CardDescription>
                A quick rundown so you know what to expect.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm leading-relaxed">
              <p>
                MCQ, true/false, and fill-in-the-blank questions are graded
                instantly when you submit.
              </p>
              <p>
                Short and long-answer questions are auto-graded by checking your
                answer for the key concepts. The post-quiz page shows you which
                ideas the grader matched and which it expected.
              </p>
              <p>
                Your mastery map updates as soon as your submission is
                evaluated.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </ThemedPage>
  );
}
