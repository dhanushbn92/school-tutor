import { useEffect, useState } from "react";

/**
 * Dashboard intro splash + persistent watermark.
 *
 * On every dashboard mount the Vidyārthi archer illustration takes
 * the whole screen — sidebar, header, content area, all covered. It
 * holds briefly, then the backdrop and the image both fade together:
 * the backdrop dissolves to nothing (revealing the sidebar + page),
 * while the image settles into a low-opacity watermark that lingers
 * quietly behind everything for the rest of the visit.
 *
 * Timing
 *   0 – 1.2 s    full opacity, screen-covering image + warm backdrop
 *   1.2 – 3.2 s  2-second cross-fade — backdrop → 0, image → 0.07
 *   3.2 s +      watermark holds at opacity 0.07 until the dashboard
 *                unmounts (route change, sign-out, etc.)
 *
 * On the next dashboard mount the whole cycle replays — explicitly
 * requested behaviour, not a tutorial flag.
 *
 * Implementation
 *   - `position: fixed inset-0 z-30` puts the splash above the
 *     sidebar (z-auto) and page header (z-20) but below the mobile
 *     sidebar drawer (z-40), so the drawer can still pop over the
 *     watermark if the user opens it.
 *   - `pointer-events-none` everywhere so the watermark never
 *     intercepts clicks. The dashboard underneath is interactive
 *     the instant the backdrop starts fading.
 *   - The image uses `object-contain` + max width / height so the
 *     full composition reads at any aspect ratio without cropping
 *     the archer or the target.
 *   - Backdrop colour matches the illustration's cream tone so the
 *     transition into the page feels like the picture is dissolving
 *     into mist rather than snapping off.
 */
const HOLD_MS = 1200;            // image + backdrop at full opacity
const FADE_MS = 2000;            // duration of the cross-fade
const WATERMARK_OPACITY = 0.07;  // resting opacity of the lingering image

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
  const [phase, setPhase] = useState<"holding" | "watermark">("holding");

  // After HOLD_MS we trigger the cross-fade. Both opacities transition
  // via CSS, so a single setState is all we need to drive the change.
  // Cleanup clears the timer to keep a fast route-change tidy.
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
      {/* Warm backdrop — covers the entire viewport during the hold,
          then fades to nothing on the cross-fade. Matches the
          illustration's cream paper tone so the dissolve feels
          painterly rather than a hard wipe. */}
      <div
        className="absolute inset-0 transition-opacity"
        style={{
          backgroundColor: "#F1E8D5",
          opacity: isWatermark ? 0 : 1,
          transitionDuration: `${FADE_MS}ms`,
          transitionTimingFunction: "ease-in-out",
        }}
      />

      {/* The illustration. Holds the centre of the screen at full
          opacity, then dims to a faint watermark that stays for the
          rest of the visit. Sized to fit within the viewport at any
          aspect ratio so the figure + target are never cropped. */}
      <img
        src="/vidyarthi-hero.png"
        alt=""
        className="absolute left-1/2 top-1/2 max-h-[85vh] max-w-[92vw] -translate-x-1/2 -translate-y-1/2 object-contain transition-opacity"
        style={{
          opacity: isWatermark ? WATERMARK_OPACITY : 1,
          transitionDuration: `${FADE_MS}ms`,
          transitionTimingFunction: "ease-in-out",
        }}
        onError={(e) => {
          // Missing asset → hide the element silently. The component
          // still mounts so the backdrop still does its thing, but
          // the page never shows a broken-image icon.
          (e.currentTarget as HTMLImageElement).style.display = "none";
        }}
      />
    </div>
  );
}
