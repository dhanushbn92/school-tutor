import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, BookOpen, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { useMySections } from "@/lib/queries";
import { useAvailableClasses, useAvailableSubjects } from "@/lib/scope";
import {
  subjectIcon,
  subjectTheme,
  subjectVar,
  subjectVarForeground,
} from "@/lib/subjectTheme";

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
        <PageHeader title="Learn" description="Subjects you've been assigned to teach." />
        <Empty
          icon={<BookOpen className="h-6 w-6" />}
          title="No subjects assigned to you yet"
          description="Ask your school admin to assign you to subjects (Manage school → Teachers). Once assigned, your subjects will appear here."
        />
      </div>
    );
  }

  return (
    <ThemedPage>
      <PageHeader
        title="Learn"
        description={
          classLevel
            ? `Subjects for Class ${classLevel}. Pick one to browse chapters, topics, and practice material.`
            : "Subjects for your class."
        }
      />

      {isMultiClass && (
        <div className="mb-4 flex flex-wrap items-end gap-3 rounded-md border border-(--color-border) bg-(--color-card) p-3">
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
      ) : (
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {filteredSubjects.map((s) => {
            // Resolve subject colour for inline use. We bind via inline
            // style props (rather than `bg-(--theme)` Tailwind shortcuts)
            // because the theme tokens are runtime-cascaded and inline
            // style is the most reliable way to consume them.
            const theme = subjectTheme(s.name);
            const Icon = subjectIcon(theme);
            const themeColor = subjectVar(theme);
            const themeFg = subjectVarForeground(theme);
            return (
              <Link
                key={s.id}
                to={`/learn/subjects/${s.id}`}
                className="group block focus:outline-none"
              >
                <Card
                  className="relative overflow-hidden rounded-2xl shadow-sm transition-all duration-150 group-hover:-translate-y-1 group-hover:shadow-xl"
                  style={{ borderLeft: `4px solid ${themeColor}` }}
                >
                  {/* Bigger subject-coloured halo in the top-right
                      corner. Large enough to read as decoration; the
                      title still anchors the eye thanks to higher
                      visual weight (bold display font, dark colour). */}
                  <div
                    aria-hidden
                    className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full opacity-25 blur-2xl"
                    style={{ background: themeColor }}
                  />
                  <CardHeader className="relative">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {/* Big subject icon tile with a vivid gradient
                            fill. Same shape language as the chapter and
                            subject heroes so the visual identity stays
                            consistent across the learning flow. */}
                        <div
                          className="flex h-14 w-14 items-center justify-center rounded-2xl shadow-md ring-1 ring-white/30"
                          style={{
                            background: `linear-gradient(135deg, ${themeColor}, color-mix(in oklab, ${themeColor} 70%, black))`,
                            color: themeFg,
                          }}
                        >
                          <Icon className="h-6 w-6" />
                        </div>
                        <CardTitle className="text-xl">{s.name}</CardTitle>
                      </div>
                      <ArrowRight className="h-5 w-5 text-(--color-muted-foreground) transition-transform group-hover:translate-x-1" />
                    </div>
                    <CardDescription className="mt-2 flex items-center gap-2">
                      {/* Board chip — lets the viewer tell CBSE Maths from
                          NIOS Maths without opening the card. */}
                      {s.board && (
                        <Badge className="text-[10px] font-bold uppercase tracking-wide">
                          {s.board}
                        </Badge>
                      )}
                      <span>Class {classLevel ?? "—"}</span>
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="relative text-sm text-(--color-muted-foreground)">
                    Browse chapters, topic summaries, and practice quizzes.
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </ThemedPage>
  );
}
