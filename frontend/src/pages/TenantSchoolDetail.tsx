import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Building2,
  GraduationCap,
  Loader2,
  Power,
  ShieldOff,
  UserPlus,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { StatCard } from "@/components/StatCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { humanError } from "@/lib/api";
import {
  usePlatformSchoolOverview,
  useTogglePlatformSchool,
} from "@/lib/queries";
import { cn } from "@/lib/utils";

type Tab = "sections" | "teachers" | "students";

const TABS: { value: Tab; label: string; icon: React.ReactNode }[] = [
  { value: "sections", label: "Sections", icon: <Users className="h-4 w-4" /> },
  { value: "teachers", label: "Teachers", icon: <UserPlus className="h-4 w-4" /> },
  { value: "students", label: "Students", icon: <GraduationCap className="h-4 w-4" /> },
];

export function TenantSchoolDetailPage() {
  const { schoolId: schoolIdParam } = useParams();
  const schoolId = schoolIdParam ? Number(schoolIdParam) : undefined;
  const overviewQ = usePlatformSchoolOverview(schoolId);
  const toggleMut = useTogglePlatformSchool();
  const [tab, setTab] = useState<Tab>("sections");
  const [confirmingDisable, setConfirmingDisable] = useState(false);

  if (overviewQ.isLoading) {
    return <Loader />;
  }
  if (!overviewQ.data) {
    return (
      <Empty
        icon={<Building2 className="h-6 w-6" />}
        title="School not found"
        description="It may have been removed, or the URL is incorrect."
        action={
          <Button asChild variant="outline">
            <Link to="/tenants">
              <ArrowLeft className="h-4 w-4" /> All tenants
            </Link>
          </Button>
        }
      />
    );
  }

  const school = overviewQ.data;

  async function setActive(next: boolean) {
    if (schoolId === undefined) return;
    try {
      await toggleMut.mutateAsync({ schoolId, isActive: next });
      toast.success(
        next
          ? "School re-enabled — all users can sign in again"
          : "School disabled — admins, teachers, and students are locked out",
      );
      setConfirmingDisable(false);
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <ThemedPage>
      <PageHeader
        title={school.brand_name?.trim() || school.name}
        description={
          <>
            <Badge variant="outline" className="mr-2">{school.board}</Badge>
            {school.brand_name ? <span>{school.name} · </span> : null}
            <span>Onboarded {formatDate(school.created_at)}</span>
            {!school.is_active && (
              <Badge variant="destructive" className="ml-2 gap-1">
                <ShieldOff className="h-3 w-3" /> Disabled
              </Badge>
            )}
          </>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button asChild variant="outline">
              <Link to="/tenants">
                <ArrowLeft className="h-4 w-4" /> All tenants
              </Link>
            </Button>
            {school.is_active ? (
              <Button
                variant="destructive"
                onClick={() => setConfirmingDisable(true)}
                disabled={toggleMut.isPending}
              >
                {toggleMut.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ShieldOff className="h-4 w-4" />
                )}
                Disable school
              </Button>
            ) : (
              <Button
                onClick={() => setActive(true)}
                disabled={toggleMut.isPending}
              >
                {toggleMut.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Power className="h-4 w-4" />
                )}
                Re-enable school
              </Button>
            )}
          </div>
        }
      />

      {confirmingDisable && school.is_active && (
        <Card className="mb-4 border-(--color-destructive)/40 bg-[color-mix(in_oklab,var(--color-destructive)_8%,transparent)]">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
            <div>
              <div className="flex items-center gap-2 text-sm font-medium">
                <ShieldOff className="h-4 w-4" />
                Disable {school.brand_name?.trim() || school.name}?
              </div>
              <div className="mt-1 text-xs text-(--color-muted-foreground)">
                The school admin, all <strong>{school.teacher_count}</strong>{" "}
                teacher{school.teacher_count === 1 ? "" : "s"} and{" "}
                <strong>{school.student_count}</strong> student
                {school.student_count === 1 ? "" : "s"} will immediately lose
                access to the platform on their next request. Existing data is
                preserved — you can re-enable any time.
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setConfirmingDisable(false)}
                disabled={toggleMut.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setActive(false)}
                disabled={toggleMut.isPending}
              >
                {toggleMut.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : null}
                Yes, disable
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Profile + counts */}
      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <StatCard
          label="Sections"
          value={school.section_count}
          icon={<Users className="h-5 w-5" />}
        />
        <StatCard
          label="Teachers"
          value={school.teacher_count}
          icon={<UserPlus className="h-5 w-5" />}
        />
        <StatCard
          label="Students"
          value={school.student_count}
          icon={<GraduationCap className="h-5 w-5" />}
        />
        <StatCard
          label="Status"
          value={school.is_active ? "Active" : "Disabled"}
          intent={school.is_active ? "success" : "danger"}
          icon={<Power className="h-5 w-5" />}
        />
      </div>

      <div className="mb-4 grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Contact</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <Row label="Email" value={school.contact_email ?? "—"} />
            <Row label="Phone" value={school.contact_phone ?? "—"} />
            <Row label="Address" value={school.address ?? "—"} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Identifiers</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <Row label="School ID" value={`#${school.id}`} />
            <Row label="Board" value={school.board} />
            <Row label="Brand" value={school.brand_name ?? "—"} />
            <Row label="Onboarded" value={formatDate(school.created_at)} />
          </CardContent>
        </Card>
      </div>

      {/* Tabs: sections / teachers / students */}
      <div className="mb-3 flex flex-wrap gap-1 rounded-lg border border-(--color-border) bg-(--color-card) p-1">
        {TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors",
              tab === t.value
                ? "bg-(--color-primary) text-(--color-primary-foreground)"
                : "hover:bg-(--color-muted)",
            )}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {tab === "sections" && <SectionsList school={school} />}
      {tab === "teachers" && <TeachersList school={school} />}
      {tab === "students" && <StudentsList school={school} />}
    </ThemedPage>
  );
}

type Overview = NonNullable<ReturnType<typeof usePlatformSchoolOverview>["data"]>;

function SectionsList({ school }: { school: Overview }) {
  if (school.sections.length === 0) {
    return <Empty title="No sections" description="This school hasn't created any sections yet." />;
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Sections</CardTitle>
        <CardDescription>{school.sections.length} active.</CardDescription>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
            <tr className="border-b border-(--color-border)">
              <th className="py-2 text-left font-medium">Section</th>
              <th className="py-2 text-left font-medium">Class</th>
              <th className="py-2 text-left font-medium">Class teacher</th>
              <th className="py-2 text-left font-medium">Year</th>
              <th className="py-2 text-right font-medium">Students</th>
            </tr>
          </thead>
          <tbody>
            {school.sections.map((s) => (
              <tr key={s.id} className="border-b border-(--color-border)/60">
                <td className="py-2 font-medium">
                  {s.class_display_name ? `${s.class_display_name} · ` : ""}
                  {s.name}
                </td>
                <td className="py-2 text-(--color-muted-foreground)">
                  {s.class_display_name ?? "—"}
                </td>
                <td className="py-2 text-(--color-muted-foreground)">
                  {s.class_teacher_name ?? "—"}
                </td>
                <td className="py-2 text-(--color-muted-foreground)">
                  {s.academic_year ?? "—"}
                </td>
                <td className="py-2 text-right">{s.student_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function TeachersList({ school }: { school: Overview }) {
  if (school.teachers.length === 0) {
    return <Empty title="No teachers" description="This school hasn't added any teachers yet." />;
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Teachers</CardTitle>
        <CardDescription>{school.teachers.length} on roster.</CardDescription>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
            <tr className="border-b border-(--color-border)">
              <th className="py-2 text-left font-medium">Name</th>
              <th className="py-2 text-left font-medium">Email</th>
              <th className="py-2 text-left font-medium">Qualification</th>
              <th className="py-2 text-right font-medium">Sections</th>
              <th className="py-2 text-right font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {school.teachers.map((t) => (
              <tr key={t.id} className="border-b border-(--color-border)/60">
                <td className="py-2 font-medium">{t.full_name}</td>
                <td className="py-2 text-(--color-muted-foreground)">{t.email}</td>
                <td className="py-2 text-(--color-muted-foreground)">
                  {t.qualification ?? "—"}
                </td>
                <td className="py-2 text-right">{t.sections_count}</td>
                <td className="py-2 text-right">
                  <Badge variant={t.is_active ? "outline" : "destructive"}>
                    {t.is_active ? "Active" : "Inactive"}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function StudentsList({ school }: { school: Overview }) {
  if (school.students.length === 0) {
    return <Empty title="No students" description="This school hasn't enrolled any students yet." />;
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Students</CardTitle>
        <CardDescription>{school.students.length} enrolled.</CardDescription>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
            <tr className="border-b border-(--color-border)">
              <th className="py-2 text-left font-medium">Name</th>
              <th className="py-2 text-left font-medium">Roll</th>
              <th className="py-2 text-left font-medium">Section</th>
              <th className="py-2 text-left font-medium">Class</th>
              <th className="py-2 text-right font-medium">Login</th>
            </tr>
          </thead>
          <tbody>
            {school.students.map((s) => (
              <tr key={s.id} className="border-b border-(--color-border)/60">
                <td className="py-2 font-medium">{s.full_name}</td>
                <td className="py-2 text-(--color-muted-foreground)">{s.roll_number ?? "—"}</td>
                <td className="py-2 text-(--color-muted-foreground)">{s.section_name ?? "—"}</td>
                <td className="py-2 text-(--color-muted-foreground)">
                  {s.class_level ? `Class ${s.class_level}` : "—"}
                </td>
                <td className="py-2 text-right">
                  {s.has_login ? (
                    <Badge variant={s.is_active ? "outline" : "destructive"}>
                      {s.is_active ? "Active" : "Inactive"}
                    </Badge>
                  ) : (
                    <Badge variant="secondary">No login</Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 py-1">
      <span className="text-(--color-muted-foreground)">{label}</span>
      <span className="text-right">{value}</span>
    </div>
  );
}

function Loader() {
  return (
    <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
      <Loader2 className="h-4 w-4 animate-spin" /> Loading…
    </div>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}
