import { type ReactElement, useId } from "react";
import {
  BookCheck,
  CalendarCheck,
  ClipboardCheck,
  Compass,
  Crown,
  Dice5,
  Flame,
  Layers,
  Lightbulb,
  Star,
  Sun,
  Target,
  Trophy,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { STAMP_PRESENTATION, type StampIconName } from "@/lib/stamps";
import type { StampKind } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Visual rendering of a stamp / badge.
 *
 * Each stamp has a `tier` (bronze / silver / gold / platinum) — this
 * component renders a different SVG shape per tier:
 *   - bronze: simple disc with a soft radial gradient
 *   - silver: shield (rounded pentagon) with double rim
 *   - gold: shield with starburst rays + warm radial glow
 *   - platinum: 8-pointed medallion + halo ring + decorative dots
 *
 * Sizing presets ('sm', 'md', 'lg') keep the proportions sensible at
 * any scale. The optional ribbon underneath carries the stamp's
 * tagline ("Legend", "Bullseye", ...) for a showcase feel; learners
 * should see this on the StampBook page where the achievement is
 * the point. Smaller badges (in the dashboard strip, for example)
 * omit the ribbon and the surrounding metadata so they fit inline.
 */
export interface StampBadgeProps {
  kind: StampKind;
  size?: "xs" | "sm" | "md" | "lg";
  /** Show the tagline ribbon under the badge. Defaults to false. */
  showRibbon?: boolean;
  /** Greyed-out 'locked' rendering for not-yet-earned slots. */
  locked?: boolean;
  className?: string;
}

const ICONS: Record<StampIconName, LucideIcon> = {
  Trophy,
  Crown,
  Star,
  Flame,
  Target,
  BookCheck,
  Lightbulb,
  Compass,
  Zap,
  Dice5,
  Layers,
  CalendarCheck,
  Sun,
  ClipboardCheck,
};

// Pixel sizes per preset (the inner SVG always uses a 100x120 viewBox
// — 100 wide, 100 tall for the shape + 20px tail of headroom for the
// ribbon below). The container height shrinks when the ribbon is off.
const SIZE_PX: Record<NonNullable<StampBadgeProps["size"]>, number> = {
  xs: 28,
  sm: 40,
  md: 72,
  lg: 112,
};

export function StampBadge({
  kind,
  size = "md",
  showRibbon = false,
  locked = false,
  className,
}: StampBadgeProps) {
  const meta = STAMP_PRESENTATION[kind];
  if (!meta) return null;
  const Icon = ICONS[meta.iconName] ?? Trophy;
  const id = useId();

  // Tier-specific palette adjustments. The base hue comes from the brand
  // colour assigned to the stamp; we layer a lighter highlight at the
  // top of the shape and darken slightly toward the bottom for depth.
  const baseColor = locked ? "#94a3b8" : meta.color;
  const highlight = locked ? "#cbd5e1" : lighten(meta.color, 0.35);
  const shadow = locked ? "#64748b" : darken(meta.color, 0.25);

  const px = SIZE_PX[size];
  const heightFactor = showRibbon ? 1.22 : 1.0;
  // Show the prideful ribbon only at sizes where it's actually legible.
  const ribbonVisible = showRibbon && (size === "md" || size === "lg");

  return (
    <div
      className={cn("inline-flex flex-col items-center", className)}
      style={{
        width: px,
        height: Math.round(px * heightFactor),
      }}
      title={`${meta.label} — ${meta.tagline}`}
    >
      <svg
        viewBox="0 0 100 120"
        width={px}
        height={Math.round(px * heightFactor)}
        aria-label={`${meta.label} badge`}
        role="img"
        style={{ overflow: "visible" }}
      >
        <defs>
          {/* Top-to-bottom highlight gradient for the main shape */}
          <radialGradient id={`grad-${id}`} cx="50%" cy="35%" r="65%">
            <stop offset="0%" stopColor={highlight} />
            <stop offset="55%" stopColor={baseColor} />
            <stop offset="100%" stopColor={shadow} />
          </radialGradient>
          {/* Halo gradient for gold/platinum */}
          <radialGradient id={`halo-${id}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={highlight} stopOpacity="0.0" />
            <stop offset="60%" stopColor={highlight} stopOpacity="0.0" />
            <stop offset="80%" stopColor={highlight} stopOpacity="0.55" />
            <stop offset="100%" stopColor={baseColor} stopOpacity="0.0" />
          </radialGradient>
          {/* Subtle drop shadow */}
          <filter id={`drop-${id}`} x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="2" />
            <feOffset dx="0" dy="2" result="offsetblur" />
            <feFlood floodColor="#000000" floodOpacity={locked ? 0.05 : 0.25} />
            <feComposite in2="offsetblur" operator="in" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Tier-specific decorations rendered BEHIND the main shape */}
        {meta.tier === "gold" && (
          <Starburst rays={12} cx={50} cy={50} r1={28} r2={48} fill={highlight} opacity={0.35} />
        )}
        {meta.tier === "platinum" && (
          <>
            <Starburst rays={16} cx={50} cy={50} r1={30} r2={52} fill={highlight} opacity={0.45} />
            <circle cx={50} cy={50} r={46} fill={`url(#halo-${id})`} />
          </>
        )}

        {/* Main shape — varies by tier */}
        <g filter={`url(#drop-${id})`}>
          {meta.tier === "bronze" && (
            <circle cx={50} cy={50} r={32} fill={`url(#grad-${id})`} stroke={shadow} strokeWidth={2} />
          )}
          {meta.tier === "silver" && <ShieldShape gradId={`grad-${id}`} stroke={shadow} />}
          {meta.tier === "gold" && (
            <>
              <ShieldShape gradId={`grad-${id}`} stroke={shadow} />
              {/* Small top star like a sheriff's badge accent */}
              <SmallStar cx={50} cy={18} size={6} fill={highlight} />
            </>
          )}
          {meta.tier === "platinum" && (
            <>
              <MedallionShape gradId={`grad-${id}`} stroke={shadow} />
              {/* Crown-ish top dots */}
              <circle cx={42} cy={18} r={2.5} fill={highlight} />
              <circle cx={50} cy={14} r={3} fill={highlight} />
              <circle cx={58} cy={18} r={2.5} fill={highlight} />
            </>
          )}
        </g>

        {/* Inner glossy highlight ellipse (top half) */}
        <ellipse
          cx={50}
          cy={36}
          rx={22}
          ry={10}
          fill="#ffffff"
          opacity={locked ? 0.08 : 0.18}
        />

        {/* Icon — centered. Use foreignObject so the lucide React component
            can render naturally and stay crisp at any scale. */}
        <foreignObject x={28} y={28} width={44} height={44}>
          <div
            style={{
              width: "100%",
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#ffffff",
              filter: locked ? "grayscale(1) opacity(0.6)" : undefined,
            }}
          >
            <Icon strokeWidth={2.25} style={{ width: "80%", height: "80%" }} />
          </div>
        </foreignObject>

        {/* Tagline ribbon */}
        {ribbonVisible && (
          <g>
            {/* Ribbon body */}
            <path
              d={`M 12 92 L 88 92 L 84 108 L 16 108 Z`}
              fill={shadow}
              stroke={baseColor}
              strokeWidth={1.5}
            />
            {/* Ribbon notched ends (give it a tail look) */}
            <path d={`M 12 92 L 6 96 L 12 100 Z`} fill={darken(shadow, 0.15)} />
            <path d={`M 88 92 L 94 96 L 88 100 Z`} fill={darken(shadow, 0.15)} />
            <text
              x={50}
              y={103}
              textAnchor="middle"
              fill="#ffffff"
              style={{
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: 0.2,
                fontFamily:
                  'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
              }}
            >
              {meta.tagline.toUpperCase()}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}

// ───── Geometry helpers ───────────────────────────────────────────────

function ShieldShape({ gradId, stroke }: { gradId: string; stroke: string }) {
  // A rounded shield (top-flat, bottom-pointed) — classic medal look.
  // Coordinates are sized to the 100x100 logical canvas.
  const d = `
    M 50 14
    C 30 14, 18 18, 18 18
    L 18 56
    C 18 76, 34 86, 50 90
    C 66 86, 82 76, 82 56
    L 82 18
    C 82 18, 70 14, 50 14
    Z`;
  return <path d={d} fill={`url(#${gradId})`} stroke={stroke} strokeWidth={2.5} />;
}

function MedallionShape({ gradId, stroke }: { gradId: string; stroke: string }) {
  // Octagonal medallion — feels like a top-tier military / olympic medal.
  const d = `
    M 50 14
    L 70 22
    L 78 40
    L 78 60
    L 70 78
    L 50 86
    L 30 78
    L 22 60
    L 22 40
    L 30 22
    Z`;
  return <path d={d} fill={`url(#${gradId})`} stroke={stroke} strokeWidth={2.5} />;
}

function SmallStar({ cx, cy, size, fill }: { cx: number; cy: number; size: number; fill: string }) {
  // Simple 5-pointed star using two overlapping triangles is overkill — use
  // an SVG polygon with star points.
  const points: string[] = [];
  for (let i = 0; i < 10; i++) {
    const angle = (Math.PI * 2 * i) / 10 - Math.PI / 2;
    const r = i % 2 === 0 ? size : size * 0.45;
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    points.push(`${x.toFixed(2)},${y.toFixed(2)}`);
  }
  return <polygon points={points.join(" ")} fill={fill} />;
}

function Starburst({
  rays,
  cx,
  cy,
  r1,
  r2,
  fill,
  opacity,
}: {
  rays: number;
  cx: number;
  cy: number;
  r1: number;
  r2: number;
  fill: string;
  opacity?: number;
}) {
  // Render rays as thin triangles around a centre — radiating outward.
  const triangles: ReactElement[] = [];
  for (let i = 0; i < rays; i++) {
    const angle = (Math.PI * 2 * i) / rays;
    const halfWidth = (Math.PI * 0.7) / rays;
    const p1x = cx + Math.cos(angle) * r2;
    const p1y = cy + Math.sin(angle) * r2;
    const p2x = cx + Math.cos(angle - halfWidth) * r1;
    const p2y = cy + Math.sin(angle - halfWidth) * r1;
    const p3x = cx + Math.cos(angle + halfWidth) * r1;
    const p3y = cy + Math.sin(angle + halfWidth) * r1;
    triangles.push(
      <polygon
        key={i}
        points={`${p1x},${p1y} ${p2x},${p2y} ${p3x},${p3y}`}
        fill={fill}
        opacity={opacity}
      />,
    );
  }
  return <>{triangles}</>;
}

// ───── Colour helpers ─────────────────────────────────────────────────

/** Lighten a hex colour by mixing toward white. amount in [0, 1]. */
function lighten(hex: string, amount: number): string {
  return mixWith(hex, "#ffffff", amount);
}

/** Darken a hex colour by mixing toward black. amount in [0, 1]. */
function darken(hex: string, amount: number): string {
  return mixWith(hex, "#000000", amount);
}

function mixWith(hex: string, target: string, amount: number): string {
  const a = hexToRgb(hex);
  const b = hexToRgb(target);
  if (!a || !b) return hex;
  const t = Math.max(0, Math.min(1, amount));
  const r = Math.round(a.r * (1 - t) + b.r * t);
  const g = Math.round(a.g * (1 - t) + b.g * t);
  const bb = Math.round(a.b * (1 - t) + b.b * t);
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${bb.toString(16).padStart(2, "0")}`;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const m = hex.replace("#", "");
  if (m.length !== 6) return null;
  const r = parseInt(m.slice(0, 2), 16);
  const g = parseInt(m.slice(2, 4), 16);
  const b = parseInt(m.slice(4, 6), 16);
  if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) return null;
  return { r, g, b };
}
