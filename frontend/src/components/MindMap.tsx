import { useState } from "react";

/**
 * Recursive mind-map node. A `detail` can be either a plain string
 * (leaf — just text inside a sub-pill) or another node that itself
 * has children (and can be expanded further). The frontend renders
 * both shapes; the LLM chapter-summary prompt currently emits the
 * string variant, but a richer future prompt can ship a multi-level
 * tree and this component will unfold it as deep as the data goes.
 */
export type MindMapDetail = string | MindMapNode;

interface MindMapNode {
  label: string;
  details?: MindMapDetail[];
}

interface MindMapData {
  title?: string;
  central_term: string;
  branches: MindMapNode[];
}

const PALETTE = [
  "oklch(70% 0.15 30)",
  "oklch(72% 0.13 90)",
  "oklch(68% 0.13 145)",
  "oklch(70% 0.13 200)",
  "oklch(70% 0.15 260)",
  "oklch(72% 0.15 320)",
];

// Truncate a label / detail to keep pills from overflowing the
// canvas. Full text always lives in the SVG <title> tag so hovering
// reveals it. The cap is conservative because long labels with
// adjacent branches collide horizontally even in single-open mode.
const MAX_LABEL_CHARS = 26;
const truncate = (s: string) => (s.length > MAX_LABEL_CHARS ? `${s.slice(0, MAX_LABEL_CHARS - 1)}…` : s);

/**
 * Radial mind-map: central term in the middle, branches arranged on
 * a circle around it.
 *
 * Two modes:
 *
 *   - Static (default, `interactive={false}`) — every branch's
 *     details render as small text labels next to the pill. Used
 *     inside flowing text (the RichExplanationView block) where a
 *     non-interactive overview is the right thing.
 *
 *   - Interactive (`interactive={true}`) — branches start collapsed.
 *     Tap a branch to drill in. SINGLE-OPEN: opening one branch
 *     auto-closes any previously open branch, which is the only
 *     reliable way to keep variable-width sub-pills from colliding
 *     with neighbouring branches on the SVG canvas. Sub-pills stack
 *     in a straight line outward from the branch in its radial
 *     direction (no arc fan). Sub-pills that themselves have
 *     `details` are clickable too — opening one shows ITS sub-pills
 *     stacked further out, so deeply nested trees unfold all the
 *     way down.
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
  // Interactive mode reserves a much bigger canvas because a fully-
  // unfolded chain of nested pills can extend a long way from the
  // centre. Static mode keeps the original compact aspect.
  const W = interactive ? Math.round(size * 1.4) : size;
  const H = interactive ? Math.round(size * 1.05) : Math.max(360, Math.round(size * 0.78));
  const cx = W / 2;
  const cy = H / 2;
  const radius = Math.min(W, H) * (interactive ? 0.22 : 0.34);

  // Single-open path key. A path is a sequence of indices
  // identifying which branch's nested chain is currently expanded.
  // For example [0, 1, 2] = branch 0 -> its detail 1 -> that
  // detail's nested detail 2. Empty string means nothing is open.
  // String-encoded so React can use it as a key.
  const [openPath, setOpenPath] = useState<number[]>([]);

  function isPathOpen(p: number[]): boolean {
    if (p.length > openPath.length) return false;
    for (let i = 0; i < p.length; i++) {
      if (openPath[i] !== p[i]) return false;
    }
    return true;
  }

  function togglePath(p: number[]) {
    if (isPathOpen(p) && p.length === openPath.length) {
      // Clicking the currently-open leaf: collapse this level.
      setOpenPath(openPath.slice(0, -1));
    } else if (isPathOpen(p)) {
      // Clicking a node further along the same open chain: stay there.
      setOpenPath(p);
    } else {
      // Clicking a fresh branch (or sub-branch): open exactly that path,
      // closing whatever was open elsewhere.
      setOpenPath(p);
    }
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
          const details = branch.details ?? [];

          const branchOpen = interactive && isPathOpen([i]);
          // Dim non-open branches when one is open, to spotlight the
          // current chain and keep visual noise down.
          const isDimmed = interactive && openPath.length > 0 && !branchOpen;

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
            <g key={`${i}-${branch.label}`} opacity={isDimmed ? 0.3 : 1} style={{ transition: "opacity 0.2s ease" }}>
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
                fullText={branch.label}
                fill={colour}
                hasChildren={interactive && details.length > 0}
                open={branchOpen}
                onClick={
                  interactive && details.length > 0
                    ? () => togglePath([i])
                    : undefined
                }
              />

              {!interactive &&
                details
                  .slice(0, 3)
                  .map((detail, di) => (
                    <text
                      key={di}
                      x={bx + dox}
                      y={by + doy + di * detailLineHeight * stackDir}
                      textAnchor={anchor}
                      fontSize={11}
                      fill="oklch(35% 0.01 260)"
                    >
                      {(() => {
                        const t = typeof detail === "string" ? detail : detail.label;
                        return t.length > 30 ? `${t.slice(0, 28)}…` : t;
                      })()}
                    </text>
                  ))}

              {/* Recursive expansion. Renders the open chain only —
                  single-open mode means at most one branch chain is
                  visible at a time. */}
              {interactive && branchOpen && (
                <NestedChain
                  details={details}
                  startX={bx}
                  startY={by}
                  dirX={dirX}
                  dirY={dirY}
                  colour={colour}
                  pathSoFar={[i]}
                  openPath={openPath}
                  onToggle={togglePath}
                />
              )}
            </g>
          );
        })}
        <CentralPill x={cx} y={cy} text={data.central_term} />
      </svg>

      {interactive && (
        <div className="mt-2 text-center text-xs text-(--color-muted-foreground)">
          Tap any branch to explore. Sub-points with a{" "}
          <span className="font-mono">+</span> can be opened further.
          {openPath.length > 0 && (
            <>
              {" · "}
              <button
                type="button"
                className="underline-offset-2 hover:underline"
                onClick={() => setOpenPath([])}
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

/* ---------- Nested chain (recursive sub-pill expansion) ---------- */

/**
 * Render one level of sub-pills extending outward from `(startX,
 * startY)` along `(dirX, dirY)`. Each sub-pill sits a fixed
 * distance further out than the previous level. If a sub-pill has
 * its own details and is the currently-open one at this depth,
 * recursively renders its chain too.
 *
 * The layout is strictly linear (no fan) so collisions with
 * neighbouring branches are impossible: a single open chain only
 * occupies the corridor along its branch's radial direction.
 */
function NestedChain({
  details,
  startX,
  startY,
  dirX,
  dirY,
  colour,
  pathSoFar,
  openPath,
  onToggle,
}: {
  details: MindMapDetail[];
  startX: number;
  startY: number;
  dirX: number;
  dirY: number;
  colour: string;
  pathSoFar: number[];
  openPath: number[];
  onToggle: (p: number[]) => void;
}) {
  // Per-level distances and offsets. We stack sub-pills LATERALLY
  // (perpendicular to the branch's radial direction) so they don't
  // sit on top of each other, then push the WHOLE stack outward as
  // the chain descends.
  const lateralSpacing = 32;
  const radialStep = 78;
  // Perpendicular unit vector for the lateral spread.
  const perpX = -dirY;
  const perpY = dirX;

  // Centre the lateral spread around the branch's radial line.
  const total = details.length;
  const lateralStart = -((total - 1) * lateralSpacing) / 2;

  return (
    <>
      {details.map((detail, di) => {
        const path = [...pathSoFar, di];
        const isOpenLeaf =
          openPath.length === path.length &&
          path.every((v, i) => v === openPath[i]);
        // For the path of an open chain to continue past this node,
        // openPath[di-position] === di
        const isOnOpenChain =
          openPath.length > path.length &&
          path.every((v, i) => v === openPath[i]);

        const lateral = lateralStart + di * lateralSpacing;
        const sx = startX + dirX * radialStep + perpX * lateral;
        const sy = startY + dirY * radialStep + perpY * lateral;

        const isNode = typeof detail !== "string";
        const label = isNode ? (detail as MindMapNode).label : (detail as string);
        const subDetails = isNode ? (detail as MindMapNode).details ?? [] : [];
        const hasChildren = subDetails.length > 0;
        const open = isOpenLeaf || isOnOpenChain;

        return (
          <g
            key={`${path.join("-")}`}
            className="animate-mindmap-pop"
            style={{
              transformOrigin: `${startX}px ${startY}px`,
              animationDelay: `${di * 40}ms`,
            }}
          >
            <line
              x1={startX}
              y1={startY}
              x2={sx}
              y2={sy}
              stroke={colour}
              strokeWidth={1.5}
              opacity={0.4}
            />
            <SubPill
              x={sx}
              y={sy}
              text={label}
              fullText={label}
              fill={colour}
              hasChildren={hasChildren}
              open={open}
              onClick={hasChildren ? () => onToggle(path) : undefined}
            />

            {/* Recurse only along the open chain. */}
            {hasChildren && open && (
              <NestedChain
                details={subDetails}
                startX={sx}
                startY={sy}
                dirX={dirX}
                dirY={dirY}
                colour={colour}
                pathSoFar={path}
                openPath={openPath}
                onToggle={onToggle}
              />
            )}
          </g>
        );
      })}
      {/* Pop animation — single inline style works for any
          NestedChain instance. */}
      <style>{`
        @keyframes mindmap-pop {
          0% { opacity: 0; transform: scale(0.6); }
          70% { opacity: 1; transform: scale(1.04); }
          100% { opacity: 1; transform: scale(1); }
        }
        .animate-mindmap-pop {
          animation: mindmap-pop 0.26s cubic-bezier(0.34, 1.56, 0.64, 1) backwards;
        }
        @media (prefers-reduced-motion: reduce) {
          .animate-mindmap-pop {
            animation: none;
          }
        }
      `}</style>
    </>
  );
}

/* ---------- Pills ---------- */

function CentralPill({ x, y, text }: { x: number; y: number; text: string }) {
  const padX = 18;
  const display = truncate(text);
  const approxWidth = Math.max(110, display.length * 9 + padX * 2);
  return (
    <g>
      <title>{text}</title>
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
        {display}
      </text>
    </g>
  );
}

function BranchPill({
  x,
  y,
  text,
  fullText,
  fill,
  hasChildren = false,
  open = false,
  onClick,
}: {
  x: number;
  y: number;
  text: string;
  fullText: string;
  fill: string;
  hasChildren?: boolean;
  open?: boolean;
  onClick?: () => void;
}) {
  const display = truncate(text);
  const chevWidth = hasChildren ? 18 : 0;
  const approxWidth = Math.max(80, display.length * 7 + 18 + chevWidth);
  const clickable = onClick !== undefined;
  return (
    <g
      onClick={onClick}
      style={clickable ? { cursor: "pointer" } : undefined}
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
      <title>{fullText}</title>
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
        textAnchor="middle"
        fontSize={12}
        fontWeight={600}
        fill="white"
      >
        {display}
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

/**
 * Sub-pill. Can itself be clickable when its node has nested
 * details — same +/- chevron treatment as a branch pill.
 */
function SubPill({
  x,
  y,
  text,
  fullText,
  fill,
  hasChildren = false,
  open = false,
  onClick,
}: {
  x: number;
  y: number;
  text: string;
  fullText: string;
  fill: string;
  hasChildren?: boolean;
  open?: boolean;
  onClick?: () => void;
}) {
  const display = truncate(text);
  const chevWidth = hasChildren ? 16 : 0;
  const approxWidth = Math.max(80, display.length * 6.6 + 18 + chevWidth);
  const clickable = onClick !== undefined;
  return (
    <g
      onClick={onClick}
      style={clickable ? { cursor: "pointer" } : undefined}
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
      <title>{fullText}</title>
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
        x={hasChildren ? x - 5 : x}
        y={y + 4}
        textAnchor="middle"
        fontSize={11}
        fill="oklch(35% 0.01 260)"
      >
        {display}
      </text>
      {hasChildren && (
        <text
          x={x + approxWidth / 2 - 9}
          y={y + 4}
          textAnchor="middle"
          fontSize={12}
          fontWeight={700}
          fill={fill}
          aria-hidden="true"
        >
          {open ? "−" : "+"}
        </text>
      )}
    </g>
  );
}
