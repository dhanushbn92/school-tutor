import { useId } from "react";
import body from "@/assets/mascot/body.png";
import type {
  EyeShape,
  MascotEffect,
  MascotPose,
  MouthShape,
} from "@/lib/mascotPoses";

/**
 * The full-body learning buddy. The body is the supplied artwork with a blank
 * face screen; the eyes, mouth and little props are drawn on top as SVG, so the
 * expression can change (and blink) while the robot keeps its look.
 *
 * Everything is in the artwork's own pixel space (323 x 564). The head is
 * tilted about -11.7 degrees, so the face is drawn in a rotated group centred
 * between the eyes.
 */

const W = 323;
const H = 564;
const FACE_CENTRE = "translate(182.5 212.5) rotate(-11.7)";
const EYE_X = 56.7;
const MOUTH_Y = 42;

const CYAN = "#5FD3FF";
const SCREEN = "#0B2A78";

export function MascotFigure({
  pose,
  className,
  label,
}: {
  pose: MascotPose;
  className?: string;
  /** Accessible name; omit for a decorative figure. */
  label?: string;
}) {
  const uid = useId().replace(/:/g, "");
  const iris = `iris-${uid}`;
  const glow = `glow-${uid}`;
  const blinks = pose.left === "open" || pose.right === "open";

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      width={W}
      height={H}
      className={className}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <defs>
        <radialGradient id={iris} cx="0.4" cy="0.35" r="0.85">
          <stop offset="0" stopColor="#6CBBFF" />
          <stop offset="1" stopColor="#1457C8" />
        </radialGradient>
        <filter id={glow} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="2.6" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <image href={body} width={W} height={H} />

      <g transform={FACE_CENTRE}>
        <Eye
          x={-EYE_X}
          shape={pose.left}
          look={pose.look}
          blinks={blinks}
          iris={iris}
          glow={glow}
        />
        <Eye
          x={EYE_X}
          shape={pose.right}
          look={pose.look}
          blinks={blinks}
          iris={iris}
          glow={glow}
        />
        <Mouth shape={pose.mouth} glow={glow} />
      </g>

      <Effect kind={pose.effect} />
    </svg>
  );
}

const fade = { transition: "opacity .14s ease" } as const;

function Eye({
  x,
  shape,
  look,
  blinks,
  iris,
  glow,
}: {
  x: number;
  shape: EyeShape;
  look: [number, number];
  blinks: boolean;
  iris: string;
  glow: string;
}) {
  return (
    <g transform={`translate(${x} 0)`}>
      {/* open eye: white ring, blue iris, dark pupil and two highlights */}
      <g style={{ ...fade, opacity: shape === "open" ? 1 : 0 }}>
        <g className={blinks ? "mascot-blink" : undefined}>
          <circle r="31" fill="#F2F8FF" filter={`url(#${glow})`} />
          <g
            style={{
              transform: `translate(${look[0]}px, ${look[1]}px)`,
              transition: "transform .3s ease",
            }}
          >
            <circle r="23" fill={`url(#${iris})`} />
            <circle r="11" fill="#0A1B5C" />
            <circle cx="-8" cy="-9" r="6" fill="#fff" />
            <circle cx="8" cy="9" r="2.6" fill="#fff" opacity="0.9" />
          </g>
        </g>
      </g>

      {/* happy eye: a glowing upturned arc */}
      <g style={{ ...fade, opacity: shape === "happy" ? 1 : 0 }}>
        <path
          d="M-24 9 Q0 -23 24 9"
          fill="none"
          stroke={CYAN}
          strokeWidth="8"
          strokeLinecap="round"
          filter={`url(#${glow})`}
        />
      </g>

      {/* wide eye: surprise */}
      <g style={{ ...fade, opacity: shape === "wide" ? 1 : 0 }}>
        <circle r="34" fill="#F7FBFF" filter={`url(#${glow})`} />
        <circle r="9" fill="#0A1B5C" />
        <circle cx="-3" cy="-3" r="3" fill="#fff" />
      </g>
    </g>
  );
}

function Mouth({ shape, glow }: { shape: MouthShape; glow: string }) {
  const stroke = { fill: "none", stroke: CYAN, strokeWidth: 5, strokeLinecap: "round" as const };
  return (
    <g transform={`translate(0 ${MOUTH_Y})`} filter={`url(#${glow})`}>
      <path
        d="M-20 0 Q0 17 20 0"
        {...stroke}
        style={{ ...fade, opacity: shape === "smile" ? 1 : 0 }}
      />
      <path
        d="M-27 -3 Q0 36 27 -3 Z"
        fill={SCREEN}
        stroke={CYAN}
        strokeWidth="5"
        strokeLinejoin="round"
        style={{ ...fade, opacity: shape === "grin" ? 1 : 0 }}
      />
      <path
        d="M-13 5 Q-5 -2 3 4 T15 2"
        {...stroke}
        style={{ ...fade, opacity: shape === "flat" ? 1 : 0 }}
      />
      <ellipse
        cx="0"
        cy="5"
        rx="9"
        ry="12"
        fill={SCREEN}
        stroke={CYAN}
        strokeWidth="5"
        style={{ ...fade, opacity: shape === "oh" ? 1 : 0 }}
      />
    </g>
  );
}

function Star({ x, y, r, fill, delay }: { x: number; y: number; r: number; fill: string; delay: number }) {
  const d = `M0 ${-r} L${r * 0.3} ${-r * 0.3} L${r} 0 L${r * 0.3} ${r * 0.3} L0 ${r} L${-r * 0.3} ${r * 0.3} L${-r} 0 L${-r * 0.3} ${-r * 0.3} Z`;
  return (
    <g transform={`translate(${x} ${y})`}>
      <path d={d} fill={fill} className="mascot-twinkle" style={{ animationDelay: `${delay}s` }} />
    </g>
  );
}

/** A small prop that floats near the head and says what the robot is up to. */
function Effect({ kind }: { kind: MascotEffect }) {
  switch (kind) {
    case "question":
      return (
        <text
          x="262"
          y="104"
          fontSize="64"
          fontWeight="800"
          fill="#2F7BFF"
          fontFamily="'Plus Jakarta Sans', 'Inter', sans-serif"
          className="mascot-prop-pop"
          transform="rotate(12 262 90)"
        >
          ?
        </text>
      );
    case "bulb":
      return (
        <g className="mascot-prop-pop" transform="translate(284 82)">
          <path d="M0 -26 C-18 -26 -26 -12 -22 2 C-20 9 -12 14 -12 22 H12 C12 14 20 9 22 2 C26 -12 18 -26 0 -26 Z" fill="#FFD23F" />
          <rect x="-11" y="22" width="22" height="7" rx="3" fill="#E6A700" />
          <rect x="-8" y="30" width="16" height="6" rx="3" fill="#C98E00" />
          <path d="M-34 -22 L-26 -16 M34 -22 L26 -16 M0 -40 L0 -32" stroke="#FFB800" strokeWidth="4" strokeLinecap="round" />
        </g>
      );
    case "bell":
      return (
        <g transform="translate(46 98)">
          <g className="mascot-bell">
            <path d="M0 -22 C-12 -22 -18 -12 -18 0 V12 L-26 22 H26 L18 12 V0 C18 -12 12 -22 0 -22 Z" fill="#FFB21A" />
            <rect x="-4" y="-30" width="8" height="9" rx="4" fill="#E6930D" />
            <circle cx="0" cy="29" r="6" fill="#E6930D" />
          </g>
        </g>
      );
    case "alert":
      return (
        <g className="mascot-prop-pop" stroke="#FFB21A" strokeWidth="6" strokeLinecap="round">
          <path d="M262 56 L270 80" />
          <path d="M284 66 L276 86" />
          <path d="M298 90 L282 100" />
        </g>
      );
    case "sparkles":
      return (
        <g>
          <Star x={36} y={74} r={13} fill="#FFB21A" delay={0} />
          <Star x={292} y={60} r={16} fill="#5FD3FF" delay={0.25} />
          <Star x={22} y={196} r={10} fill="#5FD3FF" delay={0.5} />
          <Star x={304} y={170} r={11} fill="#FFB21A" delay={0.15} />
        </g>
      );
    case "none":
      return null;
  }
}
