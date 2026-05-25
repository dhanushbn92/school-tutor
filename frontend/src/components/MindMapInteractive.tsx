import { useEffect, useMemo, useRef } from "react";
import { Markmap, deriveOptions } from "markmap-view";
import type { IPureNode } from "markmap-common";

/**
 * Detail entries on a branch can be either:
 *   - plain strings (leaves with just text), or
 *   - nested {label, details} objects (sub-branches that themselves
 *     have children — the LLM prompt can be enriched later to emit
 *     these for chapters where multi-level structure is genuinely
 *     useful, and this component will render the depth automatically).
 */
export type MindMapDetail = string | MindMapNode;

/**
 * Interactive mind-map view, powered by `markmap-view` (the same
 * D3-backed engine used by Markmap.js — the popular markdown-to-
 * mindmap tool). markmap handles all the layout, geometry,
 * collision avoidance, pan, zoom, and click-to-expand for us.
 *
 * The viewer is HORIZONTAL by default (root on the left, branches
 * flowing right) — that's the shape that scales cleanly to many
 * nodes and deep nesting without crashing into itself, which is
 * what real mind-map products use. Pan = drag, zoom = mouse wheel
 * (or pinch on touch).
 *
 * Click any node → fold / unfold its children. By default we open
 * the root + first level so the learner sees the branch labels
 * immediately; deeper levels reveal on click.
 *
 * Data shape: takes the same `MindMapData` the rest of the app
 * uses (central_term + branches with optional nested details).
 * Converts to markmap's `IPureNode` tree internally.
 */

interface MindMapNode {
  label: string;
  details?: MindMapDetail[];
}

interface MindMapData {
  title?: string;
  central_term: string;
  branches: MindMapNode[];
}

// Same brand-friendly palette the static SVG mind map uses, so the
// interactive and embedded-text versions feel like the same product.
const PALETTE = [
  "#E67E5A", // warm coral
  "#D4A93E", // mustard
  "#7DAD4A", // herb green
  "#5BA9A2", // teal
  "#7E8AC8", // periwinkle
  "#C97AB0", // dusty pink
];

export function MindMapInteractive({
  data,
  height = 480,
}: {
  data: MindMapData;
  /** SVG height in pixels. The width fills the parent container. */
  height?: number;
}) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const mmRef = useRef<Markmap | null>(null);

  // Convert our data shape into markmap's IPureNode tree once per
  // data change. useMemo so we don't rebuild on every render.
  const tree: IPureNode = useMemo(() => toMarkmapTree(data), [data]);

  useEffect(() => {
    if (!svgRef.current) return;

    // Build markmap options. `deriveOptions` accepts the JSON-style
    // subset (color array, expand level, spacing, etc.) and returns
    // the runtime-shaped option object. We then spread in the
    // runtime-only options (autoFit) that don't have JSON forms.
    const baseOptions = deriveOptions({
      // Spread top-level branches with our palette so each branch
      // (and its descendants) keeps its colour identity, the way
      // the static mind map does. markmap converts this array
      // into a (node) => colour function under the hood.
      color: PALETTE,
      // Start with the root + first level visible; deeper nodes
      // reveal when the learner clicks. Avoids overwhelming them
      // with everything at once.
      initialExpandLevel: 2,
      maxWidth: 240,
      duration: 300,
      paddingX: 12,
      spacingHorizontal: 80,
      spacingVertical: 12,
      pan: true,
      zoom: true,
    });
    const options = {
      ...baseOptions,
      // Auto-fit on mount so the whole map is visible regardless of
      // size; user can then zoom in / out at will.
      autoFit: true,
    };

    const mm = Markmap.create(svgRef.current, options, tree);
    mmRef.current = mm;

    return () => {
      mm.destroy();
      mmRef.current = null;
    };
  }, [tree]);

  return (
    <div
      className="relative overflow-hidden rounded-md border border-(--color-border) bg-(--color-card)"
      style={{ height }}
    >
      <svg
        ref={svgRef}
        // markmap will set its own viewBox + dimensions via JS;
        // these are placeholders for SSR / first paint.
        style={{ width: "100%", height: "100%", display: "block" }}
        role="img"
        aria-label={data.title ?? data.central_term}
      />
      <div className="pointer-events-none absolute right-2 bottom-2 rounded-md bg-(--color-card)/85 px-2 py-1 text-[10px] text-(--color-muted-foreground) shadow-sm backdrop-blur-sm">
        Drag to pan · scroll to zoom · click any node to expand
      </div>
    </div>
  );
}

/* ---------- Data conversion ---------- */

/**
 * Convert our MindMapData (central_term + branches) into the
 * IPureNode tree shape markmap-view expects. Each branch's
 * `details` array may contain either strings (leaves) or nested
 * nodes (which themselves have their own details). The conversion
 * is recursive so arbitrarily-deep trees work.
 */
function toMarkmapTree(data: MindMapData): IPureNode {
  return {
    content: escapeHtml(data.central_term),
    children: data.branches.map(branchToMarkmap),
  };
}

function branchToMarkmap(branch: MindMapNode): IPureNode {
  return {
    content: escapeHtml(branch.label),
    children: (branch.details ?? []).map(detailToMarkmap),
  };
}

function detailToMarkmap(detail: MindMapDetail): IPureNode {
  if (typeof detail === "string") {
    return { content: escapeHtml(detail), children: [] };
  }
  return branchToMarkmap(detail);
}

/**
 * markmap renders node `content` as HTML. Our incoming labels are
 * plain text from the LLM, so we must escape any incidental angle
 * brackets / quotes before handing them off — otherwise a label
 * containing "<3" would break the rendering or be interpreted as
 * a tag.
 */
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
