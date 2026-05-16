import { useEffect, useState } from "react";
import { Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BrandLogo } from "@/components/BrandLogo";
import { VidyarthiArcher } from "@/components/VidyarthiArcher";
import {
  BRAND_NAME,
  BRAND_PHILOSOPHY,
  BRAND_QUOTES,
  BRAND_TAGLINE,
} from "@/lib/brand";
import { cn } from "@/lib/utils";

/**
 * The dashboard's first-impression panel: brand identity + practice
 * philosophy + a small archer animation. Shown above the existing
 * stat cards so the platform's personality reads at a glance before
 * the user dives into operational widgets.
 *
 * Two presentations:
 *   - First visit (no localStorage flag): a generous hero with the
 *     full archer scene, a one-line CTA explaining what the platform
 *     is for, and a dismiss control that sets the flag.
 *   - Repeat visits: a compact band — logo, rotating quote, and a
 *     slim archer strip — that takes much less vertical room.
 *
 * The localStorage key is namespaced under `dhananjaya:` so it doesn't
 * collide with any existing per-account preferences and is easy to
 * grep / reset during onboarding tests.
 *
 * Role-aware copy: each role gets a one-line context lead so the hero
 * feels personally addressed rather than generic. Learners see a
 * "draw your bow" framing; teachers see a "guide every shot" framing;
 * platform admins see a curation framing.
 */
const STORAGE_KEY = "dhananjaya:dashboard:hero-intro-seen";

type RoleKey = "learner" | "teacher" | "school_admin" | "platform_admin";

const ROLE_INTRO: Record<RoleKey, string> = {
  learner:
    "Draw your bow. Every quiz is another arrow toward mastery — and the target gets clearer the more you practise.",
  teacher:
    "Guide every shot. Build quizzes from the bank, watch mastery climb, and intervene exactly where it matters.",
  school_admin:
    "See the whole range. Weak topics, intervention notes, and class-wide trends — surfaced where you can act on them.",
  platform_admin:
    "Curate the practice ground. Author content, approve questions, and shape the catalog that every learner draws from.",
};

const ROLE_HEADLINE: Record<RoleKey, string> = {
  learner: "Welcome to your range",
  teacher: "Welcome, teacher",
  school_admin: "Welcome to your school",
  platform_admin: "Welcome, curator",
};

export function DashboardHero({
  role,
  userName,
}: {
  /** Resolved role bucket — keeps the hero copy single-source. */
  role: RoleKey;
  /** Optional first-name for the headline. */
  userName?: string;
}) {
  const [introSeen, setIntroSeen] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    try {
      return window.localStorage.getItem(STORAGE_KEY) === "1";
    } catch {
      // Private mode / disabled storage — fall back to "already seen"
      // so we don't spam every page load with the intro.
      return true;
    }
  });

  // Rotate the quotes on the compact band. Stable per-mount index so
  // a reload picks a new one without thrashing every render. useState's
  // lazy initializer is the pure-render way to make a one-time random
  // pick (the callback runs exactly once on mount, off the render path).
  const [quote] = useState(() =>
    BRAND_QUOTES[Math.floor(Math.random() * BRAND_QUOTES.length)],
  );

  function dismissIntro() {
    setIntroSeen(true);
    try {
      window.localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // Storage may be unavailable; the in-memory flip is enough for
      // this session.
    }
  }

  // Auto-dismiss the intro after 18s so a learner who walks away from
  // the screen still lands on the working dashboard when they return.
  useEffect(() => {
    if (introSeen) return;
    const t = window.setTimeout(dismissIntro, 18_000);
    return () => window.clearTimeout(t);
    // dismissIntro is defined inline above; its deps are stable, so
    // omitting it from the dep array is safe and avoids re-arming the
    // timer on every render.
  }, [introSeen]);

  if (!introSeen) {
    return <IntroPanel role={role} userName={userName} onDismiss={dismissIntro} />;
  }
  return <CompactBand role={role} quote={quote} />;
}

/**
 * First-visit hero. Big, generous, with the archer animation centred.
 * One CTA: dismiss. Auto-dismisses after 18 s.
 */
function IntroPanel({
  role,
  userName,
  onDismiss,
}: {
  role: RoleKey;
  userName?: string;
  onDismiss: () => void;
}) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border border-(--color-border) bg-gradient-to-br",
        // Subtle brand-flavoured gradient — navy on the left fading to
        // a warm cream on the right so the colourful arrows pop.
        "from-(--color-card) via-(--color-card) to-(--color-muted)",
        "p-6 md:p-8 mb-6 text-(--color-foreground)",
      )}
    >
      {/* Dismiss button — corner placement keeps it out of the reading
          path but always reachable. */}
      <button
        type="button"
        onClick={onDismiss}
        className="absolute right-3 top-3 rounded-md p-1 text-(--color-muted-foreground) hover:bg-(--color-muted) hover:text-(--color-foreground)"
        aria-label="Dismiss the welcome panel"
      >
        <X className="h-4 w-4" />
      </button>

      <div className="grid items-center gap-6 lg:grid-cols-[1fr_minmax(0,1.2fr)]">
        <div className="space-y-4">
          <BrandLogo size={56} />
          <div>
            <h1 className="font-display text-3xl font-semibold tracking-tight md:text-4xl">
              {ROLE_HEADLINE[role]}
              {userName ? `, ${userName}` : ""}.
            </h1>
            <p className="mt-1 font-display text-sm uppercase tracking-[0.18em] text-(--color-primary)">
              {BRAND_NAME} &middot; {BRAND_TAGLINE}
            </p>
          </div>
          <p className="max-w-prose text-base leading-relaxed text-(--color-muted-foreground)">
            {ROLE_INTRO[role]}
          </p>
          <p className="max-w-prose text-sm italic leading-relaxed text-(--color-foreground)/80">
            &ldquo;{BRAND_PHILOSOPHY}&rdquo;
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button onClick={onDismiss} size="sm">
              <Sparkles className="h-4 w-4" /> Start exploring
            </Button>
            <span className="self-center text-xs text-(--color-muted-foreground)">
              This welcome shows only on your first visit.
            </span>
          </div>
        </div>

        <div className="relative">
          <VidyarthiArcher className="text-(--color-foreground)" />
        </div>
      </div>
    </div>
  );
}

/**
 * Repeat-visit band. A slim row that keeps the brand visible without
 * eating screen real estate. The rotating quote is a quiet reminder
 * of the platform's practice ethos.
 */
function CompactBand({
  role,
  quote,
}: {
  role: RoleKey;
  quote: { text: string; attribution?: string };
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 rounded-lg border border-(--color-border) bg-(--color-card) p-4 md:flex-row md:items-center md:justify-between md:gap-6">
      <div className="flex items-start gap-3">
        <BrandLogo size={36} />
        <div className="space-y-0.5">
          <p className="font-display text-sm font-semibold tracking-tight">
            {BRAND_NAME} &middot;{" "}
            <span className="text-(--color-muted-foreground)">{BRAND_TAGLINE}</span>
          </p>
          <p className="text-xs italic text-(--color-muted-foreground)">
            &ldquo;{quote.text}&rdquo;
            {quote.attribution && (
              <span className="ml-1 not-italic">— {quote.attribution}</span>
            )}
          </p>
        </div>
      </div>
      {/* Compact archer strip — present on every visit so the brand
          motif is reinforced, but small enough not to dominate. The
          role prop is accepted here for future per-role tweaks; for now
          we render the same strip everywhere. */}
      <VidyarthiArcher compact className="hidden w-[260px] flex-shrink-0 text-(--color-foreground) md:block" />
      {/* `role` is destructured for the API consumer signature even
          though the strip is identical for now. */}
      <span className="sr-only">Viewing as {role}</span>
    </div>
  );
}
