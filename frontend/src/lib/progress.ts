import type { StudentMasteryGrid } from "@/lib/types";

/**
 * Pure progress derivations for the learner home page: chapter and
 * subject roll-ups from the mastery grid, plus the "strongest topic" and
 * "best place to practise next" picks. Kept in a .ts file so components
 * can import them without tripping react-refresh's components-only rule.
 *
 * Everything is derived on the frontend from the mastery grid; there is no
 * extra API field to maintain.
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

export interface ChapterRollup {
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

export interface OutcomePick {
  chapter_id: number;
  chapter_number: number;
  chapter_title: string;
  subject_name: string | null;
  code: string;
  description: string;
  mastery: number | null;
  attempts: number;
}


export function rollupChapters(
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

/** Pick the outcome the learner is strongest at — useful as the
 *  positive anchor headline. We require at least one attempt so the
 *  display isn't a meaningless "100% on a 0-attempt outcome". */
export function pickStrongest(rollups: ChapterRollup[]): OutcomePick | null {
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
export function pickBestPlace(rollups: ChapterRollup[]): OutcomePick | null {
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

export interface SubjectRollup {
  key: string;
  subject_id: number | null;
  subject_name: string;
  chapters: ChapterRollup[];
  outcomes_total: number;
  outcomes_mastered: number;
  /** Share of this subject's outcomes mastered, 0..100 (rounded). */
  percent: number;
  /** Where to carry on in this subject; null when everything is mastered. */
  current: OutcomePick | null;
}

/** Group chapter roll-ups by subject, sorted by subject name. */
export function rollupSubjects(
  rollups: ChapterRollup[],
  fallbackName = "Your syllabus",
): SubjectRollup[] {
  const groups = new Map<string, ChapterRollup[]>();
  for (const ch of rollups) {
    const key = ch.subject_id !== null ? `id:${ch.subject_id}` : `name:${ch.subject_name ?? fallbackName}`;
    const list = groups.get(key) ?? [];
    list.push(ch);
    groups.set(key, list);
  }
  const out: SubjectRollup[] = [];
  for (const [key, chapters] of groups) {
    chapters.sort((a, b) => a.chapter_number - b.chapter_number);
    const outcomes_total = chapters.reduce((n, c) => n + c.outcomes_total, 0);
    const outcomes_mastered = chapters.reduce((n, c) => n + c.outcomes_mastered, 0);
    out.push({
      key,
      subject_id: chapters[0].subject_id,
      subject_name: chapters[0].subject_name ?? fallbackName,
      chapters,
      outcomes_total,
      outcomes_mastered,
      percent: outcomes_total === 0 ? 0 : Math.round((outcomes_mastered / outcomes_total) * 100),
      current: pickBestPlace(chapters),
    });
  }
  return out.sort((a, b) => a.subject_name.localeCompare(b.subject_name));
}
