import { Loader2, TrendingDown } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { useClassWeakTopics } from "@/lib/queries";
import type { BucketStats, CognitiveBucket } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  classLevel: number | undefined;
  subjectId: number | undefined;
  /** Title shown in CardHeader. Defaults to "Weak topics in this class". */
  title?: string;
  /**
   * Tweak copy under the title. Defaults to a teacher-oriented blurb;
   * pass your own when embedding under a school-wide page.
   */
  description?: string;
  /** Number of topics to surface. Server caps at 30. */
  limit?: number;
}

const BUCKET_ORDER: CognitiveBucket[] = ["FACTUAL", "UNDERSTANDING", "APPLICATION"];

const BUCKET_LABEL: Record<CognitiveBucket, string> = {
  FACTUAL: "Factual",
  UNDERSTANDING: "Understanding",
  APPLICATION: "Application",
};

const BUCKET_HINT: Record<CognitiveBucket, string> = {
  FACTUAL: "Recall: definitions, facts, names",
  UNDERSTANDING: "Comprehension: explain, classify, compare",
  APPLICATION: "Transfer: solve, predict, apply to new situations",
};

export function WeakTopicsCard({
  classLevel,
  subjectId,
  title = "Weak topics in this class",
  description = "Lowest mastery first. Each topic is broken down by cognitive level so you can see whether students are struggling with recall, comprehension, or application.",
  limit = 8,
}: Props) {
  const q = useClassWeakTopics({
    class_level: classLevel,
    subject_id: subjectId,
    limit,
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-(--color-primary)" />
              {title}
            </CardTitle>
            <CardDescription className="mt-1">{description}</CardDescription>
          </div>
          {q.data?.students_total !== undefined && (
            <Badge variant="outline" className="shrink-0">
              {q.data.students_total} students
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {classLevel === undefined || subjectId === undefined ? (
          <Empty
            icon={<TrendingDown className="h-6 w-6" />}
            title="Pick a class and subject"
            description="Select a class and subject to see weak topics."
          />
        ) : q.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : !q.data || q.data.topics.length === 0 ? (
          <Empty
            icon={<TrendingDown className="h-6 w-6" />}
            title="No data yet"
            description="Once your students attempt assessments tagged to topics, the weakest topics will surface here with a per-cognitive-level breakdown."
          />
        ) : (
          <div className="space-y-3">
            {q.data.topics.map((t) => (
              <TopicRow key={t.topic_id} topic={t} />
            ))}
            <p className="pt-2 text-xs text-(--color-muted-foreground)">
              <strong>Factual</strong> {BUCKET_HINT.FACTUAL.toLowerCase()}.{" "}
              <strong>Understanding</strong> {BUCKET_HINT.UNDERSTANDING.toLowerCase()}.{" "}
              <strong>Application</strong> {BUCKET_HINT.APPLICATION.toLowerCase()}.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function TopicRow({
  topic,
}: {
  topic: {
    topic_id: number;
    topic_name: string;
    chapter_number: number;
    chapter_title: string;
    average_mastery: number | null;
    students_attempted: number;
    buckets: Record<CognitiveBucket, BucketStats>;
  };
}) {
  const overallPct = topic.average_mastery
    ? Math.round(topic.average_mastery * 100)
    : null;

  return (
    <div className="rounded-md border border-(--color-border) p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs text-(--color-muted-foreground)">
            <Badge variant="outline">Ch {topic.chapter_number}</Badge>
            <span className="truncate">{topic.chapter_title}</span>
          </div>
          <div className="mt-1 text-sm font-medium">{topic.topic_name}</div>
          <div className="mt-0.5 text-xs text-(--color-muted-foreground)">
            {topic.students_attempted} student
            {topic.students_attempted === 1 ? "" : "s"} attempted
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className={cn("text-2xl font-semibold", masteryColor(overallPct))}>
            {overallPct !== null ? `${overallPct}%` : "—"}
          </div>
          <div className="text-[11px] text-(--color-muted-foreground)">
            avg mastery
          </div>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        {BUCKET_ORDER.map((bucket) => {
          const stats = topic.buckets[bucket];
          return (
            <BucketChip
              key={bucket}
              label={BUCKET_LABEL[bucket]}
              hint={BUCKET_HINT[bucket]}
              stats={stats}
            />
          );
        })}
      </div>
    </div>
  );
}

function BucketChip({
  label,
  hint,
  stats,
}: {
  label: string;
  hint: string;
  stats: BucketStats;
}) {
  const pct = stats.average_mastery
    ? Math.round(stats.average_mastery * 100)
    : null;
  return (
    <div
      title={hint}
      className="flex flex-col rounded-md border border-(--color-border) bg-(--color-muted)/30 px-2 py-1.5"
    >
      <span className="text-[11px] font-medium uppercase tracking-wide text-(--color-muted-foreground)">
        {label}
      </span>
      <span className={cn("text-base font-semibold leading-tight", masteryColor(pct))}>
        {pct !== null ? `${pct}%` : "—"}
      </span>
      <span className="text-[10px] text-(--color-muted-foreground)">
        {stats.students_attempted}{" "}
        {stats.students_attempted === 1 ? "student" : "students"}
      </span>
    </div>
  );
}

function masteryColor(pct: number | null): string {
  if (pct === null) return "text-(--color-muted-foreground)";
  if (pct < 40) return "text-red-600 dark:text-red-400";
  if (pct < 60) return "text-amber-600 dark:text-amber-400";
  if (pct < 80) return "text-(--color-foreground)";
  return "text-emerald-600 dark:text-emerald-400";
}
