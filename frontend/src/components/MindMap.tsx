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

/** Radial mind-map: central term in the middle, branches arranged on a circle. */
export function MindMap({
  data,
  size = 520,
}: {
  data: MindMapData;
  size?: number;
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

        // Layout strategy for the per-branch detail block:
        //
        // Push the block radially OUTWARD past the pill so adjacent
        // branches' details fan into different quadrants and don't
        // collide horizontally. Subsequent detail lines stack in the
        // same vertical direction the block was pushed (down for bottom
        // branches, up for top branches) so they keep moving away from
        // the pill instead of folding back into it.
        //
        // Text anchor follows the branch's quadrant so text grows away
        // from the centre, not into a neighbouring branch:
        //   - branch on the right of centre  → "start" (text grows right)
        //   - branch on the left of centre   → "end"   (text grows left)
        //   - branch above/below centre      → "middle"
        const detailLineHeight = 14;
        const radialPush = 40; // px past the pill centre, along the branch direction
        const dox = dirX * radialPush;
        const doy = dirY * radialPush;
        const stackDir = dirY < -0.15 ? -1 : 1; // up for top branches, down otherwise
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
            <BranchPill x={bx} y={by} text={branch.label} fill={colour} />
            {/* Cap to 3 lines and ~30 chars to keep horizontal extent
                bounded — overlap was much worse before because each
                line could be 42 chars wide. */}
            {(branch.details ?? []).slice(0, 3).map((detail, di) => (
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
          </g>
        );
      })}
      <CentralPill x={cx} y={cy} text={data.central_term} />
    </svg>
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
