import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type {
  Assessment,
  BloomLevel,
  ChatMessageRead,
  ChatScope,
  ChatSessionDetailRead,
  ChatSessionRead,
  Book,
  Chapter,
  ChapterDetail,
  CurriculumContext,
  GeneratedContent,
  GeneratedContentStatus,
  GeneratedContentType,
  ExplanationTier,
  ExtendedExplanation,
  InterventionNote,
  LearnerMistakesPage,
  LearnerStamp,
  LearningOutcome,
  MistakeRetryResult,
  PracticeSummary,
  Question,
  QuestionDifficulty,
  QuestionStatus,
  QuestionType,
  SchoolClass,
  Section,
  SectionPerformance,
  SectionTopicAverages,
  SectionWeakestTopics,
  Student,
  StudentMasteryGrid,
  StudentTrend,
  Subject,
  Submission,
  TeacherSubjects,
  Topic,
  ClassWeakTopics,
  PlatformSchoolSummary,
  PlatformSchoolOverview,
  PlatformLearnerSummary,
  PlatformLearnerOverview,
} from "./types";

// ---------- schools (Phase B) ----------
export interface MySchool {
  id: number;
  name: string;
  board: string;
  address: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  brand_name: string | null;
  logo_url: string | null;
  is_personal: boolean;
}

export function useMySchool(enabled = true) {
  return useQuery({
    queryKey: ["schools", "me"],
    queryFn: async () => {
      const { data } = await api.get<MySchool>("/schools/me");
      return data;
    },
    enabled,
    retry: false,
  });
}

export function useUpdateMySchool() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<MySchool>) => {
      const { data } = await api.patch<MySchool>("/schools/me", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schools", "me"] }),
  });
}

export interface TeacherRow {
  id: number;
  user_id: number;
  school_id: number;
  full_name: string;
  qualification: string | null;
}

export function useTeachers(enabled = true) {
  return useQuery({
    queryKey: ["teachers"],
    queryFn: async () => {
      const { data } = await api.get<TeacherRow[]>("/teachers");
      return data;
    },
    enabled,
  });
}

export function useStudents(enabled = true) {
  return useQuery({
    queryKey: ["students"],
    queryFn: async () => {
      const { data } = await api.get<Student[]>("/students");
      return data;
    },
    enabled,
  });
}

export function useAcademicYears(enabled = true) {
  return useQuery({
    queryKey: ["academic-years"],
    queryFn: async () => {
      const { data } = await api.get<Array<{ id: number; name: string; is_current: boolean }>>(
        "/academic-years",
      );
      return data;
    },
    enabled,
  });
}

export function useCreateSection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      class_id: number;
      academic_year_id: number;
      name: string;
      class_teacher_id?: number | null;
    }) => {
      const { data } = await api.post<Section>("/sections", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me", "sections"] }),
  });
}

export function useCreateTeacher() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      email: string;
      password: string;
      full_name: string;
      qualification?: string | null;
    }) => {
      const { data } = await api.post<TeacherRow>("/teachers", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teachers"] }),
  });
}

// ---------- teacher subject assignments ----------

/** Current teacher's effective subject scope (used by Learn / ContentLibrary). */
export function useMyTeacherSubjects(enabled = true) {
  return useQuery({
    queryKey: ["me", "teacher-subjects"],
    queryFn: async () => {
      const { data } = await api.get<TeacherSubjects>("/me/teacher-subjects");
      return data;
    },
    enabled,
  });
}

/** School-admin view of one teacher's subjects (for the assignment UI). */
export function useTeacherSubjects(teacherId: number | undefined) {
  return useQuery({
    queryKey: ["teacher-subjects", teacherId],
    queryFn: async () => {
      const { data } = await api.get<TeacherSubjects>(
        `/teachers/${teacherId}/subjects`,
      );
      return data;
    },
    enabled: teacherId !== undefined,
  });
}

/** Replace one teacher's full subject-id list. Pass [] to clear. */
export function useSetTeacherSubjects() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { teacherId: number; subjectIds: number[] }) => {
      const { data } = await api.put<TeacherSubjects>(
        `/teachers/${input.teacherId}/subjects`,
        { subject_ids: input.subjectIds },
      );
      return data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["teacher-subjects", data.teacher_id] });
      qc.invalidateQueries({ queryKey: ["me", "teacher-subjects"] });
    },
  });
}

export function useCreateStudent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      full_name: string;
      roll_number?: string | null;
      dob?: string | null;
      gender?: string | null;
      guardian_name?: string | null;
      guardian_phone?: string | null;
      login_email?: string | null;
      login_password?: string | null;
    }) => {
      const { data } = await api.post<Student>("/students", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["students"] }),
  });
}

export function useCreateEnrollment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      student_id: number;
      section_id: number;
      academic_year_id: number;
    }) => {
      const { data } = await api.post("/enrollments", body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me", "students"] });
      qc.invalidateQueries({ queryKey: ["students"] });
    },
  });
}


// ---------- auth & classes ----------
export function useClasses() {
  return useQuery({
    queryKey: ["classes"],
    queryFn: async () => {
      const { data } = await api.get<SchoolClass[]>("/curriculum/classes");
      return data;
    },
  });
}

export function useSubjects(
  classLevel?: number,
  opts?: { fetchAllWhenUndefined?: boolean },
) {
  // Default behaviour: skip the fetch until a class is picked. Pages that
  // legitimately need the full subject catalog (LearnSubject's lookup-by-id,
  // ManageSchool's per-teacher assignment editor) opt in via
  // `{ fetchAllWhenUndefined: true }`. Without this gate, pages like
  // Curriculum auto-pick a subject from the cross-class catalog before
  // their class filter has settled, which then mismatches the chapters
  // query and shows "0 chapters".
  const fetchAll = opts?.fetchAllWhenUndefined ?? false;
  return useQuery({
    queryKey: ["subjects", classLevel ?? null, fetchAll],
    queryFn: async () => {
      const params = classLevel ? { class_level: classLevel } : undefined;
      const { data } = await api.get<Subject[]>("/curriculum/subjects", { params });
      return data;
    },
    enabled: classLevel !== undefined || fetchAll,
  });
}

export function useChapters(params: {
  class_level?: number;
  subject_id?: number;
  book_id?: number;
}) {
  // Fire as long as *any* scope is provided — `subject_id` alone is enough
  // because chapters are uniquely keyed under a subject. The previous gate
  // required BOTH `class_level` AND `subject_id`, which silently broke
  // every caller (e.g. LearnSubject) that passes only one — the query
  // never fired and the page showed "0 chapters" forever. We still gate
  // off the all-undefined case because that would return every chapter
  // in the catalog, which no caller wants.
  const hasScope =
    params.class_level !== undefined ||
    params.subject_id !== undefined ||
    params.book_id !== undefined;
  return useQuery({
    queryKey: ["chapters", params],
    queryFn: async () => {
      const { data } = await api.get<Chapter[]>("/curriculum/chapters", { params });
      return data;
    },
    enabled: hasScope,
  });
}

export function useChapterDetail(chapterId?: number) {
  return useQuery({
    queryKey: ["chapter-detail", chapterId],
    queryFn: async () => {
      const { data } = await api.get<ChapterDetail>(`/curriculum/chapters/${chapterId}`);
      return data;
    },
    enabled: chapterId !== undefined,
  });
}

/** Platform-admin: create a new subject under an existing class for a
 *  given board. Used to seed NIOS / ICSE / State syllabi without
 *  dropping to a script. */
export function useCreateSubject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      class_id: number;
      name: string;
      language?: string;
      board: string;
    }) => {
      const { data } = await api.post<Subject>("/curriculum/subjects", {
        class_id: input.class_id,
        name: input.name,
        language: input.language ?? "en",
        board: input.board,
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subjects"] }),
  });
}

/** Platform-admin: create a new book under an existing subject. */
export function useCreateBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      subject_id: number;
      title: string;
      ncert_code: string;
      academic_year: string;
      source_url?: string | null;
    }) => {
      const { data } = await api.post<Book>("/curriculum/books", input);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["books"] }),
  });
}

/** Books under a subject. Used by the Onboard chapter UI's book picker. */
export function useBooks(params: { subject_id?: number; academic_year?: string }) {
  const subjectId = params.subject_id;
  return useQuery({
    queryKey: ["books", { subject_id: subjectId, academic_year: params.academic_year }],
    queryFn: async () => {
      const { data } = await api.get<Book[]>("/curriculum/books", {
        params: {
          subject_id: subjectId,
          academic_year: params.academic_year,
        },
      });
      return data;
    },
    enabled: subjectId !== undefined,
  });
}

// ---------- platform-admin chapter ingestion ----------
//
// These mutations lift the work that previously lived only in
// `scripts/extract_topics.py` etc. into the platform UI. All require
// platform_admin on the backend.

/** Multipart upload of a PDF; returns extracted text + page count
 *  without writing anything to the DB. The Onboard chapter UI uses this
 *  to pre-fill the chapter-text textarea before the admin commits. */
export function useExtractPdfText() {
  return useMutation({
    mutationFn: async (input: { file: File }) => {
      const form = new FormData();
      form.append("file", input.file);
      const { data } = await api.post<{ text: string; page_count: number }>(
        "/curriculum/extract-pdf-text",
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data;
    },
  });
}

/** Create a new Chapter row under an existing book. */
export function useCreateChapter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      book_id: number;
      chapter_number: number;
      title: string;
      full_text: string;
      source_url?: string | null;
      page_count?: number | null;
    }) => {
      const { data } = await api.post<Chapter>("/curriculum/chapters", input);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chapters"] });
      qc.invalidateQueries({ queryKey: ["chapter-detail"] });
    },
  });
}

/** Replace a chapter's topics with the supplied list. */
export function useBulkReplaceTopics() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      chapter_id: number;
      topics: Array<{ name: string; description?: string | null }>;
    }) => {
      const { data } = await api.post<{ topics: Topic[] }>(
        `/curriculum/chapters/${input.chapter_id}/topics`,
        { topics: input.topics },
      );
      return data.topics;
    },
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["chapter-detail", variables.chapter_id] });
    },
  });
}

/** Trigger LLM topic extraction. Idempotent by default; pass
 *  `overwrite=true` to wipe and replace. */
export function useExtractTopicsWithAi() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      chapter_id: number;
      overwrite?: boolean;
    }) => {
      const { data } = await api.post<{ topics: Topic[] }>(
        `/curriculum/chapters/${input.chapter_id}/topics/extract`,
        { overwrite: input.overwrite ?? false },
      );
      return data.topics;
    },
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["chapter-detail", variables.chapter_id] });
    },
  });
}

/**
 * Slice each topic's verbatim chapter text via LLM and store on
 * `Topic.full_text`. Powers the AI tutor's topic-scoped RAG context.
 *
 * Slow (~one LLM call per topic, 30-90s for a typical chapter).
 * Idempotent by default; pass `overwrite=true` to re-slice every topic.
 * Returns counts (written, skipped, errored) so the UI can show the
 * partial-success outcome.
 */
export function useExtractTopicTexts() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      chapter_id: number;
      overwrite?: boolean;
    }) => {
      const { data } = await api.post<{
        topics: Topic[];
        written: number;
        skipped: number;
        errored: number;
        errors: { topic_id: number; topic_name: string; error: string }[];
      }>(
        `/curriculum/chapters/${input.chapter_id}/topics/extract-texts`,
        { overwrite: input.overwrite ?? false },
        // Slicing one topic typically takes 5-10s; with 8 topics that's
        // ~80s. Bump axios's default no-timeout-by-default behaviour so a
        // misbehaving server connection times out cleanly at 3 minutes
        // instead of hanging forever.
        { timeout: 180_000 },
      );
      return data;
    },
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["chapter-detail", variables.chapter_id] });
    },
  });
}

/**
 * One-click chapter bootstrap. Backend kicks off topic extraction
 * synchronously (fast, returns count immediately) and schedules all
 * supported content-type generation jobs + topic-text slicing as
 * background tasks. Response describes what's queued so the UI can
 * link the admin into the Content library to monitor progress.
 */
export interface BootstrapJobInfo {
  id: number;
  content_type: string;
  status: string;
  title: string;
}

export function useBootstrapChapter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { chapter_id: number }) => {
      const { data } = await api.post<{
        topics_extracted: number;
        topic_texts_scheduled: boolean;
        jobs_scheduled: BootstrapJobInfo[];
        jobs_reused: BootstrapJobInfo[];
      }>(
        `/curriculum/chapters/${input.chapter_id}/bootstrap-content`,
        {},
        // Topic extraction runs synchronously (1 LLM call, ~5-10s).
        // Everything else is fire-and-forget on the server, so the
        // request itself is short — but bump the axios timeout anyway
        // in case the topic call is slow on a free-tier provider.
        { timeout: 60_000 },
      );
      return data;
    },
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["chapter-detail", variables.chapter_id] });
      qc.invalidateQueries({ queryKey: ["generated-content"] });
    },
  });
}

/** Replace a chapter's learning outcomes. */
export function useBulkReplaceLearningOutcomes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      chapter_id: number;
      outcomes: Array<{
        code: string;
        description: string;
        bloom_level:
          | "remember"
          | "understand"
          | "apply"
          | "analyze"
          | "evaluate"
          | "create";
        topic_name?: string | null;
      }>;
    }) => {
      const { data } = await api.post<{ outcomes: LearningOutcome[] }>(
        `/curriculum/chapters/${input.chapter_id}/learning-outcomes`,
        { outcomes: input.outcomes },
      );
      return data.outcomes;
    },
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["chapter-detail", variables.chapter_id] });
    },
  });
}

export function useCurriculumContext(chapterId?: number) {
  return useQuery({
    queryKey: ["curriculum-context", chapterId],
    queryFn: async () => {
      const { data } = await api.get<CurriculumContext>("/curriculum/context", {
        params: { chapter_id: chapterId },
      });
      return data;
    },
    enabled: chapterId !== undefined,
  });
}

// ---------- me ----------
export function useMySections() {
  return useQuery({
    queryKey: ["me", "sections"],
    queryFn: async () => {
      const { data } = await api.get<Section[]>("/me/sections");
      return data;
    },
  });
}

export function useMyStudents(sectionId?: number) {
  return useQuery({
    queryKey: ["me", "students", sectionId],
    queryFn: async () => {
      const { data } = await api.get<Student[]>("/me/students", {
        params: { section_id: sectionId },
      });
      return data;
    },
    enabled: sectionId !== undefined,
  });
}

/**
 * Lists assessments visible to the current user.
 *
 * Optional filters narrow the scope:
 * - `chapter_id` is used by the chapter Learn page's Assessments tab so the
 *   student sees only the tests for the chapter they're studying.
 * - `section_id` is used by teacher / admin section views.
 *
 * Both default to undefined (server returns the user's full visible set).
 */
export function useMyAssessments(opts?: {
  chapter_id?: number;
  section_id?: number;
}) {
  const chapterId = opts?.chapter_id;
  const sectionId = opts?.section_id;
  return useQuery({
    queryKey: ["me", "assessments", { chapterId, sectionId }],
    queryFn: async () => {
      const params: Record<string, number> = {};
      if (chapterId !== undefined) params.chapter_id = chapterId;
      if (sectionId !== undefined) params.section_id = sectionId;
      const { data } = await api.get<Assessment[]>("/me/assessments", {
        params,
      });
      return data;
    },
  });
}

export interface MySubmission {
  id: number;
  assessment_id: number;
  status: "DRAFT" | "SUBMITTED" | "EVALUATED" | "LATE";
  submitted_at: string | null;
  evaluated_at: string | null;
  total_awarded: number | null;
  max_marks: number;
}

/** All submissions owned by the current user. Lets a learner UI show
 *  "View results" / "Already done" instead of letting them re-attempt. */
export function useMySubmissions() {
  return useQuery({
    queryKey: ["me", "submissions"],
    queryFn: async () => {
      const { data } = await api.get<MySubmission[]>("/me/submissions");
      return data;
    },
  });
}

/* ---------- Practice rhythm (Stage 1 of child-centric roadmap) ---------- */

/**
 * One-shot fetch for the "Your practice" dashboard card: this week's
 * progress, the learner's weekly goal, and recent stamps. The backend
 * computes everything from `submissions.submitted_at` so there's no
 * write side-effect — safe to refetch freely.
 */
export function usePracticeSummary() {
  return useQuery({
    queryKey: ["me", "practice-summary"],
    queryFn: async () => {
      const { data } = await api.get<PracticeSummary>("/me/practice-summary");
      return data;
    },
  });
}

/** Update the learner's weekly target (1..7 days). Backend clamps the
 *  value, so a slider that lets through 0 or 10 would still be safe. */
export function useSetWeeklyGoal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (target_days: number) => {
      const { data } = await api.put<{ target_days: number; week_start: string }>(
        "/me/practice-summary/goal",
        { target_days },
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me", "practice-summary"] });
    },
  });
}

/** Full history for the stamp-book collection page. Limit is generous;
 *  paginate if any learner ever crosses 500 stamps. */
export function useMyStamps(limit = 200) {
  return useQuery({
    queryKey: ["me", "stamps", limit],
    queryFn: async () => {
      const { data } = await api.get<LearnerStamp[]>("/me/stamps", {
        params: { limit },
      });
      return data;
    },
  });
}

/* ---------- Mistake review (Stage 2 of child-centric roadmap) ---------- */

export interface MistakesFilter {
  chapter_id?: number;
  subject_id?: number;
  limit?: number;
}

/** Things I got wrong: active mistakes only — resolved rows
 *  (consecutive_corrects >= 2 by the twice-right rule) are filtered
 *  out server-side. */
export function useMyMistakes(filter: MistakesFilter = {}) {
  return useQuery({
    queryKey: ["me", "mistakes", filter],
    queryFn: async () => {
      const { data } = await api.get<LearnerMistakesPage>("/me/mistakes", {
        params: {
          chapter_id: filter.chapter_id,
          subject_id: filter.subject_id,
          limit: filter.limit ?? 100,
        },
      });
      return data;
    },
  });
}

/* ---------- Vidyārthi mascot (Stage 5 of child-centric roadmap) ---------- */

export interface MascotState {
  enabled: boolean;
  current_outfit: string;
  available_outfits: string[];
}

/** Per-learner mascot preferences. The mascot itself reads `enabled`
 *  and `current_outfit` from this query before rendering anything. */
export function useMascotState() {
  return useQuery({
    queryKey: ["me", "mascot"],
    queryFn: async () => {
      const { data } = await api.get<MascotState>("/me/mascot");
      return data;
    },
    // Mascot is a UI-affordance read; refetch on focus would be
    // distracting (mascot popping back in mid-quiz). Use a long
    // staleTime so a tab switch doesn't bounce it.
    staleTime: 5 * 60_000,
  });
}

/** Toggle the mascot on/off or equip a different outfit. */
export function useUpdateMascot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Pick<MascotState, "enabled" | "current_outfit">>) => {
      const { data } = await api.patch<MascotState>("/me/mascot", payload);
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(["me", "mascot"], data);
    },
  });
}

/* ---------- "Tell me more" chain (Stage 3 of child-centric roadmap) ---------- */

/** Lazy-fetch one tier of extended explanation for a question. Returns
 *  a mutation rather than a query because the click is the intent —
 *  we don't speculatively warm tiers the learner hasn't asked for.
 *  The backend caches forever per (question, tier), so a second
 *  click on the same chip is instant. */
export function useExplainTier() {
  return useMutation({
    mutationFn: async ({
      question_id,
      tier,
    }: {
      question_id: number;
      tier: ExplanationTier;
    }) => {
      const { data } = await api.post<ExtendedExplanation>(
        `/questions/${question_id}/explain/${tier}`,
      );
      return data;
    },
  });
}

/** Single-question retry. The backend grades the answer, updates the
 *  LearnerMistake row, and returns the verdict + correct answer +
 *  explanation. Does NOT create a Submission — retries are revision
 *  practice, not fresh attempts. */
export function useRetryMistake() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      question_id,
      answer_text,
    }: {
      question_id: number;
      answer_text: string | null;
    }) => {
      const { data } = await api.post<MistakeRetryResult>(
        `/me/mistakes/${question_id}/attempt`,
        { answer_text },
      );
      return data;
    },
    onSuccess: (result) => {
      // Always invalidate the list — even a wrong retry bumps
      // last_attempted_at, which re-orders the cards.
      qc.invalidateQueries({ queryKey: ["me", "mistakes"] });
      if (result.resolved) {
        // A resolved row may have just disappeared from the active
        // list; the count chip should refresh too.
        qc.invalidateQueries({ queryKey: ["me", "mistakes"] });
      }
    },
  });
}

/* ---------- AI tutor chat (premium) ---------- */

export interface ChatStatus {
  ai_chat_enabled: boolean;
}

export function useChatStatus() {
  return useQuery({
    queryKey: ["me", "chat-status"],
    queryFn: async () => {
      const { data } = await api.get<ChatStatus>("/me/chat-sessions/_/me");
      return data;
    },
  });
}

export function useMyChatSessions() {
  return useQuery({
    queryKey: ["me", "chat-sessions"],
    queryFn: async () => {
      const { data } = await api.get<ChatSessionRead[]>("/me/chat-sessions");
      return data;
    },
  });
}

export function useChatSession(id?: number) {
  return useQuery({
    queryKey: ["me", "chat-session", id],
    queryFn: async () => {
      const { data } = await api.get<ChatSessionDetailRead>(`/me/chat-sessions/${id}`);
      return data;
    },
    enabled: id !== undefined,
  });
}

export function useCreateChatSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      scope: ChatScope;
      chapter_id?: number;
      topic_id?: number;
    }) => {
      const { data } = await api.post<ChatSessionDetailRead>("/me/chat-sessions", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me", "chat-sessions"] }),
  });
}

export function useSendChatMessage(sessionId?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { content: string }) => {
      const { data } = await api.post<ChatMessageRead>(
        `/me/chat-sessions/${sessionId}/messages`,
        body,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me", "chat-session", sessionId] });
      qc.invalidateQueries({ queryKey: ["me", "chat-sessions"] });
    },
  });
}

export function useDeleteChatSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (sessionId: number) => {
      await api.delete(`/me/chat-sessions/${sessionId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me", "chat-sessions"] }),
  });
}

export function useMyInterventionNotes() {
  return useQuery({
    queryKey: ["me", "intervention-notes"],
    queryFn: async () => {
      const { data } = await api.get<InterventionNote[]>("/me/intervention-notes");
      return data;
    },
  });
}

// ---------- analytics ----------
export function useSectionPerformance(sectionId: number, assessmentId?: number) {
  return useQuery({
    queryKey: ["analytics", "section-performance", sectionId, assessmentId],
    queryFn: async () => {
      const { data } = await api.get<SectionPerformance>(
        `/analytics/sections/${sectionId}/performance`,
        { params: { assessment_id: assessmentId } },
      );
      return data;
    },
    enabled: assessmentId !== undefined,
  });
}

export function useSectionTopicAverages(params: {
  section_id?: number;
  class_level?: number;
  subject_id?: number;
}) {
  return useQuery({
    queryKey: ["analytics", "topic-averages", params],
    queryFn: async () => {
      const { data } = await api.get<SectionTopicAverages>(
        `/analytics/sections/${params.section_id}/topic-averages`,
        { params: { class_level: params.class_level, subject_id: params.subject_id } },
      );
      return data;
    },
    enabled:
      params.section_id !== undefined &&
      params.class_level !== undefined &&
      params.subject_id !== undefined,
  });
}

export function useSectionWeakestTopics(params: {
  section_id?: number;
  class_level?: number;
  subject_id?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["analytics", "weakest-topics", params],
    queryFn: async () => {
      const { data } = await api.get<SectionWeakestTopics>(
        `/analytics/sections/${params.section_id}/weakest-topics`,
        {
          params: {
            class_level: params.class_level,
            subject_id: params.subject_id,
            limit: params.limit ?? 5,
          },
        },
      );
      return data;
    },
    enabled:
      params.section_id !== undefined &&
      params.class_level !== undefined &&
      params.subject_id !== undefined,
  });
}

/**
 * Class-wide weak topics broken down by cognitive bucket.
 * Aggregates across every section the caller can see (school admin = all
 * sections of the class in their school; teacher = sections they class-teach).
 */
export function useClassWeakTopics(params: {
  class_level?: number;
  subject_id?: number;
  limit?: number;
  min_attempts?: number;
}) {
  return useQuery({
    queryKey: ["analytics", "class-weak-topics", params],
    queryFn: async () => {
      const { data } = await api.get<ClassWeakTopics>(
        "/analytics/class-weak-topics",
        {
          params: {
            class_level: params.class_level,
            subject_id: params.subject_id,
            limit: params.limit ?? 8,
            min_attempts: params.min_attempts ?? 1,
          },
        },
      );
      return data;
    },
    enabled:
      params.class_level !== undefined && params.subject_id !== undefined,
  });
}

export interface SectionLeaderboardEntry {
  student_id: number;
  full_name: string | null;
  roll_number: string | null;
  tests_taken: number;
  average_percentage: number | null;
  average_mastery: number | null;
}

export interface SectionLeaderboard {
  section_id: number;
  subject_id: number | null;
  students: SectionLeaderboardEntry[];
}

export function useSectionLeaderboard(params: {
  section_id?: number;
  subject_id?: number;
}) {
  return useQuery({
    queryKey: ["analytics", "section-leaderboard", params],
    queryFn: async () => {
      const { data } = await api.get<SectionLeaderboard>(
        `/analytics/sections/${params.section_id}/leaderboard`,
        { params: { subject_id: params.subject_id } },
      );
      return data;
    },
    enabled: params.section_id !== undefined,
  });
}

export function useStudentMastery(params: {
  student_id?: number;
  class_level?: number;
  subject_id?: number;
}) {
  return useQuery({
    queryKey: ["analytics", "student-mastery", params],
    queryFn: async () => {
      const { data } = await api.get<StudentMasteryGrid>(
        `/analytics/students/${params.student_id}/mastery`,
        { params: { class_level: params.class_level, subject_id: params.subject_id } },
      );
      return data;
    },
    enabled:
      params.student_id !== undefined &&
      params.class_level !== undefined &&
      params.subject_id !== undefined,
  });
}

export function useStudentTrend(params: { student_id?: number; subject_id?: number }) {
  return useQuery({
    queryKey: ["analytics", "student-trend", params],
    queryFn: async () => {
      const { data } = await api.get<StudentTrend>(
        `/analytics/students/${params.student_id}/trend`,
        { params: { subject_id: params.subject_id } },
      );
      return data;
    },
    enabled: params.student_id !== undefined && params.subject_id !== undefined,
  });
}

export function useStudentInterventionNotes(studentId?: number) {
  return useQuery({
    queryKey: ["intervention-notes", "student", studentId],
    queryFn: async () => {
      const { data } = await api.get<InterventionNote[]>(
        `/intervention-notes/students/${studentId}`,
      );
      return data;
    },
    enabled: studentId !== undefined,
  });
}

// ---------- questions ----------
export function useQuestions(filters: {
  class_level?: number;
  subject_id?: number;
  chapter_id?: number;
  outcome_code?: string;
  /** Coarse filter: "objective" = MCQ / True-False / Fill-blank; "subjective" = Short / Long answer / Case-based. */
  kind?: "objective" | "subjective";
  /** Exact QuestionType — overrides `kind` when both are present. */
  type?: QuestionType;
  difficulty?: QuestionDifficulty;
  cognitive_level?: BloomLevel;
  status?: QuestionStatus;
  source_generated_content_id?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["questions", filters],
    queryFn: async () => {
      const { data } = await api.get<Question[]>("/questions", { params: filters });
      return data;
    },
  });
}

// ---------- generated content ----------
export function useGeneratedContentList(filters: {
  content_type?: GeneratedContentType;
  status?: GeneratedContentStatus;
  chapter_id?: number;
  subject_id?: number;
  class_level?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["generated-content", filters],
    queryFn: async () => {
      const { data } = await api.get<GeneratedContent[]>("/generated-content", {
        params: filters,
      });
      return data;
    },
  });
}

export function useGeneratedContent(id?: number) {
  return useQuery({
    queryKey: ["generated-content", id],
    queryFn: async () => {
      const { data } = await api.get<GeneratedContent>(`/generated-content/${id}`);
      return data;
    },
    enabled: id !== undefined,
    refetchInterval: (q) => {
      const status = (q.state.data as GeneratedContent | undefined)?.status;
      return status === "pending" ? 2000 : false;
    },
  });
}

export function useCreateGeneration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      content_type: GeneratedContentType;
      academic_year?: string;
      class_level: number;
      subject_id: number;
      chapter_id?: number | null;
      topic_id?: number | null;
      title?: string | null;
      prompt?: string | null;
      options?: Record<string, unknown>;
      force_regenerate?: boolean;
    }) => {
      const { data } = await api.post<GeneratedContent>("/generated-content", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["generated-content"] }),
  });
}

/**
 * Platform-admin manual upload of structured (JSON-backed) content. Used
 * by the Generate page's "Upload structured content" tab to ingest a
 * pre-built chapter summary / lesson plan / worksheet / etc. without
 * going through the LLM pipeline.
 *
 * The backend validates `output_json` against the matching Pydantic
 * schema for `content_type` and rejects with HTTP 400 + structured
 * error details if the shape doesn't match. Sets status to APPROVED
 * immediately on success.
 */
export function useUploadStructuredContent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      content_type: GeneratedContentType;
      class_level: number;
      subject_id: number;
      chapter_id?: number | null;
      topic_id?: number | null;
      title: string;
      output_json: Record<string, unknown>;
    }) => {
      const { data } = await api.post<GeneratedContent>(
        "/generated-content/upload-structured",
        input,
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["generated-content"] }),
  });
}

/**
 * Platform-admin-only multipart upload of a hand-crafted HTML simulation.
 *
 * Backend route: POST /generated-content/upload-simulation. The server
 * wraps the uploaded HTML inside a SimulationOutput with the custom_html
 * template, validates against the same Pydantic schema the LLM pipeline
 * uses, renders through render_simulation_html (sandboxed iframe), and
 * persists a SIMULATION GeneratedContent row with status=APPROVED.
 */
export function useUploadSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      title: string;
      class_level: number;
      subject_id: number;
      chapter_id?: number | null;
      topic_id?: number | null;
      instructions?: string | null;
      /** Comma-separated outcome codes (optional). */
      outcome_codes?: string | null;
      file: File;
    }) => {
      const form = new FormData();
      form.append("title", input.title);
      form.append("class_level", String(input.class_level));
      form.append("subject_id", String(input.subject_id));
      if (input.chapter_id != null) form.append("chapter_id", String(input.chapter_id));
      if (input.topic_id != null) form.append("topic_id", String(input.topic_id));
      if (input.instructions) form.append("instructions", input.instructions);
      if (input.outcome_codes) form.append("outcome_codes", input.outcome_codes);
      form.append("file", input.file);
      const { data } = await api.post<GeneratedContent>(
        "/generated-content/upload-simulation",
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["generated-content"] }),
  });
}

/** Platform-admin-only multipart upload of supplementary documents (PDF/DOCX). */
export function useUploadExtraContent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      title: string;
      class_level: number;
      subject_id: number;
      chapter_id?: number | null;
      description?: string | null;
      file: File;
    }) => {
      const form = new FormData();
      form.append("title", input.title);
      form.append("class_level", String(input.class_level));
      form.append("subject_id", String(input.subject_id));
      if (input.chapter_id != null) {
        form.append("chapter_id", String(input.chapter_id));
      }
      if (input.description) form.append("description", input.description);
      form.append("file", input.file);
      const { data } = await api.post<GeneratedContent>(
        "/generated-content/upload",
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["generated-content"] }),
  });
}

// ---------- assessments + submissions ----------
export function useAssessment(id?: number) {
  return useQuery({
    queryKey: ["assessment", id],
    queryFn: async () => {
      const { data } = await api.get<Assessment>(`/assessments/${id}`);
      return data;
    },
    enabled: id !== undefined,
  });
}

export function useQuestionsByIds(ids: number[]) {
  return useQuery({
    queryKey: ["questions", "by-ids", ids.slice().sort((a, b) => a - b).join(",")],
    queryFn: async () => {
      const results = await Promise.all(
        ids.map((id) => api.get<Question>(`/questions/${id}`).then((r) => r.data)),
      );
      return results;
    },
    enabled: ids.length > 0,
  });
}

export function useSubmission(id?: number) {
  return useQuery({
    queryKey: ["submission", id],
    queryFn: async () => {
      const { data } = await api.get<Submission>(`/submissions/${id}`);
      return data;
    },
    enabled: id !== undefined,
  });
}

export function useAssessmentSubmissions(id?: number) {
  return useQuery({
    queryKey: ["assessment-submissions", id],
    queryFn: async () => {
      const { data } = await api.get<Submission[]>(`/assessments/${id}/submissions`);
      return data;
    },
    enabled: id !== undefined,
  });
}

export function useQuickQuiz() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      chapter_id?: number;
      chapter_ids?: number[];
      topic_id?: number | null;
      question_count: number;
      difficulty_mix?: Record<string, number>;
      type_mix?: Record<string, number>;
      cognitive_mix?: Record<string, number>;
      kind?: "mixed" | "subjective" | "objective";
      title?: string;
      /** Optional minute budget. null / omitted = untimed; an integer
       *  enables the countdown banner + auto-submit on the take page. */
      duration_minutes?: number | null;
    }) => {
      const { data } = await api.post<Assessment>("/me/quick-quiz", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me", "assessments"] }),
  });
}

export function useSubmitAssessment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      assessment_id: number;
      answers: Record<string, string>;
    }) => {
      const { data } = await api.post<Submission>(
        `/assessments/${body.assessment_id}/submissions`,
        { answers: body.answers },
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me", "assessments"] }),
  });
}


export function useCreateAssessmentFromBank() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      section_id: number;
      subject_id: number;
      chapter_id: number;
      topic_id?: number | null;
      type?: "QUIZ" | "WORKSHEET" | "UNIT_TEST" | "EXAM";
      title: string;
      instructions?: string | null;
      duration_minutes?: number | null;
      due_at?: string | null;
      question_count: number;
      difficulty_mix?: Record<string, number>;
      type_mix?: Record<string, number>;
      cognitive_mix?: Record<string, number>;
    }) => {
      const { data } = await api.post<Assessment>("/assessments/from-bank", body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me", "assessments"] });
    },
  });
}

/**
 * Publish a DRAFT assessment to its section so students can see + take it.
 *
 * Backend route: POST /assessments/{id}/publish (assessments.py:181).
 * 400 if the assessment is already PUBLISHED or CLOSED — the state machine
 * is one-way DRAFT → PUBLISHED → CLOSED. Surface the server message verbatim
 * via humanError() so the teacher sees "Assessment is PUBLISHED, not DRAFT"
 * rather than a generic toast.
 */
export function usePublishAssessment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (assessmentId: number) => {
      const { data } = await api.post<Assessment>(
        `/assessments/${assessmentId}/publish`,
      );
      return data;
    },
    onSuccess: (assessment) => {
      // Refresh the detail view + the teacher's assessments list + any list
      // a learner might be viewing (their own /me/assessments query).
      qc.invalidateQueries({ queryKey: ["assessment", assessment.id] });
      qc.invalidateQueries({ queryKey: ["me", "assessments"] });
    },
  });
}

/**
 * Close a PUBLISHED assessment so no further submissions land. The detail
 * view stays open so teachers can still grade and review existing
 * submissions.
 *
 * Backend route: POST /assessments/{id}/close (assessments.py:193).
 */
export function useCloseAssessment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (assessmentId: number) => {
      const { data } = await api.post<Assessment>(
        `/assessments/${assessmentId}/close`,
      );
      return data;
    },
    onSuccess: (assessment) => {
      qc.invalidateQueries({ queryKey: ["assessment", assessment.id] });
      qc.invalidateQueries({ queryKey: ["me", "assessments"] });
    },
  });
}


export function useCreateInterventionNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      student_id: number;
      note: string;
      chapter_id?: number | null;
      topic_id?: number | null;
    }) => {
      const { data } = await api.post<InterventionNote>("/intervention-notes", body);
      return data;
    },
    onSuccess: (_n, vars) => {
      qc.invalidateQueries({ queryKey: ["intervention-notes", "student", vars.student_id] });
      qc.invalidateQueries({ queryKey: ["me", "intervention-notes"] });
    },
  });
}

// ---------- platform-admin tenant management ----------

/** Every non-personal school onboarded to the platform. */
export function usePlatformSchools(enabled = true) {
  return useQuery({
    queryKey: ["platform", "schools"],
    queryFn: async () => {
      const { data } = await api.get<PlatformSchoolSummary[]>("/platform/schools");
      return data;
    },
    enabled,
  });
}

/** Detailed view of one school — sections, teachers, students all in one. */
export function usePlatformSchoolOverview(schoolId: number | undefined) {
  return useQuery({
    queryKey: ["platform", "school", schoolId],
    queryFn: async () => {
      const { data } = await api.get<PlatformSchoolOverview>(
        `/platform/schools/${schoolId}`,
      );
      return data;
    },
    enabled: schoolId !== undefined,
  });
}

/** Toggle a school's `is_active`. Cascades to every user in the school via auth. */
export function useTogglePlatformSchool() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { schoolId: number; isActive: boolean }) => {
      const { data } = await api.post<PlatformSchoolSummary>(
        `/platform/schools/${input.schoolId}/activation`,
        { is_active: input.isActive },
      );
      return data;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["platform", "schools"] });
      qc.invalidateQueries({ queryKey: ["platform", "school", vars.schoolId] });
    },
  });
}

/** Every individual_learner user on the platform. */
export function usePlatformLearners(enabled = true) {
  return useQuery({
    queryKey: ["platform", "learners"],
    queryFn: async () => {
      const { data } = await api.get<PlatformLearnerSummary[]>("/platform/learners");
      return data;
    },
    enabled,
  });
}

/** Profile + recent activity for one individual learner. */
export function usePlatformLearnerOverview(userId: number | undefined) {
  return useQuery({
    queryKey: ["platform", "learner", userId],
    queryFn: async () => {
      const { data } = await api.get<PlatformLearnerOverview>(
        `/platform/learners/${userId}`,
      );
      return data;
    },
    enabled: userId !== undefined,
  });
}

/** Toggle one learner's `is_active`. Their auth dep already checks the flag. */
export function useTogglePlatformLearner() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { userId: number; isActive: boolean }) => {
      const { data } = await api.post<PlatformLearnerSummary>(
        `/platform/learners/${input.userId}/activation`,
        { is_active: input.isActive },
      );
      return data;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["platform", "learners"] });
      qc.invalidateQueries({ queryKey: ["platform", "learner", vars.userId] });
    },
  });
}
