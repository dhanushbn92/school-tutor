import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpenCheck,
  Compass,
  HeartHandshake,
  Sprout,
  Star,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BRAND_ARROW_COLORS } from "@/lib/brand";
import type { StudentMasteryGrid } from "@/lib/types";

/**
 * Stage 4 of the child-centric roadmap — "Story-shaped progress".
 *
 * Replaces the four stat-card row that used to read like a school
 * report ("Average mastery 62%", "Outcomes 12/18"). Numbers are still
 * here, but they're framed as a journey: chapters mastered, chapters
 * in practice, chapters yet to explore. A learner's mastery isn't a
 * percentage at the bottom of a report; it's a map with three coloured
 * regions, and the dashboard says "you're partway through".
 *
 * Below the three narrative tiles sit two complementary tiles:
 *   - Strongest concept right now (positive anchor)
 *   - Best place to practise next (forward-looking nudge)
 *
 * Underneath, a compact topic-tree visual: one row per chapter, a row
 * of dots per outcome, coloured by mastery state. Hovering a dot shows
 * the outcome code + current %. This is the "where am I in the
 * syllabus?" overview at a glance — no scroll, no clicks.
 *
 * Backend mastery query stays as-is — every computation is derived
 * frontend-side. That keeps the per-stage scope tight and avoids
 * coupling to a `chapter_state` API field we'd then have to maintain.
 */

// Per-outcome mastery thresholds. Tuned for the "be encouraging" tone
// the rest of Stage 1.5 / Stage 3 set up: 0.75 is mastery, anything
// below 0.75 with attempts is "still learning", no attempts is "fresh
// territory". Don't lower mastery — kids should feel proud, not be
// handed mastery for a 50% score.
const MASTERY_FLOOR = 0.75;

// Chapter is "mastered" if at least this fraction of its outcomes are
// individually mastered. 0.8 means 4-of-5 leaves, 8-of-10 leaves —
// covers the case where one outcome is genuinely tough without
// blocking the celebratory state.
const CHAPTER_MASTERED_RATIO = 0.8;

type ChapterStatus = "MASTERED" | "IN_PRACTICE" | "TO_EXPLORE";

interface ChapterRollup {
  chapter_id: number;
  chapter_number: number;
  chapter_title: string;
  /** Optional per-chapter subject context. Populated when the
   *  mastery query returns the whole syllabus (no subject filter).
   *  When present, the syllabus map labels each row with the
   *  subject so a multi-subject grid stays readable. */
  subject_id: number | null;
  subject_name: string | null;
  status: ChapterStatus;
  outcomes_total: number;
  outcomes_attempted: number;
  outcomes_mastered: number;
  average_mastery: number | null;
  outcomes: OutcomeRollup[];
}

interface OutcomeRollup {
  code: string;
  description: string;
  /** 0..1 if attempts > 0, else null. */
  mastery: number | null;
  attempts: number;
  state: "MASTERED" | "PRACTISING" | "UNTOUCHED";
}

interface OutcomePick {
  chapter_id: number;
  chapter_number: number;
  chapter_title: string;
  subject_name: string | null;
  code: string;
  description: string;
  mastery: number | null;
  attempts: number;
}


export function LearnerProgressNarrative({
  data,
  subjectName,
  showPracticeLinks,
}: {
  data: StudentMasteryGrid | undefined;
  subjectName: string | undefined;
  /** Self-learners get a "Practice this" CTA on the best-place tile;
   *  school students don't (they take teacher-assigned quizzes). */
  showPracticeLinks: boolean;
}) {
  const rollups = useMemo(() => rollupChapters(data), [data]);
  const counts = countByStatus(rollups);
  const strongest = pickStrongest(rollups);
  const bestPlace = pickBestPlace(rollups);

  // Empty state — no mastery data yet (a brand-new learner). Fall back
  // to a single encouraging tile rather than rendering empty boxes.
  if (!data || rollups.length === 0) {
    return (
      <Card className="mb-6">
        <CardContent className="flex items-center gap-3 py-5 text-sm text-(--color-muted-foreground)">
          <Sprout className="h-5 w-5 text-(--color-success)" />
          <div>
            <div className="font-medium text-(--color-foreground)">
              Your story starts here.
            </div>
            Take your first quiz and chapters will fill in as you go.
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="mb-6 space-y-4">
      {/* Three narrative tiles — chapters as a journey, not a number. */}
      <div className="grid gap-4 md:grid-cols-3">
        <NarrativeTile
          icon={<Star className="h-5 w-5" />}
          color={BRAND_ARROW_COLORS.green}
          count={counts.MASTERED}
          label={
            counts.MASTERED === 1 ? "chapter mastered" : "chapters mastered"
          }
          blurb={
            counts.MASTERED === 0
              ? "Your first mastered chapter is just a few quizzes away."
              : counts.MASTERED === 1
                ? "One chapter you've truly nailed."
                : `${counts.MASTERED} chapters where you're consistently strong.`
          }
        />
        <NarrativeTile
          icon={<HeartHandshake className="h-5 w-5" />}
          color={BRAND_ARROW_COLORS.orange}
          count={counts.IN_PRACTICE}
          label={
            counts.IN_PRACTICE === 1
              ? "chapter in practice"
              : "chapters in practice"
          }
          blurb={
            counts.IN_PRACTICE === 0
              ? "Nothing in progress right now."
              : "Keep practising — these are the ones to push through."
          }
        />
        <NarrativeTile
          icon={<Compass className="h-5 w-5" />}
          color={BRAND_ARROW_COLORS.navy}
          count={counts.TO_EXPLORE}
          label={
            counts.TO_EXPLORE === 1
              ? "chapter to explore"
              : "chapters to explore"
          }
          blurb={
            counts.TO_EXPLORE === 0
              ? "You've touched every chapter — well done."
              : "Fresh territory waiting for your first attempt."
          }
        />
      </div>

      {/* Strongest concept + best place to practise next. Same data as
          the existing strengths/weaknesses lists below, but framed as
          a positive headline pair so the learner sees their win first
          and their next step second. */}
      <div className="grid gap-4 md:grid-cols-2">
        <HighlightTile
          icon={<Star className="h-4 w-4 text-(--color-success)" />}
          title="Strongest concept right now"
          subjectName={subjectName}
          pick={strongest}
          mode="strength"
          showPracticeLink={false}
        />
        <HighlightTile
          icon={<BookOpenCheck className="h-4 w-4 text-(--color-warning)" />}
          title="Best place to practise next"
          subjectName={subjectName}
          pick={bestPlace}
          mode="next"
          showPracticeLink={showPracticeLinks}
        />
      </div>

      {/* Topic-tree visual — one row per chapter, one dot per outcome.
          Filled-in leaves show what's been mastered. */}
      <TopicTree rollups={rollups} />
    </div>
  );
}

/* ---------------- Narrative tile (the headline 3-card row) -------- */

function NarrativeTile({
  icon,
  color,
  count,
  label,
  blurb,
}: {
  icon: React.ReactNode;
  color: string;
  count: number;
  label: string;
  blurb: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-start gap-3 py-4">
        <span
          className="mt-0.5 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border"
          style={{
            backgroundColor: `${color}1a`,
            borderColor: color,
            color,
          }}
        >
          {icon}
        </span>
        <div className="min-w-0">
          <div className="flex items-baseline gap-1.5">
            <span className="font-display text-3xl font-semibold tabular-nums leading-none">
              {count}
            </span>
            <span className="text-xs text-(--color-muted-foreground)">
              {label}
            </span>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-(--color-muted-foreground)">
            {blurb}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

/* -------- Strongest concept + best-place-to-practise tiles -------- */

function HighlightTile({
  icon,
  title,
  subjectName,
  pick,
  mode,
  showPracticeLink,
}: {
  icon: React.ReactNode;
  title: string;
  subjectName: string | undefined;
  pick: OutcomePick | null;
  mode: "strength" | "next";
  showPracticeLink: boolean;
}) {
  if (!pick) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            {icon}
            <CardTitle className="text-base">{title}</CardTitle>
          </div>
          <CardDescription>
            {mode === "strength"
              ? "Take a few quizzes — your first strong concept will show up here."
              : "Once you've practised a bit, we'll point you at the most useful next topic."}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }
  const pct = pick.mastery !== null ? Math.round(pick.mastery * 100) : null;
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          {icon}
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        <CardDescription>
          {/* Stage 4 fix — prefer the chapter's own subject_name
              (from the whole-syllabus query) over the dashboard's
              fallback "Science" so a Mathematics pick reads
              "Mathematics · Ch 3. Algebra", not "Science · Ch 3.
              Algebra". */}
          {(pick.subject_name ?? subjectName) ? `${pick.subject_name ?? subjectName} · ` : ""}
          Ch {pick.chapter_number}. {pick.chapter_title}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="text-sm font-medium leading-snug">{pick.description}</div>
        <div className="flex items-center gap-2 text-xs text-(--color-muted-foreground)">
          {pct !== null && (
            <Badge variant={mode === "strength" ? "success" : "warning"}>
              {pct}%
            </Badge>
          )}
          <span>
            {pick.attempts === 0
              ? "Not tried yet"
              : `${pick.attempts} attempt${pick.attempts === 1 ? "" : "s"}`}
          </span>
        </div>
        {showPracticeLink && mode === "next" && (
          <div className="pt-1">
            <Button asChild size="sm" variant="outline">
              <Link to={`/quick-quiz?chapter=${pick.chapter_id}`}>
                Practise this
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ---------------- Topic-tree visual ------------------------------- */

function TopicTree({ rollups }: { rollups: ChapterRollup[] }) {
  // Group chapters by subject so a whole-syllabus view stays
  // readable. A learner with one subject sees a single group; a
  // learner with multiple subjects sees subject sub-headers
  // (Mathematics, Science, English, ...). Insertion order from the
  // backend ("ORDER BY subject name, chapter number") is preserved.
  const groups: { subject_name: string; chapters: ChapterRollup[] }[] = [];
  for (const ch of rollups) {
    const key = ch.subject_name ?? "Your syllabus";
    let group = groups[groups.length - 1];
    if (!group || group.subject_name !== key) {
      group = { subject_name: key, chapters: [] };
      groups.push(group);
    }
    group.chapters.push(ch);
  }
  // When everything's one subject we drop the sub-header so the
  // single-subject case looks unchanged from before this fix.
  const showSubjectHeaders =
    groups.length > 1 || (groups[0]?.subject_name ?? null) !== "Your syllabus";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Your syllabus map</CardTitle>
        <CardDescription>
          One row per chapter, one dot per learning outcome. Green = mastered,
          amber = practising, faint = not tried yet. Hover a dot for details.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-5">
          {groups.map((group) => (
            <div key={group.subject_name}>
              {showSubjectHeaders && groups.length > 1 && (
                <div className="mb-2 flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-(--color-muted-foreground)">
                    {group.subject_name}
                  </span>
                  <span className="h-px flex-1 bg-(--color-border)" />
                  <span className="text-[10px] text-(--color-muted-foreground)">
                    {group.chapters.length} chapter
                    {group.chapters.length === 1 ? "" : "s"}
                  </span>
                </div>
              )}
              <ul className="space-y-2">
                {group.chapters.map((ch) => (
                  <li
                    key={ch.chapter_id}
                    className="flex items-start gap-3 rounded-md border border-(--color-border) px-3 py-2"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium">
                          Ch {ch.chapter_number}. {ch.chapter_title}
                        </span>
                        <ChapterStatusBadge status={ch.status} />
                      </div>
                      <div className="mt-1 text-[11px] text-(--color-muted-foreground)">
                        {ch.outcomes_mastered}/{ch.outcomes_total} outcomes mastered
                        {ch.outcomes_attempted > 0 &&
                        ch.outcomes_attempted < ch.outcomes_total
                          ? ` · ${ch.outcomes_attempted - ch.outcomes_mastered} in practice`
                          : ""}
                        {ch.outcomes_attempted === 0 ? " · not started" : ""}
                      </div>
                    </div>
                    <div
                      className="flex flex-wrap items-center gap-1 pt-0.5"
                      aria-label="outcome dots"
                    >
                      {ch.outcomes.map((o) => (
                        <OutcomeDot key={o.code} outcome={o} />
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function OutcomeDot({ outcome }: { outcome: OutcomeRollup }) {
  const pct =
    outcome.mastery !== null ? Math.round(outcome.mastery * 100) : null;
  const tooltip = `${outcome.code} — ${
    outcome.state === "MASTERED"
      ? `mastered (${pct}%)`
      : outcome.state === "PRACTISING"
        ? `practising (${pct}%)`
        : "not tried yet"
  }\n${outcome.description}`;
  const color =
    outcome.state === "MASTERED"
      ? BRAND_ARROW_COLORS.green
      : outcome.state === "PRACTISING"
        ? BRAND_ARROW_COLORS.orange
        : undefined;
  return (
    <span
      title={tooltip}
      aria-label={tooltip}
      className="inline-block h-2.5 w-2.5 rounded-full border"
      style={
        color
          ? { backgroundColor: color, borderColor: color }
          : {
              backgroundColor: "transparent",
              borderColor: "color-mix(in srgb, currentColor 30%, transparent)",
            }
      }
    />
  );
}

function ChapterStatusBadge({ status }: { status: ChapterStatus }) {
  if (status === "MASTERED") {
    return <Badge variant="success">Mastered</Badge>;
  }
  if (status === "IN_PRACTICE") {
    return <Badge variant="warning">In practice</Badge>;
  }
  return (
    <Badge variant="outline" className="text-(--color-muted-foreground)">
      To explore
    </Badge>
  );
}

/* ---------------- Derivation helpers ------------------------------ */

function rollupChapters(
  data: StudentMasteryGrid | undefined,
): ChapterRollup[] {
  if (!data) return [];
  return data.chapters.map((ch) => {
    const outcomes: OutcomeRollup[] = ch.outcomes.map((o) => {
      let state: OutcomeRollup["state"];
      if (o.attempts === 0 || o.mastery === null) {
        state = "UNTOUCHED";
      } else if (o.mastery >= MASTERY_FLOOR) {
        state = "MASTERED";
      } else {
        state = "PRACTISING";
      }
      return {
        code: o.code,
        description: o.description,
        mastery: o.mastery,
        attempts: o.attempts,
        state,
      };
    });
    const outcomes_total = outcomes.length;
    const outcomes_attempted = outcomes.filter((o) => o.state !== "UNTOUCHED").length;
    const outcomes_mastered = outcomes.filter((o) => o.state === "MASTERED").length;
    const masteries = outcomes
      .filter((o) => o.mastery !== null)
      .map((o) => o.mastery as number);
    const average_mastery =
      masteries.length === 0
        ? null
        : masteries.reduce((a, b) => a + b, 0) / masteries.length;

    let status: ChapterStatus;
    if (outcomes_attempted === 0) {
      status = "TO_EXPLORE";
    } else if (
      outcomes_total > 0 &&
      outcomes_mastered / outcomes_total >= CHAPTER_MASTERED_RATIO
    ) {
      status = "MASTERED";
    } else {
      status = "IN_PRACTICE";
    }

    return {
      chapter_id: ch.chapter_id,
      chapter_number: ch.chapter_number,
      chapter_title: ch.chapter_title,
      subject_id: ch.subject_id ?? null,
      subject_name: ch.subject_name ?? null,
      status,
      outcomes_total,
      outcomes_attempted,
      outcomes_mastered,
      average_mastery,
      outcomes,
    };
  });
}

function countByStatus(
  rollups: ChapterRollup[],
): Record<ChapterStatus, number> {
  const counts: Record<ChapterStatus, number> = {
    MASTERED: 0,
    IN_PRACTICE: 0,
    TO_EXPLORE: 0,
  };
  for (const ch of rollups) {
    counts[ch.status] += 1;
  }
  return counts;
}

/** Pick the outcome the learner is strongest at — useful as the
 *  positive anchor headline. We require at least one attempt so the
 *  display isn't a meaningless "100% on a 0-attempt outcome". */
function pickStrongest(rollups: ChapterRollup[]): OutcomePick | null {
  let best: { ch: ChapterRollup; o: OutcomeRollup } | null = null;
  for (const ch of rollups) {
    for (const o of ch.outcomes) {
      if (
        o.attempts > 0 &&
        o.mastery !== null &&
        (best === null ||
          (o.mastery > (best.o.mastery ?? 0)) ||
          (o.mastery === best.o.mastery && o.attempts > best.o.attempts))
      ) {
        best = { ch, o };
      }
    }
  }
  if (!best) return null;
  return {
    chapter_id: best.ch.chapter_id,
    chapter_number: best.ch.chapter_number,
    chapter_title: best.ch.chapter_title,
    subject_name: best.ch.subject_name,
    code: best.o.code,
    description: best.o.description,
    mastery: best.o.mastery,
    attempts: best.o.attempts,
  };
}

/** Pick the best next thing to practise. Priority order:
 *  1. The weakest *attempted* outcome — they've started this, finish it.
 *  2. An untouched outcome in a chapter already in progress — keep
 *     momentum on a chapter rather than starting a fresh one.
 *  3. The first outcome of the lowest-numbered TO_EXPLORE chapter —
 *     bias toward syllabus order to mirror the textbook reading flow.
 */
function pickBestPlace(rollups: ChapterRollup[]): OutcomePick | null {
  // 1. weakest attempted.
  let weakest: { ch: ChapterRollup; o: OutcomeRollup } | null = null;
  for (const ch of rollups) {
    for (const o of ch.outcomes) {
      if (
        o.attempts > 0 &&
        o.mastery !== null &&
        o.mastery < MASTERY_FLOOR &&
        (weakest === null || (o.mastery as number) < (weakest.o.mastery ?? 1))
      ) {
        weakest = { ch, o };
      }
    }
  }
  if (weakest) {
    return {
      chapter_id: weakest.ch.chapter_id,
      chapter_number: weakest.ch.chapter_number,
      chapter_title: weakest.ch.chapter_title,
      subject_name: weakest.ch.subject_name,
      code: weakest.o.code,
      description: weakest.o.description,
      mastery: weakest.o.mastery,
      attempts: weakest.o.attempts,
    };
  }
  // 2. untouched outcome inside an IN_PRACTICE chapter.
  for (const ch of rollups) {
    if (ch.status !== "IN_PRACTICE") continue;
    const o = ch.outcomes.find((x) => x.state === "UNTOUCHED");
    if (o) {
      return {
        chapter_id: ch.chapter_id,
        chapter_number: ch.chapter_number,
        chapter_title: ch.chapter_title,
        subject_name: ch.subject_name,
        code: o.code,
        description: o.description,
        mastery: o.mastery,
        attempts: o.attempts,
      };
    }
  }
  // 3. first outcome of the lowest-numbered TO_EXPLORE chapter.
  const fresh = rollups
    .filter((c) => c.status === "TO_EXPLORE")
    .sort((a, b) => a.chapter_number - b.chapter_number)[0];
  if (fresh && fresh.outcomes.length > 0) {
    const o = fresh.outcomes[0];
    return {
      chapter_id: fresh.chapter_id,
      chapter_number: fresh.chapter_number,
      chapter_title: fresh.chapter_title,
      subject_name: fresh.subject_name,
      code: o.code,
      description: o.description,
      mastery: o.mastery,
      attempts: o.attempts,
    };
  }
  return null;
}

// Note: derivation helpers (rollupChapters / countByStatus /
// pickStrongest / pickBestPlace) are intentionally NOT exported.
// react-refresh's components-only-export rule forbids mixing
// component + non-component exports in a single .tsx file. If we ever
// want unit tests, lift the helpers into `frontend/src/lib/progress.ts`
// (a .ts file) and import them here.
