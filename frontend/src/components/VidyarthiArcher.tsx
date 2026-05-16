import { useId } from "react";
import { BRAND_ARROW_COLORS } from "@/lib/brand";
import { cn } from "@/lib/utils";

/**
 * The vidyārthi (student archer) intro scene.
 *
 * A single hand-drawn SVG illustration of an Indian-classical student
 * archer drawing a recurve bow at a target. One full animation cycle
 * runs in 7.5 seconds and tells a small story:
 *
 *   0.0 s — 1.7 s   Draw: archer pulls the bowstring back; bow flexes.
 *   1.7 s — 2.4 s   Aim hold: a brief steady moment, bowstring at full draw.
 *   2.4 s — 2.7 s   Release: the string snaps forward, the arrow leaves the bow.
 *   2.7 s — 4.2 s   Flight: the arrow flies across the scene in a slight
 *                   parabolic arc (gravity arc, not a flat line).
 *   4.2 s — 4.5 s   Impact: the arrow lodges in the bullseye and the target
 *                   rings ripple outward in a celebratory pulse.
 *   4.5 s — 7.5 s   Hold + reset: the moment lingers, then everything fades
 *                   back into resting position to start the next loop.
 *
 * The character is drawn with filled shapes — kurta in saffron, dhoti in
 * cream, dark hair tied in a top-knot (jūṭā) — so it reads as a real
 * student archer rather than a stick figure. The bow is a proper recurve
 * with S-curve limbs and an animated bowstring; the arrow has a wooden
 * shaft, two feather flights, and a metal arrowhead.
 *
 * Everything is pure CSS keyframes (no canvas, no motion library) so the
 * scene adds nothing to the JS bundle and stays smooth even on low-end
 * devices.
 *
 * Props
 *   - `playOnce`  when true, the scene plays a single 7.5 s cycle and
 *                 then sits in its rest position. Used by the dashboard
 *                 intro overlay so the animation doesn't loop forever
 *                 while the page fades it out.
 *   - `compact`   shrinks the scene to a slim band for non-intro contexts.
 */
export function VidyarthiArcher({
  playOnce = false,
  compact = false,
  className,
}: {
  playOnce?: boolean;
  compact?: boolean;
  className?: string;
}) {
  const C = BRAND_ARROW_COLORS;
  // useId gives a stable, unique-per-mount suffix so two scenes on the
  // same page don't collide on CSS class names.
  const uid = useId().replace(/[:]/g, "");

  // Palette local to the archer scene — separate from the logo arrows
  // because the figure needs proper skin / fabric tones that are not
  // part of the multi-colour brand palette.
  const SKIN = "#D9A47A";
  const HAIR = "#231510";
  const KURTA = "#C5582B";        // warm saffron
  const KURTA_DARK = "#9A3F1E";   // shadow on kurta
  const SASH = "#F0B73C";         // gold sash
  const DHOTI = "#F4E7CA";        // cream dhoti
  const DHOTI_FOLD = "#D9C9A6";   // dhoti shadow fold
  const BOW_WOOD = "#6E3F1E";     // dark wood
  const BOW_GRIP = "#3D1F0E";     // bow handle
  const ARROW_SHAFT = "#E0C49A";  // light wood
  const ARROW_HEAD = "#3A4754";   // dark steel
  const GROUND = "#E7E2D4";       // sandy ground

  const iterationCount = playOnce ? "1" : "infinite";
  const fillMode = playOnce ? "forwards" : "none";

  // The CSS travels with the component. Every keyframe set is suffixed
  // with the useId so two archers on the same page (e.g. an intro
  // overlay + a future inline strip) can play independent timelines.
  const css = `
    /* Draw + release of the bowstring. The string is rendered as a
       <path> whose middle control point moves backward during the
       draw and snaps forward on release. */
    @keyframes archer-bowstring-${uid} {
      0%, 3%    { d: path("M 198 102 Q 198 138 198 174"); }
      22%, 32%  { d: path("M 198 102 Q 170 138 198 174"); }
      33%       { d: path("M 198 102 Q 200 138 198 174"); }
      34%, 100% { d: path("M 198 102 Q 198 138 198 174"); }
    }
    /* The back arm pulls the string. Translate it inward during the draw,
       snap forward on release, then hold. */
    @keyframes archer-back-arm-${uid} {
      0%, 3%    { transform: translateX(0); }
      22%, 32%  { transform: translateX(-22px); }
      33%, 100% { transform: translateX(0); }
    }
    /* Subtle bow flex — the limbs bend slightly during the draw, then
       snap straight on release. Implemented as a tiny scaleY on the
       bow group. */
    @keyframes archer-bow-flex-${uid} {
      0%, 3%    { transform: translate(0,0) scaleX(1); }
      22%, 32%  { transform: translate(-2px,0) scaleX(0.97); }
      33%, 100% { transform: translate(0,0) scaleX(1); }
    }
    /* Arrow lifecycle.
         0–22%   nocked on the string in rest, no transform.
         22–32%  pulled back with the string.
         33–56%  in flight, translating right + falling slightly.
         57–100% buried in the target, no further motion.
       Opacity at 100% so the arrow stays visible even when the cycle
       resets, preserving the "shot landed" moment until the bow draws
       a fresh arrow. */
    @keyframes archer-arrow-${uid} {
      0%, 3%   { transform: translate(0, 0)    rotate(0deg);  opacity: 1; }
      22%, 32% { transform: translate(-22px, 0) rotate(0deg); opacity: 1; }
      33%      { transform: translate(0, 0)    rotate(0deg);  opacity: 1; }
      45%      { transform: translate(180px, -6px) rotate(0deg); opacity: 1; }
      55%      { transform: translate(330px, 6px)  rotate(2deg); opacity: 1; }
      57%, 99% { transform: translate(345px, 8px)  rotate(2deg); opacity: 1; }
      100%     { transform: translate(345px, 8px)  rotate(2deg); opacity: 1; }
    }
    /* Target rings pulse outward on impact, then settle. */
    @keyframes archer-impact-${uid} {
      0%, 56%  { transform: scale(1);    opacity: 1; }
      59%      { transform: scale(1.18); opacity: 0.9; }
      63%      { transform: scale(1.05); opacity: 1; }
      67%, 100%{ transform: scale(1);    opacity: 1; }
    }
    /* Bullseye breath — a slow heartbeat across the cycle to give the
       target life even when no arrow is mid-flight. */
    @keyframes archer-bullseye-${uid} {
      0%, 100% { transform: scale(1); }
      50%      { transform: scale(1.08); }
    }
    /* Head bob — the archer's head tilts forward during draw, like
       sighting along the arrow, then straightens on release. */
    @keyframes archer-head-${uid} {
      0%, 5%    { transform: rotate(0deg); }
      22%, 32%  { transform: rotate(3deg); }
      35%, 100% { transform: rotate(0deg); }
    }

    .arch-bowstring-${uid} { animation: archer-bowstring-${uid} 7.5s ease-in-out ${iterationCount} ${fillMode}; }
    .arch-back-arm-${uid}  { animation: archer-back-arm-${uid}  7.5s ease-in-out ${iterationCount} ${fillMode}; transform-origin: 175px 105px; }
    .arch-bow-${uid}       { animation: archer-bow-flex-${uid}  7.5s ease-in-out ${iterationCount} ${fillMode}; transform-origin: 195px 138px; }
    .arch-arrow-${uid}     { animation: archer-arrow-${uid}     7.5s ease-in-out ${iterationCount} ${fillMode}; transform-origin: 0 0; }
    .arch-target-rings-${uid} { animation: archer-impact-${uid} 7.5s ease-in-out ${iterationCount} ${fillMode}; transform-origin: 520px 138px; transform-box: fill-box; }
    .arch-bullseye-${uid}  { animation: archer-bullseye-${uid}  7.5s ease-in-out ${iterationCount} ${fillMode}; transform-origin: 520px 138px; transform-box: fill-box; }
    .arch-head-${uid}      { animation: archer-head-${uid}      7.5s ease-in-out ${iterationCount} ${fillMode}; transform-origin: 130px 78px; }
  `;

  return (
    <div
      className={cn(
        "relative w-full overflow-hidden",
        compact ? "aspect-[16/4]" : "aspect-[16/7]",
        className,
      )}
      aria-label="A vidyārthi student drawing a bow and shooting an arrow at a target — the practice-makes-mastery motif"
    >
      <style>{css}</style>
      <svg
        viewBox="0 0 640 240"
        className="h-full w-full"
        preserveAspectRatio="xMidYMid meet"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* === BACKGROUND === Soft sky-to-sand gradient. */}
        <defs>
          <linearGradient id={`sky-${uid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stopColor="#F7F3EB" />
            <stop offset="80%" stopColor="#EFE6D2" />
            <stop offset="100%" stopColor="#E2D5B5" />
          </linearGradient>
          {/* Soft drop-shadow under the archer + target for grounding. */}
          <radialGradient id={`shadow-${uid}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%"  stopColor="#000" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#000" stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width="640" height="240" fill={`url(#sky-${uid})`} />

        {/* === GROUND === A subtle horizon strip the figures stand on. */}
        <rect x="0" y="205" width="640" height="35" fill={GROUND} />
        <line x1="0" y1="205" x2="640" y2="205" stroke="#C9BC97" strokeWidth="1" />

        {/* === DISTANT LANDSCAPE === Two faint hills for depth. */}
        <path d="M 0 205 Q 120 175 240 195 T 460 190 T 640 200 L 640 205 L 0 205 Z" fill="#E5DCC2" opacity="0.7" />

        {/* === ARCHER SHADOW === */}
        <ellipse cx="135" cy="208" rx="32" ry="4" fill={`url(#shadow-${uid})`} />

        {/* === ARCHER ===
            Origin is roughly the archer's base. Built in z-order so the
            front (bow-side) arm and bow land on top of the body. */}
        <g>
          {/* Back leg — planted, slightly behind. */}
          <path
            d="M 122 165 Q 119 188 116 205 L 124 205 Q 126 188 128 165 Z"
            fill={DHOTI}
          />
          {/* Front leg — stepped forward toward the target. */}
          <path
            d="M 138 165 Q 142 188 148 205 L 156 205 Q 152 188 146 165 Z"
            fill={DHOTI}
          />
          {/* Feet */}
          <ellipse cx="120" cy="205" rx="8" ry="2.5" fill={HAIR} />
          <ellipse cx="152" cy="205" rx="8" ry="2.5" fill={HAIR} />

          {/* Dhoti — wrap-around skirt from waist to mid-calf. The two
              folds give it a sense of fabric drape. */}
          <path
            d="M 108 130 L 158 130 L 168 175 L 100 175 Z"
            fill={DHOTI}
          />
          <path
            d="M 133 130 L 133 175"
            stroke={DHOTI_FOLD}
            strokeWidth="1"
          />
          <path
            d="M 120 135 L 116 173"
            stroke={DHOTI_FOLD}
            strokeWidth="1"
          />
          <path
            d="M 148 135 L 152 173"
            stroke={DHOTI_FOLD}
            strokeWidth="1"
          />

          {/* Kurta — torso shirt, V-neck. Saffron with a darker side
              seam shadow for depth. */}
          <path
            d="
              M 110 88
              L 156 88
              L 162 135
              L 104 135
              Z
            "
            fill={KURTA}
          />
          {/* Side shadow — gives the kurta dimension. */}
          <path
            d="M 152 88 L 156 88 L 162 135 L 156 135 Z"
            fill={KURTA_DARK}
            opacity="0.6"
          />
          {/* V-neck opening */}
          <path
            d="M 126 88 L 133 100 L 140 88 Z"
            fill={SKIN}
          />
          {/* Sash across the chest — gold, diagonal */}
          <path
            d="M 110 95 L 162 115 L 162 122 L 110 102 Z"
            fill={SASH}
          />

          {/* Head group — animated to tilt during the draw. */}
          <g className={`arch-head-${uid}`} style={{ transformOrigin: "130px 78px" }}>
            {/* Neck */}
            <rect x="127" y="80" width="11" height="9" fill={SKIN} />
            {/* Skull / face */}
            <ellipse cx="130" cy="70" rx="13" ry="15" fill={SKIN} />
            {/* Hair cap — top half of the head, with fringe. */}
            <path
              d="
                M 117 70
                Q 117 55 130 53
                Q 144 55 144 70
                Q 144 64 140 64
                Q 135 70 130 67
                Q 125 70 120 64
                Q 117 64 117 70
                Z
              "
              fill={HAIR}
            />
            {/* Top-knot (jūṭā) — small bun above the head, the signature
                of a classical Indian student archer. */}
            <ellipse cx="130" cy="48" rx="4.5" ry="5" fill={HAIR} />
            {/* Tilak — small forehead mark */}
            <ellipse cx="130" cy="64" rx="1.2" ry="2.5" fill="#B5302C" />
            {/* Eye — a single dot, looking right toward the target. */}
            <circle cx="136" cy="71" r="1.2" fill={HAIR} />
            {/* Ear */}
            <ellipse cx="120" cy="73" rx="2" ry="3" fill={SKIN} />
          </g>

          {/* === BACK ARM === Pulls the bowstring. Wraps the whole arm
              (upper + forearm + hand) in the animated group so the
              elbow-and-fist track the string together. */}
          <g className={`arch-back-arm-${uid}`}>
            {/* Upper arm — from back shoulder to elbow at draw position */}
            <path
              d="M 115 95 Q 102 95 92 92 L 92 100 Q 105 102 115 102 Z"
              fill={KURTA}
            />
            {/* Forearm — bent up to ear */}
            <path
              d="M 92 92 L 102 78 L 108 80 L 100 100 Z"
              fill={SKIN}
            />
            {/* Fist on string */}
            <circle cx="103" cy="78" r="3.5" fill={SKIN} />
          </g>

          {/* === FRONT ARM === Holds the bow. Static. */}
          <g>
            {/* Upper arm — from front shoulder forward */}
            <path
              d="M 152 95 Q 165 95 178 100 L 178 108 Q 165 105 152 105 Z"
              fill={KURTA}
            />
            {/* Forearm — extended toward bow grip */}
            <path
              d="M 178 100 L 195 130 L 191 134 L 174 108 Z"
              fill={SKIN}
            />
            {/* Fist on bow handle */}
            <circle cx="194" cy="132" r="4" fill={SKIN} />
          </g>

          {/* === BOW === Recurve shape. The wood is drawn as two
              S-curves (upper and lower limbs) joined by a darker grip.
              The whole bow group flexes slightly during the draw. */}
          <g className={`arch-bow-${uid}`}>
            {/* Upper limb — curves up from grip, ends in a tip. */}
            <path
              d="M 198 138 Q 215 122 213 102 Q 207 95 198 102"
              fill="none"
              stroke={BOW_WOOD}
              strokeWidth="4"
              strokeLinecap="round"
            />
            {/* Lower limb — mirror of the upper. */}
            <path
              d="M 198 138 Q 215 154 213 174 Q 207 181 198 174"
              fill="none"
              stroke={BOW_WOOD}
              strokeWidth="4"
              strokeLinecap="round"
            />
            {/* Grip — dark handle wrap */}
            <rect x="194" y="128" width="6" height="20" rx="2" fill={BOW_GRIP} />
            {/* Bowstring — single path whose middle moves during the draw. */}
            <path
              className={`arch-bowstring-${uid}`}
              d="M 198 102 Q 198 138 198 174"
              fill="none"
              stroke="#3A2E1F"
              strokeWidth="1"
              strokeLinecap="round"
            />
          </g>

          {/* === ARROW === Nocked on the bowstring, flies to the target.
              Drawn in its rest-on-string position; the animation drives
              it through the full draw → fly → impact lifecycle. */}
          <g className={`arch-arrow-${uid}`} transform="translate(108 138)">
            {/* Shaft — wooden, long */}
            <rect x="0" y="-1" width="90" height="2" fill={ARROW_SHAFT} rx="0.5" />
            {/* Arrowhead — pointed steel */}
            <polygon points="90,-2 96,0 90,2" fill={ARROW_HEAD} />
            {/* Fletching — two feathers at the tail. Hot-pink + orange
                so the arrow reads even at speed against the cream sky. */}
            <polygon points="0,0 -7,-4 -3,-1 -3,1 -7,4" fill={C.magenta} />
            <polygon points="-3,0 -10,-3 -6,-0.5 -6,0.5 -10,3" fill={C.orange} />
            {/* Nock — small notch at the back end */}
            <rect x="-11" y="-1" width="2" height="2" fill={HAIR} />
          </g>
        </g>

        {/* === TARGET ===
            Concentric rings on a wooden stand. Larger and more polished
            than before, with proper alternating colour bands per
            traditional archery target design. */}
        <g>
          {/* Target shadow on ground */}
          <ellipse cx="520" cy="208" rx="36" ry="4" fill={`url(#shadow-${uid})`} />

          {/* Wooden stand — two angled legs and a cross-brace */}
          <rect x="516" y="170" width="8" height="40" fill={BOW_WOOD} />
          <rect x="500" y="200" width="40" height="6" fill={BOW_WOOD} rx="1" />

          {/* Rings group — animates a single impact pulse. */}
          <g className={`arch-target-rings-${uid}`}>
            {/* Outer white ring */}
            <circle cx="520" cy="138" r="40" fill="#F7F3EB" stroke={HAIR} strokeWidth="1.5" />
            {/* Black */}
            <circle cx="520" cy="138" r="34" fill={HAIR} />
            {/* Blue */}
            <circle cx="520" cy="138" r="28" fill="#2A6FB5" />
            {/* Red */}
            <circle cx="520" cy="138" r="20" fill="#C8332E" />
            {/* Yellow (10-ring) */}
            <circle cx="520" cy="138" r="11" fill={C.yellow} />
            {/* Bullseye — gently pulses every cycle. */}
            <circle
              className={`arch-bullseye-${uid}`}
              cx="520" cy="138" r="4"
              fill={C.magenta}
            />
          </g>
        </g>
      </svg>
    </div>
  );
}
