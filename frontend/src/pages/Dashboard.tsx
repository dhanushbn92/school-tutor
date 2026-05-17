import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  BookOpenText,
  ClipboardList,
  FolderOpen,
  Loader2,
  NotebookPen,
  Sparkles,
  Users,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import { StatCard } from "@/components/StatCard";
import { WeakTopicsCard } from "@/components/WeakTopicsCard";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { DashboardHero } from "@/components/DashboardHero";
import { DashboardPurposePanel } from "@/components/DashboardPurposePanel";
import { LearnerDashboard } from "@/components/LearnerDashboard";
import { BoardContextBar, labelForSubject } from "@/components/BoardContextBar";
import { useAuth } from "@/lib/auth";
import {
  useGeneratedContentList,
  useMyAssessments,
  useMyInterventionNotes,
  useMySections,
  useMyStudents,
  useQuestions,
} from "@/lib/queries";
import { useAvailableClasses, useAvailableSubjects } from "@/lib/scope";
import { formatDate } from "@/lib/utils";

export function DashboardPage() {
  const { user } = useAuth();
  if (user?.role === "student" || user?.role === "individual_learner") {
    return <LearnerDashboard />;
  }
  const sectionsQ = useMySections();
  const firstSection = sectionsQ.data?.[0];
  const studentsQ = useMyStudents(firstSection?.id);
  const assessmentsQ = useMyAssessments();
  const notesQ = useMyInterventionNotes();

  // Class + subject picker for the Weak Topics panel. Persisted as URL would
  // be nicer but the dashboard rarely deep-links, so component state is fine.
  const availableClasses = useAvailableClasses();
  const [pickedClass, setPickedClass] = useState<number | undefined>();
  // For scoped roles (teachers) we never fall back to `firstSection?.class_level`
  // — that's the homeroom class, which can be different from the classes they
  // teach subjects in. With strict scoping, "no assigned classes" must mean
  // "no class to pick", not "fall back to homeroom".
  const effectiveClass: number | undefined =
    pickedClass ??
    availableClasses.classes[0]?.level ??
    (availableClasses.isScoped ? undefined : firstSection?.class_level);
  const availableSubjects = useAvailableSubjects(effectiveClass);
  const [pickedSubject, setPickedSubject] = useState<number | undefined>();
  const effectiveSubject: number | undefined =
    pickedSubject !== undefined &&
    availableSubjects.subjects.some((s) => s.id === pickedSubject)
      ? pickedSubject
      : availableSubjects.subjects.find((s) => s.name === "Science")?.id ??
        availableSubjects.subjects[0]?.id;

  // Reset the subject pick whenever the class changes — old subject_id won't
  // belong to the new class.
  useEffect(() => {
    setPickedSubject(undefined);
  }, [effectiveClass]);

  const questionsQ = useQuestions({ status: "DRAFT", limit: 100 });
  const generationsQ = useGeneratedContentList({ status: "ready", limit: 20 });

  if (sectionsQ.isLoading) {
    return (
      <div className="flex items-center gap-2 text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading...
      </div>
    );
  }

  // Learner roles handled by the early-return at the top of the function.
  const isPlatformAdmin = user?.role === "platform_admin";
  const isSchoolAdmin = user?.role === "school_admin";

  // Map our backend role string to the bucket DashboardHero understands.
  // school_admin + teacher share most operational chrome but the hero
  // copy benefits from distinguishing the two.
  const heroRole: "teacher" | "school_admin" | "platform_admin" = isPlatformAdmin
    ? "platform_admin"
    : isSchoolAdmin
      ? "school_admin"
      : "teacher";

  return (
    <ThemedPage>
      <DashboardHero role={heroRole} userName={firstWord(user?.full_name ?? "")} />

      {/* The platform's purpose lives at the top of every dashboard so
          new + returning users land on it before they scroll into
          operational widgets. Headline + lead + primary CTA are all
          role-tailored — a platform admin sees the curation framing,
          a teacher sees the assignment framing, a school admin sees
          the school-wide-pattern framing. */}
      <DashboardPurposePanel role={heroRole} />

      <PageHeader
        title={`Welcome, ${firstWord(user?.full_name ?? "")}`}
        description={
          isPlatformAdmin
            ? "Curate the catalog: generate content, approve questions, monitor coverage."
            : isSchoolAdmin
              ? "School-wide overview and actionable insights."
              : "Your classes, pending reviews, and areas to focus on."
        }
        actions={
          isPlatformAdmin ? (
            <Button asChild>
              <Link to="/generate">
                <Sparkles className="h-4 w-4" />
                Generate content
              </Link>
            </Button>
          ) : (
            <Button asChild>
              <Link to="/assessments/new">
                <Sparkles className="h-4 w-4" />
                New quiz from bank
              </Link>
            </Button>
          )
        }
      />

      {/* Board context — once a class + subject are picked the resolved
          board (CBSE / NIOS / ...) is the single most important piece of
          context to surface. Hidden during partial selection. */}
      <BoardContextBar
        classLevel={effectiveClass}
        subjectName={
          availableSubjects.subjects.find((s) => s.id === effectiveSubject)?.name
        }
        board={
          availableSubjects.subjects.find((s) => s.id === effectiveSubject)?.board
        }
      />

      {/* Stat cards — chosen per role so each viewer sees the numbers
          that match their job. A platform admin doesn't have classes
          or students; a teacher doesn't curate the question bank;
          a school admin watches both. */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {isPlatformAdmin ? (
          <>
            {/* Catalog curator's view — focus on the practice catalog. */}
            <StatCard
              label="Draft questions"
              value={questionsQ.data?.length ?? 0}
              sub="Awaiting approval"
              icon={<NotebookPen className="h-5 w-5" />}
              intent="warning"
            />
            <StatCard
              label="Recent generations"
              value={generationsQ.data?.length ?? 0}
              sub="Last 20 ready for publish"
              icon={<FolderOpen className="h-5 w-5" />}
              intent="success"
            />
            <StatCard
              label="Published assessments"
              value={
                assessmentsQ.data?.filter((a) => a.status === "PUBLISHED").length ??
                0
              }
              sub={`${assessmentsQ.data?.length ?? 0} total in flight`}
              icon={<ClipboardList className="h-5 w-5" />}
            />
            <StatCard
              label="Intervention notes"
              value={notesQ.data?.length ?? 0}
              sub="Filed across the platform"
              icon={<AlertTriangle className="h-5 w-5" />}
            />
          </>
        ) : isSchoolAdmin ? (
          <>
            {/* School-wide view — emphasise scope and reach. */}
            <StatCard
              label="Sections"
              value={sectionsQ.data?.length ?? 0}
              sub={
                firstSection
                  ? `Across ${availableClasses.classes.length} class levels`
                  : "No classes yet"
              }
              icon={<Users className="h-5 w-5" />}
            />
            <StatCard
              label="Students"
              value={studentsQ.data?.length ?? 0}
              sub={firstSection ? `${firstSection.class_display_name}-${firstSection.name}` : undefined}
              icon={<Users className="h-5 w-5" />}
              intent="success"
            />
            <StatCard
              label="Published assessments"
              value={
                assessmentsQ.data?.filter((a) => a.status === "PUBLISHED").length ??
                0
              }
              sub={`${assessmentsQ.data?.length ?? 0} total this term`}
              icon={<ClipboardList className="h-5 w-5" />}
            />
            <StatCard
              label="Intervention notes"
              value={notesQ.data?.length ?? 0}
              sub="Filed by your teachers"
              icon={<AlertTriangle className="h-5 w-5" />}
              intent="warning"
            />
          </>
        ) : (
          <>
            {/* Teacher's view — classroom-scoped. */}
            <StatCard
              label="My classes"
              value={sectionsQ.data?.length ?? 0}
              sub={
                firstSection
                  ? `Primary: ${firstSection.class_display_name} ${firstSection.name}`
                  : "No classes yet"
              }
              icon={<Users className="h-5 w-5" />}
            />
            <StatCard
              label="My students"
              value={studentsQ.data?.length ?? 0}
              sub={firstSection ? `${firstSection.class_display_name}-${firstSection.name}` : undefined}
              icon={<Users className="h-5 w-5" />}
              intent="success"
            />
            <StatCard
              label="Published quizzes"
              value={
                assessmentsQ.data?.filter((a) => a.status === "PUBLISHED").length ??
                0
              }
              sub={`${assessmentsQ.data?.length ?? 0} total`}
              icon={<ClipboardList className="h-5 w-5" />}
            />
            <StatCard
              label="My notes"
              value={notesQ.data?.length ?? 0}
              sub="Filed about students"
              icon={<AlertTriangle className="h-5 w-5" />}
            />
          </>
        )}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          <div className="flex flex-wrap items-end gap-3 rounded-md border border-(--color-border) bg-(--color-card) p-3">
            <div className="grid gap-1.5">
              <Label htmlFor="dash-class" className="text-xs">
                Class
              </Label>
              <Select
                value={effectiveClass ? String(effectiveClass) : undefined}
                onValueChange={(v) => setPickedClass(Number(v))}
                disabled={availableClasses.classes.length === 0}
              >
                <SelectTrigger id="dash-class" className="w-[180px]">
                  <SelectValue placeholder="Pick class" />
                </SelectTrigger>
                <SelectContent>
                  {availableClasses.classes.map((c) => (
                    <SelectItem key={c.id} value={String(c.level)}>
                      {c.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="dash-subject" className="text-xs">
                Subject
              </Label>
              <Select
                value={effectiveSubject ? String(effectiveSubject) : undefined}
                onValueChange={(v) => setPickedSubject(Number(v))}
                disabled={availableSubjects.subjects.length === 0}
              >
                <SelectTrigger id="dash-subject" className="w-[200px]">
                  <SelectValue placeholder="Pick subject" />
                </SelectTrigger>
                <SelectContent>
                  {availableSubjects.subjects.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {labelForSubject(s)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <WeakTopicsCard
            classLevel={effectiveClass}
            subjectId={effectiveSubject}
            description={
              isSchoolAdmin
                ? "Lowest mastery first across all sections of this class. Each topic is broken down by cognitive level so you can spot whether the gap is recall, comprehension, or application."
                : "Lowest mastery first across your students. Each topic is broken down by cognitive level so you can plan remediation — drill facts, re-explain concepts, or run application practice."
            }
            limit={8}
          />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Pending reviews</CardTitle>
            <CardDescription>Approve or edit before students see them.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Question bank is a platform-team curation surface — school
                admins and teachers don't see the link or row. */}
            {isPlatformAdmin && (
              <LinkRow
                icon={<NotebookPen className="h-4 w-4" />}
                label="Draft questions"
                count={questionsQ.data?.length ?? 0}
                to="/question-bank"
              />
            )}
            <LinkRow
              icon={<FolderOpen className="h-4 w-4" />}
              label="Recent generations"
              count={generationsQ.data?.length ?? 0}
              to="/content"
            />
            <LinkRow
              icon={<ClipboardList className="h-4 w-4" />}
              label="Assessments"
              count={assessmentsQ.data?.length ?? 0}
              to="/assessments"
            />
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent intervention notes</CardTitle>
            <CardDescription>Follow-up items you filed about students.</CardDescription>
          </CardHeader>
          <CardContent>
            {notesQ.isLoading ? (
              <Loader />
            ) : !notesQ.data || notesQ.data.length === 0 ? (
              <Empty
                icon={<AlertTriangle className="h-6 w-6" />}
                title="No notes yet"
                description="Write notes from a student's profile after reviewing their mastery map."
              />
            ) : (
              <ul className="space-y-3">
                {notesQ.data.slice(0, 6).map((n) => (
                  <li
                    key={n.id}
                    className="rounded-md border border-(--color-border) p-3 text-sm"
                  >
                    <div className="flex items-center justify-between gap-2 text-xs text-(--color-muted-foreground)">
                      <Link to={`/students/${n.student_id}`} className="underline-offset-4 hover:underline">
                        Student #{n.student_id}
                      </Link>
                      <span>{formatDate(n.created_at)}</span>
                    </div>
                    <p className="mt-1 line-clamp-3 text-(--color-foreground)">{n.note}</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick links</CardTitle>
            <CardDescription>Common teacher workflows.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <QuickLink to="/generate" icon={<Sparkles className="h-4 w-4" />}>
              Generate content
            </QuickLink>
            <QuickLink to="/question-bank" icon={<NotebookPen className="h-4 w-4" />}>
              Review questions
            </QuickLink>
            <QuickLink to="/assessments" icon={<ClipboardList className="h-4 w-4" />}>
              Build assessment
            </QuickLink>
            <QuickLink to="/curriculum" icon={<BookOpenText className="h-4 w-4" />}>
              Browse curriculum
            </QuickLink>
          </CardContent>
        </Card>
      </div>
    </ThemedPage>
  );
}

function firstWord(s: string): string {
  return s.split(/\s+/)[0] || "there";
}

function Loader() {
  return (
    <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
      <Loader2 className="h-4 w-4 animate-spin" /> Loading...
    </div>
  );
}

function LinkRow({
  icon,
  label,
  count,
  to,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  to: string;
}) {
  return (
    <Link
      to={to}
      className="flex items-center justify-between gap-2 rounded-md border border-(--color-border) p-3 text-sm transition-colors hover:bg-(--color-muted)"
    >
      <span className="flex items-center gap-2">
        <span className="text-(--color-muted-foreground)">{icon}</span>
        {label}
      </span>
      <span className="flex items-center gap-2">
        <Badge variant="secondary">{count}</Badge>
        <ArrowRight className="h-3.5 w-3.5 text-(--color-muted-foreground)" />
      </span>
    </Link>
  );
}

function QuickLink({
  to,
  icon,
  children,
}: {
  to: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Link
      to={to}
      className="flex items-center gap-2 rounded-md border border-(--color-border) px-3 py-3 text-sm transition-colors hover:bg-(--color-muted)"
    >
      <span className="text-(--color-primary)">{icon}</span>
      {children}
    </Link>
  );
}
