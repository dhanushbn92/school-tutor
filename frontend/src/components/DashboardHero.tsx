import { useEffect, useState } from "react";

/**
 * Dashboard intro splash.
 *
 * As simple as it sounds: the Vidyārthi archer illustration appears
 * inline at the top of the dashboard, holds briefly, fades out over
 * a couple of seconds, and unmounts. That's the whole feature.
 *
 * What this is NOT:
 *   - Not a full-screen overlay.
 *   - Not a separate page or route.
 *   - Not a card, hero panel, headline, or quote — no chrome at all.
 *
 * The image lives at `/vidyarthi-hero.png` (public folder). If the
 * asset is missing the <img> hides itself via onError so the page
 * never shows a broken-image icon.
 *
 * Plays every time the dashboard mounts — a refresh or a route
 * change back to /dashboard replays it. No localStorage gating.
 */
const HOLD_MS = 1200;     // time the image stays at full opacity
const FADE_MS = 2000;     // duration of the fade-out
const TOTAL_MS = HOLD_MS + FADE_MS + 200; // small buffer before unmount

// Props are accepted but unused at the moment — kept on the type so
// the existing call-sites in Dashboard.tsx + LearnerDashboard.tsx
// continue to compile without edits. If we ever want a role-aware
// splash again, the data is already being passed in.
interface DashboardHeroProps {
  role?: string;
  userName?: string;
}

export function DashboardHero(_props: DashboardHeroProps) {
  // _props is intentionally ignored; see the comment on DashboardHeroProps.
  void _props;
  const [phase, setPhase] = useState<"holding" | "fading" | "done">("holding");

  // Two staggered timers drive the splash forward. Cleanup clears
  // both so a fast route-change can't leave a dangling timer.
  useEffect(() => {
    const fadeAt = window.setTimeout(() => setPhase("fading"), HOLD_MS);
    const doneAt = window.setTimeout(() => setPhase("done"), TOTAL_MS);
    return () => {
      window.clearTimeout(fadeAt);
      window.clearTimeout(doneAt);
    };
  }, []);

  if (phase === "done") return null;

  return (
    <div
      // Inline at the top of the dashboard, full width of the page
      // gutter, generous max height so the image reads but doesn't
      // dominate the whole screen on big monitors.
      className="mb-6 w-full overflow-hidden transition-opacity"
      style={{
        opacity: phase === "fading" ? 0 : 1,
        transitionDuration: `${FADE_MS}ms`,
        transitionTimingFunction: "ease-in-out",
      }}
      aria-hidden={phase !== "holding"}
    >
      <img
        src="/vidyarthi-hero.png"
        alt=""
        className="mx-auto block max-h-[420px] w-full object-contain"
        onError={(e) => {
          // Missing asset → render nothing rather than the browser's
          // broken-image placeholder.
          (e.currentTarget as HTMLImageElement).style.display = "none";
        }}
      />
    </div>
  );
}
