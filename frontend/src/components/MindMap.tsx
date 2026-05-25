import { useState } from "react";

/**
 * Recursive mind-map node. A `detail` can be either a plain string
 * (leaf — just text in a sub-pill) or another node that has its
 * own children. The frontend renders both; the LLM chapter-summary
 * prompt currently emits strings, but a richer future prompt can
 * ship a multi-level tree and this component will unfold it as
 * deep as the data goes.
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

/**
 * Radial mind-map.
 *
 * Two modes:
 *
 *   - Static (`interactive={false}`, default) — compact radial SVG
 *     with central term + branches and their details as text
 *     labels. Used inside flowing text where a non-interactive
 *     overview is the right call.
 *
 *   - Interactive (`interactive={true}`) — radial SVG with the
 *     same central + branches visual, but each branch is clickable.
 *     Click a branch to fan its sub-pills out INSIDE THAT BRANCH'S
 *     ANGULAR SECTOR (so neighbouring branches' territory is never
 *     invaded). Sub-pills that are themselves nodes can be clicked
 *     to fan THEIR children further out — arbitrary depth. The
 *     whole SVG sits in a scrollable container so a deep expansion
 *     never breaks the page layout — the learner can pan around
 *     the diagram as it grows.
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
  if (interactive) {
    return <InteractiveRadial data={data} />;
  }
  return <StaticRadial data={data} size={size} />;
}

/* ================================================================ */
/* Interactive radial mind-map                                      */
/* ================================================================ */

// Layout constants. The canvas is intentionally large so a deeply
// expanded tree never butts against the edges; the wrapping
// container scrolls.
const CANVAS_W = 1400;
const CANVAS_H = 900;
const CENTER_X = CANVAS_W / 2;
const CENTER_Y = CANVAS_H / 2;
// Distance from centre to a top-level branch pill.
const R1 = 220;
// Radial step between each level of sub-pills, measured from the
// parent pill outward.
const R_STEP = 150;
// Maximum width any pill can take. Long labels wrap onto multiple
// lines via foreignObject HTML rendering. Without this cap, a
// 50-char label would stretch a pill across the entire sector and
// crash into the next branch.
const PILL_MAX_WIDTH = 160;
// Approximate chars that fit on one line at the current font size.
// Used to estimate pill heights for the layout maths.
const PILL_CHARS_PER_LINE = 18;
const PILL_LINE_HEIGHT = 16;
const PILL_VPAD = 10;

type Path = number[];

interface LaidOutNode {
  key: string;
  path: Path;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  colour: string;
  parentX: number;
  parentY: number;
  hasChildren: boolean;
  isOpen: boolean;
  /** True when this node is on the currently-open chain (its ancestor
   *  has been clicked to drill down). Used to dim siblings. */
  onOpenPath: boolean;
  /** True for the central node (rendered with the primary colour). */
  isCentre?: boolean;
  /** Depth in the tree — 0 = centre, 1 = top branch, 2 = sub-pill, … */
  depth: number;
}

function InteractiveRadial({ data }: { data: MindMapData }) {
  // Single open path through the tree. Empty = nothing expanded.
  // [0] = first branch open. [0, 2] = first branch open, its third
  // detail also open, and so on.
  const [openPath, setOpenPath] = useState<Path>([]);

  function toggleAt(path: Path) {
    setOpenPath((cur) => {
      // If clicking the currently-open leaf, collapse one level.
      if (
        cur.length === path.length &&
        path.every((v, i) => v === cur[i])
      ) {
        return cur.slice(0, -1);
      }
      // Otherwise open exactly this path (closes any other branch).
      return path;
    });
  }

  const nodes = computeLayout(data, openPath);

  return (
    <div className="relative">
      <div className="overflow-auto rounded-md border border-(--color-border) bg-(--color-card)" style={{ maxHeight: "70vh" }}>
        <svg
          viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
          width={CANVAS_W}
          height={CANVAS_H}
          role="img"
          aria-label={data.title ?? data.central_term}
          style={{ display: "block" }}
        >
          {/* Render connectors first so pills sit on top. */}
          {nodes
            .filter((n) => !n.isCentre)
            .map((n) => (
              <Connector
                key={`c-${n.key}`}
                fromX={n.parentX}
                fromY={n.parentY}
                toX={n.x}
                toY={n.y}
                colour={n.colour}
                dimmed={openPath.length > 0 && !n.onOpenPath && n.depth === 1}
              />
            ))}

          {/* Pills. */}
          {nodes.map((n) => (
            <Pill
              key={n.key}
              node={n}
              onClick={
                n.hasChildren && !n.isCentre
                  ? () => toggleAt(n.path)
                  : undefined
              }
              dimmed={
                !n.isCentre &&
                openPath.length > 0 &&
                !n.onOpenPath
              }
            />
          ))}
        </svg>
      </div>
      <div className="mt-2 text-center text-xs text-(--color-muted-foreground)">
        Tap any branch to fan it out. Pills with a{" "}
        <span className="font-mono">+</span> open further. Drag to pan
        if the diagram extends past the edge.
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
    </div>
  );
}

/* ---------- Layout ---------- */

/**
 * Compute the (x, y, w, h) for every visible pill given the data
 * + currently-open path. Returns a flat list of laid-out nodes
 * including the central pill, all top-level branches, and the
 * sub-pills along the open chain.
 *
 * The KEY rule that prevents overlap: each top-level branch owns
 * an angular SECTOR of `2π / N` radians around the centre. Its
 * sub-pills must fan within that sector (with a 15% safety margin)
 * — never into a neighbour's territory.
 *
 * Recursive sub-levels narrow their own cone within the parent's
 * sector so deeper nesting still doesn't escape the branch's
 * angular slice.
 */
function computeLayout(data: MindMapData, openPath: Path): LaidOutNode[] {
  const N = data.branches.length;
  const sectorAngle = (Math.PI * 2) / N;
  const nodes: LaidOutNode[] = [];

  // Central pill.
  const centreLabel = data.central_term;
  const centreSize = sizePill(centreLabel);
  nodes.push({
    key: "centre",
    path: [],
    label: centreLabel,
    x: CENTER_X,
    y: CENTER_Y,
    width: centreSize.width,
    height: centreSize.height,
    colour: "oklch(56% 0.14 257)",
    parentX: CENTER_X,
    parentY: CENTER_Y,
    hasChildren: true,
    isOpen: false,
    onOpenPath: false,
    isCentre: true,
    depth: 0,
  });

  data.branches.forEach((branch, i) => {
    const angle = i * sectorAngle - Math.PI / 2;
    const dirX = Math.cos(angle);
    const dirY = Math.sin(angle);
    const bx = CENTER_X + dirX * R1;
    const by = CENTER_Y + dirY * R1;
    const path: Path = [i];
    const onOpen = isPrefixOf(path, openPath);
    const colour = PALETTE[i % PALETTE.length];
    const branchSize = sizePill(branch.label);

    nodes.push({
      key: `b-${i}`,
      path,
      label: branch.label,
      x: bx,
      y: by,
      width: branchSize.width,
      height: branchSize.height,
      colour,
      parentX: CENTER_X,
      parentY: CENTER_Y,
      hasChildren: (branch.details ?? []).length > 0,
      isOpen: onOpen,
      onOpenPath: onOpen,
      depth: 1,
    });

    if (onOpen && branch.details && branch.details.length > 0) {
      // 85% of sector half-angle so adjacent sectors stay clear.
      const allowedHalfAngle = (sectorAngle / 2) * 0.85;
      layoutChildren(
        branch.details,
        path,
        bx,
        by,
        angle,
        allowedHalfAngle,
        colour,
        openPath,
        2,
        nodes,
      );
    }
  });

  return nodes;
}

/**
 * Recursively lay out the children of one node within an allowed
 * half-angle cone, then walk down the open path. Sub-pills fan in
 * a cone centred on the radial direction from `(px, py)`. Cones
 * narrow with depth so deep nesting stays inside the branch's
 * original sector.
 */
function layoutChildren(
  details: MindMapDetail[],
  parentPath: Path,
  px: number,
  py: number,
  parentAngle: number,
  allowedHalfAngle: number,
  colour: string,
  openPath: Path,
  depth: number,
  out: LaidOutNode[],
): void {
  const n = details.length;
  // Spread the children evenly across the cone, but cap individual
  // spacing so a tiny child set doesn't drift far apart.
  const spreadStep =
    n <= 1 ? 0 : Math.min((allowedHalfAngle * 2) / (n - 1), 0.35);
  const totalSpread = spreadStep * (n - 1);
  const startAngle = parentAngle - totalSpread / 2;
  // Stretch the radial reach with depth so deeper levels don't
  // bunch up too close to the parent pill.
  const reach = R_STEP + Math.max(0, (depth - 2) * 20);

  details.forEach((detail, i) => {
    const childAngle = n === 1 ? parentAngle : startAngle + i * spreadStep;
    const dirX = Math.cos(childAngle);
    const dirY = Math.sin(childAngle);
    const x = px + dirX * reach;
    const y = py + dirY * reach;
    const path = [...parentPath, i];
    const isNode = typeof detail !== "string";
    const label = isNode ? (detail as MindMapNode).label : (detail as string);
    const subDetails = isNode ? (detail as MindMapNode).details ?? [] : [];
    const hasChildren = subDetails.length > 0;
    const onOpen = isPrefixOf(path, openPath);
    const size = sizePill(label);

    out.push({
      key: `n-${path.join("-")}`,
      path,
      label,
      x,
      y,
      width: size.width,
      height: size.height,
      colour,
      parentX: px,
      parentY: py,
      hasChildren,
      isOpen: onOpen,
      onOpenPath: onOpen,
      depth,
    });

    if (hasChildren && onOpen) {
      // Narrow the child cone so grandchildren stay inside this
      // pill's local slice.
      const childAllowedHalfAngle = Math.max(
        allowedHalfAngle * 0.55,
        0.18,
      );
      layoutChildren(
        subDetails,
        path,
        x,
        y,
        childAngle,
        childAllowedHalfAngle,
        colour,
        openPath,
        depth + 1,
        out,
      );
    }
  });
}

/** True when `prefix` is a prefix of `path` (or equal). */
function isPrefixOf(prefix: Path, path: Path): boolean {
  if (prefix.length > path.length) return false;
  for (let i = 0; i < prefix.length; i++) {
    if (prefix[i] !== path[i]) return false;
  }
  return true;
}

/**
 * Estimate the pill's width + height from its label. We cap width
 * at PILL_MAX_WIDTH and grow vertically with line count. Without
 * this, long labels would stretch pills horizontally and crash
 * into neighbouring sectors.
 */
function sizePill(label: string): { width: number; height: number } {
  const lines = Math.max(1, Math.ceil(label.length / PILL_CHARS_PER_LINE));
  // Estimated width: pick PILL_MAX_WIDTH if any wrapping happens,
  // otherwise shrink to fit the actual text.
  const oneLineWidth = Math.min(label.length * 8 + 20, PILL_MAX_WIDTH);
  const width = lines > 1 ? PILL_MAX_WIDTH : oneLineWidth;
  const height = Math.max(34, lines * PILL_LINE_HEIGHT + PILL_VPAD * 2);
  return { width, height };
}

/* ---------- Visual primitives ---------- */

/**
 * Curved connector between parent and child. The curvature gives
 * the diagram an organic mind-map feel rather than the rigid look
 * of straight lines.
 */
function Connector({
  fromX,
  fromY,
  toX,
  toY,
  colour,
  dimmed,
}: {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  colour: string;
  dimmed: boolean;
}) {
  // Midpoint, bowed perpendicular to the line direction so the
  // curve fans away from the centre rather than crossing it.
  const mx = (fromX + toX) / 2;
  const my = (fromY + toY) / 2;
  return (
    <path
      d={`M ${fromX} ${fromY} Q ${mx} ${my} ${toX} ${toY}`}
      stroke={colour}
      strokeWidth={2}
      fill="none"
      opacity={dimmed ? 0.15 : 0.65}
      style={{ transition: "opacity 0.2s ease" }}
    />
  );
}

/**
 * One pill — central, branch, or sub-node. Renders the label as
 * HTML inside an SVG foreignObject so the browser can wrap long
 * text onto multiple lines automatically. A small +/− chevron sits
 * inside clickable pills (anything with children).
 */
function Pill({
  node,
  onClick,
  dimmed,
}: {
  node: LaidOutNode;
  onClick?: () => void;
  dimmed: boolean;
}) {
  const clickable = onClick !== undefined;
  const isCentre = node.isCentre === true;
  // Branches (depth 1) have a filled background in the branch
  // colour; sub-pills have a white background with a coloured
  // border for visual hierarchy.
  const filled = isCentre || node.depth === 1;
  const bg = filled
    ? node.colour
    : "var(--color-card)";
  const fg = filled ? "white" : "var(--color-foreground)";
  const border = filled ? node.colour : node.colour;
  const fontSize = isCentre ? 14 : 12;
  const fontWeight: 500 | 600 | 700 = isCentre ? 700 : 600;

  return (
    <g
      onClick={onClick}
      style={{
        cursor: clickable ? "pointer" : "default",
        opacity: dimmed ? 0.25 : 1,
        transition: "opacity 0.2s ease",
      }}
      tabIndex={clickable ? 0 : undefined}
      role={clickable ? "button" : undefined}
      aria-pressed={clickable ? node.isOpen : undefined}
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
      <title>{node.label}</title>
      <foreignObject
        x={node.x - node.width / 2}
        y={node.y - node.height / 2}
        width={node.width}
        height={node.height}
      >
        <div
          // Inline styles because SVG foreignObject children sit
          // outside Tailwind's normal cascade reliably.
          xmlns="http://www.w3.org/1999/xhtml"
          style={{
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 6,
            padding: `${PILL_VPAD}px 12px`,
            boxSizing: "border-box",
            background: bg,
            color: fg,
            border: `2px solid ${border}`,
            borderRadius: 14,
            fontSize,
            fontWeight,
            lineHeight: `${PILL_LINE_HEIGHT}px`,
            textAlign: "center",
            // Force wrapping for any continuous run of long chars.
            wordBreak: "break-word",
            overflowWrap: "break-word",
            boxShadow: node.isOpen
              ? "0 4px 14px rgba(0,0,0,0.15)"
              : "0 1px 3px rgba(0,0,0,0.08)",
          }}
        >
          <span style={{ minWidth: 0 }}>{node.label}</span>
          {node.hasChildren && !isCentre && (
            <span
              aria-hidden="true"
              style={{
                flex: "0 0 auto",
                fontSize: 14,
                fontWeight: 700,
                lineHeight: 1,
                opacity: 0.95,
              }}
            >
              {node.isOpen ? "−" : "+"}
            </span>
          )}
        </div>
      </foreignObject>
    </g>
  );
}

/* ================================================================ */
/* Static radial SVG (used in flowing-text contexts, unchanged)     */
/* ================================================================ */

function StaticRadial({
  data,
  size,
}: {
  data: MindMapData;
  size: number;
}) {
  const W = size;
  const H = Math.max(360, Math.round(size * 0.78));
  const cx = W / 2;
  const cy = H / 2;
  const radius = Math.min(W, H) * 0.34;

  return (
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

        const detailLineHeight = 14;
        const radialPush = 40;
        const dox = dirX * radialPush;
        const doy = dirY * radialPush;
        const stackDir = dirY < -0.15 ? -1 : 1;
        const anchor: "start" | "middle" | "end" =
          dirX > 0.25 ? "start" : dirX < -0.25 ? "end" : "middle";

        return (
          <g key={`${i}-${branch.label}`}>
            <line
              x1={cx}
              y1={cy}
              x2={bx}
              y2={by}
              stroke={colour}
              strokeWidth={2}
              opacity={0.65}
            />
            <BranchPillSvg x={bx} y={by} text={branch.label} fill={colour} />
            {(branch.details ?? [])
              .slice(0, 3)
              .map((detail, di) => {
                const text =
                  typeof detail === "string" ? detail : detail.label;
                return (
                  <text
                    key={di}
                    x={bx + dox}
                    y={by + doy + di * detailLineHeight * stackDir}
                    textAnchor={anchor}
                    fontSize={11}
                    fill="oklch(35% 0.01 260)"
                  >
                    {text.length > 30 ? `${text.slice(0, 28)}…` : text}
                  </text>
                );
              })}
          </g>
        );
      })}
      <CentralPillSvg x={cx} y={cy} text={data.central_term} />
    </svg>
  );
}

function CentralPillSvg({
  x,
  y,
  text,
}: {
  x: number;
  y: number;
  text: string;
}) {
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

function BranchPillSvg({
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
  const approxWidth = Math.max(80, text.length * 7 + 18);
  return (
    <g>
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
        x={x}
        y={y + 4}
        textAnchor="middle"
        fontSize={12}
        fontWeight={600}
        fill="white"
      >
        {text}
      </text>
    </g>
  );
}
