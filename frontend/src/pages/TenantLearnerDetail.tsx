import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ClipboardList,
  GraduationCap,
  Loader2,
  Power,
  ShieldOff,
  TrendingUp,
  User as UserIcon,
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
import { StatCard } from "@/components/StatCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { humanError } from "@/lib/api";
import {
  usePlatformLearnerOverview,
  useTogglePlatformLearner,
} from "@/lib/queries";

export function TenantLearnerDetailPage() {
  const { userId: userIdParam } = useParams();
  const userId = userIdParam ? Number(userIdParam) : undefined;
  const overviewQ = usePlatformLearnerOverview(userId);
  const toggleMut = useTogglePlatformLearner();
  const [confirmingDisable, setConfirmingDisable] = useState(false);

  if (overviewQ.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading…
      </div>
    );
  }
  if (!overviewQ.data) {
    return (
      <Empty
        icon={<UserIcon className="h-6 w-6" />}
        title="Learner not found"
        description="It may have been removed, or the URL is incorrect."
        action={
          <Button asChild variant="outline">
            <Link to="/tenants">
              <ArrowLeft className="h-4 w-4" /> All tenants
            </Link>
          </Button>
        }
      />
    );
  }

  const learner = overviewQ.data;

  async function setActive(next: boolean) {
    if (userId === undefined) return;
    try {
      await toggleMut.mutateAsync({ userId, isActive: next });
      toast.success(
        next
          ? "Learner re-enabled — they can sign in again"
          : "Learner disabled — they're locked out on their next request",
      );
      setConfirmingDisable(false);
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  const avgPctText =
    learner.average_percentage !== null
      ? `${learner.average_percentage.toFixed(1)}%`
      : "—";
  const avgMasteryText =
    learner.average_mastery !== null
      ? `${(learner.average_mastery * 100).toFixed(0)}%`
      : "—";

  return (
    <ThemedPage>
      <PageHeader
        title={learner.full_name}
        description={
          <>
            <span className="text-(--color-muted-foreground)">{learner.email}</span>
            {!learner.is_active && (
              <Badge variant="destructive" className="ml-2 gap-1">
                <ShieldOff className="h-3 w-3" /> Disabled
              </Badge>
            )}
          </>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button asChild variant="outline">
              <Link to="/tenants">
                <ArrowLeft className="h-4 w-4" /> All tenants
              </Link>
            </Button>
            {learner.is_active ? (
              <Button
                variant="destructive"
                onClick={() => setConfirmingDisable(true)}
                disabled={toggleMut.isPending}
              >
                {toggleMut.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ShieldOff className="h-4 w-4" />
                )}
                Disable user
              </Button>
            ) : (
              <Button
                onClick={() => setActive(true)}
                disabled={toggleMut.isPending}
              >
                {toggleMut.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Power className="h-4 w-4" />
                )}
                Re-enable user
              </Button>
            )}
          </div>
        }
      />

      {confirmingDisable && learner.is_active && (
        <Card className="mb-4 border-(--color-destructive)/40 bg-[color-mix(in_oklab,var(--color-destructive)_8%,transparent)]">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
            <div>
              <div className="flex items-center gap-2 text-sm font-medium">
                <ShieldOff className="h-4 w-4" />
                Disable {learner.full_name}?
              </div>
              <div className="mt-1 text-xs text-(--color-muted-foreground)">
                This learner will lose access on their next request. Their
                quizzes and progress are preserved — re-enable any time.
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setConfirmingDisable(false)}
                disabled={toggleMut.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setActive(false)}
                disabled={toggleMut.isPending}
              >
                {toggleMut.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : null}
                Yes, disable
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stat row */}
      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <StatCard
          label="Status"
          value={learner.is_active ? "Active" : "Disabled"}
          intent={learner.is_active ? "success" : "danger"}
          icon={<Power className="h-5 w-5" />}
        />
        <StatCard
          label="Class"
          value={learner.class_display_name ?? "—"}
          sub={learner.class_level ? `Level ${learner.class_level}` : undefined}
          icon={<GraduationCap className="h-5 w-5" />}
        />
        <StatCard
          label="Quizzes evaluated"
          value={learner.submissions_count}
          sub={
            learner.last_activity_at
              ? `Last: ${formatDate(learner.last_activity_at)}`
              : "No activity yet"
          }
          icon={<ClipboardList className="h-5 w-5" />}
        />
        <StatCard
          label="Average score"
          value={avgPctText}
          sub={`Mastery: ${avgMasteryText}`}
          icon={<TrendingUp className="h-5 w-5" />}
          intent="success"
        />
      </div>

      <div className="mb-4 grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <Row label="User ID" value={`#${learner.user_id}`} />
            <Row label="Email" value={learner.email} />
            <Row label="Signed up" value={formatDate(learner.signup_date)} />
            <Row
              label="Class enrolled"
              value={
                learner.class_display_name ??
                (learner.class_level ? `Class ${learner.class_level}` : "—")
              }
            />
            <Row
              label="Personal school ID"
              value={learner.school_id ? `#${learner.school_id}` : "—"}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Activity summary</CardTitle>
            <CardDescription>
              Aggregated over evaluated submissions only.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <Row label="Quizzes evaluated" value={String(learner.submissions_count)} />
            <Row label="Average score" value={avgPctText} />
            <Row label="Average mastery" value={avgMasteryText} />
            <Row
              label="Last activity"
              value={
                learner.last_activity_at
                  ? formatDate(learner.last_activity_at)
                  : "—"
              }
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent submissions</CardTitle>
          <CardDescription>
            Latest 5 evaluated quizzes — same data the learner sees on their dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {learner.recent_submissions.length === 0 ? (
            <Empty
              title="No submissions yet"
              description="This learner hasn't completed any quizzes."
              className="border-0 py-6"
            />
          ) : (
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
                <tr className="border-b border-(--color-border)">
                  <th className="py-2 text-left font-medium">Quiz</th>
                  <th className="py-2 text-left font-medium">Chapter</th>
                  <th className="py-2 text-right font-medium">Score</th>
                  <th className="py-2 text-right font-medium">%</th>
                  <th className="py-2 text-right font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {learner.recent_submissions.map((s) => (
                  <tr key={s.submission_id} className="border-b border-(--color-border)/60">
                    <td className="py-2 font-medium">{s.assessment_title}</td>
                    <td className="py-2 text-(--color-muted-foreground)">
                      {s.chapter_title ?? "—"}
                    </td>
                    <td className="py-2 text-right">
                      {s.score !== null && s.max_marks !== null
                        ? `${s.score} / ${s.max_marks}`
                        : "—"}
                    </td>
                    <td className="py-2 text-right">
                      {s.percentage !== null ? `${s.percentage.toFixed(0)}%` : "—"}
                    </td>
                    <td className="py-2 text-right text-(--color-muted-foreground)">
                      {s.evaluated_at ? formatDate(s.evaluated_at) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </ThemedPage>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 py-1">
      <span className="text-(--color-muted-foreground)">{label}</span>
      <span className="text-right break-all">{value}</span>
    </div>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}
