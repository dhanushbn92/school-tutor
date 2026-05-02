import { Link } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { useSectionLeaderboard } from "@/lib/queries";

/** Compact leaderboard widget — top 3 + bottom 3 with scores. */
export function SectionLeaderboardCard({
  sectionId,
  subjectId,
}: {
  sectionId: number;
  subjectId?: number;
}) {
  const q = useSectionLeaderboard({ section_id: sectionId, subject_id: subjectId });
  if (q.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading leaderboard…
      </div>
    );
  }
  const data = q.data;
  if (!data) {
    return <Empty title="Leaderboard unavailable" className="border-0 py-4" />;
  }
  const ranked = data.students.filter((s) => s.average_percentage !== null);
  if (ranked.length === 0) {
    return (
      <Empty
        title="No evaluated assessments yet"
        description="Once students take and submit tests in this subject, the leaderboard fills in."
        className="border-0 py-4"
      />
    );
  }
  const top = ranked.slice(0, 3);
  const bottom = ranked.slice().reverse().slice(0, 3);

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground) mb-2">
          Top performers
        </div>
        <ol className="space-y-1 text-sm">
          {top.map((s, i) => (
            <li
              key={s.student_id}
              className="flex items-center justify-between rounded-md border border-(--color-border) px-3 py-2"
            >
              <span className="flex items-center gap-2 min-w-0">
                <Badge variant={i === 0 ? "success" : "outline"}>{i + 1}</Badge>
                <Link
                  to={`/students/${s.student_id}`}
                  className="truncate text-(--color-primary) hover:underline"
                >
                  {s.full_name ?? `#${s.student_id}`}
                </Link>
              </span>
              <span className="font-medium">{s.average_percentage}%</span>
            </li>
          ))}
        </ol>
      </div>
      <div>
        <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground) mb-2">
          Needs support
        </div>
        <ol className="space-y-1 text-sm">
          {bottom.map((s) => (
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
              <span className="font-medium text-(--color-warning)">
                {s.average_percentage}%
              </span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
