import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { BloomLevel, CognitiveBucket, MasteryBucketStats } from "@/lib/types";
import { BLOOM_LABEL, BLOOM_TO_BUCKET, BUCKET_LABEL } from "@/lib/types";

export type HeatmapView = "combined" | CognitiveBucket | BloomLevel;

interface OutcomeCell {
  code: string;
  description: string;
  mastery: number | null;
  attempts?: number;
  students_attempted?: number;
  buckets?: Record<CognitiveBucket, MasteryBucketStats | null>;
}

interface ChapterRow {
  chapter_id: number;
  chapter_number: number;
  chapter_title: string;
  outcomes: OutcomeCell[];
}

export function MasteryHeatmap({
  title,
  description,
  chapters,
  emptyLabel = "Not attempted yet",
  view = "combined",
  headerSlot,
}: {
  title: string;
  description?: string;
  chapters: ChapterRow[];
  emptyLabel?: string;
  view?: HeatmapView;
  headerSlot?: React.ReactNode;
}) {
  const maxOutcomes = Math.max(1, ...chapters.map((c) => c.outcomes.length));
  const gridCols = `minmax(200px,240px) repeat(${maxOutcomes},minmax(72px,1fr))`;
  const viewLabel = labelForView(view);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>{title}</CardTitle>
            {description && <CardDescription>{description}</CardDescription>}
            {view !== "combined" && (
              <CardDescription>
                Showing <span className="font-medium">{viewLabel}</span> mastery only.
              </CardDescription>
            )}
          </div>
          {headerSlot}
        </div>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <div className="min-w-[640px]">
          <div
            className="mb-2 grid items-end gap-1 text-[11px] uppercase tracking-wide text-(--color-muted-foreground)"
            style={{ gridTemplateColumns: gridCols }}
          >
            <div>Chapter</div>
            <div className="col-span-full text-(--color-muted-foreground)/0" />
          </div>
          {chapters.map((chapter) => (
            <div
              key={chapter.chapter_id}
              className="mb-1 grid items-center gap-1"
              style={{ gridTemplateColumns: gridCols }}
            >
              <div className="truncate text-sm">
                <span className="text-(--color-muted-foreground) text-xs">
                  Ch {chapter.chapter_number}
                </span>{" "}
                <span className="text-(--color-foreground)">{chapter.chapter_title}</span>
              </div>
              {chapter.outcomes.map((outcome) => (
                <Cell
                  key={outcome.code}
                  outcome={outcome}
                  emptyLabel={emptyLabel}
                  view={view}
                />
              ))}
              {Array.from({ length: maxOutcomes - chapter.outcomes.length }, (_, i) => (
                <div key={`empty-${i}`} className="h-12 rounded-md bg-(--color-muted)/40" />
              ))}
            </div>
          ))}
          <Legend />
        </div>
      </CardContent>
    </Card>
  );
}

function Cell({
  outcome,
  emptyLabel,
  view,
}: {
  outcome: OutcomeCell;
  emptyLabel: string;
  view: HeatmapView;
}) {
  const resolved = resolveCellMastery(outcome, view);
  const m = resolved.mastery;
  const codeSuffix = extractCodeSuffix(outcome.code);
  const viewSuffix = view === "combined" ? "" : ` (${labelForView(view)})`;
  const tooltipLines = [
    outcome.code,
    outcome.description,
    m === null
      ? `${emptyLabel}${viewSuffix}`
      : `Mastery${viewSuffix}: ${(m * 100).toFixed(0)}%`,
    resolved.attempts !== undefined ? `Attempts${viewSuffix}: ${resolved.attempts}` : null,
    outcome.students_attempted !== undefined
      ? `Students attempted: ${outcome.students_attempted}`
      : null,
  ].filter(Boolean);
  const isEmpty = m === null;
  return (
    <div
      className={cn(
        "flex h-12 flex-col items-center justify-center rounded-md border border-(--color-border) px-1 text-center font-medium leading-none transition-transform hover:scale-[1.03]",
        isEmpty && "bg-(--color-muted)/60 text-(--color-muted-foreground)",
      )}
      style={isEmpty ? undefined : { backgroundColor: colourFor(m), color: textFor(m) }}
      title={tooltipLines.join("\n")}
    >
      <span
        className={cn(
          "block w-full truncate text-[10px] font-semibold uppercase tracking-wide",
          isEmpty ? "opacity-70" : "opacity-90",
        )}
      >
        {codeSuffix}
      </span>
      <span className="mt-1 text-[12px]">
        {isEmpty ? "—" : `${Math.round(m * 100)}%`}
      </span>
    </div>
  );
}

function labelForView(view: HeatmapView): string {
  if (view === "combined") return "Combined";
  if (view === "FACTUAL" || view === "UNDERSTANDING" || view === "APPLICATION") {
    return BUCKET_LABEL[view];
  }
  return BLOOM_LABEL[view];
}

function resolveCellMastery(
  outcome: OutcomeCell,
  view: HeatmapView,
): { mastery: number | null; attempts: number | undefined } {
  if (view === "combined") {
    return { mastery: outcome.mastery, attempts: outcome.attempts };
  }
  if (!outcome.buckets) {
    return { mastery: null, attempts: undefined };
  }
  const bucket: CognitiveBucket =
    view === "FACTUAL" || view === "UNDERSTANDING" || view === "APPLICATION"
      ? view
      : BLOOM_TO_BUCKET[view];
  const stats = outcome.buckets[bucket];
  if (stats === undefined || stats === null) {
    return { mastery: null, attempts: undefined };
  }
  return { mastery: stats.mastery, attempts: stats.attempts };
}

/** "6-SCI-WOS-01" → "WOS-01". Falls back to the full code if the format is unexpected. */
function extractCodeSuffix(code: string): string {
  const parts = code.split("-");
  if (parts.length >= 4) return parts.slice(-2).join("-");
  return code;
}

function Legend() {
  const stops = [0, 0.25, 0.5, 0.75, 1.0];
  return (
    <div className="mt-4 flex items-center gap-3 text-[11px] text-(--color-muted-foreground)">
      <span>Low</span>
      <div className="flex h-3 flex-1 max-w-60 overflow-hidden rounded-full">
        {stops.slice(0, -1).map((from, idx) => (
          <div
            key={idx}
            className="flex-1"
            style={{
              background: `linear-gradient(to right, ${colourFor(from)}, ${colourFor(stops[idx + 1])})`,
            }}
          />
        ))}
      </div>
      <span>High</span>
    </div>
  );
}

/** Traffic-light gradient: red → amber → green. */
function colourFor(mastery: number): string {
  const clamped = Math.max(0, Math.min(1, mastery));
  const hue = Math.round(clamped * 140);
  const saturation = 72;
  const lightness = 56 - clamped * 6;
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

function textFor(mastery: number): string {
  return mastery < 0.45 ? "#ffffff" : "#0b0b0b";
}
