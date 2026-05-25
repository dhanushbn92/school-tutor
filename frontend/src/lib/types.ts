// Type definitions that mirror the FastAPI Pydantic schemas.
// Keep these in sync with app/schemas/*.py on the backend.

export type UserRole =
  | "platform_admin"
  | "school_admin"
  | "teacher"
  | "student"
  | "individual_learner"
  // Stage 6 of the child-centric roadmap — guardian linked to one or
  // more learners via invite codes. Parent users have no school_id
  // (they only see children they've been explicitly linked to).
  | "parent";

export interface User {
  id: number;
  email: string;
  role: UserRole;
  school_id: number | null;
  full_name: string;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface SchoolClass {
  id: number;
  level: number;
  display_name: string;
}

export interface Subject {
  id: number;
  class_id: number;
  name: string;
  language: string;
  // Syllabus board (CBSE / NIOS / ICSE / State Board / Other). Always
  // present; new column added by migration 20260430_0022 with all
  // legacy rows backfilled to "CBSE".
  board: string;
}

export interface Book {
  id: number;
  subject_id: number;
  title: string;
  ncert_code: string;
  academic_year: string;
  source_url: string | null;
}

export interface Chapter {
  id: number;
  book_id: number;
  chapter_number: number;
  title: string;
  source_url: string | null;
  page_count: number | null;
}

export interface Topic {
  id: number;
  chapter_id: number;
  name: string;
  description: string | null;
}

export interface ChapterSection {
  id: number;
  chapter_id: number;
  section_number: string;
  title: string;
  section_text: string;
  page_start: number | null;
  page_end: number | null;
}

export interface ChapterDetail extends Chapter {
  full_text: string;
  sections: ChapterSection[];
  topics: Topic[];
  // Denormalised subject info — the chapter detail endpoint joins
  // `chapter → book → subject` and surfaces these so the Learn page can
  // theme the hero panel without a follow-up subject lookup.
  subject_id?: number | null;
  subject_name?: string | null;
}

export interface LearningOutcome {
  code: string;
  description: string;
  bloom_level: string;
  topic_id: number | null;
}

export interface CurriculumContext {
  academic_year: string;
  class_level: number;
  subject: string;
  book: string;
  chapter_id: number;
  chapter_number: number;
  chapter_title: string;
  chapter_text: string;
  context_text: string;
  topic: string | null;
  topics: string[];
  outcomes: LearningOutcome[];
  source_url: string | null;
}

export interface Section {
  id: number;
  school_id: number;
  class_id: number;
  academic_year_id: number;
  name: string;
  class_teacher_id: number | null;
  class_level: number | null;
  class_display_name: string | null;
  academic_year: string | null;
}

export interface TeacherSubjects {
  teacher_id: number;
  subject_ids: number[];
  /**
   * False when no explicit assignments exist for this teacher and the
   * service is falling back to "all subjects of class-teacher classes".
   * The UI surfaces this so a school admin understands their teachers
   * are unscoped until they opt in.
   */
  is_explicit: boolean;
}

export interface BucketStats {
  average_mastery: number | null;
  students_attempted: number;
}

export interface WeakTopicEntry {
  topic_id: number;
  topic_name: string;
  chapter_id: number;
  chapter_number: number;
  chapter_title: string;
  /** Mean mastery across all attempted (student, bucket) pairs. */
  average_mastery: number | null;
  /** Distinct students who attempted ANY bucket of this topic. */
  students_attempted: number;
  /** Per-bucket breakdown — null `average_mastery` means no attempts. */
  buckets: Record<CognitiveBucket, BucketStats>;
}

export interface ClassWeakTopics {
  class_level: number;
  subject_id: number;
  students_total: number;
  topics: WeakTopicEntry[];
}

// ---- Platform-admin tenant management ----

export interface PlatformSchoolSummary {
  id: number;
  name: string;
  board: string;
  brand_name: string | null;
  is_active: boolean;
  student_count: number;
  teacher_count: number;
  section_count: number;
  created_at: string;
}

export interface PlatformSectionSummary {
  id: number;
  name: string;
  class_level: number | null;
  class_display_name: string | null;
  academic_year: string | null;
  class_teacher_name: string | null;
  student_count: number;
}

export interface PlatformTeacherSummary {
  id: number;
  full_name: string;
  email: string;
  qualification: string | null;
  sections_count: number;
  is_active: boolean;
}

export interface PlatformStudentSummary {
  id: number;
  full_name: string;
  roll_number: string | null;
  section_name: string | null;
  class_level: number | null;
  has_login: boolean;
  is_active: boolean;
}

export interface PlatformSchoolOverview {
  id: number;
  name: string;
  board: string;
  address: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  brand_name: string | null;
  is_active: boolean;
  is_personal: boolean;
  created_at: string;
  student_count: number;
  teacher_count: number;
  section_count: number;
  sections: PlatformSectionSummary[];
  teachers: PlatformTeacherSummary[];
  students: PlatformStudentSummary[];
}

export interface PlatformLearnerSummary {
  user_id: number;
  full_name: string;
  email: string;
  is_active: boolean;
  class_level: number | null;
  signup_date: string;
  submissions_count: number;
  average_percentage: number | null;
}

export interface PlatformLearnerSubmission {
  submission_id: number;
  assessment_id: number;
  assessment_title: string;
  chapter_id: number | null;
  chapter_title: string | null;
  score: number | null;
  max_marks: number | null;
  percentage: number | null;
  submitted_at: string | null;
  evaluated_at: string | null;
  status: string;
}

export interface PlatformLearnerOverview {
  user_id: number;
  full_name: string;
  email: string;
  is_active: boolean;
  signup_date: string;
  last_login_at: string | null;
  class_level: number | null;
  class_display_name: string | null;
  school_id: number;
  submissions_count: number;
  average_percentage: number | null;
  last_activity_at: string | null;
  average_mastery: number | null;
  recent_submissions: PlatformLearnerSubmission[];
}

export interface Student {
  id: number;
  school_id: number;
  user_id: number | null;
  full_name: string;
  roll_number: string | null;
  dob: string | null;
  gender: string | null;
  guardian_name: string | null;
  guardian_phone: string | null;
}

export type ChatScope = "CHAPTER" | "TOPIC";
export type ChatRole = "USER" | "ASSISTANT";

export interface ChatSessionRead {
  id: number;
  student_id: number;
  scope: ChatScope;
  chapter_id: number | null;
  topic_id: number | null;
  title: string;
  message_count: number;
  last_message_at: string | null;
  created_at: string;
}

export interface ChatMessageRead {
  id: number;
  role: ChatRole;
  content: string;
  created_at: string;
}

export interface ChatSessionDetailRead extends ChatSessionRead {
  messages: ChatMessageRead[];
}

export type GeneratedContentType =
  | "worksheet"
  | "quiz"
  | "half_yearly_exam"
  | "ppt"
  | "diagram"
  | "simulation"
  | "lesson_plan"
  | "chapter_summary"
  | "classroom_activity"
  | "resource_list"
  | "extra_content"
  | "flow_diagram";

export interface ChapterSummaryDiagramBranch {
  label: string;
  details: string[];
}

export interface ChapterSummaryDiagram {
  title: string;
  central_term: string;
  branches: ChapterSummaryDiagramBranch[];
}

export interface ChapterSummarySection {
  heading: string;
  bullets: string[];
  diagram: ChapterSummaryDiagram | null;
}

export interface ChapterSummaryGlossaryTerm {
  term: string;
  definition: string;
}

export interface ChapterSummaryOutput {
  title: string;
  intro: string;
  overview_diagram: ChapterSummaryDiagram;
  sections: ChapterSummarySection[];
  key_takeaways: string[];
  glossary: ChapterSummaryGlossaryTerm[];
}

export interface LessonPlanActivity {
  phase: string;
  duration_minutes: number;
  description: string;
  teacher_actions: string[];
  student_actions?: string[];
}

export interface LessonPlanOutput {
  title: string;
  class_level: number;
  subject: string;
  chapter_title: string;
  duration_minutes: number;
  objectives: string[];
  prerequisites?: string[];
  materials?: string[];
  key_vocabulary?: string[];
  activities: LessonPlanActivity[];
  homework?: string[];
  assessment_ideas?: string[];
  references?: string[];
  outcome_codes_covered?: string[];
}

export interface ActivityStep {
  title: string;
  detail: string;
}

export interface ClassroomActivity {
  title: string;
  duration_minutes: number;
  objective: string;
  materials?: string[];
  steps: ActivityStep[];
  guiding_questions?: string[];
  safety_notes?: string[];
  variations?: string[];
}

export interface ClassroomActivitySetOutput {
  title: string;
  chapter_focus: string;
  activities: ClassroomActivity[];
}

// Worksheet schema mirrors `app/llm/schemas/worksheet.py`. The PDF rendered
// from this JSON used to be the canonical surface, but worksheets now render
// inline via <WorksheetView> — the PDF is no longer surfaced for download.
export type WorksheetQuestionType =
  | "MCQ"
  | "SHORT_ANSWER"
  | "LONG_ANSWER"
  | "FILL_BLANK"
  | "TRUE_FALSE"
  | "CASE_BASED";

export type WorksheetDifficulty = "EASY" | "MEDIUM" | "HARD";

export type WorksheetCognitiveLevel =
  | "REMEMBER"
  | "UNDERSTAND"
  | "APPLY"
  | "ANALYZE"
  | "EVALUATE"
  | "CREATE";

export interface WorksheetQuestion {
  type: WorksheetQuestionType;
  question: string;
  options?: string[] | null;
  answer: string;
  explanation?: string | null;
  marks: number;
  difficulty: WorksheetDifficulty;
  cognitive_level: WorksheetCognitiveLevel;
  outcome_code?: string | null;
}

export interface WorksheetOutput {
  title: string;
  instructions: string;
  total_marks: number;
  questions: WorksheetQuestion[];
}

// PPT outline schema mirrors `app/llm/schemas/ppt.py`. The PPTX file rendered
// from this JSON used to be the canonical surface, but PPT decks now render
// inline via <PPTOutlineView> — the PPTX is no longer surfaced for download.
// Speaker notes are intended for the teacher only; the PPT tab itself is
// gated to teacher / school_admin roles upstream.
export type SlideType =
  | "TITLE"
  | "OBJECTIVES"
  | "CONCEPT"
  | "EXAMPLE"
  | "ACTIVITY"
  | "QUICK_CHECK"
  | "SUMMARY";

export interface Slide {
  slide_type: SlideType;
  title: string;
  bullets: string[];
  speaker_notes?: string | null;
}

export interface PPTOutlineOutput {
  title: string;
  class_level: number;
  subject: string;
  chapter_title: string;
  slides: Slide[];
  outcome_codes_covered?: string[];
}

export interface ResourceItem {
  title: string;
  url: string;
  kind: string;
  summary: string;
  estimated_time_minutes?: number | null;
  note_for_teacher?: string | null;
}

export interface ResourceListOutput {
  chapter_focus: string;
  intro: string;
  items: ResourceItem[];
}

export type GeneratedContentStatus = "pending" | "ready" | "approved" | "failed";

export interface GeneratedContent {
  id: number;
  content_type: GeneratedContentType;
  status: GeneratedContentStatus;
  cache_key: string;
  academic_year: string;
  class_level: number;
  subject_id: number | null;
  chapter_id: number | null;
  topic_id: number | null;
  title: string;
  prompt: string | null;
  output_text: string | null;
  output_json: Record<string, unknown> | null;
  artifact_url: string | null;
  request_options: Record<string, unknown> | null;
  error_message: string | null;
  llm_provider: string | null;
  llm_model: string | null;
  created_by_id: number | null;
}

export type QuestionType =
  | "MCQ"
  | "SHORT_ANSWER"
  | "LONG_ANSWER"
  | "FILL_BLANK"
  | "TRUE_FALSE"
  | "CASE_BASED";
export type QuestionDifficulty = "EASY" | "MEDIUM" | "HARD";
export type QuestionStatus = "DRAFT" | "APPROVED" | "REJECTED" | "RETIRED";

// 6-level Bloom (canonical, stored on every Question).
export type BloomLevel =
  | "remember"
  | "understand"
  | "apply"
  | "analyze"
  | "evaluate"
  | "create";

// 3-level rollup shown by default in student/teacher UI.
export type CognitiveBucket = "FACTUAL" | "UNDERSTANDING" | "APPLICATION";

export const BLOOM_TO_BUCKET: Record<BloomLevel, CognitiveBucket> = {
  remember: "FACTUAL",
  understand: "UNDERSTANDING",
  apply: "APPLICATION",
  analyze: "APPLICATION",
  evaluate: "APPLICATION",
  create: "APPLICATION",
};

export const BUCKET_LABEL: Record<CognitiveBucket, string> = {
  FACTUAL: "Factual",
  UNDERSTANDING: "Understanding",
  APPLICATION: "Application",
};

export const BLOOM_LABEL: Record<BloomLevel, string> = {
  remember: "Remember",
  understand: "Understand",
  apply: "Apply",
  analyze: "Analyze",
  evaluate: "Evaluate",
  create: "Create",
};

export interface RichExplanationBlock {
  type: "text" | "list" | "mind_map" | "flow_diagram" | "image_caption";
  content?: string;
  title?: string;
  items?: string[];
  data?: unknown;
  caption?: string;
}

export interface RichExplanation {
  blocks: RichExplanationBlock[];
}

export interface Question {
  id: number;
  chapter_id: number;
  topic_id: number | null;
  outcome_id: number | null;
  outcome_code: string | null;
  type: QuestionType;
  difficulty: QuestionDifficulty;
  cognitive_level: BloomLevel;
  status: QuestionStatus;
  text: string;
  options: { choices?: string[] } | null;
  correct_answer: string;
  explanation: string | null;
  explanation_rich: RichExplanation | null;
  marks: number;
  source_generated_content_id: number | null;
  created_by_id: number;
  reviewed_by_id: number | null;
  review_notes: string | null;
  created_at: string;
  updated_at: string;
}

export type AssessmentType = "WORKSHEET" | "QUIZ" | "UNIT_TEST" | "EXAM";
export type AssessmentStatus = "DRAFT" | "PUBLISHED" | "CLOSED";
export type SubmissionStatus = "DRAFT" | "SUBMITTED" | "EVALUATED" | "LATE";

export interface AssessmentQuestion {
  id: number;
  question_id: number;
  order: number;
  marks_override: number | null;
  marks: number;
  question_text: string | null;
  question_type: string | null;
}

export interface Assessment {
  id: number;
  section_id: number;
  subject_id: number;
  chapter_id: number | null;
  type: AssessmentType;
  status: AssessmentStatus;
  title: string;
  instructions: string | null;
  total_marks: number;
  duration_minutes: number | null;
  due_at: string | null;
  published_at: string | null;
  created_by_id: number;
  created_at: string;
  questions: AssessmentQuestion[];
}

export interface GradingDetailsMatched {
  label: string;
  matched_phrase: string;
  marks: number;
}

export interface GradingDetailsMissed {
  label: string;
  any_of: string[];
  marks: number;
}

export interface GradingDetails {
  method: string;
  min_words_ok?: boolean;
  word_count?: number;
  min_words?: number;
  matched?: GradingDetailsMatched[];
  missed?: GradingDetailsMissed[];
  raw_score?: number;
  rubric_total?: number;
  scaled_marks?: number;
  note?: string;
}

export interface SubmissionAnswer {
  id: number;
  question_id: number;
  answer_text: string | null;
  marks_awarded: number | null;
  max_marks: number;
  auto_graded: boolean;
  grading_details: GradingDetails | null;
  teacher_remark: string | null;
}

export interface Submission {
  id: number;
  assessment_id: number;
  student_id: number;
  status: SubmissionStatus;
  submitted_at: string | null;
  evaluated_at: string | null;
  total_awarded: number | null;
  max_marks: number;
  uploaded_file_url: string | null;
  answers: SubmissionAnswer[];
}

export interface MasteryBucketStats {
  mastery: number;
  attempts: number;
  correct: number;
  last_attempt_at: string | null;
}

export interface MasteryOutcome {
  outcome_id: number;
  code: string;
  description: string;
  bloom_level: string;
  mastery: number | null;
  attempts: number;
  correct: number;
  last_attempt_at: string | null;
  buckets?: Record<CognitiveBucket, MasteryBucketStats | null>;
}

export interface MasteryChapter {
  chapter_id: number;
  chapter_number: number;
  chapter_title: string;
  outcomes: MasteryOutcome[];
}

export interface StudentMasteryGrid {
  student_id: number;
  class_level: number;
  subject_id: number;
  subject: string | null;
  chapters: MasteryChapter[];
  summary: {
    outcomes_total: number;
    outcomes_attempted: number;
    average_mastery: number | null;
    by_bucket?: Record<
      CognitiveBucket,
      { outcomes_attempted: number; average_mastery: number | null }
    >;
  };
}

export interface SectionTopicAveragesOutcome {
  outcome_id: number;
  code: string;
  description: string;
  bloom_level: string;
  average_mastery: number | null;
  students_attempted: number;
}

export interface SectionTopicAveragesChapter {
  chapter_id: number;
  chapter_number: number;
  chapter_title: string;
  outcomes: SectionTopicAveragesOutcome[];
}

export interface SectionTopicAverages {
  section_id: number;
  class_level: number;
  subject_id: number;
  students_total: number;
  chapters: SectionTopicAveragesChapter[];
}

export interface SectionWeakestTopic extends SectionTopicAveragesOutcome {
  chapter_id: number;
  chapter_number: number;
  chapter_title: string;
}

export interface SectionWeakestTopics {
  section_id: number;
  class_level: number;
  subject_id: number;
  weakest: SectionWeakestTopic[];
}

export interface StudentTrendPoint {
  assessment_id: number;
  assessment_title: string;
  assessment_type: string;
  chapter_id: number | null;
  date: string | null;
  score: number;
  max_marks: number;
  percentage: number;
}

export interface StudentTrend {
  student_id: number;
  subject_id: number;
  series: StudentTrendPoint[];
  summary: {
    tests_evaluated: number;
    average_percentage: number | null;
  };
}

export interface SectionPerformanceStudent {
  student_id: number;
  full_name: string | null;
  roll_number: string | null;
  status: string;
  total_awarded: number | null;
  max_marks: number;
  submitted_at: string | null;
  evaluated_at: string | null;
}

export interface SectionPerformance {
  section_id: number;
  assessment_id: number;
  assessment_title: string;
  assessment_type: string;
  assessment_status: string;
  total_marks: number;
  summary: {
    enrolled: number;
    submitted: number;
    evaluated: number;
    average: number | null;
    median: number | null;
    high: number | null;
    low: number | null;
  };
  students: SectionPerformanceStudent[];
}

export interface InterventionNote {
  id: number;
  student_id: number;
  teacher_id: number;
  chapter_id: number | null;
  topic_id: number | null;
  note: string;
  created_at: string;
}

// ---------- Practice rhythm (Stage 1 of child-centric roadmap) ----------

/** Stamp kinds the backend can award. UI does an exhaustive switch on
 *  these; any unknown kind falls through to a generic rendering so
 *  adding a new kind on the backend can never crash the stamp book. */
export type StampKind =
  | "QUIZ_COMPLETED"
  | "PERFECT_SCORE"
  | "PRACTICE_DAY"
  | "WEEKLY_GOAL_MET";

export interface LearnerStamp {
  id: number;
  kind: StampKind | string;
  /** ISO timestamp string. */
  earned_at: string;
  /** Per-kind context blob. Shape depends on `kind`:
   *   QUIZ_COMPLETED   { assessment_id, submission_id, total_awarded, max_marks }
   *   PERFECT_SCORE    { assessment_id, submission_id, marks }
   *   PRACTICE_DAY     { date: 'YYYY-MM-DD' }
   *   WEEKLY_GOAL_MET  { week_start, target_days, days_achieved }
   *  Callers should defensively narrow before destructuring. */
  metadata: Record<string, unknown>;
}

export interface PracticeSummary {
  /** Monday of the current ISO week, ISO date string. */
  week_start: string;
  /** Sunday of the current ISO week, ISO date string (inclusive). */
  week_end: string;
  /** Learner's target practice days for this week (1..7). */
  target_days: number;
  /** Distinct days the learner submitted at least one quiz this week. */
  practice_days_this_week: string[];
  practice_days_count_this_week: number;
  /** All-time count of distinct practice days. */
  practice_days_count_total: number;
  weekly_goal_met: boolean;
  recent_stamps: LearnerStamp[];
  /** Stage 1.5 — login streak (consecutive days the learner has
   *  signed in, with one freebie miss per ISO week). */
  streak: StreakInfo;
  /** Stage 1.5 — total points across the ledger. */
  points_total: number;
  /** Stage 1.5 — current level + progress to the next tier. */
  level: LevelInfo;
  /** Stage 1.5 — WEEKLY_GOAL_MET aggregations: all-time count + the
   *  current consecutive-week run. */
  weekly_goal_progress: WeeklyGoalProgress;
  /** Stage 1.5 — one cell per day for the last ~12 weeks (rendered
   *  as a GitHub-style consistency heatmap). */
  heatmap: HeatmapCell[];
}

export interface StreakInfo {
  /** Days in a row ending today (or the last logged-in day). */
  current: number;
  /** All-time longest streak. */
  longest: number;
  /** Grace misses already consumed in the current ISO week. */
  grace_used_this_week: number;
  /** Grace misses permitted per ISO week (currently 1). */
  grace_allowed_per_week: number;
}

export interface LevelInfo {
  /** Sanskrit-themed level name (Shishya / Vidyārthi / Ārya / Ācārya / Mahā-Ācārya). */
  name: string;
  /** One-line vibe / what this level means. */
  blurb: string;
  /** Minimum points required to enter this tier. */
  min_points: number;
  /** Name of the next tier; null at the top tier. */
  next_name: string | null;
  /** Threshold of the next tier; null at the top tier. */
  next_min_points: number | null;
  /** Points earned within the current tier (i.e. total - min_points). */
  points_into_level: number;
  /** Points still needed to reach the next tier; null at the top. */
  points_to_next: number | null;
}

export interface WeeklyGoalProgress {
  weeks_met_total: number;
  weeks_met_run: number;
}

export interface HeatmapCell {
  /** ISO date string (YYYY-MM-DD). */
  day: string;
  practiced: boolean;
}

// ---------- "Tell me more" chain (Stage 3 of child-centric roadmap) ----------

/** The three escalating tiers of extended explanation. The backend
 *  generates these on demand via LLM and caches them forever per
 *  (question, tier). New tiers may be added freely on the backend —
 *  the frontend renders unknown tiers with a generic "More" label. */
export type ExplanationTier = "DEEPER" | "ANALOGY" | "EXAMPLE";

export interface ExtendedExplanation {
  question_id: number;
  tier: ExplanationTier | string;
  text: string;
  /** ISO timestamp the row was first generated. */
  generated_at: string;
}

// ---------- Mistake review (Stage 2 of child-centric roadmap) ----------

export interface LearnerMistakeEntry {
  question_id: number;
  question_text: string;
  question_type: QuestionType | string;
  /** MCQ choices, when question_type === "MCQ". Null otherwise. */
  options: string[] | null;
  marks: number;
  difficulty: QuestionDifficulty | string;
  outcome_code: string | null;
  chapter_id: number | null;
  chapter_title: string | null;
  chapter_number: number | null;
  subject_id: number | null;
  subject_name: string | null;
  /** ISO timestamp. */
  first_wrong_at: string;
  /** ISO timestamp. */
  last_attempted_at: string;
  /** 0 or 1 (>=2 is filtered out as resolved on the backend). */
  consecutive_corrects: number;
}

export interface LearnerMistakesPage {
  total_active: number;
  items: LearnerMistakeEntry[];
}

export interface MistakeRetryResult {
  correct: boolean;
  correct_answer: string;
  explanation: string | null;
  consecutive_corrects: number;
  /** True when consecutive_corrects has reached the resolution
   *  threshold (twice-right rule) and the row will be filtered out of
   *  the active mistake list on the next refresh. */
  resolved: boolean;
}
