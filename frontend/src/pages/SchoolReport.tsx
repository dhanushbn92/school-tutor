import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, GraduationCap, Loader2, Trophy, Users } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/StatCard";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useMySchool,
  useMySections,
  useSubjects,
} from "@/lib/queries";
import { SectionLeaderboardCard } from "@/components/SectionLeaderboardCard";
import { WeakTopicsCard } from "@/components/WeakTopicsCard";
import { labelForSubject } from "@/components/BoardContextBar";

export function SchoolReportPage() {
  const sectionsQ = useMySections();
  const sections = sectionsQ.data ?? [];
  // class_level can be null (e.g. ungraded sections); drop those before sorting.
  const classLevels = Array.from(
    new Set(sections.map((s) => s.class_level).filter((v): v is number => v != null)),
  ).sort((a, b) => a - b);
  const firstClassLevel: number | undefined = classLevels[0];
  const [classLevel, setClassLevel] = useState<number | undefined>(undefined);
  const effectiveClassLevel: number | undefined = classLevel ?? firstClassLevel;
  const subjectsQ = useSubjects(effectiveClassLevel);
  const [subjectId, setSubjectId] = useState<number | undefined>();
  const chosenSubject =
    subjectId ??
    subjectsQ.data?.find((s) => s.name === "Science")?.id ??
    subjectsQ.data?.[0]?.id;
  const schoolQ = useMySchool();

  const filteredSections = sections.filter(
    (s) => effectiveClassLevel === undefined || s.class_level === effectiveClassLevel,
  );

  if (sectionsQ.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading…
      </div>
    );
  }

  return (
    <ThemedPage>
      <PageHeader
        title="School performance report"
        description={
          schoolQ.data
            ? `Cross-class roll-up for ${schoolQ.data.name}.`
            : "Cross-class roll-up of every active section."
        }
        actions={
          <div className="flex items-center gap-2">
            {classLevels.length > 1 && (
              <div className="w-32">
                <Select
                  value={String(effectiveClassLevel ?? "")}
                  onValueChange={(v) => setClassLevel(Number(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Class" />
                  </SelectTrigger>
                  <SelectContent>
                    {classLevels.map((lvl) => (
                      <SelectItem key={lvl} value={String(lvl)}>
                        Class {lvl}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            {subjectsQ.data && subjectsQ.data.length > 0 && (
              <div className="w-44">
                <Select
                  value={String(chosenSubject ?? "")}
                  onValueChange={(v) => setSubjectId(Number(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Subject" />
                  </SelectTrigger>
                  <SelectContent>
                    {subjectsQ.data.map((s) => (
                      <SelectItem key={s.id} value={String(s.id)}>
                        {labelForSubject(s)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        }
      />

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <StatCard
          label="Active sections"
          value={filteredSections.length}
          sub={effectiveClassLevel ? `Class ${effectiveClassLevel}` : "All classes"}
          icon={<Users className="h-5 w-5" />}
        />
        <StatCard
          label="Class levels"
          value={classLevels.length}
          sub={classLevels.map((c) => `Class ${c}`).join(" · ") || "—"}
          icon={<GraduationCap className="h-5 w-5" />}
        />
        <StatCard
          label="Selected subject"
          value={subjectsQ.data?.find((s) => s.id === chosenSubject)?.name ?? "—"}
          sub="Reports below are scoped to this subject"
          icon={<Trophy className="h-5 w-5" />}
        />
      </div>

      <div className="mb-6">
        <WeakTopicsCard
          classLevel={effectiveClassLevel}
          subjectId={chosenSubject}
          title={
            effectiveClassLevel
              ? `Weak topics — Class ${effectiveClassLevel}`
              : "Weak topics"
          }
          description="Lowest mastery first across every section of this class. Each topic is broken down by cognitive level — factual recall, understanding, and application — so you can see exactly where to focus teacher attention."
          limit={10}
        />
      </div>

      {filteredSections.length === 0 ? (
        <Empty
          title="No sections to report on"
          description="Add a section to your school to see reports here."
        />
      ) : (
        <div className="space-y-6">
          {filteredSections.map((s) => (
            <Card key={s.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">
                      {s.class_display_name} · {s.name}
                    </CardTitle>
                    <CardDescription>
                      Academic year {s.academic_year ?? "—"}
                    </CardDescription>
                  </div>
                  <Link
                    to={`/sections/${s.id}`}
                    className="flex items-center gap-1 text-sm text-(--color-primary) hover:underline"
                  >
                    Open section <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                <SectionLeaderboardCard
                  sectionId={s.id}
                  subjectId={chosenSubject}
                />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>How to read this</CardTitle>
          <CardDescription>
            For each section, the leaderboard shows the top performers and the
            students who currently need the most support, scoped to the selected
            subject. Click 'Open section' for the full per-class report including
            topic averages and weakest topics.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-(--color-muted-foreground)">
          <ul className="list-disc pl-5 space-y-1">
            <li>
              Use the class and subject filters at the top to focus on one class
              level or subject at a time.
            </li>
            <li>
              The percentages are average scores across all evaluated tests in the
              selected subject.
            </li>
            <li>
              <Badge variant="success">A</Badge> ≥ 85% ·
              <Badge variant="success" className="ml-1">B</Badge> ≥ 70% ·
              <Badge variant="outline" className="ml-1">C</Badge> ≥ 55% ·
              <Badge variant="warning" className="ml-1">D</Badge> ≥ 40% · below 40 needs focus.
            </li>
          </ul>
        </CardContent>
      </Card>
    </ThemedPage>
  );
}
