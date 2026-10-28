import { type ReactNode, useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  BookOpenText,
  Building2,
  ChartColumn,
  ChevronDown,
  ClipboardList,
  FolderOpen,
  House,
  LayoutDashboard,
  LogOut,
  Menu,
  NotebookPen,
  Layers,
  PlayCircle,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Target,
  Upload,
  Users,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BrandLogo } from "@/components/BrandLogo";
import { MascotCompanion } from "@/components/MascotCompanion";
import { TakeABreakNudge } from "@/components/TakeABreakNudge";
import { useAuth } from "@/lib/auth";
import { useMySchool } from "@/lib/queries";
import { MascotProvider } from "@/lib/MascotProvider";
import { BRAND_NAME } from "@/lib/brand";
import { cn } from "@/lib/utils";
import type { UserRole } from "@/lib/types";

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  roles: UserRole[];
}

const ROLE_LABEL: Record<UserRole, string> = {
  platform_admin: "Platform team",
  school_admin: "School administrator",
  teacher: "Teacher",
  student: "Student",
  individual_learner: "Self-learner",
  parent: "Parent / guardian",
};

const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: <LayoutDashboard className="h-4 w-4" />, roles: ["platform_admin", "school_admin", "teacher", "student", "individual_learner", "parent"] },
  { to: "/learn", label: "Learn", icon: <BookOpenText className="h-4 w-4" />, roles: ["platform_admin", "student", "individual_learner", "teacher", "school_admin"] },
  { to: "/videos", label: "Video lessons", icon: <PlayCircle className="h-4 w-4" />, roles: ["platform_admin", "student", "individual_learner", "teacher", "school_admin"] },
  { to: "/report-card", label: "Report card", icon: <ClipboardList className="h-4 w-4" />, roles: ["student", "individual_learner"] },
  { to: "/school-report", label: "School report", icon: <ClipboardList className="h-4 w-4" />, roles: ["school_admin"] },
  { to: "/sections", label: "Classes", icon: <Users className="h-4 w-4" />, roles: ["school_admin", "teacher"] },
  { to: "/assessments", label: "Assessments", icon: <ClipboardList className="h-4 w-4" />, roles: ["school_admin", "teacher", "student", "individual_learner"] },
  // Internal curation surface for the platform team only — schools and
  // teachers consume questions indirectly via assessments, not the bank.
  { to: "/question-bank", label: "Question bank", icon: <NotebookPen className="h-4 w-4" />, roles: ["platform_admin"] },
  // Content library is an authoring / curation surface. Learners reach the
  // material through Learn → chapter → artefacts, scoped to their (board, class).
  // Exposing the full library to learners leaked other classes and other
  // boards into the picker, so it's restricted to admin/teacher roles only.
  { to: "/content", label: "Content library", icon: <FolderOpen className="h-4 w-4" />, roles: ["platform_admin", "school_admin", "teacher"] },
  // Generation is a platform-team workflow; schools and individuals consume the catalog only.
  { to: "/generate", label: "Generate", icon: <Sparkles className="h-4 w-4" />, roles: ["platform_admin"] },
  // Bulk content ingest via a JSON bundle — lets external content creators
  // hand the platform team a single file per chapter.
  { to: "/content-bundle-upload", label: "Upload content", icon: <Upload className="h-4 w-4" />, roles: ["platform_admin"] },
  { to: "/curriculum", label: "Curriculum", icon: <BookOpenText className="h-4 w-4" />, roles: ["platform_admin", "school_admin", "teacher", "individual_learner"] },
  { to: "/manage", label: "Manage school", icon: <Building2 className="h-4 w-4" />, roles: ["school_admin"] },
  { to: "/tenants", label: "Tenants", icon: <Building2 className="h-4 w-4" />, roles: ["platform_admin"] },
  { to: "/ai-chat-admin", label: "AI tutor", icon: <ShieldCheck className="h-4 w-4" />, roles: ["platform_admin"] },
  { to: "/quick-quiz", label: "Start a quiz", icon: <Sparkles className="h-4 w-4" />, roles: ["individual_learner", "student"] },
  // Stage 2 of the child-centric roadmap — "things I got wrong" review surface.
  { to: "/me/mistakes", label: "Review mistakes", icon: <RotateCcw className="h-4 w-4" />, roles: ["individual_learner", "student"] },
  // Stage 7 of the child-centric roadmap — speedrun / surprise me / flashcards hub.
  { to: "/practice", label: "Practice variety", icon: <Layers className="h-4 w-4" />, roles: ["individual_learner", "student"] },
];

export function Shell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  // Platform admins aren't bound to a single school; skip the fetch for them.
  const schoolQ = useMySchool(Boolean(user) && user?.role !== "platform_admin");
  if (!user) return null;

  const items = NAV.filter((item) => item.roles.includes(user.role));
  const tenantName =
    user.role === "platform_admin"
      ? "Platform"
      : schoolQ.data?.brand_name?.trim() || schoolQ.data?.name || "Your school";
  const tenantSubtitle =
    user.role === "platform_admin"
      ? "Catalog curators"
      : schoolQ.data?.is_personal
        ? "Personal account"
        : schoolQ.data?.board || "School";

  // Learners and teachers get a top tab menu (and a bottom tab bar on phones)
  // instead of the sidebar the admin roles use.
  if (
    user.role === "student" ||
    user.role === "individual_learner" ||
    user.role === "teacher"
  ) {
    return (
      <TopNavLayout
        items={items}
        user={user}
        onLogout={() => {
          logout();
          navigate("/login", { replace: true });
        }}
        tenantName={tenantName}
        tenantSubtitle={tenantSubtitle}
      />
    );
  }

  return (
    <div className="flex min-h-screen bg-(--color-muted)">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 flex-col border-r border-(--color-border) bg-(--color-card) md:flex">
        <SidebarContent items={items} role={user.role} tenantName={tenantName} tenantSubtitle={tenantSubtitle} />
      </aside>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute left-0 top-0 flex h-full w-64 flex-col border-r border-(--color-border) bg-(--color-card) shadow-lg">
            <div className="flex items-center justify-end p-3">
              <Button size="icon" variant="ghost" onClick={() => setMobileOpen(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <SidebarContent
              items={items}
              role={user.role}
              tenantName={tenantName}
              tenantSubtitle={tenantSubtitle}
              onNavigate={() => setMobileOpen(false)}
            />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-(--color-border) bg-(--color-card) px-4 md:px-6">
          <div className="flex items-center gap-2 md:gap-4">
            <Button
              size="icon"
              variant="ghost"
              className="md:hidden"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="h-4 w-4" />
            </Button>
            <div className="md:hidden flex items-center gap-2">
              <BrandLogo size={22} />
              <span className="text-sm font-semibold">{BRAND_NAME}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <div className="text-sm font-medium leading-tight">{user.full_name}</div>
              <div className="text-xs text-(--color-muted-foreground)">{user.email}</div>
            </div>
            <div className="h-9 w-9 rounded-full bg-(--color-primary) text-(--color-primary-foreground) flex items-center justify-center text-sm font-medium">
              {initials(user.full_name)}
            </div>
            <Button
              size="icon"
              variant="ghost"
              title="Sign out"
              onClick={() => {
                logout();
                navigate("/login", { replace: true });
              }}
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 overflow-x-clip p-4 md:p-8">
          {/* Stage 5 — wrap the entire learner-facing page tree in
              the MascotProvider so any page can dispatch reactions
              through useMascot(). The provider is cheap (a single
              useState + memo) so we mount it unconditionally for all
              roles; MascotCompanion itself gates the actual render
              to learner roles only. */}
          <MascotProvider>
            <Outlet />
            <MascotCompanion />
            {/* Stage 10 — gentle "take a break" prompt after 20 min
                of continuous practice. Self-gated to learners and
                to learners who haven't disabled the nudge. */}
            <TakeABreakNudge />
          </MascotProvider>
        </main>
      </div>
    </div>
  );
}

interface Tab {
  to: string;
  label: string;
  /** Shorter label for the phone bottom bar. */
  short: string;
  icon: ReactNode;
  end?: boolean;
}

const tabLink = ({ isActive }: { isActive: boolean }) =>
  cn(
    "rounded-full px-3.5 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-(--color-primary)/10 font-semibold text-(--color-primary)"
      : "text-(--color-muted-foreground) hover:bg-(--color-primary)/8 hover:text-(--color-foreground)",
  );

/**
 * The top-menu layout for learners and teachers: a top bar with five tabs and
 * a "More" menu for the rest; on a phone the same five tabs sit in a bottom
 * bar and the full list is in the menu drawer.
 */
function TopNavLayout({
  items,
  user,
  onLogout,
  tenantName,
  tenantSubtitle,
}: {
  items: NavItem[];
  user: { full_name: string; email: string; role: UserRole };
  onLogout: () => void;
  tenantName: string;
  tenantSubtitle: string;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

  // Close the More menu on an outside click or Escape.
  useEffect(() => {
    if (!moreOpen) return;
    const onDown = (e: MouseEvent) => {
      if (!moreRef.current?.contains(e.target as Node)) setMoreOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMoreOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [moreOpen]);

  // School students take teacher-assigned quizzes (Assessments); self-learners
  // start their own.
  const quizzesTo = user.role === "student" ? "/assessments" : "/quick-quiz";
  const home: Tab = { to: "/", label: "Home", short: "Home", icon: <House className="h-5 w-5" />, end: true };
  const learn: Tab = { to: "/learn", label: "Learn", short: "Learn", icon: <BookOpenText className="h-5 w-5" /> };
  const tabs: Tab[] =
    user.role === "teacher"
      ? [
          home,
          { to: "/sections", label: "My classes", short: "Classes", icon: <Users className="h-5 w-5" /> },
          { to: "/assessments", label: "Quizzes", short: "Quizzes", icon: <ClipboardList className="h-5 w-5" /> },
          learn,
          { to: "/content", label: "Content library", short: "Library", icon: <FolderOpen className="h-5 w-5" /> },
        ]
      : [
          home,
          learn,
          { to: "/videos", label: "Video lessons", short: "Videos", icon: <PlayCircle className="h-5 w-5" /> },
          { to: quizzesTo, label: "Quizzes", short: "Quiz", icon: <Target className="h-5 w-5" /> },
          { to: "/report-card", label: "Report card", short: "Progress", icon: <ChartColumn className="h-5 w-5" /> },
        ];
  const tabPaths = new Set(tabs.map((t) => t.to));
  const more = items.filter((i) => !tabPaths.has(i.to));

  return (
    <div className="flex min-h-screen flex-col bg-[color-mix(in_oklab,var(--color-primary)_6%,var(--color-background))]">
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 flex h-full w-64 flex-col border-r border-(--color-border) bg-(--color-card) shadow-lg">
            <div className="flex items-center justify-end p-3">
              <Button size="icon" variant="ghost" aria-label="Close menu" onClick={() => setMobileOpen(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <SidebarContent
              items={items}
              role={user.role}
              tenantName={tenantName}
              tenantSubtitle={tenantSubtitle}
              onNavigate={() => setMobileOpen(false)}
            />
          </aside>
        </div>
      )}

      <header className="sticky top-0 z-30 border-b border-(--color-border) bg-(--color-card)">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5 md:gap-6 md:px-6">
          <Button
            size="icon"
            variant="ghost"
            className="md:hidden"
            aria-label="Open menu"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <NavLink to="/" className="flex items-center gap-2.5">
            <BrandLogo size={36} />
            <span className="font-display text-lg font-bold tracking-tight">{BRAND_NAME}</span>
          </NavLink>

          <nav aria-label="Main" className="hidden flex-1 items-center gap-1 md:flex">
            {tabs.map((t) => (
              <NavLink key={t.to} to={t.to} end={t.end} className={tabLink}>
                {t.label}
              </NavLink>
            ))}
            {more.length > 0 && (
              <div ref={moreRef} className="relative">
                <button
                  type="button"
                  aria-expanded={moreOpen}
                  aria-haspopup="true"
                  onClick={() => setMoreOpen((v) => !v)}
                  className="flex items-center gap-1 rounded-full px-3.5 py-2 text-sm font-medium text-(--color-muted-foreground) transition-colors hover:bg-(--color-primary)/8 hover:text-(--color-foreground)"
                >
                  More
                  <ChevronDown
                    className={cn("h-4 w-4 transition-transform", moreOpen && "rotate-180")}
                    aria-hidden
                  />
                </button>
                {moreOpen && (
                  <div className="absolute left-0 top-full z-40 mt-2 w-56 rounded-2xl border border-(--color-border) bg-(--color-card) p-1.5 shadow-lg">
                    {more.map((item) => (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        onClick={() => setMoreOpen(false)}
                        className={({ isActive }) =>
                          cn(
                            "flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm hover:bg-(--color-muted)",
                            isActive && "bg-(--color-primary)/10 font-semibold text-(--color-primary)",
                          )
                        }
                      >
                        {item.icon}
                        {item.label}
                      </NavLink>
                    ))}
                  </div>
                )}
              </div>
            )}
          </nav>

          <div className="ml-auto flex items-center gap-1.5">
            <div
              title={`${user.full_name} (${user.email})`}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-(--color-primary) text-sm font-semibold text-(--color-primary-foreground)"
            >
              {initials(user.full_name)}
            </div>
            <Button size="icon" variant="ghost" title="Sign out" aria-label="Sign out" onClick={onLogout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 overflow-x-clip p-4 pb-24 md:p-8 md:pb-8">
        <MascotProvider>
          <Outlet />
          <MascotCompanion />
          <TakeABreakNudge />
        </MascotProvider>
      </main>

      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-30 flex border-t border-(--color-border) bg-(--color-card) px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-1.5 md:hidden"
      >
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) =>
              cn(
                "flex min-h-12 flex-1 flex-col items-center justify-center gap-0.5 rounded-xl text-xs",
                isActive ? "font-semibold text-(--color-primary)" : "text-(--color-muted-foreground)",
              )
            }
          >
            {t.icon}
            {t.short}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

function SidebarContent({
  items,
  role,
  tenantName,
  tenantSubtitle,
  onNavigate,
}: {
  items: NavItem[];
  role: UserRole;
  tenantName: string;
  tenantSubtitle: string;
  onNavigate?: () => void;
}) {
  return (
    <>
      <div className="flex items-center gap-2.5 px-5 py-4">
        <BrandLogo size={32} />
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold tracking-tight">{tenantName}</span>
          <span className="text-[11px] text-(--color-muted-foreground)">
            {tenantSubtitle} &middot; on {BRAND_NAME}
          </span>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 px-2 pb-4">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            onClick={() => onNavigate?.()}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm text-(--color-foreground) transition-colors",
                "hover:bg-(--color-muted)",
                isActive && "bg-(--color-muted) font-medium text-(--color-primary)",
              )
            }
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-(--color-border) p-4">
        <Badge variant="outline" className="gap-1">
          <ShieldCheck className="h-3 w-3" />
          {ROLE_LABEL[role]}
        </Badge>
      </div>
    </>
  );
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}
