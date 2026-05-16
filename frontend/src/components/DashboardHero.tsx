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
 * Dhananjaya intro overlay — plays every time the dashboard mounts.
 *
 * The platform's first impression is a single cinematic moment: a
 * hand-painted Vidyārthi archer scene drifts in from a soft sand-toned
 * backdrop, holds while the welcome text fades in alongside, and the
 * whole thing dissolves away to reveal the dashboard underneath.
 *
 * Behaviour
 *   - On every dashboard mount (page refresh, route navigation back to
 *     /dashboard, sign-in): the overlay plays. There's no
 *     once-per-device gating — the user explicitly asked for it on
 *     every visit because they want the brand moment as a recurring
 *     ritual rather than a one-shot tutorial.
 *   - A small "Skip" affordance in the corner dismisses the overlay
 *     immediately for users in a hurry. No state is persisted across
 *     mounts, so the next dashboard visit shows the intro again.
 *
 * Role-aware copy
 *   The headline + one-line lead are tuned per role so the welcome
 *   feels personally addressed rather than generic.
 */

/** Total time the inner image animation runs (must match the keyframes
 *  in VidyarthiArcher). After this elapses we still hold the overlay
 *  for a short tail so any text fades that lag behind catch up before
 *  the container itself dismisses. */
const INNER_ANIMATION_MS = 7500;
const CONTAINER_FADE_MS = 1000;
const INTRO_TOTAL_MS = INNER_ANIMATION_MS + CONTAINER_FADE_MS;

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
  // Always start playing on mount. No localStorage gating — the
  // overlay is meant to be a recurring ritual, not a one-shot tutorial.
  // If we ever want to opt some users out (accessibility, repeat-
  // visitor preference) it'd be a per-account toggle, not localStorage.
  const [phase, setPhase] = useState<Phase>("playing");

  // Two timers drive the playing → fading → done transition. Cleanup
  // clears both on unmount so a fast route-change can't leave a
  // dangling timer behind. Both timers re-arm on every mount because
  // the entire effect runs whenever the component remounts.
  useEffect(() => {
    if (phase !== "playing") return;
    const fadeAt = window.setTimeout(() => setPhase("fading"), INNER_ANIMATION_MS);
    const doneAt = window.setTimeout(() => setPhase("done"), INTRO_TOTAL_MS);
    return () => {
      window.clearTimeout(fadeAt);
      window.clearTimeout(doneAt);
    };
  }, [phase]);

  if (phase === "done") return null;

  // Manual skip path: collapse to "fading" immediately so the user
  // gets the same graceful 1 s container fade rather than a jarring
  // hard-cut. The "done" timer is already armed and will unmount us
  // after the fade completes.
  const handleSkip = () => {
    if (phase === "playing") setPhase("fading");
  };

  return (
    <div
      // Full-bleed overlay. The backdrop is a warm sand tone that
      // matches the illustration so the image doesn't sit on a
      // jarringly-different surface.
      className={cn(
        "fixed inset-0 z-40 flex items-center justify-center",
        "bg-gradient-to-b from-[#F5EFE0] via-[#EFE6D2] to-[#E2D5B5]",
        "transition-opacity",
        phase === "fading" ? "opacity-0 pointer-events-none" : "opacity-100",
      )}
      style={{ transitionDuration: `${CONTAINER_FADE_MS}ms` }}
      aria-hidden={phase !== "playing"}
    >
      {/* Skip — small, unobtrusive, top-right. Users in a hurry can
          dismiss without the full 7.5 s playthrough. */}
      <button
        type="button"
        onClick={handleSkip}
        className="absolute right-5 top-5 rounded-md border border-[#C9BC97] bg-white/60 px-3 py-1.5 text-xs font-medium text-[#5C4A33] backdrop-blur transition hover:bg-white/80"
        aria-label="Skip the welcome animation and go straight to the dashboard"
      >
        Skip →
      </button>

      <div className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-6 text-center text-[#2A1F12]">
        {/* Top chrome: logo + brand name + tagline. Small, doesn't
            compete with the illustration for attention. */}
        <div className="flex items-center gap-3 opacity-0 animate-[fade-in_0.8s_ease-in-out_0.2s_forwards]">
          <BrandLogo size={48} />
          <div className="flex flex-col items-start leading-tight">
            <span className="font-display text-xl font-semibold tracking-tight">
              {BRAND_NAME}
            </span>
            <span className="font-display text-[10px] uppercase tracking-[0.22em] text-(--color-primary)">
              {BRAND_TAGLINE}
            </span>
          </div>
        </div>

        {/* The hero illustration — the centerpiece. Constrained to a
            comfortable max-width so it doesn't dominate huge screens. */}
        <div className="w-full max-w-4xl">
          <VidyarthiArcher playOnce />
        </div>

        {/* Welcome headline + role-aware lead. Fades in slightly
            after the image so the reader's eye lands on the picture
            first, then the text. */}
        <div className="space-y-3 opacity-0 animate-[fade-in_0.8s_ease-in-out_1.3s_forwards]">
          <h1 className="font-display text-2xl font-semibold tracking-tight md:text-4xl">
            {ROLE_HEADLINE[role]}
            {userName ? `, ${userName}` : ""}.
          </h1>
          <p className="mx-auto max-w-xl text-sm leading-relaxed text-[#5C4A33] md:text-base">
            {ROLE_INTRO[role]}
          </p>
          <p className="mx-auto max-w-xl text-xs italic text-[#7A6648] md:text-sm">
            &ldquo;{BRAND_PHILOSOPHY}&rdquo;
          </p>
        </div>
      </div>

      {/* One-off fade-in keyframe defined locally so we don't need to
          touch the global stylesheet. The two text blocks above use
          this same animation with staggered delays. */}
      <style>{`
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
