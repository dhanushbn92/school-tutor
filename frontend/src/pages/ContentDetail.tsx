import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  ClipboardList,
  FileText,
  Loader2,
  PlayCircle,
  ShieldOff,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { api, humanError } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { MindMap } from "@/components/MindMap";
import { FlowDiagram, type FlowDiagramData } from "@/components/FlowDiagram";
import { openArtifact } from "@/lib/artifact";
import { useGeneratedContent } from "@/lib/queries";
import type {
  ChapterSummaryOutput,
  ClassroomActivitySetOutput,
  GeneratedContentType,
  LessonPlanOutput,
  PPTOutlineOutput,
  WorksheetOutput,
} from "@/lib/types";
import {
  ActivitySetView,
  LessonPlanView,
  PPTOutlineView,
  SummaryView,
  WorksheetView,
} from "./LearnChapter";

const TYPE_LABEL: Record<GeneratedContentType, string> = {
  worksheet: "Worksheet",
  quiz: "Quiz",
  half_yearly_exam: "Half-yearly exam",
  ppt: "PPT outline",
  diagram: "Diagram",
  simulation: "Simulation",
  lesson_plan: "Lesson plan",
  chapter_summary: "Chapter summary",
  classroom_activity: "Classroom activity",
  resource_list: "Retired (resources)",
  flow_diagram: "Flow diagram",
  extra_content: "Extra content",
};

/** A standalone full-page renderer for any GeneratedContent row.
 *
 * The Content library opens artefacts (PDF/SVG/PPTX/HTML) in a new browser
 * tab via `openArtifact`. For content that lives only as `output_json`
 * (chapter summaries, classroom activities, resource lists, flow diagrams,
 * concept-map diagrams, lesson plans missing a DOCX), there's no file —
 * this page renders that JSON inline using the same components the chapter
 * page uses, so a teacher or platform admin can preview them on their own.
 */
export function ContentDetailPage() {
  const { contentId: contentIdParam } = useParams();
  const contentId = contentIdParam ? Number(contentIdParam) : undefined;
  const q = useGeneratedContent(contentId);

  if (q.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading…
      </div>
    );
  }
  if (!q.data) {
    return (
      <Empty
        icon={<FileText className="h-6 w-6" />}
        title="Content not found"
        description="It may have been retired or the URL is incorrect."
        action={
          <Button asChild variant="outline">
            <Link to="/content">
              <ArrowLeft className="h-4 w-4" /> Back to Content library
            </Link>
          </Button>
        }
      />
    );
  }

  const item = q.data;
  const typeLabel = TYPE_LABEL[item.content_type] ?? item.content_type;

  return (
    <ThemedPage>
      <PageHeader
        title={item.title}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{typeLabel}</Badge>
            <span className="text-(--color-muted-foreground)">
              Class {item.class_level ?? "—"}
              {item.chapter_id != null && ` · chapter #${item.chapter_id}`}
              {item.llm_model && ` · ${item.llm_model}`}
            </span>
          </span>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button asChild variant="outline">
              <Link to="/content">
                <ArrowLeft className="h-4 w-4" /> Back to library
              </Link>
            </Button>
            {item.chapter_id != null && (
              <Button asChild variant="outline">
                <Link to={`/learn/chapters/${item.chapter_id}`}>
                  Open chapter
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            )}
            {/* View-only types never expose an "Open file" affordance even
                if the row has an artifact_url — the inline view IS the
                surface. Extra-content uploads render as a no-toolbar PDF
                iframe; worksheets render as a structured Q&A; PPT decks
                render as an inline slide carousel. Simulation is the only
                "open in new tab" surface left, since HTML simulations need
                to run in their own browsing context. */}
            {item.artifact_url &&
              item.content_type !== "extra_content" &&
              item.content_type !== "worksheet" &&
              item.content_type !== "ppt" && (
                <Button
                  onClick={async () => {
                    try {
                      await openArtifact(item.id, { title: item.title });
                    } catch (err) {
                      toast.error(humanError(err));
                    }
                  }}
                >
                  <FileText className="h-4 w-4" /> Open file
                </Button>
              )}
          </div>
        }
      />

      <RenderByType item={item} />
    </ThemedPage>
  );
}


function RenderByType({ item }: { item: NonNullable<ReturnType<typeof useGeneratedContent>["data"]> }) {
  // The output_json shape is type-dependent; the schema-typed inline views
  // do their own runtime checks, so a soft cast through `unknown` is safe.
  const json = item.output_json as unknown;

  switch (item.content_type) {
    case "chapter_summary":
      return json ? (
        <SummaryView summary={json as ChapterSummaryOutput} />
      ) : (
        <Empty title="No summary content available" />
      );

    case "lesson_plan":
      return json ? (
        <LessonPlanView plan={json as LessonPlanOutput} />
      ) : (
        <Empty title="No lesson-plan content available" />
      );

    case "classroom_activity":
      return json ? (
        <ActivitySetView activitySet={json as ClassroomActivitySetOutput} />
      ) : (
        <Empty title="No activity content available" />
      );

    case "resource_list":
      // Retired surface: external-link resource lists were removed because
      // we don't surface external content in the platform anymore. Existing
      // rows are stamped RETIRED in the DB so they shouldn't reach this
      // branch in practice; render a tombstone if one slips through.
      return (
        <Empty
          title="This content has been retired"
          description="External-link resource lists are no longer shown on the platform. Look for an Extra content upload on the chapter page instead."
        />
      );

    case "diagram": {
      const data = json as
        | { title?: string; central_term: string; branches: { label: string; details?: string[] }[] }
        | null;
      if (!data) return <Empty title="No diagram data" />;
      return (
        <Card>
          <CardHeader>
            <CardTitle>{data.title ?? item.title ?? "Concept map"}</CardTitle>
            <CardDescription>
              A bird's-eye mind map of the chapter's main idea and how its
              sub-topics fit together.
            </CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <div className="rounded-lg border border-(--color-border) bg-(--color-card) p-2">
              <MindMap data={data} />
            </div>
          </CardContent>
        </Card>
      );
    }

    case "flow_diagram": {
      const data = json as FlowDiagramData | null;
      if (!data) return <Empty title="No flow-diagram data" />;
      return (
        <Card>
          <CardHeader>
            <CardTitle>{data.title || item.title || "Flow diagram"}</CardTitle>
            {data.description && (
              <CardDescription>{data.description}</CardDescription>
            )}
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-(--color-border) bg-(--color-card) p-2">
              <FlowDiagram data={data} />
            </div>
          </CardContent>
        </Card>
      );
    }

    case "extra_content":
      return <ExtraContentViewer item={item} />;

    case "worksheet":
      // Worksheets render inline as a structured Q&A view from
      // `output_json`. The PDF artefact still exists on disk for legacy
      // rows but is no longer surfaced — view-only inside the platform.
      return json ? (
        <WorksheetView worksheet={json as WorksheetOutput} />
      ) : (
        <Empty title="No worksheet content available" />
      );

    case "ppt":
      // PPT decks render inline as a slide carousel. The PPTX artefact is
      // no longer surfaced. Gating to teachers happens upstream — this
      // page is reachable via the Content library which is itself a
      // teacher / admin surface.
      return json ? (
        <PPTOutlineView deck={json as PPTOutlineOutput} />
      ) : (
        <Empty title="No slide deck content available" />
      );

    case "simulation": {
      // Simulations are HTML files served via the artifact endpoint and
      // opened in a new tab from the chapter Simulations tab. This page
      // only kicks in if the row exists but has no rendered artefact —
      // surface the JSON for triage.
      return (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlayCircle className="h-4 w-4" />
              No file rendered for this {TYPE_LABEL[item.content_type]?.toLowerCase()}
            </CardTitle>
            <CardDescription>
              This row exists in the catalog but its downloadable file hasn't
              been generated. Use the LLM-generated JSON below for a quick read,
              or ask the platform team to re-render it.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="max-h-[60vh] overflow-auto rounded-md bg-(--color-muted)/30 p-4 text-xs leading-relaxed">
              {JSON.stringify(item.output_json, null, 2)}
            </pre>
          </CardContent>
        </Card>
      );
    }

    case "quiz":
    case "half_yearly_exam":
      // Quizzes don't have a single inline view — questions live in the
      // question bank, the assembled quiz lives as an Assessment row.
      return (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardList className="h-4 w-4" /> Quiz / exam
            </CardTitle>
            <CardDescription>
              This generation produced questions that live in the question
              bank. Open the chapter or the assessments list to take the quiz.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {item.chapter_id != null && (
              <Button asChild variant="outline">
                <Link to={`/learn/chapters/${item.chapter_id}`}>
                  <Sparkles className="h-4 w-4" /> Practise this chapter
                </Link>
              </Button>
            )}
            <Button asChild variant="outline">
              <Link to="/assessments">
                <ClipboardList className="h-4 w-4" /> Open assessments
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/question-bank">
                Open question bank <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      );

    default:
      return <Empty title="No preview available for this content type" />;
  }
}


/**
 * In-platform viewer for platform-admin-uploaded supplementary documents.
 *
 * Loads the artefact as an authenticated blob (the artifact endpoint
 * requires a JWT and is not publicly readable), then renders it inline:
 *
 *   - PDFs go into an `<iframe>` with the URL fragment `#toolbar=0&navpanes=0`,
 *     which Chrome's built-in PDF viewer respects to suppress the download
 *     and print buttons. We don't expose any download affordance in our UI.
 *   - DOCX / DOC files don't have a browser-native viewer, so we surface a
 *     short notice + the metadata. The platform admin should upload PDFs
 *     for true inline view.
 *
 * View-only is enforced as best a browser allows: no Download button in
 * our SPA, the PDF viewer toolbar is hidden, no `<a download>` elements,
 * blob URLs are revoked on unmount. Determined users can still extract
 * the bytes via dev-tools — true DRM is out of scope.
 */
function ExtraContentViewer({
  item,
}: {
  item: NonNullable<ReturnType<typeof useGeneratedContent>["data"]>;
}) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [contentType, setContentType] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let revoked = false;
    let url: string | null = null;
    (async () => {
      try {
        const resp = await api.get<Blob>(
          `/generated-content/${item.id}/artifact`,
          { responseType: "blob" },
        );
        const ct = String(
          resp.headers["content-type"] ?? "application/octet-stream",
        ).split(";")[0].trim();
        const blob = new Blob([resp.data], { type: ct });
        url = URL.createObjectURL(blob);
        if (!revoked) {
          setBlobUrl(url);
          setContentType(ct);
        }
      } catch (err) {
        setErrorMsg(humanError(err));
      }
    })();
    return () => {
      revoked = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [item.id]);

  const meta = (item.output_json ?? {}) as {
    description?: string | null;
    original_filename?: string | null;
    size_bytes?: number | null;
  };

  if (errorMsg) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Couldn't load this document</CardTitle>
          <CardDescription>{errorMsg}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const isPdf = contentType === "application/pdf";
  const isWord =
    contentType ===
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
    contentType === "application/msword";

  return (
    <div className="space-y-3">
      {meta.description && (
        <Card>
          <CardContent className="pt-4 text-sm text-(--color-foreground)">
            {meta.description}
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-2 rounded-md border border-amber-300/60 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800/40 dark:bg-amber-950/15 dark:text-amber-200">
        <ShieldOff className="h-3.5 w-3.5" />
        <span>
          View-only: please don't download or share this document outside
          the platform.
        </span>
      </div>

      {!blobUrl ? (
        <div className="flex h-[60vh] items-center justify-center rounded-md border border-(--color-border)">
          <Loader2 className="h-5 w-5 animate-spin text-(--color-muted-foreground)" />
        </div>
      ) : isPdf ? (
        <div className="overflow-hidden rounded-md border border-(--color-border) bg-(--color-card)">
          {/* The `#toolbar=0&navpanes=0&scrollbar=1` fragment hides the
              built-in viewer's download/print/save buttons in Chromium-based
              browsers. Firefox renders without those controls anyway. */}
          <iframe
            title={item.title}
            src={`${blobUrl}#toolbar=0&navpanes=0&scrollbar=1`}
            className="h-[80vh] w-full"
            sandbox="allow-same-origin allow-scripts"
          />
        </div>
      ) : isWord ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Word document</CardTitle>
            <CardDescription>
              Browsers can't render `.docx` / `.doc` inline. Ask the platform
              team to re-upload as a PDF for in-platform viewing — we
              deliberately don't expose a download.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 text-xs text-(--color-muted-foreground)">
            {meta.original_filename && (
              <div>Original filename: <code>{meta.original_filename}</code></div>
            )}
            {meta.size_bytes != null && (
              <div>Size: {(meta.size_bytes / 1024).toFixed(1)} KB</div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Unsupported preview</CardTitle>
            <CardDescription>
              This file's MIME type ({contentType || "unknown"}) doesn't
              have an in-browser preview. Re-upload as PDF.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}
