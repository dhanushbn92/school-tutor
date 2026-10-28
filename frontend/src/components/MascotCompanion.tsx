import { useEffect, useRef, useState } from "react";
import { Bell, CalendarDays, Lightbulb, Trophy } from "lucide-react";
import { MascotFigure } from "@/components/mascot/MascotFigure";
import { MascotMenu } from "@/components/mascot/MascotMenu";
import { useAuth } from "@/lib/auth";
import { useMascot, type MascotBubbleIcon, type MascotMood } from "@/lib/mascotContext";
import { GREETING_POSE, MOOD_POSES } from "@/lib/mascotPoses";
import { useMascotState } from "@/lib/queries";

/**
 * Dhananjaya's learning buddy: a full-body robot standing in the bottom-right
 * corner of every learner page.
 *
 * - Its expression and a small animation follow the global MascotContext mood;
 *   pages dispatch reactions through `useMascot().reactWith(...)`.
 * - Clicking it opens a menu of places to go next.
 *
 * Visibility is controlled three ways:
 *   1. Role gating: only mounts for `student` / `individual_learner`.
 *   2. Server-side `enabled` flag (per user, persisted to
 *      `learner_mascot_state.enabled`), so the choice follows the learner
 *      across devices.
 *   3. Local "hidden for this session": hides the mascot until the next
 *      reload, without touching the server flag.
 */

/** Bubble icon used when a reaction does not name one. */
const DEFAULT_ICON: Partial<Record<MascotMood, MascotBubbleIcon>> = {
  REMINDER: "bell",
  VICTORY: "trophy",
  HINT: "bulb",
};

export function MascotCompanion() {
  const { user } = useAuth();
  const isLearner =
    user?.role === "student" || user?.role === "individual_learner";

  const mascotQ = useMascotState(isLearner);
  const { mood, message, icon } = useMascot();
  const [hiddenThisSession, setHiddenThisSession] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [hover, setHover] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Close the menu on an outside click or Escape.
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  if (!isLearner) return null;
  if (!mascotQ.data || !mascotQ.data.enabled) return null;
  if (hiddenThisSession) return null;

  // A real reaction wins; otherwise the buddy perks up when it is hovered or
  // its menu is open.
  const base = MOOD_POSES[mood];
  const pose = menuOpen || (hover && mood === "IDLE") ? GREETING_POSE : base;
  const bubbleIcon = icon ?? DEFAULT_ICON[mood] ?? null;

  return (
    <div
      ref={rootRef}
      className="pointer-events-none fixed right-3 bottom-20 z-30 flex flex-col items-end gap-2 md:right-6 md:bottom-3"
    >
      <style>{MOTION_CSS}</style>

      {menuOpen && (
        <MascotMenu
          onClose={() => setMenuOpen(false)}
          onHide={() => setHiddenThisSession(true)}
        />
      )}
      <div aria-live="polite" className="contents">
        {!menuOpen && message && <SpeechBubble text={message} icon={bubbleIcon} />}
      </div>

      <button
        type="button"
        aria-expanded={menuOpen}
        aria-label={`Dhananjaya's learning buddy, ${pose.description}. Open the quick menu`}
        onClick={() => setMenuOpen((v) => !v)}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onFocus={() => setHover(true)}
        onBlur={() => setHover(false)}
        className="pointer-events-auto relative cursor-pointer rounded-2xl focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-(--color-ring)"
      >
        <span
          aria-hidden
          className="absolute bottom-0 left-1/2 h-2 w-10 -translate-x-1/2 rounded-full bg-black/10 blur-[2px]"
        />
        <MascotFigure
          key={`${menuOpen ? "menu" : mood}`}
          pose={pose}
          className={`relative block h-28 w-auto select-none md:h-36 mascot-${pose.motion}`}
        />
      </button>
    </div>
  );
}

/* ----------------------------------------------------------------- */
/* Speech bubble                                                     */
/* ----------------------------------------------------------------- */

const ICONS: Record<MascotBubbleIcon, typeof Bell> = {
  bell: Bell,
  trophy: Trophy,
  bulb: Lightbulb,
  calendar: CalendarDays,
};

function SpeechBubble({
  text,
  icon,
}: {
  text: string;
  icon: MascotBubbleIcon | null;
}) {
  const Icon = icon ? ICONS[icon] : null;
  return (
    <div className="pointer-events-auto relative mr-1 flex max-w-64 items-start gap-2.5 rounded-2xl border border-(--color-border) bg-(--color-card) px-3.5 py-2.5 text-sm leading-snug text-(--color-foreground) shadow-lg">
      {Icon && (
        <span
          aria-hidden
          className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-(--color-primary)/10 text-(--color-primary)"
        >
          <Icon className="h-4 w-4" />
        </span>
      )}
      <span>{text}</span>
      <span
        aria-hidden
        className="absolute -bottom-1.5 right-10 h-3 w-3 rotate-45 border-r border-b border-(--color-border) bg-(--color-card)"
      />
    </div>
  );
}

/* ----------------------------------------------------------------- */
/* Motion: small CSS animations, switched off for reduced motion      */
/* ----------------------------------------------------------------- */

const MOTION_CSS = `
@keyframes mascot-float { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-4px) } }
@keyframes mascot-tilt { 0%,100% { transform: rotate(-2deg) } 50% { transform: rotate(2deg) } }
@keyframes mascot-bounce { 0%,100% { transform: translateY(0) } 35% { transform: translateY(-8px) } 60% { transform: translateY(0) } 78% { transform: translateY(-3px) } }
@keyframes mascot-sway { 0%,100% { transform: rotate(-2.5deg) } 50% { transform: rotate(2.5deg) } }
@keyframes mascot-jump { 0%,100% { transform: translateY(0) scale(1) } 45% { transform: translateY(-12px) scale(1.03) } }
@keyframes mascot-pulse { 0%,100% { transform: scale(1) } 50% { transform: scale(1.04) } }
@keyframes mascot-wiggle { 0%,100% { transform: rotate(0) } 15% { transform: rotate(-4deg) } 30% { transform: rotate(4deg) } 45% { transform: rotate(-3deg) } 60% { transform: rotate(3deg) } 75% { transform: rotate(0) } }
@keyframes mascot-pop { 0% { transform: scale(.92) } 55% { transform: scale(1.06) } 100% { transform: scale(1) } }
@keyframes mascot-blink { 0%,90%,100% { transform: scaleY(1) } 94% { transform: scaleY(.08) } }
@keyframes mascot-twinkle { 0%,100% { transform: scale(.6); opacity: .5 } 50% { transform: scale(1.1); opacity: 1 } }
@keyframes mascot-prop { 0% { transform: scale(.3); opacity: 0 } 70% { transform: scale(1.1); opacity: 1 } 100% { transform: scale(1); opacity: 1 } }
@keyframes mascot-ring { 0%,100% { transform: rotate(0) } 20% { transform: rotate(14deg) } 40% { transform: rotate(-12deg) } 60% { transform: rotate(8deg) } 80% { transform: rotate(-6deg) } }
.mascot-float { animation: mascot-float 3.2s ease-in-out infinite }
.mascot-float-slow { animation: mascot-float 4.4s ease-in-out infinite }
.mascot-tilt { animation: mascot-tilt 3.6s ease-in-out infinite; transform-origin: 50% 100% }
.mascot-bounce { animation: mascot-bounce .9s ease-out 2 }
.mascot-sway { animation: mascot-sway 2.4s ease-in-out infinite; transform-origin: 50% 100% }
.mascot-jump { animation: mascot-jump .85s ease-in-out infinite }
.mascot-pulse { animation: mascot-pulse 1.8s ease-in-out infinite; transform-origin: 50% 100% }
.mascot-wiggle { animation: mascot-wiggle 1.4s ease-in-out 2; transform-origin: 50% 100% }
.mascot-pop { animation: mascot-pop .45s ease-out 1; transform-origin: 50% 100% }
.mascot-blink { animation: mascot-blink 4.6s ease-in-out infinite; transform-box: fill-box; transform-origin: center }
.mascot-twinkle { animation: mascot-twinkle 1.4s ease-in-out infinite; transform-box: fill-box; transform-origin: center }
.mascot-prop-pop { animation: mascot-prop .5s ease-out 1; transform-box: fill-box; transform-origin: center }
.mascot-bell { animation: mascot-ring 1.2s ease-in-out 3; transform-origin: 0 -22px }
@media (prefers-reduced-motion: reduce) {
  .mascot-float, .mascot-float-slow, .mascot-tilt, .mascot-bounce, .mascot-sway, .mascot-jump,
  .mascot-pulse, .mascot-wiggle, .mascot-pop, .mascot-blink, .mascot-twinkle,
  .mascot-prop-pop, .mascot-bell { animation: none }
}
`;
