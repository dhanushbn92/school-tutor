import { useEffect, useState } from "react";
import { BrandLogo } from "@/components/BrandLogo";
import { VidyarthiArcher } from "@/components/VidyarthiArcher";
import {
  BRAND_NAME,
  BRAND_PHILOSOPHY,
  BRAND_TAGLINE,
} from "@/lib/brand";
import { cn } from "@/lib/utils";

/**
 * Dhananjaya intro overlay — shown once, then gone.
 *
 * The platform's first impression isn't a stat card; it's an animated
 * scene. A vidyārthi (student) draws a recurve bow and looses an arrow
 * across the screen to a target — the full draw → aim → release →
 * impact cycle plays exactly once, fades, and the dashboard takes over.
 *
 * Behaviour
 *   - On the FIRST visit per device (localStorage flag absent): the
 *     overlay mounts above the dashboard with a graceful fade-in,
 *     plays one 7.5 s archer cycle, fades out over 1 s, and unmounts.
 *     The flag is set when the overlay starts so a refresh mid-play
 *     doesn't replay it.
 *   - On every visit afterwards: the component renders nothing. The
 *     dashboard widgets show immediately, uncluttered.
 *
 * If a returning user wants the intro again they can clear the flag:
 *
 *     localStorage.removeItem("dhananjaya:dashboard:hero-intro-seen")
 *
 * Role-aware copy
 *   The headline + one-line lead are tuned per role so the welcome
 *   feels personally addressed rather than generic.
 */
const STORAGE_KEY = "dhananjaya:dashboard:hero-intro-seen";

/** Total time the overlay stays visible, in ms. Matches the archer
 *  scene's 7.5 s cycle plus a beat of "hold the moment" plus the
 *  fade-out duration so the user sees the arrow land before things
 *  start dissolving. */
const INTRO_PLAY_MS = 7500;
const INTRO_FADE_OUT_MS = 1000;
const INTRO_TOTAL_MS = INTRO_PLAY_MS + INTRO_FADE_OUT_MS;

type RoleKey = "learner" | "teacher" | "school_admin" | "platform_admin";

const ROLE_INTRO: Record<RoleKey, string> = {
  learner:
    "Draw your bow. Every quiz is another arrow toward mastery — and the target gets clearer the more you practise.",
  teacher:
    "Guide every shot. Build quizzes from the bank, watch mastery climb, and intervene exactly where it matters.",
  school_admin:
    "See the whole range. Weak topics, intervention notes, and class-wide trends — surfaced where you can act on them.",
  platform_admin:
    "Curate the practice ground. Author content, approve questions, and shape the catalog every learner draws from.",
};

const ROLE_HEADLINE: Record<RoleKey, string> = {
  learner: "Welcome to your range",
  teacher: "Welcome, teacher",
  school_admin: "Welcome to your school",
  platform_admin: "Welcome, curator",
};

type Phase = "playing" | "fading" | "done";

export function DashboardHero({
  role,
  userName,
}: {
  /** Resolved role bucket — keeps the hero copy single-source. */
  role: RoleKey;
  /** Optional first-name for the headline. */
  userName?: string;
}) {
  // Initial phase: skip entirely if we've already shown the intro on
  // this device. Reading localStorage in the useState initializer is
  // a one-time synchronous read; safe and lazy.
  const [phase, setPhase] = useState<Phase>(() => {
    if (typeof window === "undefined") return "done";
    try {
      return window.localStorage.getItem(STORAGE_KEY) === "1" ? "done" : "playing";
    } catch {
      // Private mode / disabled storage — fall through to "done" so we
      // never spam the intro every page load.
      return "done";
    }
  });

  // Record that the user has seen the intro AS SOON AS it starts. If
  // they refresh mid-play we don't want to replay; the intent is
  // strictly once-per-device. Wrapped in try/catch in case storage is
  // blocked (private mode, browser policy, etc.).
  useEffect(() => {
    if (phase !== "playing") return;
    try {
      window.localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      /* storage unavailable — the in-memory flag is enough for now */
    }
  }, [phase]);

  // Drive the playing → fading → done transition with two timers. We
  // store them on a ref-like array so the cleanup function can clear
  // both even if the component unmounts mid-transition.
  useEffect(() => {
    if (phase !== "playing") return;
    const fadeAt = window.setTimeout(() => setPhase("fading"), INTRO_PLAY_MS);
    const doneAt = window.setTimeout(() => setPhase("done"), INTRO_TOTAL_MS);
    return () => {
      window.clearTimeout(fadeAt);
      window.clearTimeout(doneAt);
    };
  }, [phase]);

  // After the intro has finished (whether by timeout or because the
  // user has seen it before), we render nothing — the dashboard
  // widgets get the full canvas. This is by design: the intro is a
  // delightful first impression, not permanent dashboard furniture.
  if (phase === "done") return null;

  return (
    <div
      className={cn(
        // Full-bleed overlay positioned inside the page's main scroll
        // container. We use position: fixed so the intro sits over
        // whatever the dashboard renders underneath. z-index above
        // the page header but below toasts / modals.
        "fixed inset-0 z-40 flex items-center justify-center bg-(--color-card)/95",
        "backdrop-blur-sm transition-opacity",
        phase === "fading" ? "opacity-0 pointer-events-none" : "opacity-100",
      )}
      style={{ transitionDuration: `${INTRO_FADE_OUT_MS}ms` }}
      aria-hidden={phase !== "playing"}
    >
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-6 px-6 text-center text-(--color-foreground)">
        <BrandLogo size={64} />
        <div className="space-y-2">
          <h1 className="font-display text-3xl font-semibold tracking-tight md:text-5xl">
            {ROLE_HEADLINE[role]}
            {userName ? `, ${userName}` : ""}.
          </h1>
          <p className="font-display text-xs uppercase tracking-[0.22em] text-(--color-primary)">
            {BRAND_NAME} &middot; {BRAND_TAGLINE}
          </p>
        </div>
        <div className="w-full max-w-3xl rounded-2xl border border-(--color-border) bg-(--color-card) shadow-sm">
          <VidyarthiArcher playOnce />
        </div>
        <p className="max-w-xl text-base leading-relaxed text-(--color-muted-foreground)">
          {ROLE_INTRO[role]}
        </p>
        <p className="max-w-xl text-sm italic text-(--color-foreground)/80">
          &ldquo;{BRAND_PHILOSOPHY}&rdquo;
        </p>
      </div>
    </div>
  );
}
