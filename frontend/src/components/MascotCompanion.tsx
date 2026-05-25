import { useState } from "react";
import { X } from "lucide-react";
import { BRAND_ARROW_COLORS } from "@/lib/brand";
import { useAuth } from "@/lib/auth";
import { useMascot, type MascotMood } from "@/lib/mascotContext";
import { useMascotState, useUpdateMascot } from "@/lib/queries";

/**
 * Vidyārthi mascot — Stage 5 of the child-centric roadmap.
 *
 * A small archer figure pinned to the bottom-right of every learner
 * page. Reads mood + speech-bubble from the global MascotContext;
 * pages dispatch reactions through `useMascot().reactWith(...)`.
 *
 * The character is intentionally minimalist — geometric shapes in the
 * brand arrow palette. The state machine + reaction plumbing is the
 * real product here; a future illustrator can swap in richer artwork
 * by replacing the SVG paths in `<MascotFigure />` without touching
 * the context, the speech-bubble layout, or the toggle wiring.
 *
 * Visibility is controlled three ways:
 *   1. Role gating — only mounts for `student` / `individual_learner`.
 *   2. Server-side `enabled` flag (per-user, persisted to
 *      `learner_mascot_state.enabled`). Toggle persists across
 *      devices.
 *   3. Local "hidden for this session" — clicking the × hides the
 *      mascot until the next reload; updating the server flag would
 *      be a hostile pattern when the user just wants quiet for a few
 *      minutes.
 */
export function MascotCompanion() {
  const { user } = useAuth();
  const isLearner =
    user?.role === "student" || user?.role === "individual_learner";

  const mascotQ = useMascotState();
  const updateMascot = useUpdateMascot();
  const { mood, message } = useMascot();
  const [hiddenThisSession, setHiddenThisSession] = useState(false);

  if (!isLearner) return null;
  if (!mascotQ.data || !mascotQ.data.enabled) return null;
  if (hiddenThisSession) return null;

  // The mascot floats above the page in the bottom-right corner. It
  // uses fixed positioning + a moderate z-index so it sits over page
  // content but BELOW modal overlays / toasts.
  return (
    <div
      className="pointer-events-none fixed right-4 bottom-4 z-30 flex flex-col items-end gap-2 md:right-6 md:bottom-6"
      aria-live="polite"
    >
      {message && <SpeechBubble text={message} />}
      <div className="pointer-events-auto relative">
        <MascotFigure mood={mood} />
        <button
          type="button"
          aria-label="Hide mascot for now"
          title="Hide mascot for now (will return on next visit)"
          onClick={() => setHiddenThisSession(true)}
          className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full border border-(--color-border) bg-(--color-card) text-(--color-muted-foreground) shadow-sm transition hover:text-(--color-foreground)"
        >
          <X className="h-3 w-3" />
        </button>
      </div>
      {/* Tiny secondary action: permanently disable the mascot from
          all devices. Only shown when the in-session hide is NOT
          active (i.e. as part of the normal display), so the link
          doesn't clutter the page after the user has hidden the
          companion. */}
      <button
        type="button"
        className="pointer-events-auto rounded-full bg-(--color-card)/90 px-2 py-0.5 text-[10px] text-(--color-muted-foreground) shadow-sm backdrop-blur-sm transition hover:text-(--color-foreground)"
        onClick={() => updateMascot.mutate({ enabled: false })}
        disabled={updateMascot.isPending}
      >
        Turn off Vidyārthi
      </button>
    </div>
  );
}

/* ----------------------------------------------------------------- */
/* Speech bubble                                                     */
/* ----------------------------------------------------------------- */

function SpeechBubble({ text }: { text: string }) {
  return (
    <div className="pointer-events-auto max-w-xs rounded-2xl rounded-br-sm border border-(--color-border) bg-(--color-card) px-3 py-2 text-xs leading-relaxed text-(--color-foreground) shadow-md">
      {text}
    </div>
  );
}

/* ----------------------------------------------------------------- */
/* SVG mascot — geometric archer in the brand palette                */
/* ----------------------------------------------------------------- */

/**
 * Single SVG with all five poses drawn at the same coordinate
 * system; we just toggle which arms / bow / arrow path is visible
 * for the current mood. The figure itself (head + kurta) is shared.
 *
 * Coordinate system is 64×64 with the figure roughly centered.
 */
function MascotFigure({ mood }: { mood: MascotMood }) {
  // Map each mood to a tiny animation that breathes life into the
  // static SVG. CSS-based; no JS animation loop, so the figure stays
  // cheap even on slow devices.
  const breathe = mood === "IDLE" ? "animate-mascot-breathe" : "";
  const wobble = mood === "RESTRING" ? "animate-mascot-wobble" : "";
  const cheer = mood === "VICTORY" ? "animate-mascot-cheer" : "";
  const focused = mood === "DRAWN" ? "animate-mascot-focus" : "";
  const fires = mood === "FIRES" ? "animate-mascot-fire" : "";

  return (
    <>
      {/* Inline keyframes — kept here so the mascot is one
          self-contained file. Tailwind utility classes reference
          these animation names. */}
      <style>{`
        @keyframes mascot-breathe {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-1.5px); }
        }
        @keyframes mascot-wobble {
          0%, 100% { transform: rotate(0); }
          25% { transform: rotate(-3deg); }
          75% { transform: rotate(3deg); }
        }
        @keyframes mascot-cheer {
          0%, 100% { transform: translateY(0) scale(1); }
          50% { transform: translateY(-3px) scale(1.04); }
        }
        @keyframes mascot-focus {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.015); }
        }
        @keyframes mascot-fire {
          0% { transform: translateX(0); }
          40% { transform: translateX(-1px); }
          100% { transform: translateX(0); }
        }
        .animate-mascot-breathe { animation: mascot-breathe 3s ease-in-out infinite; }
        .animate-mascot-wobble  { animation: mascot-wobble  1.2s ease-in-out infinite; }
        .animate-mascot-cheer   { animation: mascot-cheer   0.9s ease-in-out infinite; }
        .animate-mascot-focus   { animation: mascot-focus   2.4s ease-in-out infinite; }
        .animate-mascot-fire    { animation: mascot-fire    0.5s ease-out 1; }
      `}</style>
      <svg
        width="64"
        height="64"
        viewBox="0 0 64 64"
        role="img"
        aria-label={moodAria(mood)}
        className={`drop-shadow-md ${breathe} ${wobble} ${cheer} ${focused} ${fires}`}
      >
        {/* Soft ground shadow — makes the figure feel planted. */}
        <ellipse cx="32" cy="58" rx="16" ry="2.2" fill="rgba(0,0,0,0.12)" />

        {/* Shared figure: head + kurta body. */}
        <Figure />

        {/* Pose-specific overlays */}
        {mood === "IDLE" && <BowAtRest />}
        {mood === "DRAWN" && <BowDrawn />}
        {mood === "FIRES" && <ArrowFires />}
        {mood === "RESTRING" && <BowLowered />}
        {mood === "VICTORY" && <BowOverhead />}
      </svg>
    </>
  );
}

/** Head + kurta body. Same across every pose so the character reads
 *  as the same figure regardless of mood. */
function Figure() {
  const skin = "#E3B98A"; // warm wheat tone, India-context
  const kurta = BRAND_ARROW_COLORS.navy;
  const kurtaAccent = BRAND_ARROW_COLORS.green;
  return (
    <>
      {/* Body (kurta) */}
      <path
        d="M 24 50 L 24 36 Q 32 32 40 36 L 40 50 Z"
        fill={kurta}
      />
      {/* Kurta hem accent stripe */}
      <rect x="24" y="48" width="16" height="2" fill={kurtaAccent} />
      {/* Head */}
      <circle cx="32" cy="26" r="6" fill={skin} />
      {/* Hair tuft */}
      <path
        d="M 26 22 Q 32 17 38 22 L 38 24 L 26 24 Z"
        fill="#1f1410"
      />
      {/* Eyes */}
      <circle cx="30" cy="26.5" r="0.9" fill="#1f1410" />
      <circle cx="34" cy="26.5" r="0.9" fill="#1f1410" />
      {/* Smile (small smiling curve) */}
      <path
        d="M 30 29 Q 32 30.5 34 29"
        stroke="#1f1410"
        strokeWidth="0.7"
        fill="none"
        strokeLinecap="round"
      />
    </>
  );
}

/* ---------- pose overlays ---------- */

function BowAtRest() {
  // Bow held loosely at the side, curving down.
  return (
    <g>
      <path
        d="M 44 38 Q 50 42 47 50"
        stroke={BRAND_ARROW_COLORS.orange}
        strokeWidth="1.6"
        fill="none"
        strokeLinecap="round"
      />
      {/* Bowstring */}
      <line x1="44" y1="38" x2="47" y2="50" stroke={BRAND_ARROW_COLORS.gray} strokeWidth="0.5" />
      {/* Arm — at side */}
      <path
        d="M 40 38 Q 44 40 44 38"
        stroke={BRAND_ARROW_COLORS.navy}
        strokeWidth="2.2"
        fill="none"
        strokeLinecap="round"
      />
    </g>
  );
}

function BowDrawn() {
  // Bow pulled back, arrow nocked horizontally.
  return (
    <g>
      {/* Bow */}
      <path
        d="M 46 28 Q 56 38 46 48"
        stroke={BRAND_ARROW_COLORS.orange}
        strokeWidth="1.8"
        fill="none"
        strokeLinecap="round"
      />
      {/* Bowstring drawn (pulled back to figure) */}
      <path
        d="M 46 28 L 36 38 L 46 48"
        stroke={BRAND_ARROW_COLORS.gray}
        strokeWidth="0.6"
        fill="none"
      />
      {/* Arm extending forward */}
      <line x1="40" y1="38" x2="46" y2="38" stroke={BRAND_ARROW_COLORS.navy} strokeWidth="2.2" strokeLinecap="round" />
      {/* Drawing arm */}
      <line x1="24" y1="40" x2="36" y2="38" stroke={BRAND_ARROW_COLORS.navy} strokeWidth="2.2" strokeLinecap="round" />
      {/* Arrow */}
      <line x1="36" y1="38" x2="50" y2="38" stroke={BRAND_ARROW_COLORS.green} strokeWidth="1.2" />
      <polygon
        points="50,38 48,37 48,39"
        fill={BRAND_ARROW_COLORS.green}
      />
    </g>
  );
}

function ArrowFires() {
  // Bow loosed; arrow streaking away with motion lines.
  return (
    <g>
      {/* Bow released */}
      <path
        d="M 46 30 Q 53 38 46 46"
        stroke={BRAND_ARROW_COLORS.orange}
        strokeWidth="1.8"
        fill="none"
        strokeLinecap="round"
      />
      {/* Bowstring relaxed */}
      <line x1="46" y1="30" x2="46" y2="46" stroke={BRAND_ARROW_COLORS.gray} strokeWidth="0.6" />
      {/* Arm forward */}
      <line x1="40" y1="38" x2="46" y2="38" stroke={BRAND_ARROW_COLORS.navy} strokeWidth="2.2" strokeLinecap="round" />
      {/* Arrow zooming */}
      <line x1="50" y1="34" x2="62" y2="30" stroke={BRAND_ARROW_COLORS.green} strokeWidth="1.3" />
      <polygon
        points="62,30 60,28 60,32"
        fill={BRAND_ARROW_COLORS.green}
      />
      {/* Motion lines */}
      <line x1="48" y1="36" x2="54" y2="34" stroke={BRAND_ARROW_COLORS.yellow} strokeWidth="0.6" strokeLinecap="round" />
      <line x1="49" y1="38" x2="55" y2="37" stroke={BRAND_ARROW_COLORS.yellow} strokeWidth="0.6" strokeLinecap="round" />
    </g>
  );
}

function BowLowered() {
  // Bow lowered, head tilted slightly — restringing pose.
  return (
    <g>
      {/* Bow lowered diagonally */}
      <path
        d="M 40 44 Q 48 48 50 56"
        stroke={BRAND_ARROW_COLORS.orange}
        strokeWidth="1.6"
        fill="none"
        strokeLinecap="round"
      />
      {/* Bowstring */}
      <line x1="40" y1="44" x2="50" y2="56" stroke={BRAND_ARROW_COLORS.gray} strokeWidth="0.5" />
      {/* Arm holding bow */}
      <line x1="38" y1="40" x2="42" y2="46" stroke={BRAND_ARROW_COLORS.navy} strokeWidth="2.2" strokeLinecap="round" />
      {/* Small thought dot above head */}
      <circle cx="40" cy="18" r="1.3" fill={BRAND_ARROW_COLORS.purple} opacity="0.7" />
    </g>
  );
}

function BowOverhead() {
  // Bow held overhead in celebration.
  return (
    <g>
      {/* Bow lifted high */}
      <path
        d="M 22 16 Q 32 12 42 16"
        stroke={BRAND_ARROW_COLORS.orange}
        strokeWidth="1.8"
        fill="none"
        strokeLinecap="round"
      />
      {/* Bowstring */}
      <line x1="22" y1="16" x2="42" y2="16" stroke={BRAND_ARROW_COLORS.gray} strokeWidth="0.6" />
      {/* Both arms raised */}
      <line x1="26" y1="36" x2="22" y2="18" stroke={BRAND_ARROW_COLORS.navy} strokeWidth="2.2" strokeLinecap="round" />
      <line x1="38" y1="36" x2="42" y2="18" stroke={BRAND_ARROW_COLORS.navy} strokeWidth="2.2" strokeLinecap="round" />
      {/* Confetti */}
      <circle cx="20" cy="22" r="1" fill={BRAND_ARROW_COLORS.yellow} />
      <circle cx="46" cy="22" r="1" fill={BRAND_ARROW_COLORS.magenta} />
      <circle cx="14" cy="32" r="1" fill={BRAND_ARROW_COLORS.green} />
      <circle cx="50" cy="32" r="1" fill={BRAND_ARROW_COLORS.purple} />
    </g>
  );
}

function moodAria(mood: MascotMood): string {
  switch (mood) {
    case "IDLE":
      return "Vidyārthi — at rest";
    case "DRAWN":
      return "Vidyārthi — bow drawn, focused";
    case "FIRES":
      return "Vidyārthi — arrow flies";
    case "RESTRING":
      return "Vidyārthi — restringing the bow";
    case "VICTORY":
      return "Vidyārthi — victory pose";
  }
}

