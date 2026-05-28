import { useCallback, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, FileJson, Loader2, Upload, X } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { humanError } from "@/lib/api";
import {
  type BundleDryRunResult,
  type BundleIngestResult,
  useIngestContentBundle,
} from "@/lib/queries";

/**
 * Platform-admin tool for uploading a content-bundle JSON. Single-page
 * flow: pick file → dry-run preview → confirm → ingest → show report.
 *
 * The bundle format is documented in
 * `scripts/content_bundle_examples/README.md`. This page surfaces the
 * key rules inline so content creators don't have to dig through docs.
 */
export function ContentBundleUploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [dryRun, setDryRun] = useState<BundleDryRunResult | null>(null);
  const [ingestResult, setIngestResult] = useState<BundleIngestResult | null>(null);
  const [validationErrors, setValidationErrors] = useState<
    Array<{ field: string; message: string }>
  >([]);
  const [genericError, setGenericError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);

  const ingest = useIngestContentBundle();

  const reset = useCallback(() => {
    setFile(null);
    setDryRun(null);
    setIngestResult(null);
    setValidationErrors([]);
    setGenericError(null);
    if (fileInput.current) fileInput.current.value = "";
  }, []);

  const onFileChosen = useCallback((picked: File | null) => {
    setFile(picked);
    setDryRun(null);
    setIngestResult(null);
    setValidationErrors([]);
    setGenericError(null);
  }, []);

  const runIngest = useCallback(
    async (mode: "dry" | "real") => {
      if (!file) return;
      setValidationErrors([]);
      setGenericError(null);
      try {
        const result = await ingest.mutateAsync({ file, dry_run: mode === "dry" });
        if (result.dry_run) {
          setDryRun(result);
          setIngestResult(null);
        } else {
          setIngestResult(result);
          setDryRun(null);
        }
      } catch (err: unknown) {
        // The backend returns 422 with structured errors for schema failures.
        const e = err as {
          response?: { status?: number; data?: { detail?: unknown } };
        };
        const detail = e.response?.data?.detail;
        if (
          e.response?.status === 422 &&
          detail &&
          typeof detail === "object" &&
          "errors" in detail
        ) {
          const errs = (detail as { errors: Array<{ field: string; message: string }> }).errors;
          setValidationErrors(errs);
        } else {
          setGenericError(humanError(err));
        }
      }
    },
    [file, ingest],
  );

  return (
    <ThemedPage>
      <PageHeader
        title="Upload content bundle"
        description="Drop a content-bundle JSON to load any subset of chapter content. The minimum is just subject + chapter title + your questions. Dry-run first to preview what would be loaded."
      />

      {/* Drop zone + file picker */}
      <Card>
        <CardHeader>
          <CardTitle>1. Choose your bundle file</CardTitle>
          <CardDescription>
            A single JSON file. See the{" "}
            <a
              href="https://github.com/anaadi/school-tuter/blob/main/scripts/content_bundle_examples/README.md"
              target="_blank"
              rel="noreferrer"
              className="underline"
            >
              authoring guide
            </a>{" "}
            for the format. Maximum 5 MB.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            onDragEnter={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={(e) => {
              e.preventDefault();
              setDragActive(false);
            }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              const f = e.dataTransfer.files?.[0];
              if (f) onFileChosen(f);
            }}
            className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
              dragActive
                ? "border-(--color-primary) bg-(--color-primary)/5"
                : "border-(--color-border)"
            }`}
          >
            <Upload className="mb-3 h-8 w-8 text-(--color-muted-foreground)" />
            <p className="text-sm">
              Drag your bundle JSON here, or{" "}
              <button
                type="button"
                className="font-medium underline"
                onClick={() => fileInput.current?.click()}
              >
                browse
              </button>
            </p>
            <input
              ref={fileInput}
              type="file"
              accept=".json,application/json"
              className="hidden"
              onChange={(e) => onFileChosen(e.target.files?.[0] ?? null)}
            />
          </div>

          {file && (
            <div className="mt-4 flex items-center justify-between rounded-md border bg-(--color-muted)/30 p-3">
              <div className="flex items-center gap-2">
                <FileJson className="h-4 w-4 text-(--color-primary)" />
                <span className="text-sm font-medium">{file.name}</span>
                <Badge variant="outline" className="text-[10px]">
                  {(file.size / 1024).toFixed(1)} KB
                </Badge>
              </div>
              <button
                type="button"
                onClick={reset}
                className="rounded-sm text-(--color-muted-foreground) hover:text-(--color-foreground)"
                aria-label="Remove file"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Action buttons */}
      {file && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle>2. Validate or load</CardTitle>
            <CardDescription>
              Start with <strong>Dry run</strong> to preview the chapter and
              counts. Then click <strong>Load to platform</strong> to actually
              ingest.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => runIngest("dry")}
              disabled={ingest.isPending}
            >
              {ingest.isPending && ingest.variables?.dry_run ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Dry run (preview)
            </Button>
            <Button
              onClick={() => runIngest("real")}
              disabled={ingest.isPending || ingestResult !== null}
            >
              {ingest.isPending && !ingest.variables?.dry_run ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Load to platform
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Validation errors */}
      {validationErrors.length > 0 && (
        <Card className="mt-4 border-(--color-destructive)">
          <CardHeader className="flex flex-row items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-(--color-destructive)" />
            <CardTitle className="text-(--color-destructive)">
              Bundle failed schema validation
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-3 text-sm text-(--color-muted-foreground)">
              Fix each issue below in your JSON, then re-upload.
            </p>
            <ul className="space-y-2 text-sm">
              {validationErrors.map((err, i) => (
                <li
                  key={i}
                  className="rounded-md border border-(--color-destructive)/30 bg-(--color-destructive)/5 p-2"
                >
                  <div className="font-mono text-xs text-(--color-destructive)">
                    {err.field || "(root)"}
                  </div>
                  <div className="mt-0.5">{err.message}</div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {genericError && (
        <Card className="mt-4 border-(--color-destructive)">
          <CardHeader className="flex flex-row items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-(--color-destructive)" />
            <CardTitle className="text-(--color-destructive)">Upload failed</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">{genericError}</p>
          </CardContent>
        </Card>
      )}

      {/* Dry-run preview */}
      {dryRun && (
        <Card className="mt-4">
          <CardHeader className="flex flex-row items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-(--color-primary)" />
            <CardTitle>Dry-run preview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <Label className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
                Target chapter
              </Label>
              <p className="mt-1">
                <strong>{dryRun.curriculum.board}</strong> &nbsp;Class{" "}
                <strong>{dryRun.curriculum.class_level}</strong> &nbsp;
                {dryRun.curriculum.subject} &nbsp;— Chapter{" "}
                {dryRun.curriculum.chapter_number}:{" "}
                <strong>{dryRun.curriculum.chapter_title}</strong>
              </p>
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
                Would load
              </Label>
              <ul className="mt-1 grid gap-1 sm:grid-cols-2">
                {dryRun.would_load.chapter_text && <li>• chapter_text (replaces full_text)</li>}
                {dryRun.would_load.topics > 0 && (
                  <li>• {dryRun.would_load.topics} topic(s)</li>
                )}
                {dryRun.would_load.outcomes > 0 && (
                  <li>• {dryRun.would_load.outcomes} learning outcome(s)</li>
                )}
                {dryRun.would_load.questions > 0 && (
                  <li>• {dryRun.would_load.questions} question(s)</li>
                )}
                {dryRun.would_load.chapter_summary && <li>• chapter summary</li>}
                {dryRun.would_load.lesson_plan && <li>• lesson plan</li>}
                {dryRun.would_load.worksheet && <li>• worksheet (PDF will be re-rendered)</li>}
                {dryRun.would_load.ppt && <li>• PPT (PPTX will be re-rendered)</li>}
                {dryRun.would_load.diagram && <li>• diagram (SVG will be re-rendered)</li>}
                {dryRun.would_load.simulation && <li>• simulation (HTML will be re-rendered)</li>}
              </ul>
            </div>
            <p className="text-xs text-(--color-muted-foreground)">
              Nothing has been written to the database yet. Click{" "}
              <strong>Load to platform</strong> above to commit.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Real-ingest report */}
      {ingestResult && (
        <Card className="mt-4 border-(--color-primary)">
          <CardHeader className="flex flex-row items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-(--color-primary)" />
            <CardTitle>Bundle loaded</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p>
              Chapter <strong>#{ingestResult.report.chapter_id}</strong> updated.
            </p>
            <ul className="space-y-1">
              <li>
                <strong>Chapter text:</strong>{" "}
                {ingestResult.report.chapter_text_replaced ? "replaced" : "unchanged"}
              </li>
              <li>
                <strong>Topics:</strong> {ingestResult.report.topics.inserted} inserted,{" "}
                {ingestResult.report.topics.skipped} skipped
              </li>
              <li>
                <strong>Learning outcomes:</strong>{" "}
                {ingestResult.report.outcomes.inserted} inserted,{" "}
                {ingestResult.report.outcomes.skipped} skipped
              </li>
              <li>
                <strong>Questions:</strong> {ingestResult.report.questions.inserted} inserted,{" "}
                {ingestResult.report.questions.skipped} skipped (duplicates)
              </li>
              {ingestResult.report.content_blobs.replaced.length > 0 && (
                <li>
                  <strong>Replaced:</strong>{" "}
                  {ingestResult.report.content_blobs.replaced.join(", ")}
                </li>
              )}
              {ingestResult.report.content_blobs.inserted.length > 0 && (
                <li>
                  <strong>Newly added:</strong>{" "}
                  {ingestResult.report.content_blobs.inserted.join(", ")}
                </li>
              )}
            </ul>
            <Button variant="outline" onClick={reset} className="mt-2">
              Upload another bundle
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Quick rules / cheatsheet */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Format at a glance</CardTitle>
          <CardDescription>
            See the README in <code>scripts/content_bundle_examples/</code> for full details and worked examples.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div>
            <strong>Mandatory:</strong> only{" "}
            <code>curriculum.subject</code> and <code>curriculum.chapter_title</code>.
            The system finds the chapter automatically. If the same
            subject + chapter title exists in multiple boards or classes,
            you'll get a clear error asking for a <code>board</code> or{" "}
            <code>class_level</code> disambiguator.
          </div>
          <div>
            <strong>Just adding questions? </strong> A bundle with only{" "}
            <code>curriculum</code> + <code>questions</code> is valid —
            no summary, lesson plan, or anything else needed.
          </div>
          <div>
            <strong>Optional content blocks:</strong> chapter_text, topics,
            learning_outcomes, chapter_summary, lesson_plan, worksheet, ppt,
            diagram, simulation, questions. Include any subset.
          </div>
          <div>
            <strong>Idempotent on lists:</strong> topics, learning outcomes
            and questions are deduped by natural key (name, code, exact text)
            — re-uploading is safe.
          </div>
          <div>
            <strong>Replace-and-re-render:</strong> chapter_summary,
            lesson_plan, worksheet, ppt, diagram, simulation overwrite their
            existing row and regenerate the PDF/PPTX/SVG/HTML artefacts.
          </div>
        </CardContent>
      </Card>
    </ThemedPage>
  );
}
