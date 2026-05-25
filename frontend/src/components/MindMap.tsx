import { useState } from "react";

interface MindMapBranch {
  label: string;
  details?: string[];
}

interface MindMapData {
  title?: string;
  central_term: string;
  branches: MindMapBranch[];
}

const PALETTE = [
  "oklch(70% 0.15 30)",
  "oklch(72% 0.13 90)",
  "oklch(68% 0.13 145)",
  "oklch(70% 0.13 200)",
  "oklch(70% 0.15 260)",
  "oklch(72% 0.15 320)",
];

/**
 * Radial mind-map: central term in the middle, branches on a circle.
 *
 * Two modes:
 *   - Static (default, `interactive={false}`) — every branch's
 *     details render as small text labels next to the pill.
 *     Used inside flowing text (RichExplanationView block) where
 *     a non-interactive overview is the right thing.
 *   - Interactive (`interactive={true}`) — branches start collapsed
 *     showing only their label. Tap a branch to expand its details
 *     as sub-pills that fan out radially. Tap again to collapse.
 *     The chapter-summary surface on the Learn page uses this so
 *     kids can explore the chapter one branch at a time without
 *     being overwhelmed by every detail at once.
 */
export function MindMap({
  data,
  size = 520,
  interactive = false,
}: {
  data: MindMapData;
  size?: number;
  interactive?: boolean;
}) {
  // Interactive mode reserves more vertical room so expanded sub-
  // pills don't get clipped by the SVG viewport. Static mode keeps
  // the original compact aspect.
  const W = size;
  const H = Math.max(interactive ? 460 : 360, Math.round(size * (interactive ? 0.95 : 0.78)));
  const cx = W / 2;
  const cy = H / 2;
  const radius = Math.min(W, H) * (interactive ? 0.28 : 0.34);

  // Track which branches are currently open. We use a Set so toggle
  // is O(1) and rendering can quickly check membership. Hard-coded
  // to "all collapsed at start" — the interaction is the feature;
  // pre-expanding defeats the point.
  const [openBranches, setOpenBranches] = useState<Set<number>>(new Set());

  function toggleBranch(i: number) {
    setOpenBranches((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  }

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={data.title ?? data.central_term}
        className="h-auto w-full"
      >
        {data.branches.map((branch, i) => {
          const angle = (Math.PI * 2 * i) / data.branches.length - Math.PI / 2;
          const dirX = Math.cos(angle);
          const dirY = Math.sin(angle);
          const bx = cx + dirX * radius;
          const by = cy + dirY * radius;
          const colour = PALETTE[i % PALETTE.length];

          const isOpen = openBranches.has(i);
          const details = branch.details ?? [];

          // Layout for static (non-interactive) text labels — kept
          // verbatim from the original implementation so existing
          // callers don't shift visually.
          const detailLineHeight = 14;
          const radialPush = 40;
          const dox = dirX * radialPush;
          const doy = dirY * radialPush;
          const stackDir = dirY < -0.15 ? -1 : 1;
          const anchor: "start" | "middle" | "end" =
            dirX > 0.25 ? "start" : dirX < -0.25 ? "end" : "middle";

          return (
            <g key={`${i}-${branch.label}`}>
              {/* Spoke from the centre to the branch. */}
              <line
                x1={cx}
                y1={cy}
                x2={bx}
                y2={by}
                stroke={colour}
                strokeWidth={2}
                opacity={0.65}
              />

              <BranchPill
                x={bx}
                y={by}
                text={branch.label}
                fill={colour}
                hasChildren={interactive && details.length > 0}
                open={isOpen}
                onClick={
                  interactive && details.length > 0
                    ? () => toggleBranch(i)
                    : undefined
                }
              />

              {!interactive &&
                details.slice(0, 3).map((detail, di) => (
                  <text
                    key={di}
                    x={bx + dox}
                    y={by + doy + di * detailLineHeight * stackDir}
                    textAnchor={anchor}
                    fontSize={11}
                    fill="oklch(35% 0.01 260)"
                  >
                    {detail.length > 30 ? `${detail.slice(0, 28)}…` : detail}
                  </text>
                ))}

              {/* Interactive expand: details as sub-pills fanning out
                  past the branch pill, only when open. */}
              {interactive && isOpen && details.length > 0 && (
                <SubPills
                  branchX={bx}
                  branchY={by}
                  dirX={dirX}
                  dirY={dirY}
                  colour={colour}
                  details={details}
                />
              )}
            </g>
          );
        })}
        <CentralPill x={cx} y={cy} text={data.central_term} />
      </svg>

      {/* Caption only in interactive mode — a tiny "tap to explore"
          nudge so a learner knows the diagram does more than sit
          there. */}
      {interactive && (
        <div className="mt-2 text-center text-xs text-(--color-muted-foreground)">
          Tap any branch to see what's inside.
          {openBranches.size > 0 && (
            <>
              {" · "}
              <button
                type="button"
                className="underline-offset-2 hover:underline"
                onClick={() => setOpenBranches(new Set())}
              >
                Collapse all
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

/* ---------- Interactive sub-pills ---------- */

/**
 * Lay out the details of one branch as small pills radiating
 * outward in a shallow arc. The fan opens around the branch's own
 * direction vector — pills always point AWAY from the centre so
 * adjacent branches' details don't crash into each other.
 */
function SubPills({
  branchX,
  branchY,
  dirX,
  dirY,
  colour,
  details,
}: {
  branchX: number;
  branchY: number;
  dirX: number;
  dirY: number;
  colour: string;
  details: string[];
}) {
  // Distance from the branch pill to the sub-pill centres.
  const reach = 92;
  // Angular spread of the fan, in radians. Wider fan for more
  // details so they don't overlap.
  const spread = Math.min(Math.PI * 0.55, 0.32 + details.length * 0.18);
  const baseAngle = Math.atan2(dirY, dirX);
  const startAngle = baseAngle - spread / 2;
  const step = details.length === 1 ? 0 : spread / (details.length - 1);

  return (
    <>
      {details.map((text, i) => {
        const a = startAngle + i * step;
        const sx = branchX + Math.cos(a) * reach;
        const sy = branchY + Math.sin(a) * reach;
        return (
          <g
            key={i}
            className="animate-mindmap-pop"
            style={{
              transformOrigin: `${branchX}px ${branchY}px`,
              animationDelay: `${i * 50}ms`,
            }}
          >
            <line
              x1={branchX}
              y1={branchY}
              x2={sx}
              y2={sy}
              stroke={colour}
              strokeWidth={1.5}
              opacity={0.4}
            />
            <SubPill x={sx} y={sy} text={text} fill={colour} />
          </g>
        );
      })}
      {/* Keyframes are inline so the file is self-contained — no
          global CSS edit needed for the pop animation. */}
      <style>{`
        @keyframes mindmap-pop {
          0% { opacity: 0; transform: scale(0.5); }
          70% { opacity: 1; transform: scale(1.05); }
          100% { opacity: 1; transform: scale(1); }
        }
        .animate-mindmap-pop {
          animation: mindmap-pop 0.28s cubic-bezier(0.34, 1.56, 0.64, 1) backwards;
        }
      `}</style>
    </>
  );
}

function CentralPill({ x, y, text }: { x: number; y: number; text: string }) {
  const padX = 18;
  const approxWidth = Math.max(110, text.length * 9 + padX * 2);
  return (
    <g>
      <rect
        x={x - approxWidth / 2}
        y={y - 22}
        width={approxWidth}
        height={44}
        rx={22}
        ry={22}
        fill="oklch(56% 0.14 257)"
      />
      <text
        x={x}
        y={y + 4}
        textAnchor="middle"
        fontSize={14}
        fontWeight={600}
        fill="white"
      >
        {text}
      </text>
    </g>
  );
}

function BranchPill({
  x,
  y,
  text,
  fill,
  hasChildren = false,
  open = false,
  onClick,
}: {
  x: number;
  y: number;
  text: string;
  fill: string;
  hasChildren?: boolean;
  open?: boolean;
  onClick?: () => void;
}) {
  // Slightly wider in interactive mode to fit the +/- chevron at
  // the right edge of the pill.
  const chevWidth = hasChildren ? 18 : 0;
  const approxWidth = Math.max(80, text.length * 7 + 18 + chevWidth);
  const clickable = onClick !== undefined;
  return (
    <g
      onClick={onClick}
      style={clickable ? { cursor: "pointer" } : undefined}
      // SVG focus/aria treatment so keyboard users can also expand.
      tabIndex={clickable ? 0 : undefined}
      role={clickable ? "button" : undefined}
      aria-pressed={clickable ? open : undefined}
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
    >
      <rect
        x={x - approxWidth / 2}
        y={y - 14}
        width={approxWidth}
        height={28}
        rx={14}
        ry={14}
        fill={fill}
      />
      <text
        x={hasChildren ? x - 6 : x}
        y={y + 4}
        textAnchor={hasChildren ? "middle" : "middle"}
        fontSize={12}
        fontWeight={600}
        fill="white"
      >
        {text}
      </text>
      {hasChildren && (
        <text
          x={x + approxWidth / 2 - 10}
          y={y + 4}
          textAnchor="middle"
          fontSize={14}
          fontWeight={700}
          fill="white"
          aria-hidden="true"
        >
          {open ? "−" : "+"}
        </text>
      )}
    </g>
  );
}

function SubPill({
  x,
  y,
  text,
  fill,
}: {
  x: number;
  y: number;
  text: string;
  fill: string;
}) {
  // Cap displayed text so a long detail doesn't render off-screen.
  // Full text lives in the `<title>` so hovering a sub-pill reveals
  // it in a native tooltip — handy on desktop, ignored on touch.
  const display = text.length > 38 ? `${text.slice(0, 36)}…` : text;
  const approxWidth = Math.max(80, display.length * 6.6 + 18);
  return (
    <g>
      <title>{text}</title>
      <rect
        x={x - approxWidth / 2}
        y={y - 13}
        width={approxWidth}
        height={26}
        rx={13}
        ry={13}
        fill="white"
        stroke={fill}
        strokeWidth={1.5}
      />
      <text
        x={x}
        y={y + 4}
        textAnchor="middle"
        fontSize={11}
        fill="oklch(35% 0.01 260)"
      >
        {display}
      </text>
    </g>
  );
}
