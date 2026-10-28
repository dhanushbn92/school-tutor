import { Link } from "react-router-dom";
import { PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  SUBJECT_ICONS,
  subjectTheme,
  subjectVar,
  subjectVarSoft,
} from "@/lib/subjectTheme";
import { cn } from "@/lib/utils";

const RING_R = 26;
const RING_C = 2 * Math.PI * RING_R;

function ProgressRing({ percent, color }: { percent: number; color: string }) {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 64 64"
      role="img"
      aria-label={`${percent} percent mastered`}
      className="shrink-0"
    >
      <circle cx="32" cy="32" r={RING_R} fill="none" stroke="white" strokeWidth="7" />
      {percent > 0 && (
        <circle
          cx="32"
          cy="32"
          r={RING_R}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={`${(percent / 100) * RING_C} ${RING_C}`}
          transform="rotate(-90 32 32)"
        />
      )}
      <text
        x="32"
        y="37"
        textAnchor="middle"
        className="fill-(--color-foreground) font-display text-[14px] font-extrabold"
      >
        {percent}%
      </text>
    </svg>
  );
}

/**
 * One soft, subject-coloured card. Learners see a progress ring (share of the
 * subject's outcomes mastered) and where they are up to; staff, who have no
 * progress, see the board and class instead. The button opens the place to
 * carry on.
 *
 * `compact` is the home-page card; `large` is the Learn page card, which also
 * shows the subject icon.
 */
export function SubjectCard({
  name,
  percent,
  where,
  chapterCount,
  videos,
  board,
  to,
  cta,
  highlight = false,
  size = "compact",
}: {
  name: string;
  /** 0..100, or null when there is no progress to show (staff). */
  percent: number | null;
  where: string;
  chapterCount?: number;
  videos: number;
  board?: string | null;
  to: string;
  cta: string;
  /** Draw the button in the primary colour (a subject in progress). */
  highlight?: boolean;
  size?: "compact" | "large";
}) {
  const theme = subjectTheme(name);
  const Icon = SUBJECT_ICONS[theme];
  const large = size === "large";

  return (
    <div
      className={cn(
        "flex min-w-0 flex-col gap-4 rounded-2xl",
        large ? "p-6" : "p-5",
      )}
      style={{ background: subjectVarSoft(theme) }}
    >
      {large ? (
        <div className="flex items-start justify-between gap-3">
          <span
            aria-hidden
            className="grid h-12 w-12 place-items-center rounded-2xl bg-white"
            style={{ color: subjectVar(theme) }}
          >
            <Icon className="h-6 w-6" />
          </span>
          {percent !== null ? (
            <ProgressRing percent={percent} color={subjectVar(theme)} />
          ) : (
            board && (
              <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-(--color-foreground)">
                {board}
              </span>
            )
          )}
        </div>
      ) : null}

      <div>
        <h3
          className={cn(
            "font-display font-bold leading-tight [overflow-wrap:anywhere]",
            large ? "text-2xl" : "text-lg",
          )}
        >
          {name}
        </h3>
        {large && (
          <p className="mt-1 text-sm text-(--color-muted-foreground)">{where}</p>
        )}
      </div>

      {!large && percent !== null && (
        <div className="flex items-center gap-3.5">
          <ProgressRing percent={percent} color={subjectVar(theme)} />
          <p className="min-w-0 text-sm text-(--color-muted-foreground)">{where}</p>
        </div>
      )}

      {(chapterCount !== undefined || videos > 0) && (
        <div className="flex flex-wrap gap-2">
          {large && chapterCount !== undefined && (
            <span className="inline-flex items-center rounded-full bg-white px-3 py-1 text-xs font-semibold text-(--color-foreground)">
              {chapterCount} {chapterCount === 1 ? "chapter" : "chapters"}
            </span>
          )}
          {videos > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-xs font-semibold text-(--color-foreground)">
              <PlayCircle className="h-3.5 w-3.5" aria-hidden />
              {videos} {videos === 1 ? "video" : "videos"}
            </span>
          )}
        </div>
      )}

      <Button
        asChild
        variant={highlight ? "default" : "outline"}
        size="lg"
        className={cn(
          "mt-auto w-full rounded-xl",
          !highlight && "border-transparent bg-white hover:bg-white/70",
        )}
      >
        <Link to={to}>{cta}</Link>
      </Button>
    </div>
  );
}
