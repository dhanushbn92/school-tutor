import { Fragment, useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  BookPlus,
  Code2,
  FileText,
  Loader2,
  Rocket,
  Sparkles,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
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
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { BoardContextBar } from "@/components/BoardContextBar";
import { humanError } from "@/lib/api";
import {
  useBooks,
  useBootstrapChapter,
  useBulkReplaceLearningOutcomes,
  useBulkReplaceTopics,
  useChapters,
  useClasses,
  useCreateBook,
  useCreateChapter,
  useCreateGeneration,
  useCreateSubject,
  useExtractPdfText,
  useExtractTopicsWithAi,
  useExtractTopicTexts,
  useGeneratedContent,
  useSubjects,
  useUploadExtraContent,
  useUploadStructuredContent,
} from "@/lib/queries";
import { VALID_BOARDS } from "@/lib/boards";
import { openArtifact } from "@/lib/artifact";
import type { GeneratedContentType } from "@/lib/types";
import { cn } from "@/lib/utils";

const CONTENT_TYPES: { value: GeneratedContentType; label: string; needsChapter: boolean }[] = [
  { value: "worksheet", label: "Worksheet (PDF)", needsChapter: true },
  { value: "quiz", label: "Quiz (question bank)", needsChapter: true },
  { value: "lesson_plan", label: "Lesson plan (DOCX)", needsChapter: true },
  { value: "ppt", label: "PPT outline (PPTX)", needsChapter: true },
  { value: "diagram", label: "Concept map (SVG)", needsChapter: true },
  { value: "simulation", label: "Simulation (HTML)", needsChapter: true },
];

// Keep this in sync with `SimulationTemplate` in
// `app/llm/schemas/simulation.py`. The dropdown is grouped by family
// in the order it renders so admins can scan by use-case.
type SimTemplate =
  | "auto"
  // Generic 2D activities
  | "match_pairs"
  | "categorize"
  | "timeline_order"
  | "sentence_builder"
  | "vocab_pairs"
  | "labeled_hotspots"
  // 2D math/science
  | "graph_explorer"
  | "circuit_2d"
  // 3D scenes
  | "three_d_scene"
  | "three_d_projectile"
  | "three_d_orbit"
  | "three_d_field_lines"
  | "three_d_wave"
  | "molecule_3d"
  // Tier-2 escape hatch
  | "custom_html";

interface SimTemplateOption {
  value: SimTemplate;
  label: string;
  /** Optional heading shown ABOVE this option to break the list into
   *  visually-grouped sections in the dropdown. */
  group?: string;
  description: string;
}

const SIM_TEMPLATES: SimTemplateOption[] = [
  // Auto
  { value: "auto", label: "Auto (let AI pick)", description: "Recommended — AI picks the best visual model for the chapter." },

  // Generic 2D activities — work for any subject.
  { value: "match_pairs",      group: "Activities (any subject)",   label: "Match the pairs",            description: "Two-column matching drill. Good for term ↔ definition, English ↔ translation, formula ↔ name." },
  { value: "categorize",       label: "Drag-and-sort (categorize)", description: "Drag items into labelled bins. Works for any classification topic — number sets, parts of speech, taxonomic groups." },
  { value: "timeline_order",   label: "Timeline / sequence",         description: "Drag events into chronological or causal order. Useful for processes, life cycles, problem-solving steps, historical events." },
  { value: "sentence_builder", label: "Sentence builder",            description: "Drag word/symbol tiles into the correct order. Languages grammar, mathematical proofs, logical syllogisms. Distractor tiles supported." },
  { value: "vocab_pairs",      label: "Vocabulary pairs / memory",   description: "Specialised pairs game with optional audio + image cards. Ships with a flip-and-find memory mode." },
  { value: "labeled_hotspots", label: "Labelled hotspots on an image", description: "Image with clickable hotspots. Anatomy, chemistry apparatus, geography maps, language image-vocab. Optional drag-the-label quiz mode." },

  // 2D Math / Science.
  { value: "graph_explorer",   group: "Math / Physics / Chemistry", label: "Graph explorer (function plotter)", description: "Slider-driven function plotting via math.js. y = a sin(bx + c), exponential decay, projectile range, dose-response, pH curves." },
  { value: "circuit_2d",       label: "Circuit schematic (2D)",       description: "Schematic-style circuit canvas with batteries, resistors, capacitors, switches. Auto-computes total R + I for series / parallel topologies." },

  // 3D scenes.
  { value: "three_d_scene",      group: "3D scenes (Three.js)", label: "3D scene (generic)",  description: "Centre + surrounding objects with edges. Works for solar systems, atoms, food webs, cells, ecosystems." },
  { value: "three_d_projectile", label: "3D projectile motion",         description: "Interactive launch with sliders for v0, angle, gravity, bearing. Animated trajectory + range / height / time of flight readouts." },
  { value: "three_d_orbit",      label: "3D orbital motion",             description: "Animated orbits with adjustable radii, periods, inclinations. Works for planetary systems, electron-around-nucleus, satellites." },
  { value: "three_d_field_lines", label: "3D field lines",               description: "Numerical streamlines around point sources for electric / magnetic / gravitational fields. Live density + length sliders." },
  { value: "three_d_wave",       label: "3D wave (string)",             description: "Animated wave with sliders for amplitude, wavelength, frequency. Switch between transverse, longitudinal, and standing modes." },
  { value: "molecule_3d",        label: "3D molecule (atoms + bonds)",  description: "Atom-and-bond viewer with CPK colouring. Click an atom for info. Single / double / triple bonds. Use for water, methane, benzene, DNA bases, amino acids." },

  // Tier-2 escape hatch.
  { value: "custom_html",        group: "Bespoke", label: "Custom HTML (sandboxed)", description: "Fully bespoke per-lesson sim. The LLM emits a self-contained HTML document that runs inside a sandboxed iframe (no platform data access). Use only when no template above fits — admin review required before publish." },
];

type Mode = "generate" | "upload" | "structured" | "onboard";

export function GeneratePage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("generate");
  const classesQ = useClasses();
  const [classLevel, setClassLevel] = useState<number | undefined>(undefined);
  const subjectsQ = useSubjects(classLevel);
  const [subjectId, setSubjectId] = useState<number | undefined>(undefined);
  const chaptersQ = useChapters({ class_level: classLevel, subject_id: subjectId });
  const [chapterId, setChapterId] = useState<number | undefined>(undefined);
  const [contentType, setContentType] = useState<GeneratedContentType>("worksheet");
  const [questionCount, setQuestionCount] = useState<number>(8);
  const [simTemplate, setSimTemplate] = useState<SimTemplate>("auto");

  const createGen = useCreateGeneration();
  const [activeId, setActiveId] = useState<number | undefined>(undefined);
  const activeGenQ = useGeneratedContent(activeId);

  // Auto-pick first options when they load
  useEffect(() => {
    if (!classLevel && classesQ.data && classesQ.data.length > 0) {
      const six = classesQ.data.find((c) => c.level === 6) ?? classesQ.data[0];
      setClassLevel(six.level);
    }
  }, [classLevel, classesQ.data]);
  useEffect(() => {
    if (!subjectId && subjectsQ.data && subjectsQ.data.length > 0) {
      const science = subjectsQ.data.find((s) => s.name === "Science") ?? subjectsQ.data[0];
      setSubjectId(science.id);
    }
  }, [subjectId, subjectsQ.data]);
  useEffect(() => {
    if (!chapterId && chaptersQ.data && chaptersQ.data.length > 0) {
      setChapterId(chaptersQ.data[0].id);
    }
  }, [chapterId, chaptersQ.data]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!classLevel || !subjectId) {
      toast.error("Pick a class and subject");
      return;
    }
    try {
      const options: Record<string, unknown> = {};
      if (contentType === "worksheet" || contentType === "quiz") {
        options.question_count = questionCount;
        options.include_answer_key = true;
      }
      if (contentType === "simulation" && simTemplate !== "auto") {
        options.template = simTemplate;
      }
      const row = await createGen.mutateAsync({
        content_type: contentType,
        class_level: classLevel,
        subject_id: subjectId,
        chapter_id: chapterId ?? null,
        force_regenerate: true,
        options,
      });
      setActiveId(row.id);
      toast.success(`Generation queued (id ${row.id})`);
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  const active = activeGenQ.data;

  return (
    <ThemedPage>
      <PageHeader
        title="Add content"
        description={
          mode === "generate"
            ? "Classroom-ready artefacts from chapter content and learning outcomes — built by the AI pipeline."
            : mode === "upload"
              ? "Upload a supplementary document (PDF / Word) for in-platform viewing. Users can read but cannot download."
              : mode === "onboard"
                ? "Bring a brand-new chapter onto the platform — paste the text or upload a PDF, then add topics and outcomes."
                : "Upload pre-built structured content (chapter summary, lesson plan, worksheet, …) as JSON. Validated against the platform schema before publishing."
        }
      />

      <div className="mb-6 flex flex-wrap gap-1 rounded-lg border border-(--color-border) bg-(--color-card) p-1">
        <button
          onClick={() => setMode("onboard")}
          className={cn(
            "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors",
            mode === "onboard"
              ? "bg-(--color-primary) text-(--color-primary-foreground)"
              : "hover:bg-(--color-muted)",
          )}
        >
          <BookPlus className="h-4 w-4" /> Onboard chapter
        </button>
        <button
          onClick={() => setMode("generate")}
          className={cn(
            "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors",
            mode === "generate"
              ? "bg-(--color-primary) text-(--color-primary-foreground)"
              : "hover:bg-(--color-muted)",
          )}
        >
          <Sparkles className="h-4 w-4" /> Generate with AI
        </button>
        <button
          onClick={() => setMode("structured")}
          className={cn(
            "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors",
            mode === "structured"
              ? "bg-(--color-primary) text-(--color-primary-foreground)"
              : "hover:bg-(--color-muted)",
          )}
        >
          <Code2 className="h-4 w-4" /> Upload structured content
        </button>
        <button
          onClick={() => setMode("upload")}
          className={cn(
            "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors",
            mode === "upload"
              ? "bg-(--color-primary) text-(--color-primary-foreground)"
              : "hover:bg-(--color-muted)",
          )}
        >
          <Upload className="h-4 w-4" /> Upload extra content
        </button>
      </div>

      {mode === "onboard" ? (
        <OnboardChapterFlow />
      ) : (
      <div className="grid gap-6 lg:grid-cols-2">
        {mode === "structured" ? <UploadStructuredForm /> : mode === "upload" ? <UploadExtraForm /> : (
        <Card>
          <CardHeader>
            <CardTitle>What would you like to generate?</CardTitle>
            <CardDescription>
              Pick a chapter and content type. We build from the outcomes on record.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Class</Label>
                  <Select
                    value={classLevel !== undefined ? String(classLevel) : ""}
                    onValueChange={(v) => {
                      setClassLevel(Number(v));
                      setSubjectId(undefined);
                      setChapterId(undefined);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Class..." />
                    </SelectTrigger>
                    <SelectContent>
                      {classesQ.data?.map((c) => (
                        <SelectItem key={c.id} value={String(c.level)}>
                          {c.display_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Subject</Label>
                  <Select
                    value={subjectId !== undefined ? String(subjectId) : ""}
                    onValueChange={(v) => {
                      setSubjectId(Number(v));
                      setChapterId(undefined);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Subject..." />
                    </SelectTrigger>
                    <SelectContent>
                      {subjectsQ.data?.map((s) => (
                        <SelectItem key={s.id} value={String(s.id)}>
                          [{s.board}] {s.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label>Chapter</Label>
                <Select
                  value={chapterId !== undefined ? String(chapterId) : ""}
                  onValueChange={(v) => setChapterId(Number(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Chapter..." />
                  </SelectTrigger>
                  <SelectContent>
                    {chaptersQ.data?.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>
                        Ch {c.chapter_number}. {c.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label>Content type</Label>
                <Select value={contentType} onValueChange={(v) => setContentType(v as GeneratedContentType)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CONTENT_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {(contentType === "worksheet" || contentType === "quiz") && (
                <div className="space-y-1.5">
                  <Label htmlFor="qcount">Number of questions</Label>
                  <Input
                    id="qcount"
                    type="number"
                    min={3}
                    max={20}
                    value={questionCount}
                    onChange={(e) => setQuestionCount(Number(e.target.value))}
                  />
                </div>
              )}

              {contentType === "simulation" && (
                <div className="space-y-1.5">
                  <Label>Simulation style</Label>
                  <Select value={simTemplate} onValueChange={(v) => setSimTemplate(v as SimTemplate)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {/* Partition the flat SIM_TEMPLATES list at every
                          item that starts a new group. Each partition
                          renders as a Radix `SelectGroup` with its
                          own `SelectLabel`. This is the structure
                          Radix expects — wrapping `Label` directly
                          inside `Content` (without `Group`) caused
                          the page to blank on simulation selection in
                          some browsers. */}
                      {(() => {
                        const groups: { name: string | null; items: typeof SIM_TEMPLATES }[] = [];
                        for (const t of SIM_TEMPLATES) {
                          if (t.group || groups.length === 0) {
                            groups.push({ name: t.group ?? null, items: [t] });
                          } else {
                            groups[groups.length - 1].items.push(t);
                          }
                        }
                        return groups.map((g, gi) => (
                          <Fragment key={g.name ?? `__nogroup_${gi}`}>
                            {gi > 0 && <SelectSeparator />}
                            <SelectGroup>
                              {g.name && <SelectLabel>{g.name}</SelectLabel>}
                              {g.items.map((t) => (
                                <SelectItem key={t.value} value={t.value}>
                                  {t.label}
                                </SelectItem>
                              ))}
                            </SelectGroup>
                          </Fragment>
                        ));
                      })()}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-(--color-muted-foreground)">
                    {SIM_TEMPLATES.find((t) => t.value === simTemplate)?.description}
                  </p>
                </div>
              )}

              <Button type="submit" disabled={createGen.isPending} className="w-full">
                {createGen.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Generate
              </Button>
            </form>
          </CardContent>
        </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Generation status</CardTitle>
            <CardDescription>
              {active ? `Latest: #${active.id}` : "Your generation will appear here once started."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!active && !activeGenQ.isLoading ? (
              <p className="text-sm text-(--color-muted-foreground)">
                Nothing in progress. Submit the form to begin.
              </p>
            ) : null}
            {active && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Badge
                    variant={
                      active.status === "ready"
                        ? "success"
                        : active.status === "failed"
                          ? "destructive"
                          : "warning"
                    }
                  >
                    {active.status.toUpperCase()}
                  </Badge>
                  <span className="text-sm">{active.title}</span>
                </div>
                {active.status === "pending" && (
                  <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    The model is writing. Polling every couple of seconds...
                  </div>
                )}
                {active.status === "failed" && (
                  <div className="rounded-md border border-(--color-destructive) bg-[color-mix(in_oklab,var(--color-destructive)_10%,transparent)] p-3 text-sm text-(--color-destructive)">
                    {active.error_message ?? "Generation failed."}
                  </div>
                )}
                {active.status === "ready" && active.artifact_url && (
                  <div className="flex gap-2">
                    <Button
                      onClick={async () => {
                        try {
                          await openArtifact(active.id, { title: active.title });
                        } catch (err) {
                          toast.error(humanError(err));
                        }
                      }}
                    >
                      Open artifact
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => navigate("/content")}
                    >
                      View in library
                    </Button>
                  </div>
                )}
                {active.status === "ready" && !active.artifact_url && (
                  <Button asChild variant="outline">
                    <Link to="/question-bank">Review generated questions</Link>
                  </Button>
                )}
                <div className="text-xs text-(--color-muted-foreground)">
                  Model: {active.llm_model ?? "—"} &middot; Type: {active.content_type}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      )}
    </ThemedPage>
  );
}


/**
 * Upload form for platform-admin-curated supplementary content.
 *
 * Accepts PDF and Word (.doc / .docx). PDFs render inline in the in-platform
 * viewer; Word docs surface a "view-only — please re-upload as PDF" notice
 * (browsers can't render Word). The artefact is stored authenticated; no
 * downloadable URL is exposed in the SPA.
 */
function UploadExtraForm() {
  const classesQ = useClasses();
  const [classLevel, setClassLevel] = useState<number | undefined>();
  const subjectsQ = useSubjects(classLevel);
  const [subjectId, setSubjectId] = useState<number | undefined>();
  const chaptersQ = useChapters({
    class_level: classLevel,
    subject_id: subjectId,
  });
  const [chapterId, setChapterId] = useState<number | undefined>();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const upload = useUploadExtraContent();

  function reset() {
    setTitle("");
    setDescription("");
    setFile(null);
    setChapterId(undefined);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!classLevel || !subjectId) {
      toast.error("Pick a class and subject");
      return;
    }
    if (!title.trim()) {
      toast.error("Give the document a title");
      return;
    }
    if (!file) {
      toast.error("Pick a file to upload");
      return;
    }
    try {
      const row = await upload.mutateAsync({
        title: title.trim(),
        class_level: classLevel,
        subject_id: subjectId,
        chapter_id: chapterId ?? null,
        description: description.trim() || null,
        file,
      });
      toast.success(`Uploaded — view at /content/${row.id}`);
      reset();
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload extra content</CardTitle>
        <CardDescription>
          PDF (preferred) or Word, up to 25 MB. The file appears in the
          chapter view as <em>view-only</em> — students and teachers can read
          but not download.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Class</Label>
              <Select
                value={classLevel !== undefined ? String(classLevel) : ""}
                onValueChange={(v) => {
                  setClassLevel(Number(v));
                  setSubjectId(undefined);
                  setChapterId(undefined);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Class..." />
                </SelectTrigger>
                <SelectContent>
                  {classesQ.data?.map((c) => (
                    <SelectItem key={c.id} value={String(c.level)}>
                      {c.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Subject</Label>
              <Select
                value={subjectId !== undefined ? String(subjectId) : ""}
                onValueChange={(v) => {
                  setSubjectId(Number(v));
                  setChapterId(undefined);
                }}
                disabled={classLevel === undefined}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      classLevel === undefined ? "Pick a class first" : "Subject..."
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {subjectsQ.data?.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      [{s.board}] {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Chapter (optional)</Label>
            <Select
              value={chapterId !== undefined ? String(chapterId) : ""}
              onValueChange={(v) => setChapterId(Number(v))}
              disabled={!chaptersQ.data?.length}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    subjectId === undefined
                      ? "Pick a subject first"
                      : "Pin to a chapter (optional)"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {chaptersQ.data?.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    Ch {c.chapter_number}. {c.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[11px] text-(--color-muted-foreground)">
              When set, the file appears under "Extra reading" on that chapter's page.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label>Title</Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Photosynthesis — extended reading"
              maxLength={200}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label>Description (optional)</Label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Short blurb shown above the document"
              maxLength={500}
            />
          </div>

          <div className="space-y-1.5">
            <Label>File (PDF or Word)</Label>
            <Input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
            {file && (
              <p className="flex items-center gap-2 text-[11px] text-(--color-muted-foreground)">
                <FileText className="h-3.5 w-3.5" />
                {file.name} · {(file.size / 1024).toFixed(1)} KB
              </p>
            )}
            <p className="text-[11px] text-(--color-muted-foreground)">
              Tip: PDFs render inline. Word documents are accepted but show
              a "view-only — please re-upload as PDF" notice because browsers
              can't preview them.
            </p>
          </div>

          <Button type="submit" disabled={upload.isPending} className="w-full">
            {upload.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            Upload
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}


// Content types that the structured-upload endpoint accepts. Mirrors the
// _STRUCTURED_UPLOAD_SCHEMAS dict on the backend — keep both in sync when
// adding new schema-backed types.
const STRUCTURED_CONTENT_TYPES: {
  value: GeneratedContentType;
  label: string;
  hint: string;
}[] = [
  {
    value: "chapter_summary",
    label: "Chapter summary",
    hint: "Intro, overview diagram, sections, key takeaways, and glossary.",
  },
  {
    value: "lesson_plan",
    label: "Lesson plan",
    hint: "Objectives, materials, phases, homework, assessment ideas.",
  },
  {
    value: "classroom_activity",
    label: "Classroom activities",
    hint: "Activity set with steps, materials, and guiding questions.",
  },
  {
    value: "worksheet",
    label: "Worksheet",
    hint: "Title, instructions, and a list of questions with answers.",
  },
  {
    value: "ppt",
    label: "Slide deck (PPT outline)",
    hint: "Slides with title, bullets, and optional speaker notes.",
  },
  {
    value: "diagram",
    label: "Concept map (mind map)",
    hint: "Central term plus a list of branches with sub-bullets.",
  },
  {
    value: "flow_diagram",
    label: "Flow diagram",
    hint: "Title, description, nodes (steps), and the edges between them.",
  },
];

/**
 * Upload form for hand-crafted structured content.
 *
 * Workflow:
 *   1. Pick the content type — the helper hint reminds the admin what
 *      shape the JSON needs to take.
 *   2. Pick class / subject / chapter (chapter optional).
 *   3. Give it a title.
 *   4. Either paste JSON into the textarea OR upload a .json file.
 *      If both are supplied, the textarea wins.
 *   5. Submit. Server validates against the matching Pydantic schema and
 *      surfaces validation errors inline.
 *
 * The textarea auto-fills when a file is selected, so the admin can
 * review/tweak before sending. Status is APPROVED on success.
 */
function UploadStructuredForm() {
  const classesQ = useClasses();
  const [classLevel, setClassLevel] = useState<number | undefined>();
  const subjectsQ = useSubjects(classLevel);
  const [subjectId, setSubjectId] = useState<number | undefined>();
  const chaptersQ = useChapters({
    class_level: classLevel,
    subject_id: subjectId,
  });
  const [chapterId, setChapterId] = useState<number | undefined>();
  const [contentType, setContentType] = useState<GeneratedContentType | undefined>();
  const [title, setTitle] = useState("");
  const [jsonText, setJsonText] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const upload = useUploadStructuredContent();

  function reset() {
    setTitle("");
    setJsonText("");
    setParseError(null);
    setChapterId(undefined);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  // When the admin picks a .json file, hydrate the textarea so they can
  // review the content before submitting. Reading via FileReader keeps
  // everything client-side; the file itself isn't sent to the server.
  function handleFile(file: File | null) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result ?? "");
      setJsonText(text);
      // Reset error so the textarea-validation effect re-runs.
      setParseError(null);
    };
    reader.onerror = () => {
      toast.error("Couldn't read that file");
    };
    reader.readAsText(file);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!classLevel || !subjectId) {
      toast.error("Pick a class and subject");
      return;
    }
    if (!contentType) {
      toast.error("Pick a content type");
      return;
    }
    if (!title.trim()) {
      toast.error("Give the content a title");
      return;
    }
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(jsonText);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Invalid JSON";
      setParseError(msg);
      toast.error(`JSON parse failed: ${msg}`);
      return;
    }
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      const msg = "JSON must be an object (curly braces), not an array or value";
      setParseError(msg);
      toast.error(msg);
      return;
    }
    setParseError(null);
    try {
      const row = await upload.mutateAsync({
        content_type: contentType,
        class_level: classLevel,
        subject_id: subjectId,
        chapter_id: chapterId ?? null,
        title: title.trim(),
        output_json: parsed,
      });
      toast.success(`Uploaded — view at /content/${row.id}`);
      reset();
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  const hint = STRUCTURED_CONTENT_TYPES.find((t) => t.value === contentType)?.hint;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload structured content</CardTitle>
        <CardDescription>
          Paste JSON (or upload a .json file) for any schema-backed content
          type. Validated against the platform schema before publishing —
          if anything's off, you'll see exactly which field needs fixing.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Content type</Label>
            <Select
              value={contentType ?? ""}
              onValueChange={(v) => setContentType(v as GeneratedContentType)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Pick a content type..." />
              </SelectTrigger>
              <SelectContent>
                {STRUCTURED_CONTENT_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {hint && (
              <p className="text-[11px] text-(--color-muted-foreground)">
                {hint}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Class</Label>
              <Select
                value={classLevel !== undefined ? String(classLevel) : ""}
                onValueChange={(v) => {
                  setClassLevel(Number(v));
                  setSubjectId(undefined);
                  setChapterId(undefined);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Class..." />
                </SelectTrigger>
                <SelectContent>
                  {classesQ.data?.map((c) => (
                    <SelectItem key={c.id} value={String(c.level)}>
                      {c.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Subject</Label>
              <Select
                value={subjectId !== undefined ? String(subjectId) : ""}
                onValueChange={(v) => {
                  setSubjectId(Number(v));
                  setChapterId(undefined);
                }}
                disabled={classLevel === undefined}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      classLevel === undefined ? "Pick a class first" : "Subject..."
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {subjectsQ.data?.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      [{s.board}] {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Chapter (optional)</Label>
            <Select
              value={chapterId !== undefined ? String(chapterId) : ""}
              onValueChange={(v) => setChapterId(Number(v))}
              disabled={!chaptersQ.data?.length}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    subjectId === undefined
                      ? "Pick a subject first"
                      : "Pin to a chapter (optional)"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {chaptersQ.data?.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    Ch {c.chapter_number}. {c.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Title</Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Photosynthesis — chapter summary"
              maxLength={200}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label>Upload .json file (optional)</Label>
            <Input
              ref={fileInputRef}
              type="file"
              accept=".json,application/json"
              onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
            />
            <p className="text-[11px] text-(--color-muted-foreground)">
              Picking a file pre-fills the JSON box below — review, edit if
              needed, then submit.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label>JSON content</Label>
            <textarea
              value={jsonText}
              onChange={(e) => {
                setJsonText(e.target.value);
                setParseError(null);
              }}
              placeholder={`{\n  "title": "...",\n  ...\n}`}
              rows={12}
              className="w-full rounded-md border border-(--color-input) bg-(--color-background) px-3 py-2 font-mono text-xs leading-relaxed shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--color-ring)"
              required
              spellCheck={false}
            />
            {parseError && (
              <p className="text-[11px] text-(--color-destructive)">
                {parseError}
              </p>
            )}
          </div>

          <Button type="submit" disabled={upload.isPending} className="w-full">
            {upload.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Code2 className="h-4 w-4" />
            )}
            Upload structured content
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}


// --------------------------------------------------------------------------
// Onboard chapter flow — three independent cards (create, topics, outcomes).
//
// The cards share an `activeChapterId` so the admin can chain operations:
// after creating a chapter, the topics and outcomes cards default to that
// chapter. Each card also lets the admin pick any other chapter to act on,
// so the workflow is sequential by default but not rigid.
// --------------------------------------------------------------------------

const BLOOM_LEVELS = [
  "remember",
  "understand",
  "apply",
  "analyze",
  "evaluate",
  "create",
] as const;
type BloomLevelLiteral = (typeof BLOOM_LEVELS)[number];

function OnboardChapterFlow() {
  // Shared state — set when a chapter is created, picked, or after a
  // bootstrap kicks off, so the manual cards default to it.
  const [activeChapterId, setActiveChapterId] = useState<number | undefined>();

  return (
    <div className="space-y-6">
      {/* Curriculum scaffolding — used rarely (typically when standing
          up a new board like NIOS). Sits at the top so admins find it
          when they're hitting the "no books available" empty state in
          the Create chapter card below. */}
      <div className="grid gap-6 lg:grid-cols-2">
        <CreateSubjectCard />
        <CreateBookCard />
      </div>
      {/* Quick bootstrap is the "lazy path": create a chapter, click
          one button, and the backend pipelines everything. The manual
          cards below are still useful for fine-grained control or for
          fixing up an already-onboarded chapter. */}
      <QuickBootstrapCard
        activeChapterId={activeChapterId}
        onPickChapter={setActiveChapterId}
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <CreateChapterCard onCreated={(id) => setActiveChapterId(id)} />
        <div className="space-y-6">
          <ChapterTopicsCard
            activeChapterId={activeChapterId}
            onPickChapter={setActiveChapterId}
          />
          <ChapterLearningOutcomesCard
            activeChapterId={activeChapterId}
            onPickChapter={setActiveChapterId}
          />
        </div>
      </div>
    </div>
  );
}

// --- Quick bootstrap (one-click full pipeline) --------------------------

/**
 * "Lazy path" onboarding: pick a chapter, hit one button, backend
 * extracts topics + slices topic texts + schedules every supported
 * content-type generation as a background job. The admin then watches
 * progress in the Content library — no further action needed unless
 * something fails.
 *
 * Topic extraction runs synchronously (fast), so the admin gets
 * immediate feedback that something happened. Everything else is
 * fire-and-forget on the server.
 */
function QuickBootstrapCard({
  activeChapterId,
  onPickChapter,
}: {
  activeChapterId: number | undefined;
  onPickChapter: (id: number) => void;
}) {
  const navigate = useNavigate();
  const bootstrap = useBootstrapChapter();

  async function handleClick() {
    if (!activeChapterId) {
      toast.error("Pick a chapter first");
      return;
    }
    const pendingToast = toast.loading(
      "Starting the chapter bootstrap… extracting topics now, queueing content generation in the background.",
    );
    try {
      const result = await bootstrap.mutateAsync({ chapter_id: activeChapterId });
      toast.dismiss(pendingToast);
      const parts = [
        `Extracted ${result.topics_extracted} topic${result.topics_extracted === 1 ? "" : "s"}`,
        result.topic_texts_scheduled ? "queued topic-text slicing" : null,
        result.jobs_scheduled.length
          ? `started ${result.jobs_scheduled.length} generation job${result.jobs_scheduled.length === 1 ? "" : "s"}`
          : null,
        result.jobs_reused.length
          ? `${result.jobs_reused.length} already cached`
          : null,
      ].filter(Boolean);
      toast.success(parts.join(" · "), {
        action: {
          label: "Open library",
          onClick: () => navigate("/content"),
        },
      });
    } catch (err) {
      toast.dismiss(pendingToast);
      toast.error(humanError(err));
    }
  }

  return (
    <Card
      className="border-2"
      style={{
        borderColor: "color-mix(in oklab, var(--color-primary) 40%, transparent)",
      }}
    >
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl md:text-2xl">
          <Rocket className="h-5 w-5 text-(--color-primary)" />
          Quick bootstrap (one click)
        </CardTitle>
        <CardDescription className="text-base">
          Pick a chapter that already has its full text loaded. We'll
          extract topics, slice topic texts for the AI tutor, and queue
          generation jobs for chapter summary, lesson plan, worksheet,
          slide deck, concept map, and simulation. Existing content is
          reused; new jobs run in the background — track them in the
          Content library.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ChapterPicker value={activeChapterId} onChange={onPickChapter} />
        <Button
          type="button"
          onClick={handleClick}
          disabled={bootstrap.isPending || !activeChapterId}
          className="w-full"
          size="lg"
        >
          {bootstrap.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Rocket className="h-4 w-4" />
          )}
          Generate everything for this chapter
        </Button>
        <p className="text-[11px] text-(--color-muted-foreground)">
          Idempotent: clicking again won't duplicate existing content;
          cached rows are preserved. Use the AI tab's "force regenerate"
          option per content type if you want to overwrite a specific
          piece of content.
        </p>
      </CardContent>
    </Card>
  );
}


// --- Curriculum scaffolding (subjects + books) --------------------------
//
// Rarely used (typically only when standing up a new board like NIOS).
// Each card is independent and short — admins fill, submit, move on.
// Both endpoints are platform-admin only on the backend; the Generate
// route is itself admin-gated so we don't add another role check here.

function CreateSubjectCard() {
  const classesQ = useClasses();
  const [classId, setClassId] = useState<number | undefined>();
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("en");
  const [board, setBoard] = useState<string>(VALID_BOARDS[0]);

  const createSubject = useCreateSubject();

  function reset() {
    setClassId(undefined);
    setName("");
    setLanguage("en");
    setBoard(VALID_BOARDS[0]);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!classId) {
      toast.error("Pick a class");
      return;
    }
    if (!name.trim()) {
      toast.error("Enter a subject name");
      return;
    }
    try {
      const row = await createSubject.mutateAsync({
        class_id: classId,
        name: name.trim(),
        language: language.trim() || "en",
        board,
      });
      toast.success(
        `Created ${row.board} ${row.name} for class ${row.class_id}. ` +
          `Now create a Book under it →`,
      );
      reset();
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base md:text-lg">Create subject</CardTitle>
        <CardDescription>
          Add a new subject to a class for any board. Use this when
          onboarding a brand-new board (e.g. NIOS) — the existing CBSE
          subjects stay untouched.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Class</Label>
              <Select
                value={classId !== undefined ? String(classId) : ""}
                onValueChange={(v) => setClassId(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Class..." />
                </SelectTrigger>
                <SelectContent>
                  {classesQ.data?.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Board</Label>
              <Select value={board} onValueChange={setBoard}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {VALID_BOARDS.map((b) => (
                    <SelectItem key={b} value={b}>
                      {b}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Subject name</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Mathematics"
                maxLength={120}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>Language</Label>
              <Input
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                placeholder="en"
                maxLength={20}
              />
            </div>
          </div>
          <Button
            type="submit"
            disabled={createSubject.isPending}
            className="w-full"
          >
            {createSubject.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <BookPlus className="h-4 w-4" />
            )}
            Create subject
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function CreateBookCard() {
  const classesQ = useClasses();
  const [classLevel, setClassLevel] = useState<number | undefined>();
  const subjectsQ = useSubjects(classLevel, { fetchAllWhenUndefined: false });
  const [subjectId, setSubjectId] = useState<number | undefined>();
  const [title, setTitle] = useState("");
  const [ncertCode, setNcertCode] = useState("");
  const [academicYear, setAcademicYear] = useState("2026-27");
  const [sourceUrl, setSourceUrl] = useState("");

  const createBook = useCreateBook();

  function reset() {
    setSubjectId(undefined);
    setTitle("");
    setNcertCode("");
    setAcademicYear("2026-27");
    setSourceUrl("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!subjectId) {
      toast.error("Pick a subject");
      return;
    }
    if (!title.trim() || !ncertCode.trim() || !academicYear.trim()) {
      toast.error("Title, code, and academic year are required");
      return;
    }
    try {
      const row = await createBook.mutateAsync({
        subject_id: subjectId,
        title: title.trim(),
        ncert_code: ncertCode.trim(),
        academic_year: academicYear.trim(),
        source_url: sourceUrl.trim() || null,
      });
      toast.success(
        `Created book "${row.title}" — now use the Create chapter card below to add chapters.`,
      );
      reset();
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base md:text-lg">Create book</CardTitle>
        <CardDescription>
          Add a book under an existing subject. The platform admin's
          subject picker shows every board, so you can attach a book to
          a NIOS subject just as easily as a CBSE one.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Class</Label>
              <Select
                value={classLevel !== undefined ? String(classLevel) : ""}
                onValueChange={(v) => {
                  setClassLevel(Number(v));
                  setSubjectId(undefined);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Class..." />
                </SelectTrigger>
                <SelectContent>
                  {classesQ.data?.map((c) => (
                    <SelectItem key={c.id} value={String(c.level)}>
                      {c.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Subject</Label>
              <Select
                value={subjectId !== undefined ? String(subjectId) : ""}
                onValueChange={(v) => setSubjectId(Number(v))}
                disabled={classLevel === undefined}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      classLevel === undefined
                        ? "Pick a class first"
                        : "Subject..."
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {subjectsQ.data?.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      [{s.board}] {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Book title</Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="NIOS Secondary Mathematics"
              maxLength={200}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Code</Label>
              <Input
                value={ncertCode}
                onChange={(e) => setNcertCode(e.target.value)}
                placeholder="nios-sec-math"
                maxLength={20}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>Academic year</Label>
              <Input
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                placeholder="2026-27"
                maxLength={20}
                required
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Source URL (optional)</Label>
            <Input
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="https://..."
            />
          </div>
          <Button
            type="submit"
            disabled={createBook.isPending}
            className="w-full"
          >
            {createBook.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <BookPlus className="h-4 w-4" />
            )}
            Create book
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}


// --- Card 1 -------------------------------------------------------------

function CreateChapterCard({ onCreated }: { onCreated: (id: number) => void }) {
  const classesQ = useClasses();
  const [classLevel, setClassLevel] = useState<number | undefined>();
  const subjectsQ = useSubjects(classLevel);
  const [subjectId, setSubjectId] = useState<number | undefined>();
  const booksQ = useBooks({ subject_id: subjectId });
  const [bookId, setBookId] = useState<number | undefined>();

  const [chapterNumber, setChapterNumber] = useState("");
  const [title, setTitle] = useState("");
  const [fullText, setFullText] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [pageCount, setPageCount] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const extractPdf = useExtractPdfText();
  const createChapter = useCreateChapter();
  const createBook = useCreateBook();

  // Resolve the picked subject + book so the context bar can display the
  // board prominently. We compute these on each render — both lookups
  // are O(N) over a small in-memory list, no perf concern.
  const selectedSubject = subjectsQ.data?.find((s) => s.id === subjectId);
  const selectedBook = booksQ.data?.find((b) => b.id === bookId);

  // "Auto-create a default book" mode: triggers when a subject is picked
  // and that subject has zero books yet. Without this, the admin would
  // hit a dead-end ("Pick a book first" error with no way to do so) the
  // very first time they onboard a chapter under a brand-new NIOS
  // subject. We make the missing book step transparent: a notice shows
  // up explaining what's about to happen, and submit handles both the
  // book + chapter creation in one flow.
  const noBooksYet =
    subjectId !== undefined &&
    booksQ.isSuccess &&
    (booksQ.data?.length ?? 0) === 0;

  function reset() {
    setChapterNumber("");
    setTitle("");
    setFullText("");
    setSourceUrl("");
    setPageCount(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handlePdfPick(file: File | null) {
    if (!file) return;
    try {
      const result = await extractPdf.mutateAsync({ file });
      setFullText(result.text);
      setPageCount(result.page_count);
      toast.success(
        `Extracted ${result.page_count} pages — review and edit if needed before creating the chapter.`,
      );
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    // Validate inputs that don't depend on book first so the admin gets
    // every fix-me message at once instead of trickling through.
    if (!subjectId || !selectedSubject) {
      toast.error("Pick a class and subject");
      return;
    }
    const num = Number(chapterNumber);
    if (!Number.isFinite(num) || num < 1) {
      toast.error("Chapter number must be a positive integer");
      return;
    }
    if (!title.trim()) {
      toast.error("Title is required");
      return;
    }
    if (!fullText.trim()) {
      toast.error("Paste the chapter text or extract it from a PDF");
      return;
    }
    // Resolve book — pick the dropdown value, OR auto-create a default
    // book if the subject has none yet. The default book uses a stable
    // ncert_code derived from the subject so a second attempt under the
    // same subject reuses it (the backend rejects duplicate codes; we
    // surface that as a clear toast).
    let effectiveBookId = bookId;
    if (!effectiveBookId) {
      if (!noBooksYet) {
        toast.error("Pick a book first");
        return;
      }
      try {
        const slug = selectedSubject.name
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .slice(0, 14);
        const board = selectedSubject.board.toLowerCase();
        const defaultBook = await createBook.mutateAsync({
          subject_id: subjectId,
          title: `${selectedSubject.board} ${selectedSubject.name} (Default)`,
          ncert_code: `${board}-${slug}-def`.slice(0, 20),
          academic_year: "2026-27",
        });
        effectiveBookId = defaultBook.id;
        toast.info(
          `Auto-created default book "${defaultBook.title}" — you can edit its title later.`,
        );
      } catch (err) {
        toast.error(
          `Couldn't auto-create a default book: ${humanError(err)}. ` +
            `Use the "Create book" card above and try again.`,
        );
        return;
      }
    }
    try {
      const row = await createChapter.mutateAsync({
        book_id: effectiveBookId,
        chapter_number: num,
        title: title.trim(),
        full_text: fullText,
        source_url: sourceUrl.trim() || null,
        page_count: pageCount,
      });
      toast.success(`Chapter created — id ${row.id}`);
      onCreated(row.id);
      reset();
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>1. Create chapter</CardTitle>
        <CardDescription>
          Pick a book, then either paste the chapter text or upload a PDF
          and we'll extract it for you.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <BoardContextBar
          classLevel={classLevel}
          subjectName={selectedSubject?.name}
          board={selectedSubject?.board}
          extra={selectedBook?.title}
        />
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Class</Label>
              <Select
                value={classLevel !== undefined ? String(classLevel) : ""}
                onValueChange={(v) => {
                  setClassLevel(Number(v));
                  setSubjectId(undefined);
                  setBookId(undefined);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Class..." />
                </SelectTrigger>
                <SelectContent>
                  {classesQ.data?.map((c) => (
                    <SelectItem key={c.id} value={String(c.level)}>
                      {c.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Subject</Label>
              <Select
                value={subjectId !== undefined ? String(subjectId) : ""}
                onValueChange={(v) => {
                  setSubjectId(Number(v));
                  setBookId(undefined);
                }}
                disabled={classLevel === undefined}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      classLevel === undefined ? "Pick a class first" : "Subject..."
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {subjectsQ.data?.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      [{s.board}] {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Book</Label>
            <Select
              value={bookId !== undefined ? String(bookId) : ""}
              onValueChange={(v) => setBookId(Number(v))}
              disabled={!booksQ.data?.length}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    subjectId === undefined
                      ? "Pick a subject first"
                      : noBooksYet
                        ? "No books yet — we'll auto-create one"
                        : "Book..."
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {booksQ.data?.map((b) => (
                  <SelectItem key={b.id} value={String(b.id)}>
                    {b.title} ({b.academic_year})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {noBooksYet && (
              // Inline helper so the admin doesn't see "Pick a book
              // first" as a dead-end. Surfaces the auto-create
              // behaviour up-front rather than hiding it inside the
              // submit handler.
              <p className="text-[11px] text-(--color-muted-foreground)">
                This subject has no books yet. We'll create a default
                book named{" "}
                <strong>
                  {selectedSubject?.board} {selectedSubject?.name} (Default)
                </strong>{" "}
                automatically when you click <em>Create chapter</em>. Use
                the <em>Create book</em> card above first if you want a
                specific book title / academic year.
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Chapter number</Label>
              <Input
                value={chapterNumber}
                onChange={(e) => setChapterNumber(e.target.value)}
                placeholder="3"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>Source URL (optional)</Label>
              <Input
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                placeholder="https://..."
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Title</Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="The Wonderful World of Science"
              maxLength={300}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label>Upload PDF (optional)</Label>
            <Input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => handlePdfPick(e.target.files?.[0] ?? null)}
              disabled={extractPdf.isPending}
            />
            <p className="text-[11px] text-(--color-muted-foreground)">
              Picking a PDF auto-fills the text box below — review and edit
              before creating. {extractPdf.isPending && "Extracting…"}
            </p>
          </div>

          <div className="space-y-1.5">
            <Label>Chapter text</Label>
            <textarea
              value={fullText}
              onChange={(e) => setFullText(e.target.value)}
              placeholder="Paste the full chapter text, or upload a PDF above to auto-fill."
              rows={10}
              className="w-full rounded-md border border-(--color-input) bg-(--color-background) px-3 py-2 text-xs leading-relaxed shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--color-ring)"
              required
            />
            {pageCount !== null && (
              <p className="text-[11px] text-(--color-muted-foreground)">
                Page count from PDF: {pageCount}
              </p>
            )}
          </div>

          <Button
            type="submit"
            disabled={createChapter.isPending}
            className="w-full"
          >
            {createChapter.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <BookPlus className="h-4 w-4" />
            )}
            Create chapter
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// --- Helper: chapter picker reused by Cards 2 + 3 -----------------------

function ChapterPicker({
  value,
  onChange,
}: {
  value: number | undefined;
  onChange: (id: number) => void;
}) {
  const classesQ = useClasses();
  const [classLevel, setClassLevel] = useState<number | undefined>();
  const subjectsQ = useSubjects(classLevel);
  const [subjectId, setSubjectId] = useState<number | undefined>();
  const chaptersQ = useChapters({
    class_level: classLevel,
    subject_id: subjectId,
  });

  // Resolve subject + chapter for the context bar so the topics /
  // outcomes cards always show which board they're operating on.
  const selectedSubject = subjectsQ.data?.find((s) => s.id === subjectId);
  const selectedChapter = chaptersQ.data?.find((c) => c.id === value);

  return (
    <div className="space-y-3">
      <BoardContextBar
        classLevel={classLevel}
        subjectName={selectedSubject?.name}
        board={selectedSubject?.board}
        extra={
          selectedChapter
            ? `Ch ${selectedChapter.chapter_number}. ${selectedChapter.title}`
            : undefined
        }
      />
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="space-y-1.5">
        <Label className="text-xs">Class</Label>
        <Select
          value={classLevel !== undefined ? String(classLevel) : ""}
          onValueChange={(v) => {
            setClassLevel(Number(v));
            setSubjectId(undefined);
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Class..." />
          </SelectTrigger>
          <SelectContent>
            {classesQ.data?.map((c) => (
              <SelectItem key={c.id} value={String(c.level)}>
                {c.display_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5">
        <Label className="text-xs">Subject</Label>
        <Select
          value={subjectId !== undefined ? String(subjectId) : ""}
          onValueChange={(v) => setSubjectId(Number(v))}
          disabled={classLevel === undefined}
        >
          <SelectTrigger>
            <SelectValue placeholder="Subject..." />
          </SelectTrigger>
          <SelectContent>
            {subjectsQ.data?.map((s) => (
              <SelectItem key={s.id} value={String(s.id)}>
                [{s.board}] {s.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5">
        <Label className="text-xs">Chapter</Label>
        <Select
          value={value !== undefined ? String(value) : ""}
          onValueChange={(v) => onChange(Number(v))}
          disabled={!chaptersQ.data?.length}
        >
          <SelectTrigger>
            <SelectValue placeholder="Chapter..." />
          </SelectTrigger>
          <SelectContent>
            {chaptersQ.data?.map((c) => (
              <SelectItem key={c.id} value={String(c.id)}>
                Ch {c.chapter_number}. {c.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
    </div>
  );
}

// --- Card 2 -------------------------------------------------------------

function ChapterTopicsCard({
  activeChapterId,
  onPickChapter,
}: {
  activeChapterId: number | undefined;
  onPickChapter: (id: number) => void;
}) {
  const [topicsText, setTopicsText] = useState("");
  const bulkReplace = useBulkReplaceTopics();
  const aiExtract = useExtractTopicsWithAi();
  const sliceTexts = useExtractTopicTexts();

  // Parse the textarea: each line is "name | description" or just "name".
  // Blank lines are ignored. Returns an array of topic items or null on
  // any malformed line so we can fail loudly without writing partial data.
  function parseTopics(): { name: string; description?: string }[] | null {
    const lines = topicsText
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    if (lines.length === 0) return null;
    return lines.map((l) => {
      const idx = l.indexOf("|");
      if (idx === -1) return { name: l };
      return {
        name: l.slice(0, idx).trim(),
        description: l.slice(idx + 1).trim() || undefined,
      };
    });
  }

  async function handleManualSubmit() {
    if (!activeChapterId) {
      toast.error("Pick a chapter first");
      return;
    }
    const parsed = parseTopics();
    if (!parsed || parsed.length === 0) {
      toast.error("Add at least one topic");
      return;
    }
    try {
      const rows = await bulkReplace.mutateAsync({
        chapter_id: activeChapterId,
        topics: parsed,
      });
      toast.success(`Saved ${rows.length} topic${rows.length === 1 ? "" : "s"}`);
      setTopicsText("");
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  async function handleAiExtract() {
    if (!activeChapterId) {
      toast.error("Pick a chapter first");
      return;
    }
    try {
      const rows = await aiExtract.mutateAsync({
        chapter_id: activeChapterId,
        overwrite: false,
      });
      const lines = rows
        .map((t) => `${t.name} | ${t.description ?? ""}`)
        .join("\n");
      setTopicsText(lines);
      toast.success(
        `Extracted ${rows.length} topic${rows.length === 1 ? "" : "s"}. ` +
          `Edit the list and click Save to overwrite, or leave as-is.`,
      );
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  async function handleSliceTexts() {
    if (!activeChapterId) {
      toast.error("Pick a chapter first");
      return;
    }
    // The op is genuinely slow (one LLM call per topic). Pre-warn the
    // admin so they don't think the page froze. The button stays
    // disabled while pending.
    const pendingToast = toast.loading(
      "Slicing topic texts… one LLM call per topic, this may take a minute or two.",
    );
    try {
      const result = await sliceTexts.mutateAsync({
        chapter_id: activeChapterId,
        overwrite: false,
      });
      toast.dismiss(pendingToast);
      const parts: string[] = [];
      if (result.written > 0) parts.push(`wrote ${result.written}`);
      if (result.skipped > 0) parts.push(`skipped ${result.skipped} already-populated`);
      if (result.errored > 0) parts.push(`${result.errored} errored`);
      const summary = parts.join(", ") || "no topics processed";
      if (result.errored > 0) {
        toast.warning(`Topic texts: ${summary}. Check the Onboard tab again to retry.`);
      } else {
        toast.success(`Topic texts: ${summary}.`);
      }
    } catch (err) {
      toast.dismiss(pendingToast);
      toast.error(humanError(err));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>2. Topics</CardTitle>
        <CardDescription>
          Either extract them from chapter text with AI, or paste your own
          (one per line). Saving replaces any existing topics on the chapter.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ChapterPicker value={activeChapterId} onChange={onPickChapter} />
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={handleAiExtract}
            disabled={aiExtract.isPending || !activeChapterId}
          >
            {aiExtract.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Extract topics with AI
          </Button>
          {/* Topic-text slicing: per-topic verbatim slice for the AI
              tutor's RAG context. Only useful once topics exist on the
              chapter; we don't gate that here because the backend
              already returns a clean error if there are no topics. */}
          <Button
            type="button"
            variant="outline"
            onClick={handleSliceTexts}
            disabled={sliceTexts.isPending || !activeChapterId}
            title={
              activeChapterId
                ? "Slice each topic's verbatim text from the chapter for AI tutor topic-scoped chat"
                : "Pick a chapter first"
            }
          >
            {sliceTexts.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileText className="h-4 w-4" />
            )}
            Slice topic texts (AI tutor)
          </Button>
        </div>
        <div className="space-y-1.5">
          <Label>Topics (one per line — "name | description")</Label>
          <textarea
            value={topicsText}
            onChange={(e) => setTopicsText(e.target.value)}
            placeholder={`Magnetic Poles | Two ends of a magnet that attract or repel\nProperties of a Magnet | Behaviours like attraction, repulsion, polarity`}
            rows={8}
            className="w-full rounded-md border border-(--color-input) bg-(--color-background) px-3 py-2 text-xs leading-relaxed shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--color-ring)"
          />
        </div>
        <Button
          type="button"
          onClick={handleManualSubmit}
          disabled={bulkReplace.isPending || !activeChapterId}
          className="w-full"
        >
          {bulkReplace.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ArrowRight className="h-4 w-4" />
          )}
          Save topics
        </Button>
      </CardContent>
    </Card>
  );
}

// --- Card 3 -------------------------------------------------------------

function ChapterLearningOutcomesCard({
  activeChapterId,
  onPickChapter,
}: {
  activeChapterId: number | undefined;
  onPickChapter: (id: number) => void;
}) {
  const [outcomesText, setOutcomesText] = useState("");
  const bulkReplace = useBulkReplaceLearningOutcomes();

  // Parse outcomes: each line is "code | bloom | description | topic_name?"
  // bloom must be one of the 6 valid values. Any unknown bloom or a line
  // missing required fields raises so we show a clear toast instead of
  // sending invalid data to the server.
  function parseOutcomes():
    | {
        code: string;
        description: string;
        bloom_level: BloomLevelLiteral;
        topic_name?: string;
      }[]
    | string {
    const lines = outcomesText
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    if (lines.length === 0) return "Paste at least one outcome";
    const out: ReturnType<typeof parseOutcomes> = [];
    for (let i = 0; i < lines.length; i++) {
      const parts = lines[i].split("|").map((p) => p.trim());
      if (parts.length < 3) {
        return `Line ${i + 1}: need at least "code | bloom | description"`;
      }
      const [code, bloomRaw, description, topicName] = parts;
      const bloom = bloomRaw.toLowerCase();
      if (!BLOOM_LEVELS.includes(bloom as BloomLevelLiteral)) {
        return `Line ${i + 1}: bloom_level "${bloomRaw}" must be one of ${BLOOM_LEVELS.join(", ")}`;
      }
      (out as ReturnType<typeof parseOutcomes> & object[]).push({
        code,
        description,
        bloom_level: bloom as BloomLevelLiteral,
        topic_name: topicName || undefined,
      });
    }
    return out;
  }

  async function handleSubmit() {
    if (!activeChapterId) {
      toast.error("Pick a chapter first");
      return;
    }
    const parsed = parseOutcomes();
    if (typeof parsed === "string") {
      toast.error(parsed);
      return;
    }
    try {
      const rows = await bulkReplace.mutateAsync({
        chapter_id: activeChapterId,
        outcomes: parsed,
      });
      toast.success(
        `Saved ${rows.length} learning outcome${rows.length === 1 ? "" : "s"}`,
      );
      setOutcomesText("");
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>3. Learning outcomes</CardTitle>
        <CardDescription>
          One outcome per line: <code>code | bloom | description | topic
          name (optional)</code>. Bloom level must be one of: remember,
          understand, apply, analyze, evaluate, create.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ChapterPicker value={activeChapterId} onChange={onPickChapter} />
        <div className="space-y-1.5">
          <Label>Outcomes</Label>
          <textarea
            value={outcomesText}
            onChange={(e) => setOutcomesText(e.target.value)}
            placeholder={`WOS-1 | remember | List two examples of physical changes\nWOS-2 | understand | Explain why ice melts when heated | States of Matter`}
            rows={8}
            className="w-full rounded-md border border-(--color-input) bg-(--color-background) px-3 py-2 text-xs leading-relaxed shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--color-ring)"
          />
        </div>
        <Button
          type="button"
          onClick={handleSubmit}
          disabled={bulkReplace.isPending || !activeChapterId}
          className="w-full"
        >
          {bulkReplace.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ArrowRight className="h-4 w-4" />
          )}
          Save outcomes
        </Button>
      </CardContent>
    </Card>
  );
}
