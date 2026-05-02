import { useMemo } from "react";

export interface FlowNode {
  id: string;
  label: string;
  detail?: string | null;
  kind?: "start" | "step" | "decision" | "end";
}

export interface FlowEdge {
  src: string;
  dst: string;
  label?: string | null;
}

export interface FlowDiagramData {
  title: string;
  description?: string | null;
  nodes: FlowNode[];
  edges: FlowEdge[];
}

const NODE_W = 200;
const NODE_H = 56;
const ROW_GAP = 40;
const COL_GAP = 30;
const MARGIN = 24;

const KIND_FILL: Record<NonNullable<FlowNode["kind"]>, string> = {
  start: "#2f8d5b",
  step: "#4f6df5",
  decision: "#d99f15",
  end: "#7c3aed",
};

const KIND_STROKE: Record<NonNullable<FlowNode["kind"]>, string> = {
  start: "#1f6c44",
  step: "#3a51b8",
  decision: "#a87c11",
  end: "#5b25b5",
};

interface PositionedNode extends FlowNode {
  rank: number;
  col: number;
  x: number;
  y: number;
}

/** Layered top-down layout. Rank = BFS depth from any start-rooted node.
 *  Nodes within the same rank are spread evenly horizontally. */
export function FlowDiagram({ data }: { data: FlowDiagramData }) {
  const { positioned, edgesWithPath, width, height } = useMemo(() => {
    const byId = new Map(data.nodes.map((n) => [n.id, n]));
    const outgoing = new Map<string, string[]>();
    const incoming = new Map<string, string[]>();
    for (const n of data.nodes) {
      outgoing.set(n.id, []);
      incoming.set(n.id, []);
    }
    for (const e of data.edges) {
      outgoing.get(e.src)?.push(e.dst);
      incoming.get(e.dst)?.push(e.src);
    }

    // Rank assignment: BFS from nodes with no incoming edges, fall back to
    // first node. Diagrams may contain cycles (e.g. retry loops in the
    // scientific-method flow) — track visited nodes per BFS source so a back
    // edge doesn't cause an infinite loop. Each node's rank ends up as the
    // *shortest* distance from a root, which is what layered layouts expect.
    const rank = new Map<string, number>();
    const roots = data.nodes.filter(
      (n) => (incoming.get(n.id) || []).length === 0,
    );
    const seeds = roots.length ? roots : [data.nodes[0]];
    const queue: Array<{ id: string; depth: number }> = [];
    seeds.forEach((s) => {
      rank.set(s.id, 0);
      queue.push({ id: s.id, depth: 0 });
    });
    // Hard iteration cap is a defence in depth — even the fix below should
    // make this unreachable, but on a malformed graph we bail rather than hang.
    const maxIters = data.nodes.length * data.edges.length + data.nodes.length;
    let iters = 0;
    while (queue.length && iters++ < maxIters) {
      const { id, depth } = queue.shift()!;
      // If we've already assigned a smaller rank since this entry was queued,
      // skip — any descendants we'd produce would have rank >= existing+1
      // already, so re-walking adds nothing.
      const own = rank.get(id);
      if (own !== undefined && own < depth) continue;
      for (const dst of outgoing.get(id) || []) {
        const existing = rank.get(dst);
        const candidate = depth + 1;
        if (existing === undefined || candidate < existing) {
          rank.set(dst, candidate);
          queue.push({ id: dst, depth: candidate });
        }
        // else: dst already has a smaller-or-equal rank → don't re-walk.
      }
    }
    // Any unreached nodes go after the max
    let maxRank = 0;
    rank.forEach((r) => { if (r > maxRank) maxRank = r; });
    for (const n of data.nodes) {
      if (!rank.has(n.id)) rank.set(n.id, maxRank + 1);
    }
    maxRank = Math.max(...Array.from(rank.values()));

    // Group nodes by rank
    const byRank = new Map<number, FlowNode[]>();
    for (const n of data.nodes) {
      const r = rank.get(n.id) ?? 0;
      if (!byRank.has(r)) byRank.set(r, []);
      byRank.get(r)!.push(n);
    }

    const maxCols = Math.max(...Array.from(byRank.values()).map((row) => row.length));
    const width = MARGIN * 2 + maxCols * NODE_W + (maxCols - 1) * COL_GAP;

    const positioned: PositionedNode[] = [];
    for (const r of Array.from(byRank.keys()).sort((a, b) => a - b)) {
      const row = byRank.get(r)!;
      const rowWidth = row.length * NODE_W + (row.length - 1) * COL_GAP;
      const startX = (width - rowWidth) / 2;
      row.forEach((n, i) => {
        positioned.push({
          ...n,
          rank: r,
          col: i,
          x: startX + i * (NODE_W + COL_GAP),
          y: MARGIN + r * (NODE_H + ROW_GAP),
        });
      });
    }
    const height = MARGIN * 2 + (maxRank + 1) * NODE_H + maxRank * ROW_GAP;

    const posById = new Map(positioned.map((p) => [p.id, p]));
    const edgesWithPath = data.edges.map((e) => {
      const a = posById.get(e.src)!;
      const b = posById.get(e.dst)!;
      const ax = a.x + NODE_W / 2;
      const ay = a.y + NODE_H;
      const bx = b.x + NODE_W / 2;
      const by = b.y;
      // Cubic curve for nice flow
      const midY = (ay + by) / 2;
      const path = `M ${ax} ${ay} C ${ax} ${midY}, ${bx} ${midY}, ${bx} ${by}`;
      const labelX = (ax + bx) / 2;
      const labelY = midY;
      return { e, a, b, path, labelX, labelY, isBack: by < ay };
    });

    return { positioned, edgesWithPath, width, height };
    // byId is referenced in dev only; suppress unused warning by reading it.
    void byId;
  }, [data]);

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full">
        <defs>
          <marker
            id="flow-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#5b6184" />
          </marker>
        </defs>
        {edgesWithPath.map(({ e, path, labelX, labelY, isBack }, i) => (
          <g key={i}>
            <path
              d={path}
              fill="none"
              stroke={isBack ? "#a3a8c2" : "#5b6184"}
              strokeWidth={isBack ? 1.5 : 2}
              strokeDasharray={isBack ? "4 4" : "0"}
              markerEnd="url(#flow-arrow)"
            />
            {e.label && (
              <g transform={`translate(${labelX}, ${labelY})`}>
                <rect
                  x={-(e.label.length * 3.4 + 8)}
                  y={-9}
                  width={e.label.length * 6.8 + 16}
                  height={18}
                  rx={9}
                  fill="white"
                  stroke="#d6d8ee"
                />
                <text
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="11"
                  fill="#3a3f63"
                  fontWeight="600"
                >
                  {e.label}
                </text>
              </g>
            )}
          </g>
        ))}
        {positioned.map((n) => (
          <FlowNodeBox key={n.id} node={n} />
        ))}
      </svg>
    </div>
  );
}

function FlowNodeBox({ node }: { node: PositionedNode }) {
  const kind = node.kind ?? "step";
  const fill = KIND_FILL[kind];
  const stroke = KIND_STROKE[kind];
  const isDecision = kind === "decision";
  const isEnd = kind === "end" || kind === "start";
  return (
    <g transform={`translate(${node.x}, ${node.y})`}>
      {isDecision ? (
        <polygon
          points={`${NODE_W / 2},0 ${NODE_W},${NODE_H / 2} ${NODE_W / 2},${NODE_H} 0,${NODE_H / 2}`}
          fill={fill}
          stroke={stroke}
          strokeWidth={2}
        />
      ) : (
        <rect
          x={0}
          y={0}
          width={NODE_W}
          height={NODE_H}
          rx={isEnd ? NODE_H / 2 : 10}
          ry={isEnd ? NODE_H / 2 : 10}
          fill={fill}
          stroke={stroke}
          strokeWidth={2}
        />
      )}
      <text
        x={NODE_W / 2}
        y={node.detail ? NODE_H / 2 - 6 : NODE_H / 2 + 4}
        textAnchor="middle"
        fontSize={13}
        fontWeight={600}
        fill="white"
      >
        {trim(node.label, 30)}
      </text>
      {node.detail && (
        <text
          x={NODE_W / 2}
          y={NODE_H / 2 + 10}
          textAnchor="middle"
          fontSize={10}
          fill="white"
          fillOpacity={0.85}
        >
          {trim(node.detail, 50)}
        </text>
      )}
    </g>
  );
}

function trim(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}
