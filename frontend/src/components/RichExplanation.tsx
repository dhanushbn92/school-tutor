import { MindMap } from "@/components/MindMap";
import { FlowDiagram } from "@/components/FlowDiagram";
import type { FlowDiagramData } from "@/components/FlowDiagram";
import type { RichExplanation, RichExplanationBlock } from "@/lib/types";

/** Renders structured "rich explanation" blocks attached to a Question.
 *  Used on the post-quiz results page to give students a teacher-quality
 *  walk-through of the long-answer questions, complete with mind maps and
 *  flow diagrams. */
export function RichExplanationView({ data }: { data: RichExplanation }) {
  return (
    <div className="space-y-4">
      {data.blocks.map((block, i) => (
        <Block key={i} block={block} />
      ))}
    </div>
  );
}

interface MindMapBlockData {
  title?: string;
  central_term: string;
  branches: { label: string; details?: string[] }[];
}

function Block({ block }: { block: RichExplanationBlock }) {
  switch (block.type) {
    case "text":
      return (
        <p className="text-sm leading-relaxed text-(--color-foreground)">
          {block.content}
        </p>
      );
    case "list":
      return (
        <div>
          {block.title && (
            <div className="text-xs font-semibold uppercase tracking-wide text-(--color-muted-foreground) mb-1">
              {block.title}
            </div>
          )}
          <ul className="space-y-1 text-sm leading-relaxed">
            {(block.items ?? []).map((item, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-(--color-primary)">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      );
    case "mind_map": {
      const data = block.data as MindMapBlockData | undefined;
      if (!data) return null;
      return (
        <div className="overflow-x-auto rounded-md border border-(--color-border) bg-(--color-muted)/40 p-2">
          <MindMap data={data} size={420} />
        </div>
      );
    }
    case "flow_diagram": {
      const data = block.data as FlowDiagramData | undefined;
      if (!data) return null;
      return (
        <div className="rounded-md border border-(--color-border) bg-(--color-muted)/30 p-2">
          <FlowDiagram data={data} />
        </div>
      );
    }
    case "image_caption":
      return (
        <div className="text-xs italic text-(--color-muted-foreground)">
          {block.caption}
        </div>
      );
    default:
      return null;
  }
}
