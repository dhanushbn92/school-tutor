import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useMascot } from "@/lib/mascotContext";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  BookOpen,
  BookText,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  Eye,
  EyeOff,
  ExternalLink,
  FileText,
  Maximize2,
  Minimize2,
  RotateCcw,
  XCircle,
  GraduationCap,
  Layers,
  Lightbulb,
  Loader2,
  Lock,
  Network,
  PlayCircle,
  Presentation,
  Sparkles,
  TriangleAlert,
  Upload,
  User as UserIcon,
  Users,
  Video,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ThemedSection, ThemedTitleMark } from "@/components/themed";
import { MindMapInteractive } from "@/components/MindMapInteractive";
import { FlowDiagram } from "@/components/FlowDiagram";
import type { FlowDiagramData } from "@/components/FlowDiagram";
import { loadArtifactObjectUrl, openArtifact } from "@/lib/artifact";
import { humanError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import {
  useChapterDetail,
  useChapterVideos,
  useChatStatus,
  useCreateChatSession,
  useGeneratedContentList,
  useMyAssessments,
  useMySubmissions,
  type MySubmission,
} from "@/lib/queries";
import {
  subjectTheme,
  subjectVar,
  subjectVarForeground,
} from "@/lib/subjectTheme";
import type {
  Assessment,
  ChapterSummaryOutput,
  ChapterSummarySection,
  ChapterSummaryGlossaryTerm,
  ChapterVideo,
  ClassroomActivitySetOutput,
  ClassroomActivity,
  GeneratedContent,
  LessonPlanOutput,
  PPTOutlineOutput,
  SlideType,
  WorksheetOutput,
  WorksheetQuestion,
} from "@/lib/types";

export function LearnChapterPage() {
  const { user } = useAuth();
  const { chapterId: chapterIdParam } = useParams();
  const chapterId = chapterIdParam ? Number(chapterIdParam) : undefined;

  // The learning buddy studies along while a chapter is open (a no-op for
  // anyone without the mascot).
  const mascot = useMascot();
  const { reactWith: mascotReact, reset: mascotReset } = mascot;
  useEffect(() => {
    mascotReact("READING");
    return () => mascotReset();
  }, [mascotReact, mascotReset]);

  const detailQ = useChapterDetail(chapterId);

  const summariesQ = useGeneratedContentList({
    content_type: "chapter_summary",
    chapter_id: chapterId,
    status: "approved",
    limit: 1,
  });
  const lessonPlansQ = useGeneratedContentList({
    content_type: "lesson_plan",
    chapter_id: chapterId,
    status: "approved",
    limit: 1,
  });
  const activitiesQ = useGeneratedContentList({
    content_type: "classroom_activity",
    chapter_id: chapterId,
    status: "approved",
    limit: 1,
  });
  // PPT outline — teacher-facing slide deck. The tab is gated to teachers /
  // school admins downstream so students never see this content (or the
  // speaker notes inside it).
  const pptsQ = useGeneratedContentList({
    content_type: "ppt",
    chapter_id: chapterId,
    status: "approved",
    limit: 1,
  });
  const simulationsQ = useGeneratedContentList({
    content_type: "simulation",
    chapter_id: chapterId,
    status: "approved",
    limit: 5,
  });
  // Extra content uploaded by the platform admin (PDF/DOCX) — viewable
  // inline only, no external links, no downloads.
  const extraContentQ = useGeneratedContentList({
    content_type: "extra_content",
    chapter_id: chapterId,
    status: "approved",
    limit: 10,
  });
  const extraContent = extraContentQ.data ?? [];
  // Video lectures — shown between the summary-family tabs and the worksheets.
  const videosQ = useChapterVideos(chapterId);
  const videos = videosQ.data ?? [];

  // Assessments for this chapter — surfaces in the Assessments tab so the
  // student can take a test in-place rather than navigating to /assessments.
  // Filtering is server-side via /me/assessments?chapter_id=... so the role
  // / section / status guards stay centralised in assessment_service.
  const assessmentsQ = useMyAssessments({ chapter_id: chapterId });
  const assessments = assessmentsQ.data ?? [];
  // The user's prior submissions (across ALL assessments) — we look up the
  // matching one per chapter assessment to render "Done · X/Y" or "Submitted"
  // instead of a Take button. Endpoint is small and shared across pages, so
  // an unfiltered fetch is fine.
  const mySubmissionsQ = useMySubmissions();
  const mySubmissions = mySubmissionsQ.data ?? [];

  const summary = (summariesQ.data?.[0]?.output_json ?? null) as ChapterSummaryOutput | null;
  const lessonPlan = (lessonPlansQ.data?.[0]?.output_json ?? null) as LessonPlanOutput | null;
  const activitySet = (activitiesQ.data?.[0]?.output_json ?? null) as ClassroomActivitySetOutput | null;
  const pptOutline = (pptsQ.data?.[0]?.output_json ?? null) as PPTOutlineOutput | null;
  const simulations = simulationsQ.data ?? [];
  const worksheetsQ = useGeneratedContentList({
    content_type: "worksheet",
    chapter_id: chapterId,
    status: "approved",
    limit: 10,
  });
  const worksheets = worksheetsQ.data ?? [];
  const flowsQ = useGeneratedContentList({
    content_type: "flow_diagram",
    chapter_id: chapterId,
    status: "approved",
    limit: 5,
  });
  const flows = flowsQ.data ?? [];
  const diagramsQ = useGeneratedContentList({
    content_type: "diagram",
    chapter_id: chapterId,
    status: "approved",
    limit: 5,
  });
  const diagrams = diagramsQ.data ?? [];

  const isLearner =
    user?.role === "individual_learner" || user?.role === "student";
  const isTeacherOrAdmin =
    user?.role === "teacher" || user?.role === "school_admin";

  const navigate = useNavigate();
  const chatStatusQ = useChatStatus();
  const createChat = useCreateChatSession();
  const aiChatEnabled = chatStatusQ.data?.ai_chat_enabled === true;

  async function startChat(scope: "CHAPTER" | "TOPIC", topicId?: number) {
    if (!isLearner) return;
    if (!aiChatEnabled) {
      toast.error(
        "AI tutor is a premium feature. Ask your school admin to enable it.",
      );
      return;
    }
    if (chapterId === undefined) return;
    try {
      const session = await createChat.mutateAsync(
        scope === "CHAPTER"
          ? { scope: "CHAPTER", chapter_id: chapterId }
          : { scope: "TOPIC", topic_id: topicId! },
      );
      navigate(`/chat/${session.id}`);
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  if (detailQ.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading chapter…
      </div>
    );
  }
  if (!detailQ.data) {
    return <Empty icon={<BookOpen className="h-6 w-6" />} title="Chapter not found" />;
  }

  const ch = detailQ.data;
  const topics = ch.topics ?? [];

  // Per-tab "the underlying query failed" flags. Without these, a
  // failed fetch produced an empty array, which made the tab silently
  // disappear (`available: list.length > 0`) — students could swear a
  // chapter has worksheets that aren't showing. Now we keep the tab
  // visible and render an error placeholder inside.
  const loadErrors = {
    summary: summariesQ.isError,
    visuals: flowsQ.isError || diagramsQ.isError,
    videos: videosQ.isError,
    worksheets: worksheetsQ.isError,
    assessments: assessmentsQ.isError,
    simulations: simulationsQ.isError,
    lessonPlan: lessonPlansQ.isError,
    activities: activitiesQ.isError,
    slides: pptsQ.isError,
    extra: extraContentQ.isError,
  };

  return (
    <ChapterTabbedLayout
      ch={ch}
      topics={topics}
      summary={summary}
      summariesLoading={summariesQ.isLoading}
      lessonPlan={lessonPlan}
      activitySet={activitySet}
      pptOutline={pptOutline}
      flows={flows}
      diagrams={diagrams}
      videos={videos}
      worksheets={worksheets}
      simulations={simulations}
      extraContent={extraContent}
      assessments={assessments}
      mySubmissions={mySubmissions}
      loadErrors={loadErrors}
      isLearner={isLearner}
      isTeacherOrAdmin={isTeacherOrAdmin}
      aiChatEnabled={aiChatEnabled}
      startChat={startChat}
      createChatPending={createChat.isPending}
    />
  );
}


// ---------- Tabbed layout ----------

type TabKey =
  | "topics"
  | "summary"
  | "takeaways"
  | "glossary"
  | "visuals"
  | "videos"
  | "worksheets"
  | "assessments"
  | "simulations"
  | "lesson_plan"
  | "activities"
  | "slides"
  | "extra";

interface TabSpec {
  key: TabKey;
  label: string;
  icon: ReactNode;
  available: boolean;
  render: () => ReactNode;
  /** Small count/label pill shown inside the tab (e.g. number of videos). */
  badge?: string;
}

interface ChapterTabbedLayoutProps {
  ch: {
    id: number;
    title: string;
    chapter_number: number;
    subject_id?: number | null;
    subject_name?: string | null;
  };
  topics: Array<{ id: number; name: string; description?: string | null }>;
  summary: ChapterSummaryOutput | null;
  summariesLoading: boolean;
  lessonPlan: LessonPlanOutput | null;
  activitySet: ClassroomActivitySetOutput | null;
  pptOutline: PPTOutlineOutput | null;
  flows: GeneratedContent[];
  diagrams: GeneratedContent[];
  videos: ChapterVideo[];
  worksheets: GeneratedContent[];
  simulations: GeneratedContent[];
  extraContent: GeneratedContent[];
  assessments: Assessment[];
  mySubmissions: MySubmission[];
  /**
   * Per-tab "underlying query failed" flags. When true, the tab stays
   * visible (instead of silently hiding because the data array is empty)
   * and renders <TabErrorState> so the user knows the data couldn't
   * load — distinguishing "nothing here yet" from "we tried and failed".
   */
  loadErrors: {
    summary: boolean;
    visuals: boolean;
    videos: boolean;
    worksheets: boolean;
    assessments: boolean;
    simulations: boolean;
    lessonPlan: boolean;
    activities: boolean;
    slides: boolean;
    extra: boolean;
  };
  isLearner: boolean;
  isTeacherOrAdmin: boolean;
  aiChatEnabled: boolean;
  startChat: (scope: "CHAPTER" | "TOPIC", topicId?: number) => void;
  createChatPending: boolean;
}

function ChapterTabbedLayout(props: ChapterTabbedLayoutProps) {
  const {
    ch,
    topics,
    summary,
    summariesLoading,
    lessonPlan,
    activitySet,
    pptOutline,
    flows,
    diagrams,
    videos,
    worksheets,
    simulations,
    extraContent,
    assessments,
    mySubmissions,
    loadErrors,
    isLearner,
    isTeacherOrAdmin,
    aiChatEnabled,
    startChat,
    createChatPending,
  } = props;

  // Resolve subject colours up front — needed by both the tab spec render
  // functions and the hero panel below. Declared once at the top of the
  // function so React's useMemo dep array sees stable identities.
  const chapterTheme = subjectTheme(ch.subject_name);
  const themeColor = subjectVar(chapterTheme);
  const themeFg = subjectVarForeground(chapterTheme);

  // A tab is shown only if its content actually exists. A learner won't see
  // an empty "Lesson plan" tab; a chapter with no uploaded extras hides
  // the "Extra reading" tab entirely. This keeps the tab strip honest.
  const tabs: TabSpec[] = useMemo(() => {
    const list: TabSpec[] = [];
    list.push({
      key: "topics",
      label: "Topics",
      icon: <Layers className="h-4 w-4" />,
      available: true,  // always show, even if empty (informs the user)
      render: () => (
        <TopicsTab
          topics={topics}
          isLearner={isLearner}
          aiChatEnabled={aiChatEnabled}
          startChat={startChat}
          createChatPending={createChatPending}
          themeColor={themeColor}
          themeFg={themeFg}
        />
      ),
    });
    list.push({
      key: "summary",
      label: "Summary",
      icon: <BookOpen className="h-4 w-4" />,
      available: !!summary || summariesLoading || loadErrors.summary,
      render: () =>
        loadErrors.summary && !summary ? (
          <TabErrorState label="Summary" />
        ) : (
          <SummaryTab
            summary={summary}
            summariesLoading={summariesLoading}
            themeColor={themeColor}
          />
        ),
    });
    // Key takeaways and Glossary used to live inside the Summary tab.
    // Surfacing them as their own tabs keeps every tab small and
    // focused — students can jump straight to "what should I remember"
    // (takeaways) or "what does this word mean" (glossary) without
    // scrolling through the whole summary recap.
    list.push({
      key: "takeaways",
      label: "Key takeaways",
      icon: <Lightbulb className="h-4 w-4" />,
      available: (summary?.key_takeaways.length ?? 0) > 0,
      render: () => (
        <KeyTakeawaysTab
          takeaways={summary?.key_takeaways ?? []}
          themeColor={themeColor}
        />
      ),
    });
    list.push({
      key: "glossary",
      label: "Glossary",
      icon: <BookText className="h-4 w-4" />,
      available: (summary?.glossary.length ?? 0) > 0,
      render: () => (
        <GlossaryTab
          terms={summary?.glossary ?? []}
          themeColor={themeColor}
        />
      ),
    });
    list.push({
      key: "visuals",
      label: "Visuals",
      icon: <Network className="h-4 w-4" />,
      available:
        flows.length > 0 || diagrams.length > 0 || loadErrors.visuals,
      render: () =>
        loadErrors.visuals && flows.length === 0 && diagrams.length === 0 ? (
          <TabErrorState label="Visuals" />
        ) : (
          <VisualsTab flows={flows} diagrams={diagrams} themeColor={themeColor} />
        ),
    });
    // Video lectures sit after the summary-family tabs and before the
    // worksheets: learners watch the lesson, then practise.
    list.push({
      key: "videos",
      label: "Videos",
      icon: <Video className="h-4 w-4" />,
      badge: videos.length > 0 ? String(videos.length) : undefined,
      available: videos.length > 0 || loadErrors.videos,
      render: () =>
        loadErrors.videos && videos.length === 0 ? (
          <TabErrorState label="Videos" />
        ) : (
          <VideosTab videos={videos} themeColor={themeColor} />
        ),
    });
    list.push({
      key: "worksheets",
      label: "Worksheets",
      icon: <FileText className="h-4 w-4" />,
      available: worksheets.length > 0 || loadErrors.worksheets,
      render: () =>
        loadErrors.worksheets && worksheets.length === 0 ? (
          <TabErrorState label="Worksheets" />
        ) : (
          <WorksheetsTab worksheets={worksheets} themeColor={themeColor} />
        ),
    });
    // Assessments tab — students take chapter tests in-place. Visible to
    // teachers / admins too (their visibility comes from the same backend
    // endpoint), so they can scan what's published for the chapter without
    // leaving the Learn page.
    list.push({
      key: "assessments",
      label: "Tests",
      icon: <ClipboardCheck className="h-4 w-4" />,
      available: assessments.length > 0 || loadErrors.assessments,
      render: () =>
        loadErrors.assessments && assessments.length === 0 ? (
          <TabErrorState label="Tests" />
        ) : (
          <AssessmentsTab
            assessments={assessments}
            mySubmissions={mySubmissions}
            isLearner={isLearner}
            themeColor={themeColor}
          />
        ),
    });
    list.push({
      key: "simulations",
      label: "Simulations",
      icon: <PlayCircle className="h-4 w-4" />,
      available: simulations.length > 0 || loadErrors.simulations,
      render: () =>
        loadErrors.simulations && simulations.length === 0 ? (
          <TabErrorState label="Simulations" />
        ) : (
          <SimulationsTab simulations={simulations} themeColor={themeColor} />
        ),
    });
    list.push({
      key: "lesson_plan",
      label: "Lesson plan",
      icon: <ClipboardList className="h-4 w-4" />,
      // Teacher-gated tabs only surface the error if the role is allowed
      // to see them in the first place — otherwise a failed lesson-plan
      // fetch would expose the tab to learners.
      available:
        isTeacherOrAdmin && (!!lessonPlan || loadErrors.lessonPlan),
      render: () =>
        loadErrors.lessonPlan && !lessonPlan ? (
          <TabErrorState label="Lesson plan" />
        ) : lessonPlan ? (
          <LessonPlanTab plan={lessonPlan} />
        ) : null,
    });
    list.push({
      key: "activities",
      label: "Activities",
      icon: <Users className="h-4 w-4" />,
      available:
        isTeacherOrAdmin && (!!activitySet || loadErrors.activities),
      render: () =>
        loadErrors.activities && !activitySet ? (
          <TabErrorState label="Activities" />
        ) : activitySet ? (
          <ActivitySetView activitySet={activitySet} />
        ) : null,
    });
    // Slides tab — teacher-only by design. The underlying PPTOutlineView
    // exposes speaker notes which aren't meant for student eyes; gating at
    // the tab level keeps that content out of the learner's reach without
    // needing role logic inside the renderer.
    list.push({
      key: "slides",
      label: "Slides",
      icon: <Presentation className="h-4 w-4" />,
      available: isTeacherOrAdmin && (!!pptOutline || loadErrors.slides),
      render: () =>
        loadErrors.slides && !pptOutline ? (
          <TabErrorState label="Slides" />
        ) : pptOutline ? (
          <PPTOutlineView deck={pptOutline} />
        ) : null,
    });
    list.push({
      key: "extra",
      label: "Extra reading",
      icon: <Upload className="h-4 w-4" />,
      available: extraContent.length > 0 || loadErrors.extra,
      render: () =>
        loadErrors.extra && extraContent.length === 0 ? (
          <TabErrorState label="Extra reading" />
        ) : (
          <ExtraReadingTab items={extraContent} themeColor={themeColor} />
        ),
    });
    return list;
  }, [
    topics,
    summary,
    summariesLoading,
    flows,
    diagrams,
    videos,
    worksheets,
    simulations,
    isTeacherOrAdmin,
    lessonPlan,
    activitySet,
    pptOutline,
    extraContent,
    assessments,
    mySubmissions,
    loadErrors,
    isLearner,
    aiChatEnabled,
    createChatPending,
    startChat,
  ]);

  const visibleTabs = tabs.filter((t) => t.available);

  // A link like /learn/chapters/12?tab=videos opens straight on that tab. It is
  // derived rather than copied into state, so it still works when the tabs
  // arrive after the first render (the video list loads on its own), and a
  // tab the learner picks always wins.
  const [searchParams] = useSearchParams();
  const requestedKey = visibleTabs.find((t) => t.key === searchParams.get("tab"))?.key;
  const [pickedKey, setPickedKey] = useState<TabKey | null>(null);
  // Learners land on the video lesson when there is one (watch, then
  // practise); everyone else on the first tab.
  const defaultKey: TabKey =
    isLearner && visibleTabs.some((t) => t.key === "videos")
      ? "videos"
      : (visibleTabs[0]?.key ?? "topics");
  const activeKey: TabKey = pickedKey ?? requestedKey ?? defaultKey;
  // If the active tab disappears (data changed underneath), fall back to
  // the first visible one rather than rendering nothing.
  const activeTab = visibleTabs.find((t) => t.key === activeKey) ?? visibleTabs[0];

  // "Your path": a tab counts as done once the learner has opened it and moved
  // on, remembered on this device; the quiz step is done once a quiz for this
  // chapter has been submitted.
  const { user } = useAuth();
  const visitedKey = `st.chapter-path.${user?.id ?? "anon"}.${ch.id}`;
  const [visited, setVisited] = useState<Set<TabKey>>(() => readVisited(visitedKey));
  function openTab(next: TabKey) {
    if (next === activeKey) return;
    if (isLearner) {
      const seen = new Set(visited).add(activeKey);
      setVisited(seen);
      writeVisited(visitedKey, seen);
    }
    setPickedKey(next);
    setMoreOpen(false);
  }
  const hasTab = (k: TabKey) => visibleTabs.some((t) => t.key === k);
  const quizDone = mySubmissions.some(
    (s) =>
      s.status !== "DRAFT" && assessments.some((a) => a.id === s.assessment_id),
  );
  const pathSteps: PathStep[] = isLearner
    ? [
        ...(hasTab("videos") ? [{ id: "videos", label: "Watch the lesson", tab: "videos" as TabKey }] : []),
        ...(hasTab("summary") ? [{ id: "summary", label: "Read the summary", tab: "summary" as TabKey }] : []),
        ...(hasTab("worksheets") ? [{ id: "worksheets", label: "Do the worksheet", tab: "worksheets" as TabKey }] : []),
        { id: "quiz", label: "Take the chapter quiz", tab: null },
      ]
    : [];
  const isDone = (s: PathStep) => (s.tab ? visited.has(s.tab) : quizDone);
  const doneCount = pathSteps.filter(isDone).length;
  const nextStep = pathSteps.find((s) => !isDone(s));

  // The tab strip shows the main sections; the rest live under "More".
  const primaryKeys: TabKey[] = isLearner
    ? ["videos", "summary", "topics", "simulations", "worksheets"]
    : ["topics", "summary", "videos", "simulations", "worksheets"];
  const primaryTabs = primaryKeys
    .map((k) => visibleTabs.find((t) => t.key === k))
    .filter((t): t is TabSpec => t !== undefined);
  const moreTabs = visibleTabs.filter((t) => !primaryKeys.includes(t.key));
  const moreActive = moreTabs.find((t) => t.key === activeKey);
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!moreOpen) return;
    const onDown = (e: MouseEvent) => {
      if (!moreRef.current?.contains(e.target as Node)) setMoreOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMoreOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [moreOpen]);

  // Back link targets the parent subject page when we know it; otherwise
  // we fall back to the all-subjects list.
  const backTo = ch.subject_id ? `/learn/subjects/${ch.subject_id}` : "/learn";
  const backLabel = ch.subject_name ? `Back to ${ch.subject_name}` : "Back to subjects";

  const tabButton = (t: TabSpec) => {
    const active = activeKey === t.key;
    return (
      <button
        key={t.key}
        type="button"
        role="tab"
        aria-selected={active}
        onClick={() => openTab(t.key)}
        className={cn(
          "flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-colors",
          active
            ? "bg-(--color-primary)/10 text-(--color-primary)"
            : "text-(--color-muted-foreground) hover:bg-(--color-muted) hover:text-(--color-foreground)",
        )}
      >
        {t.label}
        {t.badge && (
          <span className="rounded-full bg-(--color-primary)/10 px-2 py-0.5 text-xs font-bold text-(--color-primary)">
            {t.badge}
          </span>
        )}
      </button>
    );
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <Link
            to={backTo}
            className="inline-flex items-center gap-1.5 text-sm text-(--color-muted-foreground) hover:text-(--color-foreground)"
          >
            <ArrowLeft className="h-4 w-4" />
            {backLabel}
          </Link>
          <h1 className="mt-1.5 font-display text-2xl font-extrabold tracking-tight md:text-3xl">
            Chapter {ch.chapter_number} · {ch.title}
          </h1>
          <p className="mt-1 text-sm text-(--color-muted-foreground)">
            {topics.length} {topics.length === 1 ? "topic" : "topics"}
            {isLearner ? " ahead. Watch, read, then practise." : " in this chapter"}
          </p>
        </div>
        {isLearner && (
          <div className="flex flex-wrap gap-2">
            <Button asChild size="lg" className="rounded-xl">
              <Link to={`/quick-quiz?chapter=${ch.id}`}>
                <Sparkles className="h-4 w-4" /> Let's practise
              </Link>
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="rounded-xl"
              onClick={() => startChat("CHAPTER")}
              disabled={createChatPending}
              title={
                aiChatEnabled
                  ? "Start an AI tutor chat scoped to this whole chapter"
                  : "AI tutor is a premium feature. Ask your admin to enable it"
              }
            >
              {aiChatEnabled ? <Bot className="h-4 w-4" /> : <Lock className="h-4 w-4" />}
              {aiChatEnabled ? "Ask the AI tutor" : "AI tutor (premium)"}
            </Button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Chapter sections">
        {primaryTabs.map(tabButton)}
        {moreTabs.length > 0 && (
          <div ref={moreRef} className="relative">
            <button
              type="button"
              aria-expanded={moreOpen}
              aria-haspopup="true"
              onClick={() => setMoreOpen((v) => !v)}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold transition-colors",
                moreActive
                  ? "bg-(--color-primary)/10 text-(--color-primary)"
                  : "text-(--color-muted-foreground) hover:bg-(--color-muted) hover:text-(--color-foreground)",
              )}
            >
              {moreActive ? moreActive.label : "More"}
              <ChevronDown className={cn("h-4 w-4 transition-transform", moreOpen && "rotate-180")} aria-hidden />
            </button>
            {moreOpen && (
              <div className="absolute left-0 top-full z-30 mt-2 w-56 rounded-2xl border border-(--color-border) bg-(--color-card) p-1.5 shadow-lg">
                {moreTabs.map((t) => (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => openTab(t.key)}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm hover:bg-(--color-muted)",
                      activeKey === t.key && "bg-(--color-primary)/10 font-semibold text-(--color-primary)",
                    )}
                  >
                    {t.icon}
                    {t.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {pathSteps.length > 0 && (
        <Card className="rounded-2xl px-5 py-3">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
            <div className="flex items-center gap-3">
              <h2 className="font-display text-base font-bold">Your path</h2>
              <span className="text-sm text-(--color-muted-foreground)">
                {doneCount} of {pathSteps.length}
              </span>
              <div
                className="h-2 w-24 overflow-hidden rounded-full bg-(--color-muted)"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={pathSteps.length}
                aria-valuenow={doneCount}
                aria-label="Chapter steps done"
              >
                <div
                  className="h-full rounded-full bg-(--color-primary)"
                  style={{ width: `${Math.round((doneCount / pathSteps.length) * 100)}%` }}
                />
              </div>
            </div>
            <ol className="flex min-w-0 flex-1 flex-wrap items-center gap-x-4 gap-y-1">
              {pathSteps.map((s, i) => {
                const done = isDone(s);
                const current = s === nextStep;
                const dot = (
                  <span
                    aria-hidden
                    className={cn(
                      "grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold",
                      done
                        ? "bg-(--color-primary) text-(--color-primary-foreground)"
                        : "bg-(--color-muted) text-(--color-muted-foreground)",
                    )}
                  >
                    {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
                  </span>
                );
                const rowClass = cn(
                  "flex items-center gap-2 py-1 text-left text-sm",
                  current && "font-semibold",
                );
                return (
                  <li key={s.id}>
                    {s.tab ? (
                      <button type="button" className={rowClass} onClick={() => openTab(s.tab as TabKey)}>
                        {dot}
                        {s.label}
                      </button>
                    ) : (
                      <Link className={rowClass} to={`/quick-quiz?chapter=${ch.id}`}>
                        {dot}
                        {s.label}
                      </Link>
                    )}
                  </li>
                );
              })}
            </ol>
            {nextStep ? (
              nextStep.tab ? (
                <Button className="rounded-xl" onClick={() => openTab(nextStep.tab as TabKey)}>
                  Next: {nextStep.label.toLowerCase()}
                </Button>
              ) : (
                <Button asChild className="rounded-xl">
                  <Link to={`/quick-quiz?chapter=${ch.id}`}>Next: take the quiz</Link>
                </Button>
              )
            ) : (
              <span className="text-sm text-(--color-muted-foreground)">
                All steps done. A fresh quiz keeps it sharp.
              </span>
            )}
          </div>
        </Card>
      )}

      {/* Active tab content. The `key` forces React to remount on tab change
          so the entrance animation re-fires. */}
      <div key={activeKey} className="min-w-0 space-y-4 animate-in fade-in duration-300">
        {activeTab?.render()}
      </div>
    </div>
  );
}

interface PathStep {
  id: string;
  label: string;
  /** The tab that opens this step, or null for the quiz step. */
  tab: TabKey | null;
}

/** The tabs a learner has already seen in this chapter, kept on this device. */
function readVisited(key: string): Set<TabKey> {
  try {
    const raw = localStorage.getItem(key);
    return new Set(raw ? (JSON.parse(raw) as TabKey[]) : []);
  } catch {
    return new Set();
  }
}

function writeVisited(key: string, seen: Set<TabKey>): void {
  try {
    localStorage.setItem(key, JSON.stringify([...seen]));
  } catch {
    // Storage can be blocked; the path simply will not be remembered.
  }
}


// ---------- Per-tab renderers ----------

function TopicsTab({
  topics,
  isLearner,
  aiChatEnabled,
  startChat,
  createChatPending,
  themeColor,
  themeFg,
}: {
  topics: ChapterTabbedLayoutProps["topics"];
  isLearner: boolean;
  aiChatEnabled: boolean;
  startChat: ChapterTabbedLayoutProps["startChat"];
  createChatPending: boolean;
  themeColor: string;
  themeFg: string;
}) {
  return (
    <ThemedSection themeColor={themeColor}>
      <CardHeader>
        <CardTitle className="flex items-center text-xl md:text-2xl">
          <ThemedTitleMark themeColor={themeColor} />
          What you'll learn
        </CardTitle>
        <CardDescription className="text-base">
          {isLearner
            ? "Each topic is a small step — tap any one to start exploring or ask the AI tutor to walk you through it."
            : "The main ideas covered in this chapter."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {topics.length === 0 ? (
          <Empty
            scene="spark"
            accent={themeColor}
            title="Topics will appear here soon"
            description="Once your teacher publishes them, you'll see the chapter broken down into bite-sized topics here."
            className="border-0 py-4"
          />
        ) : (
          // Topic cards — each one's a friendly tile with a big
          // numbered badge in the subject colour, the topic text,
          // and a chevron that animates to the right on hover. The
          // chevron is a soft cue that the row is interactive even
          // though the explicit click target is the "Ask AI" button.
          <ol className="space-y-3">
            {topics.map((t, idx) => (
              <li
                key={t.id}
                className="group flex items-stretch gap-4 rounded-2xl border-2 border-(--color-border) bg-(--color-card) p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                onMouseEnter={(e) =>
                  (e.currentTarget.style.borderColor = themeColor)
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.borderColor = "")
                }
              >
                {/* Big numbered tile — subject gradient, white text,
                    drop shadow. h-14 w-14 (56px) makes the number
                    pleasantly readable at a glance. */}
                <div
                  className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl text-lg font-bold shadow-md transition-transform group-hover:scale-105 group-hover:rotate-3"
                  style={{
                    background: `linear-gradient(135deg, ${themeColor}, color-mix(in oklab, ${themeColor} 70%, black))`,
                    color: themeFg,
                  }}
                >
                  {idx + 1}
                </div>
                <div className="min-w-0 flex-1 self-center">
                  <div className="text-base font-semibold leading-snug md:text-lg">
                    {t.name}
                  </div>
                  {t.description && (
                    <p className="mt-1 text-sm leading-relaxed text-(--color-muted-foreground)">
                      {t.description}
                    </p>
                  )}
                </div>
                <div className="flex flex-shrink-0 items-center gap-2 self-center">
                  {isLearner && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="rounded-full transition-transform hover:scale-105 active:scale-95"
                      onClick={() => startChat("TOPIC", t.id)}
                      disabled={createChatPending}
                      title={
                        aiChatEnabled
                          ? `Open AI tutor scoped to '${t.name}'`
                          : "AI tutor is a premium feature — ask your admin to enable it"
                      }
                    >
                      {aiChatEnabled ? (
                        <Bot className="h-3.5 w-3.5" />
                      ) : (
                        <Lock className="h-3.5 w-3.5" />
                      )}
                      Ask AI
                    </Button>
                  )}
                  {/* Animated chevron — on rest it sits muted, on
                      hover it slides right and adopts the subject
                      colour. Reinforces that the row is a "go"
                      affordance even when no Ask-AI button shows. */}
                  <ArrowRight
                    className="h-5 w-5 text-(--color-muted-foreground) transition-all duration-200 group-hover:translate-x-1"
                    style={{}}
                  />
                </div>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </ThemedSection>
  );
}



/**
 * Visible-but-empty fallback when a tab's underlying query failed.
 * Shown instead of silently hiding the tab — so a teacher who knows
 * "this chapter has worksheets" doesn't end up wondering why the tab
 * disappeared. The user can refresh or escalate to support.
 *
 * The wording deliberately stays vague about *what* failed (could be a
 * dropped network call, a backend 500, a transient auth blip) — pinning
 * blame is rarely useful and "try refreshing" handles 90% of cases.
 */
function TabErrorState({ label }: { label: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TriangleAlert className="h-4 w-4 text-(--color-warning)" />
          Couldn't load {label.toLowerCase()}
        </CardTitle>
        <CardDescription>
          We weren't able to fetch this section just now. Refresh the page
          and try again — if it keeps failing, ask your school admin to
          check the platform status.
        </CardDescription>
      </CardHeader>
    </Card>
  );
}


function SummaryTab({
  summary,
  summariesLoading,
  themeColor,
}: {
  summary: ChapterSummaryOutput | null;
  summariesLoading: boolean;
  themeColor: string;
}) {
  if (summariesLoading) {
    return (
      <ThemedSection themeColor={themeColor}>
        <CardContent className="py-6">
          <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading summary…
          </div>
        </CardContent>
      </ThemedSection>
    );
  }
  if (!summary) {
    return (
      <ThemedSection themeColor={themeColor}>
        <CardHeader>
          <CardTitle className="flex items-center">
            <ThemedTitleMark themeColor={themeColor} />
            Chapter summary
          </CardTitle>
          <CardDescription>Coming soon.</CardDescription>
        </CardHeader>
        <CardContent>
          <Empty
            scene="leaf"
            accent={themeColor}
            title="Summary's not ready yet"
            description="Once your teacher publishes the chapter summary, you'll find a quick recap right here."
            className="border-0 py-4"
          />
        </CardContent>
      </ThemedSection>
    );
  }
  // Glossary and key takeaways now live in their own tabs (Glossary
  // and Key takeaways) so each tab stays focused and bite-sized. The
  // Summary tab here is just the chapter recap + section breakdowns.
  return <SummaryView summary={summary} excludeGlossary />;
}


/**
 * Key takeaways tab. The chapter summary's `key_takeaways` field is the
 * student's "pin this on the wall" list — bite-sized highlights they
 * can skim before a test. Lifted out of the Summary tab so each tab
 * stays small and the takeaways get their own, prominent surface.
 */
function KeyTakeawaysTab({
  takeaways,
  themeColor,
}: {
  takeaways: string[];
  themeColor: string;
}) {
  if (takeaways.length === 0) {
    return (
      <Empty
        scene="trophy"
        accent={themeColor}
        title="No key takeaways yet"
        description="Once the chapter summary is published, the key takeaways for this chapter will show up here."
      />
    );
  }
  return (
    <ThemedSection themeColor={themeColor}>
      <CardHeader>
        <CardTitle className="flex items-center text-xl md:text-2xl">
          <ThemedTitleMark themeColor={themeColor} />
          Key takeaways
        </CardTitle>
        <CardDescription className="text-base">
          The big ideas worth remembering — perfect for a quick revision
          before a test.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2.5 text-sm md:text-base">
          {takeaways.map((kt, i) => (
            <li
              key={i}
              className="flex items-start gap-3 rounded-xl bg-[color-mix(in_oklab,var(--color-success)_5%,transparent)] p-3"
            >
              <span className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-(--color-success) text-xs font-bold text-white">
                ✓
              </span>
              <span className="leading-relaxed">{kt}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </ThemedSection>
  );
}


/**
 * Glossary tab. Vocabulary list lifted out of the Summary tab so it
 * gets its own surface — students who just want to drill terms (or
 * teachers reviewing what's covered) don't have to scroll past the
 * full chapter recap to find them.
 */
function GlossaryTab({
  terms,
  themeColor,
}: {
  terms: ChapterSummaryGlossaryTerm[];
  themeColor: string;
}) {
  if (terms.length === 0) {
    return (
      <Empty
        scene="books"
        accent={themeColor}
        title="No glossary yet"
        description="Vocabulary terms from this chapter will appear here once the summary is generated."
      />
    );
  }
  return (
    <ThemedSection themeColor={themeColor}>
      <CardHeader>
        <CardTitle className="flex items-center text-xl md:text-2xl">
          <ThemedTitleMark themeColor={themeColor} />
          Glossary
        </CardTitle>
        <CardDescription className="text-base">
          Words and phrases worth remembering from this chapter.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-3 sm:grid-cols-2">
          {terms.map((g, i) => (
            <div
              key={i}
              className="rounded-xl border-2 border-(--color-border) bg-(--color-card) p-4 transition-all duration-150 hover:-translate-y-0.5 hover:shadow-md"
              onMouseEnter={(e) =>
                (e.currentTarget.style.borderColor = themeColor)
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.borderColor = "")
              }
            >
              <dt className="text-base font-semibold leading-tight">{g.term}</dt>
              <dd className="mt-1.5 text-sm leading-relaxed text-(--color-muted-foreground)">
                {g.definition}
              </dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </ThemedSection>
  );
}


function VisualsTab({
  flows,
  diagrams,
  themeColor,
}: {
  flows: GeneratedContent[];
  diagrams: GeneratedContent[];
  themeColor: string;
}) {
  if (flows.length === 0 && diagrams.length === 0) {
    return (
      <Empty
        scene="telescope"
        accent={themeColor}
        title="Visuals coming soon"
        description="Flow diagrams and concept maps will appear here as your teacher adds them."
      />
    );
  }
  return (
    <>
      {flows.map((f) => {
        const data = f.output_json as unknown as FlowDiagramData | null;
        if (!data) return null;
        return (
          <ThemedSection key={f.id} themeColor={themeColor}>
            <CardHeader>
              <CardTitle className="flex items-center text-lg md:text-xl">
                <ThemedTitleMark themeColor={themeColor} />
                {data.title}
              </CardTitle>
              {data.description && (
                <CardDescription className="text-base">
                  {data.description}
                </CardDescription>
              )}
              <Badge variant="outline" className="mt-2 w-fit text-[10px]">
                Flow diagram
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="rounded-xl border border-(--color-border) bg-(--color-card) p-3">
                <FlowDiagram data={data} />
              </div>
            </CardContent>
          </ThemedSection>
        );
      })}

      {diagrams.map((d) => {
        const data = d.output_json as unknown as
          | { title?: string; central_term: string; branches: { label: string; details?: string[] }[] }
          | null;
        if (!data) return null;
        return (
          <ThemedSection key={d.id} themeColor={themeColor}>
            <CardHeader>
              <CardTitle className="flex items-center text-lg md:text-xl">
                <ThemedTitleMark themeColor={themeColor} />
                {data.title ?? d.title ?? "Concept map"}
              </CardTitle>
              <CardDescription className="text-base">
                A bird's-eye view of the chapter's main idea and how its
                sub-topics connect.
              </CardDescription>
              <Badge variant="outline" className="mt-2 w-fit text-[10px]">
                Concept map
              </Badge>
            </CardHeader>
            <CardContent>
              <MindMapInteractive data={data} height={520} />
            </CardContent>
          </ThemedSection>
        );
      })}
    </>
  );
}


function WorksheetsTab({
  worksheets,
  themeColor,
}: {
  worksheets: GeneratedContent[];
  themeColor: string;
}) {
  // Render each worksheet inline via <WorksheetView> from its output_json.
  // We previously surfaced a list of "open in new tab" PDF buttons; the new
  // surface keeps the user inside the platform — no download path.
  //
  // Filter to rows that actually carry worksheet JSON (legacy rows might
  // have a PDF but no parsed JSON; show a tombstone for those rather than a
  // blank section).
  const usable = worksheets.filter((w) => w.output_json !== null);
  const orphaned = worksheets.filter((w) => w.output_json === null);

  if (worksheets.length === 0) {
    return (
      <Empty
        scene="books"
        accent={themeColor}
        title="Worksheets coming soon"
        description="Practice worksheets will appear here once your teacher publishes them. They're a great way to test what you've learned."
      />
    );
  }

  return (
    <div className="space-y-4">
      {usable.map((w) => {
        const data = w.output_json as unknown as WorksheetOutput;
        return <WorksheetView key={w.id} worksheet={data} />;
      })}
      {orphaned.length > 0 && (
        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">
              {orphaned.length}{" "}
              {orphaned.length === 1 ? "worksheet needs" : "worksheets need"}{" "}
              re-rendering
            </CardTitle>
            <CardDescription>
              These rows exist in the catalog but their structured content
              isn't available for inline view. Ask the platform team to
              re-generate.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}


/**
 * Tests / assessments tab. Lists the assessments published for this
 * chapter and lets the student take one in-place — the previous flow
 * required them to leave the Learn page and visit /assessments first.
 *
 * Each row shows: title (link to detail), type, status / submission badge,
 * marks, question count, due date, and a primary action button:
 *   - Already submitted  → "View results" → /assessments/:id
 *   - PUBLISHED & learner → "Take test"  → /assessments/:id/take
 *   - DRAFT / CLOSED      → "Open"        → /assessments/:id (read-only)
 *
 * Teachers and admins see the same listing but never get the "Take test"
 * CTA — `isLearner` gates that.
 */
function AssessmentsTab({
  assessments,
  mySubmissions,
  isLearner,
  themeColor,
}: {
  assessments: Assessment[];
  mySubmissions: MySubmission[];
  isLearner: boolean;
  themeColor: string;
}) {
  // We compare each row's `created_by_id` against the current user to
  // distinguish self-started quizzes (the student tapped "Start a quiz" /
  // /quick-quiz) from teacher-assigned ones. Pulling the user inline keeps
  // the prop-drilling minimal — `isLearner` is already derived upstream
  // but the user.id we need for this comparison wasn't being threaded.
  const { user } = useAuth();
  const currentUserId = user?.id;

  // Build a fast lookup so each row's submission status comes back O(1) —
  // the list endpoint returns submissions across all of the user's
  // assessments, not just this chapter's.
  const submissionByAssessment = useMemo(() => {
    const map = new Map<number, MySubmission>();
    for (const s of mySubmissions) map.set(s.assessment_id, s);
    return map;
  }, [mySubmissions]);

  if (assessments.length === 0) {
    return (
      <Empty
        scene="trophy"
        accent={themeColor}
        title="No tests yet"
        description="When tests are published for this chapter, they'll show up here. Try the Practice button at the top to start a quick quiz of your own anytime."
      />
    );
  }

  return (
    <ThemedSection themeColor={themeColor}>
      <CardHeader>
        <CardTitle className="flex items-center text-xl md:text-2xl">
          <ThemedTitleMark themeColor={themeColor} />
          {isLearner ? "Take a test" : "Tests for this chapter"}
        </CardTitle>
        <CardDescription className="text-base">
          {isLearner
            ? "Pick one to attempt — your score updates your mastery map. Tests assigned by your teacher have a graduation cap; ones you started yourself show a person."
            : "Assessments published for this chapter."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {assessments.map((a) => {
          const mySub = submissionByAssessment.get(a.id);
          // Status display priority: my submission (if any) trumps the
          // assessment's own status, because what the student cares about
          // is "did I do this yet" not "is it published". For non-learners
          // we always show the assessment status.
          const showSubmissionBadge = isLearner && mySub !== undefined;
          // Source: did the current user start this themselves (e.g. via
          // /quick-quiz) or did a teacher assign it? We surface this only
          // for learners — for teachers / admins the field is noise (they
          // already know what they authored vs. what colleagues did).
          const isSelfStarted =
            currentUserId !== undefined && a.created_by_id === currentUserId;
          return (
            <div
              key={a.id}
              /* The row isn't a single click target (title and action
                 button each go to different URLs) so we don't wrap it in
                 a Link. We do, however, want the row to feel alive —
                 hover lifts the border to the chapter's subject colour
                 (--theme is published by the page-level wrapper from
                 step #1) and tints the background slightly, mirroring
                 the active-tab treatment from step #4. */
              className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-(--color-border) bg-(--color-card) px-3 py-2 transition-all duration-150 hover:border-(--theme)/40 hover:shadow-sm"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    to={`/assessments/${a.id}`}
                    className="font-medium underline-offset-4 hover:underline truncate"
                  >
                    {a.title}
                  </Link>
                  <Badge variant="outline" className="text-[10px]">
                    {a.type}
                  </Badge>
                  {isLearner && (
                    isSelfStarted ? (
                      <Badge variant="secondary" className="gap-1">
                        <UserIcon className="h-3 w-3" /> Self-study
                      </Badge>
                    ) : (
                      <Badge variant="default" className="gap-1">
                        <GraduationCap className="h-3 w-3" /> Assigned
                      </Badge>
                    )
                  )}
                  {showSubmissionBadge ? (
                    mySub.status === "EVALUATED" ? (
                      <Badge variant="success" className="gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Done · {mySub.total_awarded ?? 0}/{mySub.max_marks}
                      </Badge>
                    ) : (
                      <Badge variant="warning">Submitted</Badge>
                    )
                  ) : (
                    <Badge
                      variant={
                        a.status === "PUBLISHED"
                          ? "success"
                          : a.status === "CLOSED"
                            ? "outline"
                            : "secondary"
                      }
                    >
                      {a.status}
                    </Badge>
                  )}
                </div>
                <div className="mt-0.5 text-xs text-(--color-muted-foreground)">
                  {a.questions?.length ?? 0}{" "}
                  {(a.questions?.length ?? 0) === 1 ? "question" : "questions"}{" "}
                  · {a.total_marks} marks
                  {a.duration_minutes ? ` · ${a.duration_minutes} min` : ""}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {/* Action priority: results > take > open. The Take CTA is
                    learner-only so a teacher viewing the same row sees
                    "Open" and can inspect the assessment without filling
                    in answers. */}
                {isLearner && mySub ? (
                  <Button asChild size="sm" variant="outline">
                    <Link to={`/assessments/${a.id}`}>
                      View results <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </Button>
                ) : isLearner && a.status === "PUBLISHED" ? (
                  <Button asChild size="sm">
                    <Link to={`/assessments/${a.id}/take`}>
                      Take test <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </Button>
                ) : (
                  <Button asChild size="sm" variant="outline">
                    <Link to={`/assessments/${a.id}`}>
                      Open <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </CardContent>
    </ThemedSection>
  );
}


// Google Drive file ids are URL-safe base64-ish tokens. Validating before we
// build a URL means a bad row can never smuggle a different host or path
// into the iframe `src`.
const DRIVE_ID_RE = /^[A-Za-z0-9_-]{20,100}$/;

function videoEmbedUrl(video: ChapterVideo): string | null {
  if (video.provider === "gdrive" && DRIVE_ID_RE.test(video.external_id)) {
    return `https://drive.google.com/file/d/${video.external_id}/preview`;
  }
  return null;
}

function VideosTab({
  videos,
  themeColor,
}: {
  videos: ChapterVideo[];
  themeColor: string;
}) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (videos.length === 0) {
    return (
      <Empty
        scene="puzzle"
        accent={themeColor}
        title="Video lectures on the way"
        description="Lessons for this chapter will appear here when they're ready."
      />
    );
  }

  const index = Math.min(activeIndex, videos.length - 1);
  const current = videos[index];
  const src = videoEmbedUrl(current);

  return (
    <ThemedSection themeColor={themeColor}>
      <CardHeader>
        <CardTitle className="flex items-center text-xl md:text-2xl">
          <ThemedTitleMark themeColor={themeColor} />
          Video lectures
        </CardTitle>
        <CardDescription className="text-base">
          Watch the lesson first, then the word-by-word parts, before you try
          the worksheets.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="relative aspect-video w-full overflow-hidden rounded-xl border bg-black">
          {src ? (
            <>
              <iframe
                // Re-mount per video so switching parts resets the player.
                key={current.id}
                src={src}
                title={current.title}
                className="h-full w-full"
                // No picture-in-picture: it would pull the video out of the page.
                allow="autoplay; fullscreen"
                allowFullScreen
                // `allow-popups` is deliberately NOT granted. Google's player has a
                // "pop out" button that opens the file on drive.google.com in a
                // new tab, where the URL can be copied and shared. Without the
                // permission the browser refuses to open any new window from here.
                sandbox="allow-scripts allow-same-origin allow-presentation"
              />
              {/* Belt and braces: swallow clicks on the corner where the player
                  draws its pop-out button, and its right-click menu. */}
              <div
                aria-hidden
                className="absolute right-0 top-0 z-10 h-16 w-20"
                onContextMenu={(e) => e.preventDefault()}
              />
            </>
          ) : (
            <div className="flex h-full items-center justify-center p-6 text-center text-sm text-white/80">
              This video can't be played right now.
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-2">
          <p className="min-w-0 truncate text-base font-medium">
            {current.title}
          </p>
          <div className="flex shrink-0 gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={index === 0}
              onClick={() => setActiveIndex(index - 1)}
            >
              <ChevronLeft className="h-4 w-4" /> Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={index === videos.length - 1}
              onClick={() => setActiveIndex(index + 1)}
            >
              Next <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          {videos.map((v, i) => (
            <Button
              key={v.id}
              className="w-full justify-start rounded-xl py-5 text-base"
              variant={i === index ? "default" : "outline"}
              onClick={() => setActiveIndex(i)}
            >
              <PlayCircle className="h-5 w-5" />
              <span className="min-w-0 truncate">{v.title}</span>
            </Button>
          ))}
        </div>
      </CardContent>
    </ThemedSection>
  );
}


function SimulationsTab({
  simulations,
  themeColor,
}: {
  simulations: GeneratedContent[];
  themeColor: string;
}) {
  const [activeId, setActiveId] = useState<number | null>(null);
  const [src, setSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // Native browser full screen is tracked from the `fullscreenchange` event;
  // `expanded` is the CSS fallback for browsers with no element full screen
  // (notably iPhone Safari), where we cover the viewport ourselves instead.
  const [nativeFull, setNativeFull] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const viewerRef = useRef<HTMLDivElement>(null);
  const urlRef = useRef<string | null>(null);
  // Bumped on every open/close so a slow, superseded fetch can't overwrite
  // the simulation the learner has since switched to.
  const requestRef = useRef(0);

  const isFull = nativeFull || expanded;
  const active = simulations.find((s) => s.id === activeId) ?? null;

  function releaseUrl() {
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
  }

  // Free the blob when the tab is left.
  useEffect(() => releaseUrl, []);

  useEffect(() => {
    const onChange = () => setNativeFull(document.fullscreenElement === viewerRef.current);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  useEffect(() => {
    if (!expanded) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [expanded]);

  async function play(sim: GeneratedContent) {
    const ticket = ++requestRef.current;
    releaseUrl();
    setActiveId(sim.id);
    setSrc(null);
    setLoading(true);
    try {
      const loaded = await loadArtifactObjectUrl(sim.id);
      if (ticket !== requestRef.current) {
        if (loaded) URL.revokeObjectURL(loaded.url);
        return;
      }
      if (!loaded) {
        // Already explained to the user with a toast.
        setActiveId(null);
        return;
      }
      urlRef.current = loaded.url;
      setSrc(loaded.url);
    } catch (err) {
      if (ticket === requestRef.current) {
        setActiveId(null);
        toast.error(humanError(err));
      }
    } finally {
      if (ticket === requestRef.current) setLoading(false);
    }
  }

  function closeViewer() {
    requestRef.current++;
    if (document.fullscreenElement) void document.exitFullscreen().catch(() => {});
    releaseUrl();
    setExpanded(false);
    setSrc(null);
    setActiveId(null);
    setLoading(false);
  }

  async function toggleFullScreen() {
    // Leaving: clear both modes, whichever one is active.
    if (document.fullscreenElement || expanded) {
      setExpanded(false);
      if (document.fullscreenElement) await document.exitFullscreen().catch(() => {});
      return;
    }
    const el = viewerRef.current;
    if (el?.requestFullscreen) {
      // Real browsers answer straight away. Some embedded browsers / WebViews
      // accept the request but never settle it, so don't wait forever: if it
      // hasn't taken effect shortly, cover the viewport ourselves instead.
      const entered = await Promise.race([
        el.requestFullscreen().then(
          () => true,
          () => false, // denied or unsupported here
        ),
        new Promise<boolean>((resolve) =>
          setTimeout(() => resolve(document.fullscreenElement === el), 800),
        ),
      ]);
      if (entered) return;
    }
    setExpanded(true);
  }

  if (simulations.length === 0) {
    return (
      <Empty
        scene="puzzle"
        accent={themeColor}
        title="Simulations on the way"
        description="Interactive scenes and activities will appear here when they're ready."
      />
    );
  }
  return (
    <ThemedSection themeColor={themeColor}>
      <CardHeader>
        <CardTitle className="flex items-center text-xl md:text-2xl">
          <ThemedTitleMark themeColor={themeColor} />
          Simulations
        </CardTitle>
        <CardDescription className="text-base">
          Tap any one to play it right here. Use Full screen for a bigger view.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {active && (
          <div
            ref={viewerRef}
            className={cn(
              "flex flex-col overflow-hidden border bg-(--color-card) shadow-sm",
              expanded ? "fixed inset-0 z-50 rounded-none" : "rounded-xl",
              nativeFull && "rounded-none",
            )}
          >
            <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
              <p className="min-w-0 truncate text-sm font-medium md:text-base">
                {active.title || "Simulation"}
              </p>
              <div className="flex shrink-0 items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => void toggleFullScreen()}
                  title={isFull ? "Exit full screen" : "Full screen"}
                >
                  {isFull ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                  <span className="hidden sm:inline">{isFull ? "Exit full screen" : "Full screen"}</span>
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  title="Open in a new tab"
                  aria-label="Open in a new tab"
                  onClick={async () => {
                    try {
                      await openArtifact(active.id, { title: active.title });
                    } catch (err) {
                      toast.error(humanError(err));
                    }
                  }}
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  title="Close"
                  aria-label="Close simulation"
                  onClick={closeViewer}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div
              className={cn(
                "relative bg-white",
                isFull ? "min-h-0 flex-1" : "h-[70vh] min-h-[420px]",
              )}
            >
              {loading || !src ? (
                <div className="flex h-full items-center justify-center gap-2 text-sm text-(--color-muted-foreground)">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading simulation…
                </div>
              ) : (
                <iframe
                  key={active.id}
                  src={src}
                  title={active.title || "Simulation"}
                  className="absolute inset-0 h-full w-full border-0"
                  allowFullScreen
                  // Simulations are generated, self-contained pages. Running them
                  // in an opaque-origin sandbox (no `allow-same-origin`) means their
                  // scripts cannot read this app's login token or call its API.
                  sandbox="allow-scripts allow-modals"
                />
              )}
            </div>
          </div>
        )}

        <div className="space-y-2">
          {simulations.map((sim) => (
            <Button
              key={sim.id}
              className="w-full justify-start rounded-xl py-6 text-base transition-transform hover:-translate-y-0.5 hover:shadow-md"
              variant={sim.id === activeId ? "default" : "outline"}
              onClick={() => void play(sim)}
            >
              <PlayCircle className="h-5 w-5" />
              {sim.title || "Play simulation"}
            </Button>
          ))}
        </div>
      </CardContent>
    </ThemedSection>
  );
}


function ExtraReadingTab({
  items,
  themeColor,
}: {
  items: GeneratedContent[];
  themeColor: string;
}) {
  if (items.length === 0) {
    return (
      <Empty
        scene="leaf"
        accent={themeColor}
        title="No extras yet"
        description="If your teacher uploads any extra reading material, you'll find it here."
      />
    );
  }
  return (
    <ThemedSection themeColor={themeColor}>
      <CardHeader>
        <CardTitle className="flex items-center text-xl md:text-2xl">
          <ThemedTitleMark themeColor={themeColor} />
          Extra reading
        </CardTitle>
        <CardDescription className="text-base">
          Bonus material to deepen your understanding. Opens in our in-platform
          viewer — no downloads.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {items.map((ec) => (
          <Link
            key={ec.id}
            to={`/content/${ec.id}`}
            className="group flex items-center justify-between gap-3 rounded-xl border-2 border-(--color-border) p-4 transition-all duration-150 hover:-translate-y-0.5 hover:border-(--color-primary)/40 hover:shadow-md"
          >
            <div className="flex items-center gap-3 text-sm font-medium md:text-base">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[color-mix(in_oklab,var(--color-primary)_10%,transparent)] text-(--color-primary)">
                <FileText className="h-5 w-5" />
              </div>
              {ec.title}
            </div>
            <ArrowRight className="h-5 w-5 text-(--color-muted-foreground) transition-transform group-hover:translate-x-1" />
          </Link>
        ))}
      </CardContent>
    </ThemedSection>
  );
}

export function SummaryView({
  summary,
  excludeGlossary = false,
}: {
  summary: ChapterSummaryOutput;
  /**
   * When true, skip the glossary block. Used by the chapter Learn page
   * (which surfaces glossary as its own tab so each tab stays small and
   * focused) while pages that want the canonical full summary — like
   * ContentDetail — leave it false to keep the legacy single-page view.
   */
  excludeGlossary?: boolean;
}) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Chapter summary</CardTitle>
          <CardDescription>{summary.intro}</CardDescription>
        </CardHeader>
        <CardContent>
          <MindMapInteractive data={summary.overview_diagram} height={520} />
        </CardContent>
      </Card>

      {summary.sections.map((section, i) => (
        <SectionBlock key={i} section={section} index={i + 1} />
      ))}

      {!excludeGlossary && summary.glossary.length > 0 && (
        <GlossaryBlock terms={summary.glossary} />
      )}
    </div>
  );
}

function SectionBlock({
  section,
  index,
}: {
  section: ChapterSummarySection;
  index: number;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start gap-3">
          <Badge variant="outline" className="mt-0.5">
            {index}
          </Badge>
          <CardTitle className="text-base leading-snug">{section.heading}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="space-y-2 text-sm leading-relaxed">
          {section.bullets.map((b, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-(--color-primary)">•</span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
        {section.diagram && (
          <MindMapInteractive data={section.diagram} height={420} />
        )}
      </CardContent>
    </Card>
  );
}

function GlossaryBlock({ terms }: { terms: ChapterSummaryGlossaryTerm[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Glossary</CardTitle>
        <CardDescription>Words to remember from this chapter.</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-3 sm:grid-cols-2">
          {terms.map((g, i) => (
            <div
              key={i}
              className="rounded-md border border-(--color-border) px-3 py-2"
            >
              <dt className="text-sm font-medium">{g.term}</dt>
              <dd className="mt-1 text-xs text-(--color-muted-foreground)">{g.definition}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

export function LessonPlanView({ plan }: { plan: LessonPlanOutput }) {
  return (
    <Card id="lesson-plan">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Lesson plan ({plan.duration_minutes} min)</CardTitle>
          <Badge variant="secondary">Teacher</Badge>
        </div>
        <CardDescription>{plan.title}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div>
          <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
            Objectives
          </div>
          <ul className="mt-1 space-y-1">
            {plan.objectives.map((o, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-(--color-primary)">•</span>
                <span>{o}</span>
              </li>
            ))}
          </ul>
        </div>

        {plan.materials && plan.materials.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
              Materials
            </div>
            <ul className="mt-1 list-disc pl-5">
              {plan.materials.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
            Phases
          </div>
          <ol className="mt-1 space-y-3">
            {plan.activities.map((a, i) => (
              <li
                key={i}
                className="rounded-md border border-(--color-border) px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <div className="font-medium">
                    {i + 1}. {a.phase}
                  </div>
                  <Badge variant="outline">{a.duration_minutes} min</Badge>
                </div>
                <p className="mt-1 text-(--color-muted-foreground)">{a.description}</p>
                {a.teacher_actions.length > 0 && (
                  <div className="mt-2">
                    <div className="text-[11px] uppercase tracking-wide text-(--color-muted-foreground)">
                      Teacher
                    </div>
                    <ul className="list-disc pl-5">
                      {a.teacher_actions.map((t, j) => (
                        <li key={j}>{t}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {a.student_actions && a.student_actions.length > 0 && (
                  <div className="mt-2">
                    <div className="text-[11px] uppercase tracking-wide text-(--color-muted-foreground)">
                      Students
                    </div>
                    <ul className="list-disc pl-5">
                      {a.student_actions.map((s, j) => (
                        <li key={j}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </li>
            ))}
          </ol>
        </div>

        {plan.homework && plan.homework.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
              Homework
            </div>
            <ul className="mt-1 list-disc pl-5">
              {plan.homework.map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Inline worksheet renderer. Replaces the old "open the PDF in a new tab"
 * flow — content stays inside the platform with no download surface.
 *
 * The view is structured as a question stack with per-question "Show
 * answer" toggles, plus a master toggle at the top so a teacher
 * projecting the worksheet can flip every answer on/off at once. MCQ /
 * TRUE_FALSE options render as a labelled list; the correct option gets a
 * subtle highlight when answers are revealed.
 */
/**
 * Worksheet rendered as a small interactive practice surface.
 *
 * Each question is editable in place: students click an option (MCQ /
 * TRUE_FALSE), type their answer (FILL_BLANK, SHORT_ANSWER,
 * LONG_ANSWER, CASE_BASED), and tap "Check answer" to see the verdict
 * alongside the model answer + explanation. A separate "Show answer"
 * path stays available for the "I just want to see it" case.
 *
 * State is per-question:
 *   - `attempt[i]`  the learner's current input (string)
 *   - `checked[i]`  true once they've checked → reveals verdict
 *   - `revealed[i]` true if they tapped "Show answer" without
 *                   attempting → reveals the answer with no verdict
 *
 * The "Show / hide all answers" master button at the top now flips
 * the `revealed` bit en masse for the read-only path; it does NOT
 * touch `attempt` or `checked` so a learner's typed answers survive
 * a reveal-all toggle.
 */
export function WorksheetView({ worksheet }: { worksheet: WorksheetOutput }) {
  const [attempt, setAttempt] = useState<Record<number, string>>({});
  const [checked, setChecked] = useState<Record<number, boolean>>({});
  const [revealed, setRevealed] = useState<Record<number, boolean>>({});

  const allRevealed =
    worksheet.questions.length > 0 &&
    worksheet.questions.every((_, i) => revealed[i] || checked[i]);

  function toggleAll() {
    if (allRevealed) {
      setRevealed({});
    } else {
      const all: Record<number, boolean> = {};
      worksheet.questions.forEach((_, i) => {
        all[i] = true;
      });
      setRevealed(all);
    }
  }

  function setAttemptFor(i: number, v: string) {
    setAttempt((prev) => ({ ...prev, [i]: v }));
    // Editing the attempt invalidates the verdict — they're trying again.
    setChecked((prev) => ({ ...prev, [i]: false }));
  }
  function checkAnswer(i: number) {
    setChecked((prev) => ({ ...prev, [i]: true }));
  }
  function showAnswer(i: number) {
    setRevealed((prev) => ({ ...prev, [i]: true }));
  }
  function resetOne(i: number) {
    setAttempt((prev) => ({ ...prev, [i]: "" }));
    setChecked((prev) => ({ ...prev, [i]: false }));
    setRevealed((prev) => ({ ...prev, [i]: false }));
  }

  return (
    <Card id="worksheet">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>{worksheet.title}</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline">
              {worksheet.questions.length}{" "}
              {worksheet.questions.length === 1 ? "question" : "questions"}
            </Badge>
            <Badge variant="secondary">{worksheet.total_marks} marks</Badge>
          </div>
        </div>
        <CardDescription>{worksheet.instructions}</CardDescription>
        <div className="mt-2 flex justify-end">
          <Button
            size="sm"
            variant="outline"
            onClick={toggleAll}
            disabled={worksheet.questions.length === 0}
          >
            {allRevealed ? (
              <>
                <EyeOff className="h-3.5 w-3.5" /> Hide all answers
              </>
            ) : (
              <>
                <Eye className="h-3.5 w-3.5" /> Show all answers
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {worksheet.questions.map((q, i) => (
          <WorksheetQuestionCard
            key={i}
            index={i + 1}
            question={q}
            attempt={attempt[i] ?? ""}
            checked={!!checked[i]}
            revealed={!!revealed[i]}
            onAttemptChange={(v) => setAttemptFor(i, v)}
            onCheck={() => checkAnswer(i)}
            onShow={() => showAnswer(i)}
            onReset={() => resetOne(i)}
          />
        ))}
      </CardContent>
    </Card>
  );
}

/**
 * One worksheet question rendered as an interactive practice card.
 *
 * The render switches on `question.type`:
 *   - MCQ / TRUE_FALSE → clickable option list (radio semantics).
 *   - FILL_BLANK → single-line text input.
 *   - SHORT_ANSWER / LONG_ANSWER / CASE_BASED → multi-line textarea
 *     (rows scale with expected answer length).
 *
 * Verdict logic
 *   For objective types (MCQ / TRUE_FALSE / FILL_BLANK) we can
 *   auto-grade by comparing the attempt to `question.answer`
 *   (case-insensitive, trimmed for FILL_BLANK). For subjective
 *   types we cannot grade reliably, so we just show the model answer
 *   side-by-side and let the learner self-evaluate.
 */
function WorksheetQuestionCard({
  index,
  question,
  attempt,
  checked,
  revealed,
  onAttemptChange,
  onCheck,
  onShow,
  onReset,
}: {
  index: number;
  question: WorksheetQuestion;
  attempt: string;
  checked: boolean;
  revealed: boolean;
  onAttemptChange: (v: string) => void;
  onCheck: () => void;
  onShow: () => void;
  onReset: () => void;
}) {
  const isMcq = question.type === "MCQ";
  const isTrueFalse = question.type === "TRUE_FALSE";
  const isFillBlank = question.type === "FILL_BLANK";
  const isShortAnswer = question.type === "SHORT_ANSWER";
  const isLongAnswer = question.type === "LONG_ANSWER";
  const isCaseBased = question.type === "CASE_BASED";
  const hasOptions = (isMcq || isTrueFalse) && (question.options?.length ?? 0) > 0;
  // Objective types can be auto-graded by string comparison. Anything
  // else needs side-by-side comparison with the model answer.
  const isObjective = isMcq || isTrueFalse || isFillBlank;

  // Verdict (only valid when `checked` is true and the type is
  // objective). FILL_BLANK comparison is case-insensitive + trimmed
  // because spelling variation shouldn't be the difference between
  // "I knew it" and "I didn't".
  const normalisedAttempt = attempt.trim();
  const normalisedAnswer = question.answer.trim();
  const isCorrect =
    isObjective &&
    (isFillBlank
      ? normalisedAttempt.toLowerCase() === normalisedAnswer.toLowerCase()
      : normalisedAttempt === normalisedAnswer);
  const hasAttempt = normalisedAttempt.length > 0;
  // The model answer is shown once the learner has either checked
  // their answer or asked to see it directly.
  const showAnswerPanel = checked || revealed;

  return (
    <div className="rounded-md border border-(--color-border) bg-(--color-card) p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2 text-xs text-(--color-muted-foreground)">
          <Badge variant="outline">{question.type.replace("_", " ")}</Badge>
          <Badge variant="secondary">{question.difficulty}</Badge>
          <span>
            {question.marks} {question.marks === 1 ? "mark" : "marks"}
          </span>
          {question.outcome_code && (
            <Badge variant="outline">{question.outcome_code}</Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Verdict badge — only after Check on objective types. */}
          {checked && isObjective && hasAttempt && (
            isCorrect ? (
              <Badge variant="success" className="gap-1">
                <CheckCircle2 className="h-3 w-3" /> Correct
              </Badge>
            ) : (
              <Badge variant="destructive" className="gap-1">
                <XCircle className="h-3 w-3" /> Try again
              </Badge>
            )
          )}
          {checked && !isObjective && (
            <Badge variant="outline" className="gap-1">
              Self-review
            </Badge>
          )}
        </div>
      </div>
      <div className="mt-2 font-medium leading-snug">
        Q{index}. {question.question}
      </div>

      {/* --- INPUT SECTION ----------------------------------------- */}
      {hasOptions && (
        <ul className="mt-3 space-y-1.5">
          {question.options!.map((opt, j) => {
            const selected = attempt === opt;
            const isAnswerKey = opt === question.answer;
            // Highlight green only if (a) we've checked or revealed
            // AND (b) the option is the correct one. Selected-but-
            // wrong gets a red border to make the mistake legible.
            const showAsCorrect = showAnswerPanel && isAnswerKey;
            const showAsWrong =
              checked && selected && !isAnswerKey;
            return (
              <li key={j}>
                <label
                  className={cn(
                    "flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 text-sm transition-colors",
                    showAsCorrect &&
                      "border-(--color-success) bg-[color-mix(in_oklab,var(--color-success)_10%,transparent)]",
                    showAsWrong &&
                      "border-(--color-destructive) bg-[color-mix(in_oklab,var(--color-destructive)_8%,transparent)]",
                    !showAsCorrect && !showAsWrong && selected &&
                      "border-(--color-primary) bg-[color-mix(in_oklab,var(--color-primary)_8%,transparent)]",
                    !showAsCorrect && !showAsWrong && !selected &&
                      "border-(--color-border) hover:bg-(--color-muted)",
                  )}
                >
                  <input
                    type="radio"
                    name={`ws-q-${index}`}
                    value={opt}
                    checked={selected}
                    onChange={(e) => onAttemptChange(e.target.value)}
                    className="h-4 w-4 accent-(--color-primary)"
                  />
                  <span className="font-mono text-xs text-(--color-muted-foreground)">
                    {String.fromCharCode(65 + j)}.
                  </span>
                  <span className="flex-1">{opt}</span>
                  {showAsCorrect && (
                    <Badge variant="success" className="ml-auto">
                      Correct answer
                    </Badge>
                  )}
                </label>
              </li>
            );
          })}
        </ul>
      )}
      {isFillBlank && (
        <div className="mt-3 space-y-1.5">
          <Label htmlFor={`ws-input-${index}`} className="sr-only">
            Your answer
          </Label>
          <Input
            id={`ws-input-${index}`}
            value={attempt}
            placeholder="Type your answer…"
            onChange={(e) => onAttemptChange(e.target.value)}
            className={cn(
              checked && hasAttempt && isCorrect &&
                "border-(--color-success) focus-visible:ring-(--color-success)",
              checked && hasAttempt && !isCorrect &&
                "border-(--color-destructive) focus-visible:ring-(--color-destructive)",
            )}
          />
        </div>
      )}
      {(isShortAnswer || isLongAnswer || isCaseBased) && (
        <div className="mt-3 space-y-1.5">
          <Label htmlFor={`ws-input-${index}`} className="sr-only">
            Your answer
          </Label>
          <textarea
            id={`ws-input-${index}`}
            value={attempt}
            placeholder="Type your answer…"
            onChange={(e) => onAttemptChange(e.target.value)}
            rows={isShortAnswer ? 3 : isLongAnswer ? 6 : 7}
            className="flex w-full rounded-md border border-(--color-input) bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-(--color-muted-foreground) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--color-ring)"
          />
        </div>
      )}

      {/* --- ACTION ROW -------------------------------------------- */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {!checked && !revealed && (
          <Button
            size="sm"
            onClick={onCheck}
            disabled={!hasAttempt}
            // Subtle "fill it in first" cue — disabled when there's
            // nothing to check.
          >
            <CheckCircle2 className="h-3.5 w-3.5" /> Check answer
          </Button>
        )}
        {!revealed && (
          <Button size="sm" variant="outline" onClick={onShow}>
            <Eye className="h-3.5 w-3.5" /> Show answer
          </Button>
        )}
        {(checked || revealed) && (
          <Button size="sm" variant="ghost" onClick={onReset}>
            <RotateCcw className="h-3.5 w-3.5" /> Try again
          </Button>
        )}
      </div>

      {/* --- ANSWER PANEL ------------------------------------------ */}
      {showAnswerPanel && (
        <div className="mt-3 space-y-2">
          {/* For MCQ/TF the option highlight already shows the answer;
              only non-option types need a dedicated answer panel. */}
          {!hasOptions && (
            <div>
              <div className="text-[11px] uppercase tracking-wide text-(--color-muted-foreground)">
                {isObjective ? "Correct answer" : "Model answer"}
              </div>
              <div
                className={cn(
                  "mt-1 rounded-md p-3 whitespace-pre-wrap",
                  isObjective
                    ? "border border-(--color-success) bg-[color-mix(in_oklab,var(--color-success)_8%,transparent)]"
                    : "border border-(--color-primary)/40 bg-[color-mix(in_oklab,var(--color-primary)_6%,transparent)]",
                )}
              >
                {question.answer}
              </div>
              {!isObjective && checked && hasAttempt && (
                <p className="mt-2 text-xs text-(--color-muted-foreground)">
                  Compare your answer to the model and note what was
                  missing — that comparison is the practice.
                </p>
              )}
            </div>
          )}
          {question.explanation && (
            <div className="rounded-md border border-(--color-border) bg-(--color-muted)/40 p-3 text-xs text-(--color-muted-foreground)">
              <span className="font-medium">Explanation: </span>
              {question.explanation}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Inline PPT renderer. Replaces the old "open the PPTX in a new tab" flow
 * with a slide carousel — content stays inside the platform with no
 * download surface.
 *
 * Layout: one slide visible at a time in a 16:9-ish card. Prev / Next
 * buttons + slide counter at the bottom; arrow keys also navigate. A row
 * of slide-number dots provides direct jump access.
 *
 * Speaker notes are visible by default (this view is gated to teachers
 * upstream; students never reach it). A toggle hides them for projection
 * mode so the teacher can show the deck on a classroom screen without the
 * notes panel competing for attention.
 */
export function PPTOutlineView({ deck }: { deck: PPTOutlineOutput }) {
  const [index, setIndex] = useState(0);
  const [showNotes, setShowNotes] = useState(true);

  const total = deck.slides.length;
  const slide = deck.slides[index];
  const canPrev = index > 0;
  const canNext = index < total - 1;

  // Arrow-key navigation. Only fires when no input/textarea/contenteditable
  // is focused — otherwise typing in a quiz field on the same page would
  // jump slides unexpectedly.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      if (target) {
        const tag = target.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable) {
          return;
        }
      }
      if (e.key === "ArrowLeft" && index > 0) {
        e.preventDefault();
        setIndex((i) => Math.max(0, i - 1));
      } else if (e.key === "ArrowRight" && index < total - 1) {
        e.preventDefault();
        setIndex((i) => Math.min(total - 1, i + 1));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, total]);

  if (!slide) {
    return <Empty title="This deck has no slides" />;
  }

  return (
    <Card id="ppt-outline">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>{deck.title}</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline">
              {total} {total === 1 ? "slide" : "slides"}
            </Badge>
            <Badge variant="secondary">Teacher</Badge>
          </div>
        </div>
        <CardDescription>
          Class {deck.class_level} · {deck.subject} · {deck.chapter_title}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* The slide canvas. Min-height is generous so navigation between
            short-bullet and long-bullet slides doesn't jitter the layout. */}
        <div className="rounded-lg border border-(--color-border) bg-(--color-card) p-6 shadow-sm min-h-[320px] flex flex-col">
          <div className="mb-3 flex items-center justify-between">
            <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
              {SLIDE_TYPE_LABEL[slide.slide_type]}
            </Badge>
            <span className="text-xs text-(--color-muted-foreground) tabular-nums">
              {index + 1} / {total}
            </span>
          </div>
          <h2 className="text-2xl font-semibold leading-tight">{slide.title}</h2>
          {slide.bullets.length > 0 && (
            <ul className="mt-4 space-y-2">
              {slide.bullets.map((b, i) => (
                <li key={i} className="flex gap-2 text-base leading-relaxed">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-(--color-primary) flex-shrink-0" />
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Speaker notes — teacher-facing prep material that wouldn't show
            on a projector. Toggleable so the teacher can hide them when
            screen-sharing. */}
        {slide.speaker_notes && (
          <div className="rounded-md border border-(--color-border) bg-(--color-muted)/40">
            <button
              type="button"
              className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-(--color-foreground) hover:bg-(--color-muted) cursor-pointer text-left bg-transparent"
              onClick={() => setShowNotes((v) => !v)}
            >
              <span className="flex items-center gap-1.5">
                {showNotes ? (
                  <EyeOff className="h-3.5 w-3.5" />
                ) : (
                  <Eye className="h-3.5 w-3.5" />
                )}
                Speaker notes
              </span>
              <span className="text-[11px] uppercase tracking-wide text-(--color-muted-foreground)">
                {showNotes ? "Hide" : "Show"}
              </span>
            </button>
            {showNotes && (
              <div className="px-3 pb-3 pt-1 text-sm text-(--color-muted-foreground) whitespace-pre-wrap">
                {slide.speaker_notes}
              </div>
            )}
          </div>
        )}

        {/* Navigation row: prev / dots / next. Dots are clickable for
            direct jump on shorter decks; on the max-20-slide schema they
            stay readable on desktop. */}
        <div className="flex items-center justify-between gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setIndex((i) => Math.max(0, i - 1))}
            disabled={!canPrev}
          >
            <ChevronLeft className="h-4 w-4" /> Prev
          </Button>
          <div className="flex flex-wrap items-center justify-center gap-1.5">
            {deck.slides.map((_, i) => (
              <button
                key={i}
                type="button"
                aria-label={`Go to slide ${i + 1}`}
                onClick={() => setIndex(i)}
                className={cn(
                  "h-2 w-2 rounded-full transition-colors cursor-pointer",
                  i === index
                    ? "bg-(--color-primary)"
                    : "bg-(--color-muted-foreground)/30 hover:bg-(--color-muted-foreground)/60",
                )}
              />
            ))}
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setIndex((i) => Math.min(total - 1, i + 1))}
            disabled={!canNext}
          >
            Next <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// Human-readable labels for the slide-type enum from the LLM schema.
// Splits TITLE / OBJECTIVES / CONCEPT / EXAMPLE / ACTIVITY / QUICK_CHECK /
// SUMMARY into readable pills the teacher can use to scan the deck flow.
const SLIDE_TYPE_LABEL: Record<SlideType, string> = {
  TITLE: "Title",
  OBJECTIVES: "Objectives",
  CONCEPT: "Concept",
  EXAMPLE: "Example",
  ACTIVITY: "Activity",
  QUICK_CHECK: "Quick check",
  SUMMARY: "Summary",
};


export function ActivitySetView({ activitySet }: { activitySet: ClassroomActivitySetOutput }) {
  return (
    <Card id="classroom-activities">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Classroom activities</CardTitle>
          <Badge variant="secondary">Teacher</Badge>
        </div>
        <CardDescription>{activitySet.chapter_focus}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {activitySet.activities.map((a, i) => (
          <ActivityCard key={i} activity={a} index={i + 1} />
        ))}
      </CardContent>
    </Card>
  );
}

function ActivityCard({ activity, index }: { activity: ClassroomActivity; index: number }) {
  return (
    <div className="rounded-md border border-(--color-border) p-3 text-sm">
      <div className="flex items-center justify-between">
        <div className="font-medium">
          {index}. {activity.title}
        </div>
        <Badge variant="outline">{activity.duration_minutes} min</Badge>
      </div>
      <p className="mt-1 text-(--color-muted-foreground)">{activity.objective}</p>
      {activity.materials && activity.materials.length > 0 && (
        <div className="mt-2">
          <div className="text-[11px] uppercase tracking-wide text-(--color-muted-foreground)">
            Materials
          </div>
          <ul className="list-disc pl-5">
            {activity.materials.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-2">
        <div className="text-[11px] uppercase tracking-wide text-(--color-muted-foreground)">
          Steps
        </div>
        <ol className="list-decimal space-y-1 pl-5">
          {activity.steps.map((s, i) => (
            <li key={i}>
              <span className="font-medium">{s.title}: </span>
              <span className="text-(--color-muted-foreground)">{s.detail}</span>
            </li>
          ))}
        </ol>
      </div>
      {activity.guiding_questions && activity.guiding_questions.length > 0 && (
        <div className="mt-2">
          <div className="text-[11px] uppercase tracking-wide text-(--color-muted-foreground)">
            Guiding questions
          </div>
          <ul className="list-disc pl-5">
            {activity.guiding_questions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      )}
      {activity.safety_notes && activity.safety_notes.length > 0 && (
        <div className="mt-2 rounded-md border border-(--color-warning) bg-[color-mix(in_oklab,var(--color-warning)_8%,transparent)] px-3 py-1 text-xs text-(--color-warning)">
          Safety: {activity.safety_notes.join(" · ")}
        </div>
      )}
    </div>
  );
}

/**
 * Lesson plan tab. Pure structured render of the LessonPlanOutput JSON via
 * `<LessonPlanView>` — no DOCX download. Content stays inside the platform.
 * The compact summary strip at the top is informational (duration, phase
 * count, objective count) so the teacher can size up the plan at a glance
 * before scrolling into the phase-by-phase view.
 */
function LessonPlanTab({ plan }: { plan: LessonPlanOutput }) {
  return (
    <>
      <div className="flex flex-wrap items-center gap-2 rounded-md border border-(--color-border) bg-(--color-card) px-3 py-2 text-xs text-(--color-muted-foreground)">
        <span>
          {plan.duration_minutes} min · {plan.activities.length} phases ·{" "}
          {plan.objectives.length} objectives
        </span>
      </div>
      <LessonPlanView plan={plan} />
    </>
  );
}

