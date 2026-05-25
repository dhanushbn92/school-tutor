import { useState } from "react";
import { ChevronDown, ChevronRight, Minimize2 } from "lucide-react";

/**
 * Recursive mind-map node. A `detail` can be either a plain string
 * (leaf — just a piece of text in a card) or another node that has
 * its own children. Both shapes render correctly; the LLM
 * chapter-summary prompt currently emits strings, but a richer
 * future prompt can ship a multi-level tree and this component
 * will unfold it as deep as the data goes.
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
 * MindMap with two modes:
 *
 *   - Static (default, `interactive={false}`) — radial SVG diagram
 *     with the central term in the middle and branches on a circle
 *     around it. Used inside flowing text (RichExplanationView)
 *     where it serves as an at-a-glance visual.
 *
 *   - Interactive (`interactive={true}`) — HTML-based tree view.
 *     Central concept at the top; branches as colour-coded cards
 *     in a responsive grid below; click any card to expand its
 *     children inline. Children can themselves be expandable nodes
 *     (multi-level). The whole tree lives in a scrollable container
 *     so an enormously deep expansion never crowds the page.
 *
 *     We use HTML for the interactive view because SVG has no
 *     auto-layout — variable-width pills sized to text content
 *     overlapped neighbours on the radial canvas. HTML flexbox/grid
 *     auto-flows everything correctly regardless of label length
 *     or tree depth.
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
    return <InteractiveTree data={data} />;
  }
  return <StaticRadial data={data} size={size} />;
}

/* ================================================================ */
/* Interactive tree (HTML)                                          */
/* ================================================================ */

function InteractiveTree({ data }: { data: MindMapData }) {
  // openBranchIdx tracks the single open top-level branch. Single-
  // open at the top level keeps the visual focused; nested levels
  // within an open branch can each manage their own open state, so
  // the learner can drill in multiple steps simultaneously inside
  // one branch.
  const [openBranchIdx, setOpenBranchIdx] = useState<number | null>(null);

  return (
    <div className="rounded-xl border border-(--color-border) bg-(--color-card) p-3">
      {/* Centre concept. Always visible at the top so the learner
          can see the "where am I" anchor while drilling in. */}
      <div className="mb-4 flex justify-center">
        <div className="rounded-full bg-(--color-primary) px-5 py-2 font-display text-base font-semibold text-(--color-primary-foreground) shadow-sm">
          {data.central_term}
        </div>
      </div>

      {/* Branch row. Responsive grid: as many columns as fit; each
          branch card is at least 220px wide. Branches are clickable
          to open / close. */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {data.branches.map((branch, i) => (
          <BranchCard
            key={`${i}-${branch.label}`}
            branch={branch}
            colour={PALETTE[i % PALETTE.length]}
            isOpen={openBranchIdx === i}
            onToggle={() =>
              setOpenBranchIdx((cur) => (cur === i ? null : i))
            }
            isAnyOpen={openBranchIdx !== null}
          />
        ))}
      </div>

      <div className="mt-3 text-center text-xs text-(--color-muted-foreground)">
        Tap any branch to explore. Sub-points with a chevron can be
        opened further.
        {openBranchIdx !== null && (
          <>
            {" · "}
            <button
              type="button"
              className="inline-flex items-center gap-1 underline-offset-2 hover:underline"
              onClick={() => setOpenBranchIdx(null)}
            >
              <Minimize2 className="h-3 w-3" />
              Collapse all
            </button>
          </>
        )}
      </div>
    </div>
  );
}

/* ---------- Branch card (top-level) ---------- */

function BranchCard({
  branch,
  colour,
  isOpen,
  onToggle,
  isAnyOpen,
}: {
  branch: MindMapNode;
  colour: string;
  isOpen: boolean;
  onToggle: () => void;
  isAnyOpen: boolean;
}) {
  const hasChildren = (branch.details ?? []).length > 0;
  // Dim other branches when one is open, to spotlight the current
  // drill-down without removing them entirely (the learner still
  // needs to see the alternatives).
  const dimmed = isAnyOpen && !isOpen;

  return (
    <div
      className="rounded-lg border transition-all"
      style={{
        borderColor: isOpen ? colour : "var(--color-border)",
        borderWidth: isOpen ? 2 : 1,
        opacity: dimmed ? 0.5 : 1,
        // Span the full row when open so the expanded content has
        // breathing room.
        gridColumn: isOpen ? "1 / -1" : undefined,
      }}
    >
      <button
        type="button"
        onClick={onToggle}
        disabled={!hasChildren}
        className="flex w-full items-center justify-between gap-2 rounded-t-lg px-3 py-2 text-left font-medium text-white"
        style={{ backgroundColor: colour }}
        aria-expanded={isOpen}
      >
        <span className="min-w-0 break-words">{branch.label}</span>
        {hasChildren && (
          <span className="shrink-0">
            {isOpen ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </span>
        )}
      </button>

      {isOpen && hasChildren && (
        // Scroll cap so an obscenely deep tree never breaks the
        // page layout. 60vh = ~half the screen; enough to read,
        // small enough to scroll past.
        <div className="max-h-[60vh] overflow-y-auto px-3 py-3">
          <NestedList details={branch.details!} colour={colour} depth={0} />
        </div>
      )}
    </div>
  );
}

/* ---------- Nested list (recursive) ---------- */

/**
 * Recursive renderer for the details inside an open branch. Each
 * detail is either:
 *
 *   - A plain string  → leaf row with a coloured bullet + text.
 *   - A `MindMapNode` → expandable row with its own +/− chevron,
 *                       which when opened recursively renders the
 *                       node's details one indent deeper.
 *
 * Indentation is communicated via a left-border in the branch's
 * colour, giving the tree the "branch line" feel of a classic
 * mind-map without needing absolute positioning.
 */
function NestedList({
  details,
  colour,
  depth,
}: {
  details: MindMapDetail[];
  colour: string;
  depth: number;
}) {
  return (
    <ul
      // Each level of depth indents 16px and shows a left border in
      // the branch colour, which visually traces the tree path.
      className="space-y-1"
      style={{
        paddingLeft: depth === 0 ? 0 : 16,
        borderLeft: depth === 0 ? "none" : `2px solid ${colour}33`,
        marginLeft: depth === 0 ? 0 : 4,
      }}
    >
      {details.map((detail, i) => (
        <DetailRow
          key={i}
          detail={detail}
          colour={colour}
          depth={depth}
        />
      ))}
    </ul>
  );
}

function DetailRow({
  detail,
  colour,
  depth,
}: {
  detail: MindMapDetail;
  colour: string;
  depth: number;
}) {
  // Each row owns its own open state so a learner can have several
  // sub-branches expanded simultaneously inside one top-level branch.
  // (Single-open lives at the top level only; once you're inside a
  // branch, drill freely.)
  const [open, setOpen] = useState(false);

  if (typeof detail === "string") {
    // Leaf — just a bullet + the text. No interaction.
    return (
      <li className="flex items-start gap-2 text-sm leading-relaxed text-(--color-foreground)">
        <span
          aria-hidden="true"
          className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full"
          style={{ backgroundColor: colour }}
        />
        <span className="min-w-0 break-words">{detail}</span>
      </li>
    );
  }

  const hasChildren = (detail.details ?? []).length > 0;

  return (
    <li>
      <button
        type="button"
        onClick={() => hasChildren && setOpen((o) => !o)}
        disabled={!hasChildren}
        className="flex w-full items-start gap-2 rounded-md px-2 py-1 text-left text-sm transition hover:bg-(--color-muted)/60 disabled:cursor-default disabled:hover:bg-transparent"
        aria-expanded={hasChildren ? open : undefined}
      >
        {hasChildren ? (
          <span
            className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full"
            style={{ backgroundColor: `${colour}22`, color: colour }}
          >
            {open ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </span>
        ) : (
          <span
            aria-hidden="true"
            className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full"
            style={{ backgroundColor: colour }}
          />
        )}
        <span className="min-w-0 break-words font-medium text-(--color-foreground)">
          {detail.label}
        </span>
      </button>
      {hasChildren && open && detail.details && (
        <div className="mt-1">
          <NestedList
            details={detail.details}
            colour={colour}
            depth={depth + 1}
          />
        </div>
      )}
    </li>
  );
}

/* ================================================================ */
/* Static radial SVG (unchanged — used in flowing-text contexts)    */
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
