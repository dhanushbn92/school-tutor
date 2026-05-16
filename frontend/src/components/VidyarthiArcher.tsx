import { useId } from "react";
import { cn } from "@/lib/utils";

/**
 * The Vidyārthi archer intro scene.
 *
 * The visual is a hand-painted illustration shipped as a static asset
 * (`/vidyarthi-hero.png` in the public folder). Hand-drawing this
 * scene in SVG produced amateur results; using a proper illustration
 * is the right answer. The component's only job is to display the
 * image with a cinematic fade-in / hold / fade-out cycle.
 *
 * Timing (7.5 s, runs once when playOnce is true)
 *   0.0–1.5 s   fade in with a subtle scale-down + de-blur, so the
 *               scene resolves like a focusing camera
 *   1.5–5.0 s   hold at full opacity, no movement — the viewer
 *               actually gets to enjoy the image
 *   5.0–7.5 s   slow, graceful fade-out over 2.5 s
 *
 * The parent overlay (DashboardHero) controls when this component
 * mounts / unmounts. The fade values here drive the inner image; the
 * parent just keeps the container around long enough for the cycle
 * to complete.
 *
 * If the asset hasn't been placed yet, the broken-image alt text
 * renders so the page still tells the story. Swap in a real image
 * and the scene comes alive without any code change.
 */
export function VidyarthiArcher({
  playOnce = false,
  className,
}: {
  /** When true, run the fade cycle exactly once and end at opacity 0
   *  so the parent can unmount us cleanly. Looping mode is kept for
   *  future per-page accents that might want a perpetual ambient
   *  archer somewhere small. */
  playOnce?: boolean;
  className?: string;
}) {
  // useId gives a deterministic, mount-stable suffix so two archers on
  // the same page wouldn't share keyframes (which would coalesce their
  // timelines). Strip React's ":r0:" colons so the value is a legal
  // CSS identifier.
  const uid = useId().replace(/[:]/g, "");

  // The keyframes do all the work. Cubic-bezier easing on the open
  // and close makes the fade feel cinematic rather than mechanical.
  // The slight scale + blur on entry mimics a camera coming into focus.
  const css = `
    @keyframes archer-cinematic-${uid} {
      0%   { opacity: 0; transform: scale(1.02); filter: blur(3px); }
      20%  { opacity: 1; transform: scale(1);    filter: blur(0); }
      66%  { opacity: 1; transform: scale(1);    filter: blur(0); }
      100% { opacity: 0; transform: scale(1);    filter: blur(0); }
    }
    .archer-image-${uid} {
      animation: archer-cinematic-${uid} 7.5s cubic-bezier(0.22, 0.61, 0.36, 1)
                 ${playOnce ? "1 forwards" : "infinite"};
      will-change: opacity, transform, filter;
    }
    /* Reduce motion: respect the OS setting. Users who prefer
       reduced motion get a static, fully-opaque image — they still
       see the welcome, just without the animated entrance / exit. */
    @media (prefers-reduced-motion: reduce) {
      .archer-image-${uid} {
        animation: none;
        opacity: 1;
        transform: none;
        filter: none;
      }
    }
  `;

  return (
    <div
      className={cn(
        "relative w-full overflow-hidden rounded-2xl",
        // Aspect ratio is tuned to the source illustration's
        // composition: wide landscape with the archer on the left and
        // the target right of center. object-cover keeps the focal
        // points visible across screen sizes.
        "aspect-[3/2]",
        className,
      )}
      aria-label="A vidyārthi student in traditional dress drawing a bow at a target — the practice-makes-mastery motif"
    >
      <style>{css}</style>
      <img
        src="/vidyarthi-hero.png"
        alt="A young Indian student (vidyārthi) in a cream dhoti and saffron sash, drawing a wooden bow and aiming a steel-tipped arrow at a traditional target. A temple and trees in the background."
        className={`archer-image-${uid} h-full w-full object-cover`}
        loading="eager"
        // Hide gracefully if the asset isn't placed yet — we don't
        // want a broken-image icon spoiling the welcome.
        onError={(e) => {
          (e.currentTarget as HTMLImageElement).style.visibility = "hidden";
        }}
      />
    </div>
  );
}
