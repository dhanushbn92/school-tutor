import { useEffect, useState } from "react";

/**
 * Dashboard intro splash.
 *
 * One image. One animation. One easing curve. Gone.
 *
 * Previous attempts layered a radial cream backdrop, a vignette
 * mask, a discrete "hold / fade / watermark" state machine, and
 * cross-fades between two opacity tracks. Each piece looked fine in
 * isolation; together they read as "staged" — the moving parts gave
 * away that something was happening.
 *
 * This version is the minimum that meets the brief:
 *
 *   - No backdrop. The dashboard is visible the whole time, behind
 *     the illustration. As the illustration fades, the dashboard
 *     gradually emerges — that's literally "fade out to background".
 *   - No state machine. A single CSS keyframe animation drives the
 *     entire 7-second cycle. Cubic-bezier easing on both ends keeps
 *     the motion buttery; no two-phase joins to give the artifice
 *     away.
 *   - A soft elliptical mask softens the image's own rectangular
 *     edges into the page so the picture dissolves into the
 *     dashboard rather than sitting on it like a cut-out.
 *
 * Timeline (7 s total)
 *   0.0 — 0.5 s   gentle fade in (0 → 1) so the picture appears,
 *                 it doesn't pop onto the screen
 *   0.5 — 2.0 s   hold at full opacity — the viewer has time to
 *                 actually take the scene in
 *   2.0 — 7.0 s   long, smooth fade out (1 → 0). The dashboard
 *                 widgets underneath become more legible every
 *                 frame; by the end the image is gone.
 *
 * Plays on every dashboard mount (page refresh, route navigation,
 * sign-in) — the user wants the practice ritual as a recurring
 * moment, not a one-shot tutorial.
 */
const ANIMATION_MS = 7000;

// Props are accepted but unused — kept on the type so the existing
// call-sites continue to compile without edits.
interface DashboardHeroProps {
  role?: string;
  userName?: string;
}

export function DashboardHero(_props: DashboardHeroProps) {
  void _props;
  const [done, setDone] = useState(false);

  // Single timer: unmount once the animation has completed. A small
  // buffer keeps us from yanking the element while the last frame
  // is still painting.
  useEffect(() => {
    const t = window.setTimeout(() => setDone(true), ANIMATION_MS + 200);
    return () => window.clearTimeout(t);
  }, []);

  if (done) return null;

  return (
    <div
      // Full-viewport container, but the image is anchored to the
      // TOP of the screen (items-start) rather than vertically
      // centred — that's where the user wants the practice ritual
      // to live. The bottom of the viewport stays free so the
      // dashboard widgets underneath are visible from the first
      // frame; the picture simply dissolves above them.
      // pointer-events-none means the dashboard is interactive from
      // frame zero — the splash is decoration, never a gate.
      className="pointer-events-none fixed inset-0 z-30 flex items-start justify-center pt-10 md:pt-16"
      aria-hidden="true"
    >
      <style>{`
        /* Single keyframe set drives the entire cycle. Stops at 7 %
           and 28 % give us a gentle fade-in and a brief hold without
           introducing a separate animation or state transition.
           The cubic-bezier curve keeps the motion smooth at every
           inflection point. */
        @keyframes dh-hero-fade {
          0%   { opacity: 0; }
          7%   { opacity: 1; }
          28%  { opacity: 1; }
          100% { opacity: 0; }
        }
        .dh-hero-image {
          animation: dh-hero-fade ${ANIMATION_MS}ms cubic-bezier(0.42, 0, 0.58, 1) forwards;
          will-change: opacity;
        }
        @media (prefers-reduced-motion: reduce) {
          /* Users who opted out of motion get a quick, simple fade
             rather than the full 7 s ritual. The splash is
             decorative; respecting the OS preference is the right
             call. */
          .dh-hero-image {
            animation-duration: 600ms;
          }
        }
      `}</style>
      <img
        src="/vidyarthi-hero.png"
        alt=""
        // Constrained to roughly the top half of the viewport
        // (max-h: 55vh) so the dashboard below stays in view while
        // the splash plays. Width caps at 70vmin so the image keeps
        // its breathing room on wide monitors.
        className="dh-hero-image block max-h-[55vh] max-w-[70vmin] object-contain"
        style={{
          // Soft elliptical mask. Full opacity through the heart of
          // the picture, fading smoothly to transparent at the
          // corners so the illustration dissolves into the dashboard
          // instead of stamping a hard rectangular edge onto it.
          maskImage:
            "radial-gradient(ellipse at center, rgba(0,0,0,1) 55%, rgba(0,0,0,0) 100%)",
          WebkitMaskImage:
            "radial-gradient(ellipse at center, rgba(0,0,0,1) 55%, rgba(0,0,0,0) 100%)",
        }}
        onError={(e) => {
          // Asset missing → render nothing rather than the browser's
          // broken-image icon.
          (e.currentTarget as HTMLImageElement).style.display = "none";
        }}
      />
    </div>
  );
}
