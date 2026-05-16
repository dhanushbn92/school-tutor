import { useEffect, useState } from "react";

/**
 * Dashboard intro splash + persistent watermark.
 *
 * On every dashboard mount the Vidyārthi archer illustration appears
 * as a soft circular vignette in the centre of the screen — the
 * archer is at the heart of the bright spot, and the picture fades
 * smoothly to transparent toward the edges (no hard rectangular
 * border). It holds briefly, then cross-fades: the cream backdrop
 * dissolves to nothing (revealing the dashboard + sidebar) and the
 * image settles into a faint full-screen watermark that lingers
 * quietly for the rest of the visit.
 *
 * Timing
 *   0 – 1.2 s    full-opacity circular vignette + cream backdrop
 *   1.2 – 3.2 s  2-second cross-fade — backdrop → 0, image → 0.07
 *   3.2 s +      watermark holds until the dashboard unmounts
 *
 * The circular focus
 *   - The archer in the source illustration sits at roughly 23% from
 *     the left of the canvas. To put him at the centre of the
 *     circular crop we shift the image horizontally with translate()
 *     while keeping height filling the container, then clip with
 *     overflow + border-radius.
 *   - On top of that we apply a radial-gradient mask: full opacity
 *     out to 42% of the radius, falling to zero at the edge. The
 *     result is a vignette with no hard outline — the picture
 *     dissolves softly into the cream backdrop.
 *
 * Plays on every dashboard mount (page refresh, route navigation
 * back to /dashboard, sign-in). No localStorage gating — the user
 * wants this as a recurring brand moment, not a one-shot tutorial.
 */
const HOLD_MS = 1200;
const FADE_MS = 2000;
const WATERMARK_OPACITY = 0.07;
/** Horizontal shift applied to the image inside its circular frame
 *  so the archer (~23% from the left of the source illustration)
 *  lands at the centre of the visible circle. */
const ARCHER_SHIFT_PCT = -23;
/** CSS radial-gradient mask. Tuned so the bright core comfortably
 *  contains the archer, with a generous soft falloff to the edges
 *  so the vignette never feels hard. Two prefixes for cross-browser
 *  coverage (Chromium/Safari accept -webkit, Firefox accepts the
 *  unprefixed property). */
const VIGNETTE_MASK =
  "radial-gradient(circle at 50% 50%, rgba(0,0,0,1) 42%, rgba(0,0,0,0.55) 72%, rgba(0,0,0,0) 100%)";

// Props are accepted but unused — kept on the type so the existing
// call-sites continue to compile without edits.
interface DashboardHeroProps {
  role?: string;
  userName?: string;
}

export function DashboardHero(_props: DashboardHeroProps) {
  void _props;
  const [phase, setPhase] = useState<"holding" | "watermark">("holding");

  useEffect(() => {
    const t = window.setTimeout(() => setPhase("watermark"), HOLD_MS);
    return () => window.clearTimeout(t);
  }, []);

  const isWatermark = phase === "watermark";

  return (
    <div
      className="pointer-events-none fixed inset-0 z-30"
      aria-hidden="true"
    >
      {/* Warm backdrop — a radial cream gradient rather than a flat
          wash. Solid at the centre where the archer image sits, then
          fading out toward the screen edges so the dashboard peeks
          through at the corners from the very first frame. The
          dashboard becomes more visible the further you look from
          centre; in the centre the cream hides everything underneath.
          On the cross-fade the whole backdrop dissolves to nothing. */}
      <div
        className="absolute inset-0 transition-opacity"
        style={{
          background:
            "radial-gradient(circle at center, " +
            "#F1E8D5 0%, " +
            "#F1E8D5 30%, " +
            "rgba(241,232,213, 0.85) 50%, " +
            "rgba(241,232,213, 0.5) 70%, " +
            "rgba(241,232,213, 0) 100%)",
          opacity: isWatermark ? 0 : 1,
          transitionDuration: `${FADE_MS}ms`,
          transitionTimingFunction: "ease-in-out",
        }}
      />

      {/* Circular vignette frame. Centred on the viewport, sized
          relative to the smaller viewport dimension so it scales
          gracefully on mobile and large monitors alike. The radial
          mask gives it a soft circular falloff with no hard rim. */}
      <div
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 overflow-hidden transition-opacity"
        style={{
          width: "min(70vmin, 640px)",
          height: "min(70vmin, 640px)",
          opacity: isWatermark ? WATERMARK_OPACITY : 1,
          transitionDuration: `${FADE_MS}ms`,
          transitionTimingFunction: "ease-in-out",
          maskImage: VIGNETTE_MASK,
          WebkitMaskImage: VIGNETTE_MASK,
        }}
      >
        {/* The image is positioned inside the circle with a horizontal
            shift so the archer (left-of-centre in the source) lands at
            the visual centre of the bright spot. Height fills the
            container; width is allowed to overflow either side and is
            clipped by the parent's overflow-hidden. */}
        <img
          src="/vidyarthi-hero.png"
          alt=""
          className="absolute h-full w-auto max-w-none"
          style={{
            left: "50%",
            top: "50%",
            transform: `translate(${ARCHER_SHIFT_PCT}%, -50%)`,
          }}
          onError={(e) => {
            // Missing asset → hide silently rather than show the
            // browser's broken-image icon.
            (e.currentTarget as HTMLImageElement).style.display = "none";
          }}
        />
      </div>
    </div>
  );
}
