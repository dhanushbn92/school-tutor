import { type ReactNode, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  BookOpenText,
  Building2,
  ClipboardList,
  FolderOpen,
  LayoutDashboard,
  LogOut,
  Menu,
  NotebookPen,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BrandLogo } from "@/components/BrandLogo";
import { useAuth } from "@/lib/auth";
import { useMySchool } from "@/lib/queries";
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
};

const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: <LayoutDashboard className="h-4 w-4" />, roles: ["platform_admin", "school_admin", "teacher", "student", "individual_learner"] },
  { to: "/learn", label: "Learn", icon: <BookOpenText className="h-4 w-4" />, roles: ["platform_admin", "student", "individual_learner", "teacher", "school_admin"] },
  { to: "/report-card", label: "Report card", icon: <ClipboardList className="h-4 w-4" />, roles: ["student", "individual_learner"] },
  { to: "/school-report", label: "School report", icon: <ClipboardList className="h-4 w-4" />, roles: ["school_admin"] },
  { to: "/sections", label: "Classes", icon: <Users className="h-4 w-4" />, roles: ["school_admin", "teacher"] },
  { to: "/assessments", label: "Assessments", icon: <ClipboardList className="h-4 w-4" />, roles: ["school_admin", "teacher", "student", "individual_learner"] },
  // Internal curation surface for the platform team only — schools and
  // teachers consume questions indirectly via assessments, not the bank.
  { to: "/question-bank", label: "Question bank", icon: <NotebookPen className="h-4 w-4" />, roles: ["platform_admin"] },
  { to: "/content", label: "Content library", icon: <FolderOpen className="h-4 w-4" />, roles: ["platform_admin", "school_admin", "teacher", "individual_learner"] },
  // Generation is a platform-team workflow; schools and individuals consume the catalog only.
  { to: "/generate", label: "Generate", icon: <Sparkles className="h-4 w-4" />, roles: ["platform_admin"] },
  { to: "/curriculum", label: "Curriculum", icon: <BookOpenText className="h-4 w-4" />, roles: ["platform_admin", "school_admin", "teacher", "individual_learner"] },
  { to: "/manage", label: "Manage school", icon: <Building2 className="h-4 w-4" />, roles: ["school_admin"] },
  { to: "/tenants", label: "Tenants", icon: <Building2 className="h-4 w-4" />, roles: ["platform_admin"] },
  { to: "/ai-chat-admin", label: "AI tutor", icon: <ShieldCheck className="h-4 w-4" />, roles: ["platform_admin"] },
  { to: "/quick-quiz", label: "Start a quiz", icon: <Sparkles className="h-4 w-4" />, roles: ["individual_learner", "student"] },
  // Stage 2 of the child-centric roadmap — "things I got wrong" review surface.
  { to: "/me/mistakes", label: "Review mistakes", icon: <RotateCcw className="h-4 w-4" />, roles: ["individual_learner", "student"] },
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

      <div className="flex flex-1 flex-col">
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
            <div className="text-right">
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
        <main className="mx-auto w-full max-w-7xl flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
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
