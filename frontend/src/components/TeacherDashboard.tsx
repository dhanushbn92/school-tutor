import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Empty } from "@/components/ui/empty";
import {
  useClassWeakTopics,
  useMyAssessments,
  useMyStudents,
  useSectionLeaderboard,
} from "@/lib/queries";
import { useAvailableSubjects } from "@/lib/scope";
import { BUCKET_LABEL } from "@/lib/types";
import type { CognitiveBucket, Section, WeakTopicEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

const BUCKETS: CognitiveBucket[] = ["FACTUAL", "UNDERSTANDING", "APPLICATION"];

/** Cell colours for a mastery value: green is strong, amber so-so, pink weak. */
function cellStyle(value: number | null): { background: string; color: string } {
  if (value === null) return { background: "#EEF2F8", color: "#6B7A90" };
  if (value >= 0.7) return { background: "#D6EFDF", color: "#14532D" };
  if (value >= 0.5) return { background: "#FADBA8", color: "#6B4200" };
  return { background: "#F6C5CE", color: "#7B1E30" };
}

const chip = (active: boolean) =>
  cn(
    "rounded-full border px-4 py-2 text-sm font-semibold transition-colors",
    active
      ? "border-(--color-foreground) bg-(--color-foreground) text-(--color-background)"
      : "border-(--color-border) bg-(--color-card) text-(--color-muted-foreground) hover:text-(--color-foreground)",
  );

function initials(name: string | null): string {
  return (name ?? "?")
    .split(/\s+/)
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

/**
 * The teacher's home: one class at a time. Where the class is stuck, by topic
 * and by kind of question, and which students need support, with the two
 * things a teacher does next (assign a quiz, open the class report) in reach.
 */
export function TeacherDashboard({ sections }: { sections: Section[] }) {
  const [sectionId, setSectionId] = useState<number | undefined>();
  const section = sections.find((s) => s.id === sectionId) ?? sections[0];
  const className = `${section.class_display_name ?? `Class ${section.class_level ?? ""}`}-${section.name}`;

  const studentsQ = useMyStudents(section.id);
  const assessmentsQ = useMyAssessments();
  const subjectsScope = useAvailableSubjects(section.class_level ?? undefined);
  const subjects = subjectsScope.subjects;

  const [pickedSubject, setPickedSubject] = useState<number | undefined>();
  const subject =
    subjects.find((s) => s.id === pickedSubject) ??
    subjects.find((s) => s.name === "Science") ??
    subjects[0];

  const weakQ = useClassWeakTopics({
    class_level: section.class_level ?? undefined,
    subject_id: subject?.id,
    limit: 8,
  });
  const boardQ = useSectionLeaderboard({
    section_id: section.id,
    subject_id: subject?.id,
  });

  const published = (assessmentsQ.data ?? []).filter((a) => a.status === "PUBLISHED").length;
  const topics = weakQ.data?.topics ?? [];
  // Only students with results count, and only those below 60% need a hand.
  const withResults = (boardQ.data?.students ?? []).filter(
    (s) => s.average_mastery !== null && s.tests_taken > 0,
  );
  const needSupport = withResults
    .filter((s) => (s.average_mastery ?? 1) < 0.6)
    .sort((a, b) => (a.average_mastery ?? 1) - (b.average_mastery ?? 1))
    .slice(0, 4);

  const suggestion = buildSuggestion(topics);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-extrabold tracking-tight">{className}</h1>
          <p className="mt-1.5 text-base text-(--color-muted-foreground)">
            {studentsQ.data ? `${studentsQ.data.length} students` : "Students"}
            {subject ? ` · ${subject.name}` : ""} · {published} published quizzes
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild size="lg" variant="secondary" className="rounded-xl">
            <Link to={`/sections/${section.id}`}>Class report</Link>
          </Button>
          <Button asChild size="lg" className="rounded-xl">
            <Link to="/assessments/new">Assign a quiz</Link>
          </Button>
        </div>
      </div>

      {sections.length > 1 && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Choose a class">
          {sections.map((s) => (
            <button
              key={s.id}
              type="button"
              aria-pressed={s.id === section.id}
              onClick={() => {
                setSectionId(s.id);
                setPickedSubject(undefined);
              }}
              className={chip(s.id === section.id)}
            >
              {s.class_display_name ?? `Class ${s.class_level ?? ""}`}-{s.name}
            </button>
          ))}
        </div>
      )}

      {subjects.length > 1 && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Choose a subject">
          {subjects.map((s) => (
            <button
              key={s.id}
              type="button"
              aria-pressed={s.id === subject?.id}
              onClick={() => setPickedSubject(s.id)}
              className={chip(s.id === subject?.id)}
            >
              {s.name}
            </button>
          ))}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_21rem] lg:items-start">
        <Card className="rounded-2xl p-6">
          <h2 className="font-display text-lg font-bold">Mastery by topic and question type</h2>
          <p className="mt-0.5 text-sm text-(--color-muted-foreground)">
            Weakest topics first. Green is strong, pink needs work.
          </p>

          {!subject ? (
            <Empty title="No subjects assigned yet" className="border-0 py-6" />
          ) : weakQ.isLoading ? (
            <div className="mt-6 flex items-center gap-2 text-sm text-(--color-muted-foreground)">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </div>
          ) : topics.length === 0 ? (
            <Empty
              title="No results yet"
              description="Once students attempt quizzes tagged to topics, the class picture appears here."
              className="border-0 py-6"
            />
          ) : (
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[30rem] border-separate border-spacing-y-1.5 text-sm">
                <thead>
                  <tr className="text-left text-xs text-(--color-muted-foreground)">
                    <th className="pb-1 pr-3 font-medium">Topic</th>
                    {BUCKETS.map((b) => (
                      <th key={b} className="pb-1 text-center font-medium">
                        {BUCKET_LABEL[b]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {topics.map((t) => (
                    <tr key={t.topic_id}>
                      <td className="max-w-56 pr-3">
                        <div className="truncate font-semibold">{t.topic_name}</div>
                        <div className="truncate text-xs text-(--color-muted-foreground)">
                          Chapter {t.chapter_number} · {t.students_attempted}{" "}
                          {t.students_attempted === 1 ? "student" : "students"}
                        </div>
                      </td>
                      {BUCKETS.map((b) => {
                        const v = t.buckets[b]?.average_mastery ?? null;
                        return (
                          <td key={b} className="px-1 text-center">
                            <div
                              className="mx-auto flex h-9 min-w-14 items-center justify-center rounded-lg text-xs font-bold"
                              style={cellStyle(v)}
                            >
                              {v === null ? "—" : Math.round(v * 100)}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {suggestion && (
            <div className="mt-5 flex flex-wrap items-center gap-3 rounded-xl bg-(--color-primary)/8 px-4 py-3 text-sm leading-relaxed">
              <span className="min-w-0 flex-1">
                <b>Suggestion:</b> {suggestion}
              </span>
              <Button asChild size="sm" className="rounded-lg">
                <Link to="/assessments/new">New quiz from the bank</Link>
              </Button>
            </div>
          )}
        </Card>

        <Card className="rounded-2xl p-6">
          <h2 className="font-display text-lg font-bold">Students who need support</h2>
          {needSupport.length === 0 ? (
            <p className="mt-3 text-sm text-(--color-muted-foreground)">
              {withResults.length > 0
                ? "Nobody is below 60% right now. Nice work."
                : "No results yet. Once students take quizzes, the ones who need a hand show up here."}
            </p>
          ) : (
            <ul className="mt-2 divide-y divide-(--color-border)">
              {needSupport.map((s) => {
                const pct = Math.round((s.average_mastery ?? 0) * 100);
                return (
                  <li key={s.student_id} className="flex items-center gap-3 py-3">
                    <span
                      aria-hidden
                      className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-bold"
                      style={cellStyle(s.average_mastery)}
                    >
                      {initials(s.full_name)}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-semibold">{s.full_name ?? "Student"}</div>
                      <div className="text-xs text-(--color-muted-foreground)">
                        Mastery {pct}% · {s.tests_taken} {s.tests_taken === 1 ? "quiz" : "quizzes"}
                      </div>
                    </div>
                    <Link
                      to={`/students/${s.student_id}`}
                      className="text-sm font-semibold text-(--color-primary) hover:underline"
                    >
                      Open
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
          <Button asChild variant="secondary" className="mt-3 w-full rounded-xl">
            <Link to={`/sections/${section.id}`}>See all students</Link>
          </Button>
        </Card>
      </div>
    </div>
  );
}

/** One plain-language next step from the weakest kind of question in the class. */
function buildSuggestion(topics: WeakTopicEntry[]): string | null {
  const withData = topics.filter((t) => BUCKETS.some((b) => t.buckets[b]?.average_mastery != null));
  if (withData.length === 0) return null;
  let weakest: { bucket: CognitiveBucket; avg: number } | null = null;
  for (const b of BUCKETS) {
    const vals = withData
      .map((t) => t.buckets[b]?.average_mastery)
      .filter((v): v is number => v !== null && v !== undefined);
    if (vals.length === 0) continue;
    const avg = vals.reduce((a, c) => a + c, 0) / vals.length;
    if (weakest === null || avg < weakest.avg) weakest = { bucket: b, avg };
  }
  if (!weakest) return null;
  return `The class finds ${BUCKET_LABEL[weakest.bucket].toLowerCase()} questions hardest, most of all in ${withData[0].topic_name}. A short quiz on it would help.`;
}
