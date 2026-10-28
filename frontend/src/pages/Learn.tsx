import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { BookOpen, Loader2 } from "lucide-react";
import { SubjectCard } from "@/components/SubjectCard";
import { Empty } from "@/components/ui/empty";
import { BoardContextBar, labelForSubject } from "@/components/BoardContextBar";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/lib/auth";
import {
  useFeaturedVideos,
  useMySections,
  useMyStudents,
  useStudentMastery,
} from "@/lib/queries";
import { rollupChapters, rollupSubjects } from "@/lib/progress";
import { useAvailableClasses, useAvailableSubjects } from "@/lib/scope";
import { cn } from "@/lib/utils";

type Filter = "all" | "progress" | "videos";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All subjects" },
  { key: "progress", label: "In progress" },
  { key: "videos", label: "With videos" },
];

export function LearnPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();

  // Students/individual learners are pinned to their own class — no picker.
  // Teachers see only the classes they're assigned to (via their sections);
  // school admins and platform admins see the full curriculum. Platform admins
  // have no sections, so without `isMultiClass` they'd fall through to a null
  // classLevel and see nothing. The dropdown is persisted in the URL so
  // back-navigation from a chapter restores the same view.
  const isMultiClass =
    user?.role === "school_admin" ||
    user?.role === "teacher" ||
    user?.role === "platform_admin";

  const sectionsQ = useMySections();
  const available = useAvailableClasses();

  const urlClass = Number(params.get("class")) || undefined;
  const sectionClass = sectionsQ.data?.[0]?.class_level ?? undefined;
  const firstAvailableClass = available.classes[0]?.level ?? undefined;

  const classLevel = isMultiClass
    ? (urlClass ?? firstAvailableClass)
    : sectionClass;

  // For teachers this returns the intersection of "subjects of classLevel"
  // with their explicit assignments (or fallback). Other roles see all
  // subjects of the class.
  const subjectsScope = useAvailableSubjects(classLevel);
  const urlSubjectId = Number(params.get("subject")) || undefined;
  const subjects = subjectsScope.subjects;
  const filteredSubjects = urlSubjectId
    ? subjects.filter((s) => s.id === urlSubjectId)
    : subjects;

  // Learners also see where they are up to in each subject, and how many
  // videos it has; both come from data the home page already loads.
  const [filter, setFilter] = useState<Filter>("all");
  const section = sectionsQ.data?.[0];
  const studentsQ = useMyStudents(isMultiClass ? undefined : section?.id);
  const myStudent = studentsQ.data?.find((st) => st.user_id === user?.id);
  const masteryQ = useStudentMastery({
    student_id: myStudent?.id,
    class_level: section?.class_level ?? undefined,
    allSubjects: true,
  });
  const featuredQ = useFeaturedVideos();
  const progressBySubject = useMemo(() => {
    const m = new Map<number, ReturnType<typeof rollupSubjects>[number]>();
    for (const r of rollupSubjects(rollupChapters(masteryQ.data))) {
      if (r.subject_id !== null) m.set(r.subject_id, r);
    }
    return m;
  }, [masteryQ.data]);
  const videosBySubject = useMemo(() => {
    const m = new Map<number, number>();
    for (const c of featuredQ.data?.chapters ?? []) {
      m.set(c.subject_id, (m.get(c.subject_id) ?? 0) + c.video_count);
    }
    return m;
  }, [featuredQ.data]);

  function setClass(level: number) {
    const next = new URLSearchParams(params);
    next.set("class", String(level));
    next.delete("subject"); // subject ids don't carry across classes
    setParams(next, { replace: true });
  }
  function setSubject(id: number | "all") {
    const next = new URLSearchParams(params);
    if (id === "all") next.delete("subject");
    else next.set("subject", String(id));
    setParams(next, { replace: true });
  }

  if (sectionsQ.isLoading || (isMultiClass && available.isLoading)) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading…
      </div>
    );
  }

  // Teacher logged in but with no subject assignments AND not a class teacher
  // of any section. Without this guard we'd fall through to a fully empty
  // state with confusing copy.
  if (user?.role === "teacher" && available.classes.length === 0) {
    return (
      <div>
        <PageTitle title="Learn" subtitle="Subjects you've been assigned to teach." />
        <Empty
          icon={<BookOpen className="h-6 w-6" />}
          title="No subjects assigned to you yet"
          description="Ask your school admin to assign you to subjects (Manage school → Teachers). Once assigned, your subjects will appear here."
        />
      </div>
    );
  }

  const showFilters = !isMultiClass;
  const visibleSubjects = filteredSubjects.filter((sub) => {
    if (!showFilters || filter === "all") return true;
    if (filter === "videos") return (videosBySubject.get(sub.id) ?? 0) > 0;
    return hasStarted(progressBySubject.get(sub.id));
  });
  const board = subjects[0]?.board;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <PageTitle
          title="Learn"
          subtitle={
            classLevel
              ? `Class ${classLevel}${board ? ` · ${board}` : ""}. Pick a subject to ${isMultiClass ? "browse chapters and practice material" : "continue"}.`
              : "Subjects for your class."
          }
        />
        {showFilters && (
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter subjects">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                aria-pressed={filter === f.key}
                className={cn(
                  "rounded-full border px-4 py-2 text-sm font-semibold transition-colors",
                  filter === f.key
                    ? "border-(--color-foreground) bg-(--color-foreground) text-(--color-background)"
                    : "border-(--color-border) bg-(--color-card) text-(--color-muted-foreground) hover:text-(--color-foreground)",
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {isMultiClass && (
        <div className="mb-4 flex flex-wrap items-end gap-3 rounded-2xl border border-(--color-border) bg-(--color-card) p-3">
          <div className="grid gap-1.5">
            <Label htmlFor="learn-class" className="text-xs">
              Class
            </Label>
            <Select
              value={classLevel ? String(classLevel) : undefined}
              onValueChange={(v) => setClass(Number(v))}
            >
              <SelectTrigger id="learn-class" className="w-[180px]">
                <SelectValue placeholder="Pick class" />
              </SelectTrigger>
              <SelectContent>
                {available.classes.map((c) => (
                  <SelectItem key={c.id} value={String(c.level)}>
                    {c.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="learn-subject" className="text-xs">
              Subject
            </Label>
            <Select
              value={urlSubjectId ? String(urlSubjectId) : "all"}
              onValueChange={(v) => setSubject(v === "all" ? "all" : Number(v))}
              disabled={subjects.length === 0}
            >
              <SelectTrigger id="learn-subject" className="w-[200px]">
                <SelectValue placeholder="All subjects" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All subjects</SelectItem>
                {subjects.map((s) => (
                  <SelectItem key={s.id} value={String(s.id)}>
                    {labelForSubject(s)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* When a single subject is filtered, surface its board prominently.
          When "All subjects" is showing the per-card board badges below
          do that job, so we hide this strip. */}
      {urlSubjectId !== undefined && (
        <BoardContextBar
          classLevel={classLevel}
          subjectName={subjects.find((s) => s.id === urlSubjectId)?.name}
          board={subjects.find((s) => s.id === urlSubjectId)?.board}
        />
      )}

      {subjectsScope.isLoading ? (
        <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading subjects…
        </div>
      ) : filteredSubjects.length === 0 ? (
        <Empty
          icon={<BookOpen className="h-6 w-6" />}
          title="No subjects yet"
          description={
            isMultiClass
              ? "No subjects configured for this class. Try a different class."
              : "Your class doesn't have subjects configured yet. Please check back soon."
          }
        />
      ) : visibleSubjects.length === 0 ? (
        <Empty
          icon={<BookOpen className="h-6 w-6" />}
          title="Nothing matches this filter"
          description="Try All subjects to see everything in your class."
        />
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(17rem,1fr))] gap-5">
          {visibleSubjects.map((sub) => {
            const prog = progressBySubject.get(sub.id);
            const started = !isMultiClass && hasStarted(prog);
            const chapters = prog?.chapters.length;
            const where = isMultiClass
              ? `Class ${classLevel ?? ""}`
              : prog?.current
                ? `Chapter ${prog.current.chapter_number} of ${chapters}`
                : chapters
                  ? `${chapters} chapters`
                  : "Not started";
            return (
              <SubjectCard
                key={sub.id}
                size="large"
                name={sub.name}
                board={sub.board}
                percent={isMultiClass ? null : (prog?.percent ?? 0)}
                where={where}
                chapterCount={chapters}
                videos={videosBySubject.get(sub.id) ?? 0}
                highlight={started}
                cta={isMultiClass ? "Open" : started ? "Continue" : "Start"}
                to={
                  started && prog?.current
                    ? `/learn/chapters/${prog.current.chapter_id}`
                    : `/learn/subjects/${sub.id}`
                }
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

/** True once the learner has attempted anything in the subject. */
function hasStarted(p: { chapters: { outcomes_attempted: number }[] } | undefined): boolean {
  return p?.chapters.some((c) => c.outcomes_attempted > 0) ?? false;
}

/** The flat page heading used on the learner-facing pages. */
function PageTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <h1 className="font-display text-3xl font-extrabold tracking-tight">{title}</h1>
      <p className="mt-1.5 text-base text-(--color-muted-foreground)">{subtitle}</p>
    </div>
  );
}
