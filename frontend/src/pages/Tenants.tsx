import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Building2,
  GraduationCap,
  Loader2,
  ShieldOff,
  User as UserIcon,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { usePlatformLearners, usePlatformSchools } from "@/lib/queries";
import { cn } from "@/lib/utils";

type Tab = "schools" | "learners";

const TABS: { value: Tab; label: string; icon: React.ReactNode }[] = [
  { value: "schools", label: "Schools", icon: <Building2 className="h-4 w-4" /> },
  { value: "learners", label: "Individual learners", icon: <UserIcon className="h-4 w-4" /> },
];

export function TenantsPage() {
  const [tab, setTab] = useState<Tab>("schools");

  return (
    <ThemedPage>
      <PageHeader
        title="Tenants"
        description="Every school and individual learner using the platform. Open one to view their dashboard or toggle their access."
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

      {tab === "schools" ? <SchoolsTab /> : <LearnersTab />}
    </ThemedPage>
  );
}

function SchoolsTab() {
  const schoolsQ = usePlatformSchools();
  const [filter, setFilter] = useState("");

  if (schoolsQ.isLoading) return <Loader />;
  const all = schoolsQ.data ?? [];
  const needle = filter.trim().toLowerCase();
  const rows = needle
    ? all.filter(
        (s) =>
          s.name.toLowerCase().includes(needle) ||
          (s.brand_name?.toLowerCase().includes(needle) ?? false) ||
          s.board.toLowerCase().includes(needle),
      )
    : all;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Input
          placeholder="Filter by name, brand, board…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-sm"
        />
        <div className="text-xs text-(--color-muted-foreground)">
          {rows.length} of {all.length} school{all.length === 1 ? "" : "s"}
        </div>
      </div>

      {rows.length === 0 ? (
        <Empty
          icon={<Building2 className="h-6 w-6" />}
          title={all.length === 0 ? "No schools yet" : "No matches"}
          description={
            all.length === 0
              ? "Schools that sign up via /signup-school will appear here."
              : "No school matched your filter."
          }
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((s) => (
            <Link
              key={s.id}
              to={`/tenants/schools/${s.id}`}
              className="group block focus:outline-none"
            >
              <Card className="transition-shadow group-hover:shadow-md">
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <CardTitle className="text-base leading-snug">
                        {s.brand_name?.trim() || s.name}
                      </CardTitle>
                      <CardDescription className="mt-0.5 truncate">
                        {s.brand_name ? s.name : null}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {!s.is_active && (
                        <Badge variant="destructive" className="gap-1">
                          <ShieldOff className="h-3 w-3" /> Disabled
                        </Badge>
                      )}
                      <Badge variant="outline">{s.board}</Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <Stat label="Students" value={s.student_count} />
                    <Stat label="Teachers" value={s.teacher_count} />
                    <Stat label="Sections" value={s.section_count} />
                  </div>
                  <div className="mt-3 flex items-center justify-between text-xs text-(--color-muted-foreground)">
                    <span>Joined {formatDate(s.created_at)}</span>
                    <span className="inline-flex items-center gap-1 text-(--color-primary)">
                      Open <ArrowRight className="h-3.5 w-3.5" />
                    </span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function LearnersTab() {
  const learnersQ = usePlatformLearners();
  const [filter, setFilter] = useState("");

  if (learnersQ.isLoading) return <Loader />;
  const all = learnersQ.data ?? [];
  const needle = filter.trim().toLowerCase();
  const rows = needle
    ? all.filter(
        (l) =>
          l.full_name.toLowerCase().includes(needle) ||
          l.email.toLowerCase().includes(needle),
      )
    : all;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Input
          placeholder="Filter by name or email…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-sm"
        />
        <div className="text-xs text-(--color-muted-foreground)">
          {rows.length} of {all.length} learner{all.length === 1 ? "" : "s"}
        </div>
      </div>

      {rows.length === 0 ? (
        <Empty
          icon={<UserIcon className="h-6 w-6" />}
          title={all.length === 0 ? "No individual learners yet" : "No matches"}
          description={
            all.length === 0
              ? "Self-signups via /signup-individual will appear here."
              : "No learner matched your filter."
          }
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((l) => (
            <Link
              key={l.user_id}
              to={`/tenants/learners/${l.user_id}`}
              className="group block focus:outline-none"
            >
              <Card className="transition-shadow group-hover:shadow-md">
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <CardTitle className="text-base leading-snug">
                        {l.full_name}
                      </CardTitle>
                      <CardDescription className="mt-0.5 truncate text-xs">
                        {l.email}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {!l.is_active && (
                        <Badge variant="destructive" className="gap-1">
                          <ShieldOff className="h-3 w-3" /> Disabled
                        </Badge>
                      )}
                      {l.class_level && (
                        <Badge variant="outline" className="gap-1">
                          <GraduationCap className="h-3 w-3" /> Class {l.class_level}
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="grid grid-cols-2 gap-2 text-center">
                    <Stat label="Quizzes taken" value={l.submissions_count} />
                    <Stat
                      label="Avg %"
                      value={
                        l.average_percentage !== null
                          ? `${l.average_percentage.toFixed(0)}%`
                          : "—"
                      }
                    />
                  </div>
                  <div className="mt-3 flex items-center justify-between text-xs text-(--color-muted-foreground)">
                    <span>Joined {formatDate(l.signup_date)}</span>
                    <span className="inline-flex items-center gap-1 text-(--color-primary)">
                      Open <ArrowRight className="h-3.5 w-3.5" />
                    </span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-(--color-border) bg-(--color-muted)/30 px-2 py-1.5">
      <div className="text-base font-semibold leading-tight">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-(--color-muted-foreground)">
        {label}
      </div>
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
