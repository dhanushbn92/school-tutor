import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  FileText,
  Filter,
  FolderOpen,
  Image as ImageIcon,
  Loader2,
  Presentation,
  Puzzle,
  Sparkles,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Empty } from "@/components/ui/empty";
import {
  useChapterDetail,
  useChapters,
  useGeneratedContentList,
} from "@/lib/queries";
import { useAvailableClasses, useAvailableSubjects } from "@/lib/scope";
import { openArtifact } from "@/lib/artifact";
import { ThemedPage } from "@/components/themed";
import { BoardContextBar, labelForSubject } from "@/components/BoardContextBar";
import { humanError } from "@/lib/api";
import type { GeneratedContentType } from "@/lib/types";

const TYPE_META: Record<
  GeneratedContentType | "all",
  { label: string; icon: React.ReactNode }
> = {
  all: { label: "All types", icon: <FolderOpen className="h-4 w-4" /> },
  worksheet: { label: "Worksheet", icon: <FileText className="h-4 w-4" /> },
  quiz: { label: "Quiz", icon: <FileText className="h-4 w-4" /> },
  lesson_plan: { label: "Lesson plan", icon: <FileText className="h-4 w-4" /> },
  ppt: { label: "PPT outline", icon: <Presentation className="h-4 w-4" /> },
  diagram: { label: "Diagram", icon: <ImageIcon className="h-4 w-4" /> },
  simulation: { label: "Simulation", icon: <Puzzle className="h-4 w-4" /> },
  half_yearly_exam: { label: "Half-yearly exam", icon: <FileText className="h-4 w-4" /> },
  chapter_summary: { label: "Chapter summary", icon: <FileText className="h-4 w-4" /> },
  classroom_activity: { label: "Classroom activity", icon: <FileText className="h-4 w-4" /> },
  // resource_list is intentionally hidden from the UI — no external links.
  // The TYPE_META row stays so legacy rows still resolve a label/icon.
  resource_list: { label: "(retired) Resources", icon: <FileText className="h-4 w-4" /> },
  flow_diagram: { label: "Flow diagram", icon: <ImageIcon className="h-4 w-4" /> },
  extra_content: { label: "Extra content", icon: <FileText className="h-4 w-4" /> },
};

const TYPE_OPTIONS: (GeneratedContentType | "all")[] = [
  "all",
  "worksheet",
  "quiz",
  "lesson_plan",
  "ppt",
  "diagram",
  "simulation",
  "extra_content",
];

const ALL = "all" as const;

export function ContentLibraryPage() {
  // Teachers are scoped to their assigned classes. We auto-select their first
  // class as the default and hide "All classes" from the picker so they can't
  // accidentally see content for classes they don't teach. Other roles see
  // every curriculum class and start with no class filter.
  const available = useAvailableClasses();
  const initialClass: number | "all" =
    available.isScoped && available.classes[0]
      ? available.classes[0].level
      : ALL;

  // Cascading filter state. ALL means "no filter on this dimension."
  const [classLevel, setClassLevel] = useState<number | "all">(initialClass);
  const [subjectId, setSubjectId] = useState<number | "all">(ALL);
  const [chapterId, setChapterId] = useState<number | "all">(ALL);
  const [topicId, setTopicId] = useState<number | "all">(ALL);
  const [contentType, setContentType] = useState<GeneratedContentType | "all">(ALL);

  // Once the scoped-classes list resolves we may need to bump the default —
  // initialClass was computed before the query settled.
  useEffect(() => {
    if (
      available.isScoped &&
      classLevel === ALL &&
      available.classes[0]
    ) {
      setClassLevel(available.classes[0].level);
    }
  }, [available.isScoped, available.classes, classLevel]);

  // For teachers this returns the intersection of "subjects of classLevel"
  // with their assignments — so a teacher who teaches only Class 6 Science
  // will see just Science in the subject dropdown when Class 6 is picked.
  const subjectsScope = useAvailableSubjects(
    classLevel === ALL ? undefined : classLevel,
  );
  const chaptersQ = useChapters({
    class_level: classLevel === ALL ? undefined : classLevel,
    subject_id: subjectId === ALL ? undefined : subjectId,
  });
  const chapterDetailQ = useChapterDetail(chapterId === ALL ? undefined : chapterId);

  // When a parent filter changes, blank out the descendants so we never show a
  // stale child selection that no longer matches the parent's options.
  useEffect(() => {
    setSubjectId(ALL);
    setChapterId(ALL);
    setTopicId(ALL);
  }, [classLevel]);
  useEffect(() => {
    setChapterId(ALL);
    setTopicId(ALL);
  }, [subjectId]);

  // Scoped users (teachers) don't get an "All subjects" option — without this
  // the Select trigger would show no label after the class auto-resets to ALL.
  // Auto-pin to the first assigned subject of the chosen class so they always
  // see content scoped to one of their subjects.
  useEffect(() => {
    if (
      subjectsScope.isScoped &&
      classLevel !== ALL &&
      subjectsScope.subjects.length > 0 &&
      (subjectId === ALL ||
        !subjectsScope.subjects.some((s) => s.id === subjectId))
    ) {
      setSubjectId(subjectsScope.subjects[0].id);
    }
  }, [subjectsScope.isScoped, subjectsScope.subjects, classLevel, subjectId]);
  useEffect(() => {
    setTopicId(ALL);
  }, [chapterId]);

  const listQ = useGeneratedContentList({
    content_type: contentType === ALL ? undefined : contentType,
    // After the catalog reorientation (Phase A) every published artifact is
    // APPROVED. Platform admins can still see READY/DRAFT via the Generate
    // page; this view is the curated catalog.
    status: "approved",
    class_level: classLevel === ALL ? undefined : classLevel,
    subject_id: subjectId === ALL ? undefined : subjectId,
    chapter_id: chapterId === ALL ? undefined : chapterId,
    limit: 200,
  });

  // Topic filter is client-side: many of our generations don't carry a topic_id,
  // so applying it server-side would hide otherwise-relevant chapter content.
  const items = useMemo(() => {
    if (!listQ.data) return [];
    if (topicId === ALL) return listQ.data;
    return listQ.data.filter((item) => item.topic_id === topicId);
  }, [listQ.data, topicId]);

  // For a scoped user (teacher) the "default" classLevel is their first
  // assigned class, and the default subjectId is auto-pinned by an effect
  // above. Neither should count as an active filter — only chapter, topic,
  // and content-type should drive the "Clear all" pill.
  const defaultClassLevel: number | "all" =
    available.isScoped && available.classes[0]
      ? available.classes[0].level
      : ALL;
  const anyFilterActive = available.isScoped
    ? chapterId !== ALL || topicId !== ALL || contentType !== ALL
    : classLevel !== defaultClassLevel ||
      subjectId !== ALL ||
      chapterId !== ALL ||
      topicId !== ALL ||
      contentType !== ALL;

  const topics = chapterDetailQ.data?.topics ?? [];
  const noTopicsForChapter =
    chapterId !== ALL && chapterDetailQ.isSuccess && topics.length === 0;

  function clearFilters() {
    setChapterId(ALL);
    setTopicId(ALL);
    setContentType(ALL);
    if (!available.isScoped) {
      setClassLevel(defaultClassLevel);
      setSubjectId(ALL);
    }
    // Scoped users keep their auto-pinned class/subject — clearing those
    // would leave the dropdowns empty (since "All" isn't an option for them).
  }

  // Teacher with no subject assignments AND not a class teacher of any
  // section — without this guard their dropdowns would be empty and the
  // listing would still query server-side without a class filter.
  if (
    !available.isLoading &&
    available.isScoped &&
    available.classes.length === 0
  ) {
    return (
      <ThemedPage>
        <PageHeader
          title="Content library"
          description="Browse AI-generated content for the subjects you teach."
        />
        <Empty
          icon={<FolderOpen className="h-6 w-6" />}
          title="No subjects assigned to you yet"
          description="Ask your school admin to assign you to subjects (Manage school → Teachers). Your content will appear here once assigned."
        />
      </ThemedPage>
    );
  }

  return (
    <ThemedPage>
      <PageHeader
        title="Content library"
        description="Every AI-generated artifact that has rendered successfully. Narrow by class, subject, chapter, topic, and type."
        actions={
          <Button asChild>
            <Link to="/generate">
              <Sparkles className="h-4 w-4" />
              Generate new
            </Link>
          </Button>
        }
      />

      {/* Board context — surfaces CBSE / NIOS / ... once a class +
          subject are picked. Hidden during partial selection. */}
      <BoardContextBar
        classLevel={classLevel === ALL ? undefined : (classLevel as number)}
        subjectName={
          subjectId === ALL
            ? undefined
            : subjectsScope.subjects.find((s) => s.id === subjectId)?.name
        }
        board={
          subjectId === ALL
            ? undefined
            : subjectsScope.subjects.find((s) => s.id === subjectId)?.board
        }
      />

      <Card className="mb-5">
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Filter className="h-4 w-4 text-(--color-muted-foreground)" />
            Filters
          </div>
          {anyFilterActive && (
            <Button size="sm" variant="ghost" onClick={clearFilters}>
              <X className="h-3.5 w-3.5" />
              Clear all
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
            <FilterField label="Class">
              <Select
                value={String(classLevel)}
                onValueChange={(v) => setClassLevel(v === ALL ? ALL : Number(v))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {/* Scoped roles (teachers) shouldn't see "All classes" — it
                      would show content for classes they don't teach. */}
                  {!available.isScoped && (
                    <SelectItem value={ALL}>All classes</SelectItem>
                  )}
                  {available.classes.map((c) => (
                    <SelectItem key={c.id} value={String(c.level)}>
                      {c.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterField>

            <FilterField label="Subject">
              <Select
                value={String(subjectId)}
                onValueChange={(v) => setSubjectId(v === ALL ? ALL : Number(v))}
                disabled={classLevel === ALL || subjectsScope.subjects.length === 0}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={classLevel === ALL ? "Pick a class first" : "All subjects"}
                  />
                </SelectTrigger>
                <SelectContent>
                  {/* Scoped users (teachers) shouldn't see "All subjects" — it
                      would broaden beyond their assigned subjects. */}
                  {!subjectsScope.isScoped && (
                    <SelectItem value={ALL}>All subjects</SelectItem>
                  )}
                  {subjectsScope.subjects.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {labelForSubject(s)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterField>

            <FilterField label="Chapter">
              <Select
                value={String(chapterId)}
                onValueChange={(v) => setChapterId(v === ALL ? ALL : Number(v))}
                disabled={subjectId === ALL || !chaptersQ.data?.length}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      subjectId === ALL ? "Pick a subject first" : "All chapters"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>All chapters</SelectItem>
                  {chaptersQ.data?.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      Ch {c.chapter_number}. {c.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterField>

            <FilterField label="Topic">
              <Select
                value={String(topicId)}
                onValueChange={(v) => setTopicId(v === ALL ? ALL : Number(v))}
                disabled={chapterId === ALL || noTopicsForChapter}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      chapterId === ALL
                        ? "Pick a chapter first"
                        : noTopicsForChapter
                          ? "No topics yet for this chapter"
                          : "All topics"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>All topics</SelectItem>
                  {topics.map((t) => (
                    <SelectItem key={t.id} value={String(t.id)}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {noTopicsForChapter && (
                <p className="mt-1 text-[11px] text-(--color-muted-foreground)">
                  Items in this chapter aren't yet tagged at the topic level.
                </p>
              )}
            </FilterField>

            <FilterField label="Type">
              <Select
                value={contentType}
                onValueChange={(v) => setContentType(v as GeneratedContentType | "all")}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TYPE_OPTIONS.map((t) => (
                    <SelectItem key={t} value={t}>
                      {TYPE_META[t].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterField>
          </div>
        </CardContent>
      </Card>

      <div className="mb-3 text-sm text-(--color-muted-foreground)">
        {listQ.isLoading
          ? "Loading…"
          : `${items.length} item${items.length === 1 ? "" : "s"}`}
      </div>

      {listQ.isLoading ? (
        <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      ) : items.length === 0 ? (
        <Empty
          icon={<FolderOpen className="h-6 w-6" />}
          title={anyFilterActive ? "No matches" : "Nothing here yet"}
          description={
            anyFilterActive
              ? "Loosen the filters above, or generate something for this scope."
              : "Generate a worksheet, quiz, lesson plan, or diagram to populate the library."
          }
          action={
            <div className="flex gap-2">
              {anyFilterActive && (
                <Button variant="outline" onClick={clearFilters}>
                  Clear filters
                </Button>
              )}
              <Button asChild>
                <Link to="/generate">
                  <Sparkles className="h-4 w-4" />
                  Generate content
                </Link>
              </Button>
            </div>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            const meta = TYPE_META[item.content_type] ?? TYPE_META.all;
            return (
              <Card
                key={item.id}
                /* Subtle lift on hover to suggest the card has an
                   interactive element inside (the Open button). We
                   don't make the entire card clickable — the action
                   logic branches per content type, so the explicit
                   button stays the click target. The shadow + border
                   accent is enough feedback that the row is "alive". */
                className="flex h-full flex-col transition-all duration-150 hover:border-(--color-primary)/30 hover:shadow-md"
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className="gap-1">
                      {meta.icon}
                      {meta.label}
                    </Badge>
                    <span className="text-xs text-(--color-muted-foreground)">
                      Class {item.class_level}
                    </span>
                  </div>
                  <CardTitle className="mt-2 line-clamp-2 text-base">{item.title}</CardTitle>
                  <CardDescription>
                    {item.llm_model ?? "stub"} · chapter #{item.chapter_id ?? "—"}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-1 flex items-end justify-between">
                  {/* "Open" branches by content type, not artefact presence:
                      - extra_content / worksheet / ppt -> always
                        /content/:id (in-platform viewer, no download
                        path). Worksheets render structured Q&A; PPT decks
                        render as an inline slide carousel; extra_content
                        renders as a no-toolbar PDF iframe.
                      - artifact_url set                -> openArtifact()
                        opens the rendered file (SVG / HTML simulation) in
                        a new tab. Used for simulations and other surfaces
                        that intentionally keep an out-of-page viewer.
                      - no artifact_url                 -> navigate to
                        /content/:id, a full-page renderer that draws the
                        content from output_json (chapter summaries,
                        classroom activities, flow diagrams, mind-maps...).
                  */}
                  {item.content_type === "extra_content" ||
                  item.content_type === "worksheet" ||
                  item.content_type === "ppt" ? (
                    <Button size="sm" variant="outline" asChild>
                      <Link to={`/content/${item.id}`}>
                        Open
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </Button>
                  ) : item.artifact_url ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        try {
                          await openArtifact(item.id, { title: item.title });
                        } catch (err) {
                          toast.error(humanError(err));
                        }
                      }}
                    >
                      Open
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  ) : (
                    <Button size="sm" variant="outline" asChild>
                      <Link to={`/content/${item.id}`}>
                        Open
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </Button>
                  )}
                  <span className="text-xs text-(--color-muted-foreground)">#{item.id}</span>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </ThemedPage>
  );
}

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
        {label}
      </Label>
      {children}
    </div>
  );
}
