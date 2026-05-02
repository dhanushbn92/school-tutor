import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Building2, Loader2, Pencil, Plus, UserPlus, Users } from "lucide-react";
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { humanError } from "@/lib/api";
import { VALID_BOARDS } from "@/lib/boards";
import {
  useAcademicYears,
  useClasses,
  useCreateEnrollment,
  useCreateSection,
  useCreateStudent,
  useCreateTeacher,
  useMySchool,
  useMySections,
  useSetTeacherSubjects,
  useStudents,
  useSubjects,
  useTeacherSubjects,
  useTeachers,
  useUpdateMySchool,
} from "@/lib/queries";
import type { SchoolClass, Subject } from "@/lib/types";
import { cn } from "@/lib/utils";

type Tab = "school" | "sections" | "teachers" | "students";

const TABS: { value: Tab; label: string; icon: React.ReactNode }[] = [
  { value: "school", label: "School", icon: <Building2 className="h-4 w-4" /> },
  { value: "sections", label: "Sections", icon: <Users className="h-4 w-4" /> },
  { value: "teachers", label: "Teachers", icon: <UserPlus className="h-4 w-4" /> },
  { value: "students", label: "Students", icon: <Users className="h-4 w-4" /> },
];

export function ManageSchoolPage() {
  const [tab, setTab] = useState<Tab>("school");

  return (
    <ThemedPage>
      <PageHeader
        title="Manage school"
        description="Set up your school, classes, teachers and students. Everything here is scoped to your tenant; other schools never see this data."
      />

      <div className="mb-6 flex flex-wrap gap-1 rounded-lg border border-(--color-border) bg-(--color-card) p-1">
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

      {tab === "school" && <SchoolDetailsTab />}
      {tab === "sections" && <SectionsTab />}
      {tab === "teachers" && <TeachersTab />}
      {tab === "students" && <StudentsTab />}
    </ThemedPage>
  );
}

// --- School details tab ---

function SchoolDetailsTab() {
  const schoolQ = useMySchool();
  const update = useUpdateMySchool();
  const [draft, setDraft] = useState({
    name: "",
    board: "",
    brand_name: "",
    contact_email: "",
    contact_phone: "",
    address: "",
  });

  useEffect(() => {
    if (schoolQ.data) {
      setDraft({
        name: schoolQ.data.name,
        board: schoolQ.data.board,
        brand_name: schoolQ.data.brand_name ?? "",
        contact_email: schoolQ.data.contact_email ?? "",
        contact_phone: schoolQ.data.contact_phone ?? "",
        address: schoolQ.data.address ?? "",
      });
    }
  }, [schoolQ.data]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await update.mutateAsync({
        name: draft.name,
        board: draft.board,
        brand_name: draft.brand_name || null,
        contact_email: draft.contact_email || null,
        contact_phone: draft.contact_phone || null,
        address: draft.address || null,
      });
      toast.success("School details saved");
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  if (schoolQ.isLoading) return <Loader />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>School profile</CardTitle>
        <CardDescription>
          The brand name appears in the sidebar across the app. Other fields show on parent
          communications later.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="name">School name</Label>
            <Input
              id="name"
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="brand_name">Display name (sidebar)</Label>
            <Input
              id="brand_name"
              value={draft.brand_name}
              onChange={(e) => setDraft({ ...draft, brand_name: e.target.value })}
              placeholder="e.g. Sunshine Public"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="board">Board</Label>
            <Select
              value={draft.board || undefined}
              onValueChange={(v) => setDraft({ ...draft, board: v })}
            >
              <SelectTrigger id="board">
                <SelectValue placeholder="Pick a board..." />
              </SelectTrigger>
              <SelectContent>
                {VALID_BOARDS.map((b) => (
                  <SelectItem key={b} value={b}>
                    {b}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="contact_email">Contact email</Label>
            <Input
              id="contact_email"
              type="email"
              value={draft.contact_email}
              onChange={(e) => setDraft({ ...draft, contact_email: e.target.value })}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="contact_phone">Contact phone</Label>
            <Input
              id="contact_phone"
              value={draft.contact_phone}
              onChange={(e) => setDraft({ ...draft, contact_phone: e.target.value })}
            />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <Label htmlFor="address">Address</Label>
            <Input
              id="address"
              value={draft.address}
              onChange={(e) => setDraft({ ...draft, address: e.target.value })}
            />
          </div>
          <div className="md:col-span-2">
            <Button type="submit" disabled={update.isPending}>
              {update.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Save changes
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// --- Sections tab ---

function SectionsTab() {
  const sectionsQ = useMySections();
  const classesQ = useClasses();
  const yearsQ = useAcademicYears();
  const teachersQ = useTeachers();
  const create = useCreateSection();

  const [classId, setClassId] = useState<number | undefined>();
  const [yearId, setYearId] = useState<number | undefined>();
  const [name, setName] = useState("");
  const [classTeacherId, setClassTeacherId] = useState<number | undefined>();

  useEffect(() => {
    if (!yearId && yearsQ.data?.length) {
      setYearId(
        yearsQ.data.find((y) => y.is_current)?.id ?? yearsQ.data[0].id,
      );
    }
  }, [yearId, yearsQ.data]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!classId || !yearId || !name.trim()) {
      toast.error("Pick a class, year and section name");
      return;
    }
    try {
      await create.mutateAsync({
        class_id: classId,
        academic_year_id: yearId,
        name: name.trim().toUpperCase(),
        class_teacher_id: classTeacherId ?? null,
      });
      setName("");
      toast.success("Section created");
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr_3fr]">
      <Card>
        <CardHeader>
          <CardTitle>New section</CardTitle>
          <CardDescription>
            Sections are class + year + label (A, B, …). Class levels are restricted to 6–10
            for MVP.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Class</Label>
                <Select
                  value={classId !== undefined ? String(classId) : ""}
                  onValueChange={(v) => setClassId(Number(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Pick a class" />
                  </SelectTrigger>
                  <SelectContent>
                    {classesQ.data
                      ?.filter((c) => c.level >= 6 && c.level <= 10)
                      .map((c) => (
                        <SelectItem key={c.id} value={String(c.id)}>
                          {c.display_name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Section name</Label>
                <Input
                  maxLength={3}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="A"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Academic year</Label>
              <Select
                value={yearId !== undefined ? String(yearId) : ""}
                onValueChange={(v) => setYearId(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {yearsQ.data?.map((y) => (
                    <SelectItem key={y.id} value={String(y.id)}>
                      {y.name}
                      {y.is_current ? " (current)" : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Class teacher (optional)</Label>
              <Select
                value={classTeacherId !== undefined ? String(classTeacherId) : ""}
                onValueChange={(v) => setClassTeacherId(v === "" ? undefined : Number(v))}
                disabled={!teachersQ.data?.length}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      teachersQ.data?.length ? "No class teacher" : "Add a teacher first"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {teachersQ.data?.map((t) => (
                    <SelectItem key={t.id} value={String(t.id)}>
                      {t.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" disabled={create.isPending} className="w-full">
              {create.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              Create section
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Existing sections</CardTitle>
          <CardDescription>{sectionsQ.data?.length ?? 0} active.</CardDescription>
        </CardHeader>
        <CardContent>
          {sectionsQ.data && sectionsQ.data.length > 0 ? (
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
                <tr className="border-b border-(--color-border)">
                  <th className="py-2 text-left font-medium">Class</th>
                  <th className="py-2 text-left font-medium">Section</th>
                  <th className="py-2 text-left font-medium">Year</th>
                  <th className="py-2 text-left font-medium">Class teacher</th>
                </tr>
              </thead>
              <tbody>
                {sectionsQ.data.map((s) => (
                  <tr key={s.id} className="border-b border-(--color-border)/60">
                    <td className="py-2">{s.class_display_name}</td>
                    <td className="py-2 font-medium">{s.name}</td>
                    <td className="py-2 text-(--color-muted-foreground)">
                      {s.academic_year}
                    </td>
                    <td className="py-2 text-(--color-muted-foreground)">
                      {s.class_teacher_id ? `#${s.class_teacher_id}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Empty title="No sections yet" description="Use the form on the left to add your first section." />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// --- Teachers tab ---

function TeachersTab() {
  const teachersQ = useTeachers();
  const create = useCreateTeacher();
  const [draft, setDraft] = useState({ full_name: "", email: "", password: "", qualification: "" });

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await create.mutateAsync({
        full_name: draft.full_name.trim(),
        email: draft.email.trim().toLowerCase(),
        password: draft.password,
        qualification: draft.qualification.trim() || null,
      });
      setDraft({ full_name: "", email: "", password: "", qualification: "" });
      toast.success("Teacher account created");
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr_3fr]">
      <Card>
        <CardHeader>
          <CardTitle>Add teacher</CardTitle>
          <CardDescription>
            Creates a teacher account in your school. Share the email + password securely;
            the teacher can change the password later.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="space-y-1.5">
              <Label>Full name</Label>
              <Input required value={draft.full_name} onChange={(e) => setDraft({ ...draft, full_name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label>Email</Label>
              <Input type="email" required value={draft.email} onChange={(e) => setDraft({ ...draft, email: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label>Initial password</Label>
              <Input type="password" required minLength={8} value={draft.password} onChange={(e) => setDraft({ ...draft, password: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label>Qualification (optional)</Label>
              <Input value={draft.qualification} onChange={(e) => setDraft({ ...draft, qualification: e.target.value })} placeholder="M.Sc. Physics, B.Ed." />
            </div>
            <Button type="submit" disabled={create.isPending} className="w-full">
              {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              Create teacher
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Teachers</CardTitle>
          <CardDescription>
            {teachersQ.data?.length ?? 0} on roster. Click <em>Edit subjects</em>{" "}
            to assign each teacher the subjects they teach. Teachers only see
            assigned subjects in Learn, Content Library, and the Dashboard —
            unassigned teachers see no subjects until you set them up here.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {teachersQ.data && teachersQ.data.length > 0 ? (
            <ul className="divide-y divide-(--color-border)/60">
              {teachersQ.data.map((t) => (
                <TeacherRow key={t.id} teacherId={t.id} fullName={t.full_name} qualification={t.qualification} />
              ))}
            </ul>
          ) : (
            <Empty title="No teachers yet" description="Add your first teacher using the form on the left." />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/** One row in the teachers list — collapsed view + inline subject editor. */
function TeacherRow({
  teacherId,
  fullName,
  qualification,
}: {
  teacherId: number;
  fullName: string;
  qualification: string | null;
}) {
  const [editing, setEditing] = useState(false);
  const subjectsQ = useTeacherSubjects(teacherId);
  // We fetch the full subject catalog once and group by class for the editor.
  // Opt in to the cross-class fetch — useSubjects(undefined) is otherwise
  // gated to avoid race-mismatches on pages that pick a class first.
  const allSubjectsQ = useSubjects(undefined, { fetchAllWhenUndefined: true });
  const classesQ = useClasses();

  const subjectsById = useMemo(() => {
    const map = new Map<number, Subject>();
    (allSubjectsQ.data ?? []).forEach((s) => map.set(s.id, s));
    return map;
  }, [allSubjectsQ.data]);

  const summary = subjectsQ.data?.subject_ids ?? [];

  return (
    <li className="py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="font-medium">{fullName}</div>
          {qualification && (
            <div className="text-xs text-(--color-muted-foreground)">{qualification}</div>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {!subjectsQ.isSuccess ? (
              <span className="text-xs text-(--color-muted-foreground)">
                Loading subjects…
              </span>
            ) : summary.length === 0 ? (
              <Badge variant="outline" className="text-xs">
                No subjects assigned
              </Badge>
            ) : (
              <>
                {summary.map((sid) => {
                  const subj = subjectsById.get(sid);
                  if (!subj) return null;
                  const cls = classesQ.data?.find((c) => c.id === subj.class_id);
                  return (
                    <Badge key={sid} variant="outline" className="text-xs">
                      {cls ? `${cls.display_name} · ` : ""}{subj.name}
                    </Badge>
                  );
                })}
              </>
            )}
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setEditing((v) => !v)}
          disabled={!subjectsQ.isSuccess || !allSubjectsQ.isSuccess}
        >
          <Pencil className="h-3.5 w-3.5" />
          {editing ? "Cancel" : "Edit subjects"}
        </Button>
      </div>

      {editing && allSubjectsQ.data && classesQ.data && (
        <div className="mt-3">
          <SubjectAssignmentEditor
            teacherId={teacherId}
            classes={classesQ.data}
            subjects={allSubjectsQ.data}
            // Strict scoping: `summary` already is exactly the explicit
            // assignments (or empty if none). No fallback subjects to filter
            // out anymore.
            initialSelected={summary}
            onDone={() => setEditing(false)}
          />
        </div>
      )}
    </li>
  );
}

function SubjectAssignmentEditor({
  teacherId,
  classes,
  subjects,
  initialSelected,
  onDone,
}: {
  teacherId: number;
  classes: SchoolClass[];
  subjects: Subject[];
  initialSelected: number[];
  onDone: () => void;
}) {
  const [selected, setSelected] = useState<Set<number>>(
    () => new Set(initialSelected),
  );
  const setMut = useSetTeacherSubjects();

  // Group subjects by class so the editor mirrors the natural curriculum
  // layout — admins think "this teacher handles Class 6 Science + Class 7
  // Science", not "subjects 4, 11, 18".
  const byClass = useMemo(() => {
    const map = new Map<number, Subject[]>();
    for (const s of subjects) {
      const arr = map.get(s.class_id) ?? [];
      arr.push(s);
      map.set(s.class_id, arr);
    }
    return map;
  }, [subjects]);

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function save() {
    try {
      await setMut.mutateAsync({
        teacherId,
        subjectIds: Array.from(selected).sort((a, b) => a - b),
      });
      toast.success(
        selected.size === 0
          ? "Cleared assignments — teacher will see no subjects until you assign some"
          : "Subject assignments saved",
      );
      onDone();
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <div className="rounded-md border border-(--color-border) bg-(--color-muted)/30 p-3">
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {classes.map((c) => {
          const items = byClass.get(c.id) ?? [];
          if (items.length === 0) return null;
          return (
            <div key={c.id} className="space-y-1">
              <div className="text-xs font-medium uppercase tracking-wide text-(--color-muted-foreground)">
                {c.display_name}
              </div>
              {items.map((s) => (
                <label
                  key={s.id}
                  className="flex items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-(--color-card)"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(s.id)}
                    onChange={() => toggle(s.id)}
                  />
                  <span>{s.name}</span>
                </label>
              ))}
            </div>
          );
        })}
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-(--color-muted-foreground)">
        <span>
          {selected.size === 0
            ? "No subjects checked → teacher will see no subjects in Learn or Content Library until you assign at least one."
            : `${selected.size} subject${selected.size === 1 ? "" : "s"} selected.`}
        </span>
        <div className="flex gap-2">
          <Button size="sm" variant="ghost" onClick={onDone} disabled={setMut.isPending}>
            Cancel
          </Button>
          <Button size="sm" onClick={save} disabled={setMut.isPending}>
            {setMut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Save
          </Button>
        </div>
      </div>
    </div>
  );
}

// --- Students tab ---

function StudentsTab() {
  const studentsQ = useStudents();
  const sectionsQ = useMySections();
  const yearsQ = useAcademicYears();
  const createStudent = useCreateStudent();
  const createEnrollment = useCreateEnrollment();

  const [draft, setDraft] = useState({
    full_name: "",
    roll_number: "",
    guardian_name: "",
    guardian_phone: "",
    login_email: "",
    login_password: "",
  });
  const [enrollSectionId, setEnrollSectionId] = useState<number | undefined>();

  useEffect(() => {
    if (!enrollSectionId && sectionsQ.data?.length) {
      setEnrollSectionId(sectionsQ.data[0].id);
    }
  }, [enrollSectionId, sectionsQ.data]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!draft.full_name.trim()) {
      toast.error("Full name is required");
      return;
    }
    try {
      const created = await createStudent.mutateAsync({
        full_name: draft.full_name.trim(),
        roll_number: draft.roll_number.trim() || null,
        guardian_name: draft.guardian_name.trim() || null,
        guardian_phone: draft.guardian_phone.trim() || null,
        login_email: draft.login_email.trim() ? draft.login_email.trim().toLowerCase() : null,
        login_password: draft.login_password || null,
      });
      // Auto-enroll into the picked section if one is selected.
      if (enrollSectionId && yearsQ.data?.length) {
        const yearId = yearsQ.data.find((y) => y.is_current)?.id ?? yearsQ.data[0].id;
        try {
          await createEnrollment.mutateAsync({
            student_id: created.id,
            section_id: enrollSectionId,
            academic_year_id: yearId,
          });
        } catch (err) {
          toast.error("Student created but enrollment failed: " + humanError(err));
        }
      }
      setDraft({
        full_name: "",
        roll_number: "",
        guardian_name: "",
        guardian_phone: "",
        login_email: "",
        login_password: "",
      });
      toast.success("Student added");
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr_3fr]">
      <Card>
        <CardHeader>
          <CardTitle>Add student</CardTitle>
          <CardDescription>
            Auto-enrolls into the chosen section. Login credentials are optional — you can
            invite the student to log in later.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Full name</Label>
                <Input required value={draft.full_name} onChange={(e) => setDraft({ ...draft, full_name: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label>Roll number</Label>
                <Input value={draft.roll_number} onChange={(e) => setDraft({ ...draft, roll_number: e.target.value })} placeholder="6A-01" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Guardian name</Label>
                <Input value={draft.guardian_name} onChange={(e) => setDraft({ ...draft, guardian_name: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label>Guardian phone</Label>
                <Input value={draft.guardian_phone} onChange={(e) => setDraft({ ...draft, guardian_phone: e.target.value })} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Enroll into section</Label>
              <Select
                value={enrollSectionId !== undefined ? String(enrollSectionId) : ""}
                onValueChange={(v) => setEnrollSectionId(Number(v))}
                disabled={!sectionsQ.data?.length}
              >
                <SelectTrigger>
                  <SelectValue placeholder={sectionsQ.data?.length ? "Pick a section" : "Add a section first"} />
                </SelectTrigger>
                <SelectContent>
                  {sectionsQ.data?.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.class_display_name} · {s.name} ({s.academic_year})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="rounded-md border border-(--color-border) bg-(--color-muted)/40 p-3">
              <p className="mb-2 text-xs uppercase tracking-wide text-(--color-muted-foreground)">
                Optional login (so the student can sign in)
              </p>
              <div className="space-y-2">
                <Input
                  type="email"
                  value={draft.login_email}
                  onChange={(e) => setDraft({ ...draft, login_email: e.target.value })}
                  placeholder="student.email@yourschool.edu"
                />
                <Input
                  type="password"
                  value={draft.login_password}
                  onChange={(e) => setDraft({ ...draft, login_password: e.target.value })}
                  placeholder="Initial password (min 8 chars)"
                  minLength={8}
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={createStudent.isPending || createEnrollment.isPending}
              className="w-full"
            >
              {createStudent.isPending || createEnrollment.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              Add student
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Students</CardTitle>
          <CardDescription>{studentsQ.data?.length ?? 0} on roster.</CardDescription>
        </CardHeader>
        <CardContent>
          {studentsQ.data && studentsQ.data.length > 0 ? (
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
                <tr className="border-b border-(--color-border)">
                  <th className="py-2 text-left font-medium">Roll</th>
                  <th className="py-2 text-left font-medium">Name</th>
                  <th className="py-2 text-left font-medium">Guardian</th>
                  <th className="py-2 text-left font-medium" />
                </tr>
              </thead>
              <tbody>
                {studentsQ.data.map((s) => (
                  <tr key={s.id} className="border-b border-(--color-border)/60">
                    <td className="py-2 text-(--color-muted-foreground)">{s.roll_number ?? "—"}</td>
                    <td className="py-2 font-medium">{s.full_name}</td>
                    <td className="py-2 text-(--color-muted-foreground)">
                      {s.guardian_name ? `${s.guardian_name} · ${s.guardian_phone ?? ""}` : "—"}
                    </td>
                    <td className="py-2">
                      <Badge variant="outline">#{s.id}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Empty title="No students yet" description="Add your first student using the form on the left." />
          )}
        </CardContent>
      </Card>
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
