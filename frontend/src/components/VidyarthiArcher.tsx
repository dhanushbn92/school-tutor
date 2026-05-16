import { useId } from "react";
import { BRAND_ARROW_COLORS } from "@/lib/brand";
import { cn } from "@/lib/utils";

/**
 * A small inline-SVG scene: a vidyārthi (student) on the left drawing
 * a bow, a stack of concentric-ring targets on the right, and arrows
 * flying from one to the other on a repeating, slightly-staggered loop.
 *
 * The intent is to nail the platform's promise — repeated, deliberate
 * practice toward mastery — in a single glance. The arrows are coloured
 * with the brand palette so the animation also doubles as a logo accent.
 *
 * Built with pure CSS keyframes (no canvas / motion lib) so it adds
 * nothing to the JS bundle and stays smooth on low-end devices.
 *
 * Use it either:
 *   - inline as part of the persistent hero (compact prop), OR
 *   - in a one-time "first-visit" intro overlay (default).
 *
 * The intro variant is gated by a localStorage key elsewhere; this
 * component itself is purely presentational.
 */
export function VidyarthiArcher({
  compact = false,
  className,
}: {
  compact?: boolean;
  className?: string;
}) {
  const C = BRAND_ARROW_COLORS;
  // Stable arrow IDs so the per-archer CSS classes don't collide when
  // two animators are mounted on the same page (e.g. intro hero AND
  // the compact band). React's useId is the pure way to do this — the
  // value is deterministic across the tree for the same mount position.
  // Strip the React-prefix ":r0:" colons so the value is a legal CSS
  // identifier suffix.
  const uid = useId().replace(/[:]/g, "");

  // Inline scoped <style> — the keyframe set is small and we want it
  // to travel with the component so a page can import + drop it in
  // without touching the global stylesheet.
  const css = `
    @keyframes dh-fly-${uid} {
      0%   { transform: translateX(0)   translateY(0)    rotate(0deg); opacity: 0; }
      6%   { opacity: 1; }
      55%  { transform: translateX(180px) translateY(-2px) rotate(-2deg); opacity: 1; }
      95%  { transform: translateX(220px) translateY(0)    rotate(0deg); opacity: 1; }
      100% { transform: translateX(220px) translateY(0)    rotate(0deg); opacity: 0; }
    }
    @keyframes dh-bowstring-${uid} {
      0%, 60%, 100% { transform: scaleX(1); }
      30%           { transform: scaleX(0.78) translateX(-6px); }
    }
    @keyframes dh-pulse-${uid} {
      0%, 100% { transform: scale(1);   opacity: 1; }
      50%      { transform: scale(1.06); opacity: 0.85; }
    }
    .dh-arrow-${uid} {
      transform-origin: center;
      animation: dh-fly-${uid} 4s cubic-bezier(0.22, 0.61, 0.36, 1) infinite;
    }
    .dh-bowstring-${uid} {
      transform-origin: center;
      animation: dh-bowstring-${uid} 4s cubic-bezier(0.42, 0, 0.58, 1) infinite;
    }
    .dh-bullseye-${uid} {
      transform-origin: center;
      transform-box: fill-box;
      animation: dh-pulse-${uid} 4s ease-in-out infinite;
    }
  `;

  return (
    <div
      className={cn(
        "relative overflow-hidden",
        compact ? "h-32" : "h-48 md:h-56",
        className,
      )}
      aria-label="Animated archer practising at a target — the practice-makes-mastery motif"
    >
      <style>{css}</style>
      <svg
        viewBox="0 0 320 120"
        className="h-full w-full"
        preserveAspectRatio="xMidYMid meet"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Ground line — subtle, just to anchor the figures. */}
        <line
          x1="0" y1="105" x2="320" y2="105"
          stroke="currentColor"
          strokeOpacity="0.12"
          strokeWidth="1"
          strokeDasharray="4 4"
        />

        {/* === Vidyarthi (student archer) on the left === */}
        <g transform="translate(20 30)" stroke={C.navy} strokeLinecap="round" strokeLinejoin="round" fill="none">
          {/* Head */}
          <circle cx="20" cy="10" r="7" fill={C.navy} stroke="none" />
          {/* Torso */}
          <line x1="20" y1="17" x2="20" y2="48" strokeWidth="3" />
          {/* Front arm — pushing the bow */}
          <line x1="20" y1="26" x2="42" y2="32" strokeWidth="3" />
          {/* Back arm — pulling the bowstring */}
          <line x1="20" y1="26" x2="8"  y2="30" strokeWidth="3" />
          {/* Front leg — bent forward */}
          <line x1="20" y1="48" x2="32" y2="72" strokeWidth="3" />
          {/* Back leg — planted */}
          <line x1="20" y1="48" x2="12" y2="72" strokeWidth="3" />

          {/* Bow — quarter-arc to the right of the front hand */}
          <path
            d="M 42 14 Q 60 32 42 50"
            stroke={C.green}
            strokeWidth="3.5"
            fill="none"
          />
          {/* Bowstring — animated draw + release */}
          <line
            className={`dh-bowstring-${uid}`}
            x1="42" y1="14" x2="42" y2="50"
            stroke={C.navy}
            strokeOpacity="0.6"
            strokeWidth="1"
          />
        </g>

        {/* === Three arrows in flight, staggered === */}
        {[
          { color: C.orange,  y: 56, delay: "0s",   tilt: -0.5 },
          { color: C.magenta, y: 54, delay: "1.3s", tilt: 0 },
          { color: C.yellow,  y: 58, delay: "2.6s", tilt: 0.5 },
        ].map((a, i) => (
          <g
            key={i}
            className={`dh-arrow-${uid}`}
            transform={`translate(64 ${a.y}) rotate(${a.tilt})`}
            style={{ animationDelay: a.delay }}
          >
            {/* Shaft */}
            <line x1="0" y1="0" x2="22" y2="0" stroke={a.color} strokeWidth="2" strokeLinecap="round" />
            {/* Head — tiny triangle */}
            <polygon points="22,0 18,-3 18,3" fill={a.color} />
            {/* Fletching — two short feathers at the tail */}
            <line x1="0" y1="0" x2="-4" y2="-3" stroke={a.color} strokeWidth="1.5" strokeLinecap="round" />
            <line x1="0" y1="0" x2="-4" y2="3"  stroke={a.color} strokeWidth="1.5" strokeLinecap="round" />
          </g>
        ))}

        {/* === Target on the right === */}
        <g transform="translate(280 60)">
          {/* Stand */}
          <line x1="0" y1="20" x2="0" y2="45" stroke={C.gray} strokeWidth="2" strokeLinecap="round" />
          <line x1="-10" y1="45" x2="10" y2="45" stroke={C.gray} strokeWidth="2.5" strokeLinecap="round" />

          {/* Concentric rings — matches the multi-colour palette */}
          <circle cx="0" cy="0" r="26" fill={C.navy} />
          <circle cx="0" cy="0" r="20" fill="#FFFFFF" />
          <circle cx="0" cy="0" r="16" fill={C.purple} />
          <circle cx="0" cy="0" r="11" fill="#FFFFFF" />
          <circle cx="0" cy="0" r="7"  fill={C.orange} />
          {/* Bullseye — pulses on the same 4 s loop as the arrows */}
          <circle className={`dh-bullseye-${uid}`} cx="0" cy="0" r="3.5" fill={C.magenta} />
        </g>
      </svg>
    </div>
  );
}
