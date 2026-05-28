import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth";
import { Shell } from "@/components/layout/Shell";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { RequireRole } from "@/components/layout/RequireRole";
import { LoginPage } from "@/pages/Login";
import { SignupSchoolPage } from "@/pages/SignupSchool";
import { SignupIndividualPage } from "@/pages/SignupIndividual";
import { SignupParentPage } from "@/pages/SignupParent";
import { ManageSchoolPage } from "@/pages/ManageSchool";
import { DashboardPage } from "@/pages/Dashboard";
import { TakeAssessmentPage } from "@/pages/TakeAssessment";
import { QuickQuizPage } from "@/pages/QuickQuiz";
import { StampBookPage } from "@/pages/StampBook";
import { MyMistakesPage } from "@/pages/MyMistakes";
import { PracticePage } from "@/pages/Practice";
import { FlashcardsPage } from "@/pages/Flashcards";
import { SectionsPage } from "@/pages/Sections";
import { SectionDetailPage } from "@/pages/SectionDetail";
import { StudentDetailPage } from "@/pages/StudentDetail";
import { AssessmentsPage } from "@/pages/Assessments";
import { AssessmentDetailPage } from "@/pages/AssessmentDetail";
import { NewQuizPage } from "@/pages/NewQuiz";
import { QuestionBankPage } from "@/pages/QuestionBank";
import { ContentLibraryPage } from "@/pages/ContentLibrary";
import { ContentDetailPage } from "@/pages/ContentDetail";
import { GeneratePage } from "@/pages/Generate";
import { CurriculumPage } from "@/pages/Curriculum";
import { LearnPage } from "@/pages/Learn";
import { LearnSubjectPage } from "@/pages/LearnSubject";
import { LearnChapterPage } from "@/pages/LearnChapter";
import { ReportCardPage } from "@/pages/ReportCard";
import { SchoolReportPage } from "@/pages/SchoolReport";
import { ChatPage } from "@/pages/Chat";
import { AiChatAdminPage } from "@/pages/AiChatAdmin";
import { TenantsPage } from "@/pages/Tenants";
import { TenantSchoolDetailPage } from "@/pages/TenantSchoolDetail";
import { TenantLearnerDetailPage } from "@/pages/TenantLearnerDetail";
import { ContentBundleUploadPage } from "@/pages/ContentBundleUpload";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, err) => {
        if ((err as { response?: { status?: number } })?.response?.status === 401) return false;
        return count < 1;
      },
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup-school" element={<SignupSchoolPage />} />
            <Route path="/signup-individual" element={<SignupIndividualPage />} />
            <Route path="/signup-parent" element={<SignupParentPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Shell />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="sections" element={<SectionsPage />} />
              <Route path="sections/:sectionId" element={<SectionDetailPage />} />
              <Route path="students/:studentId" element={<StudentDetailPage />} />
              <Route path="assessments" element={<AssessmentsPage />} />
              <Route
                path="assessments/new"
                element={
                  <RequireRole allowed={["school_admin", "teacher"]}>
                    <NewQuizPage />
                  </RequireRole>
                }
              />
              <Route path="assessments/:assessmentId" element={<AssessmentDetailPage />} />
              <Route
                path="assessments/:assessmentId/take"
                element={
                  <RequireRole allowed={["student", "individual_learner", "teacher", "school_admin"]}>
                    <TakeAssessmentPage />
                  </RequireRole>
                }
              />
              <Route
                path="quick-quiz"
                element={
                  <RequireRole allowed={["individual_learner", "student"]}>
                    <QuickQuizPage />
                  </RequireRole>
                }
              />
              <Route
                path="me/stamps"
                element={
                  <RequireRole allowed={["individual_learner", "student"]}>
                    <StampBookPage />
                  </RequireRole>
                }
              />
              <Route
                path="me/mistakes"
                element={
                  <RequireRole allowed={["individual_learner", "student"]}>
                    <MyMistakesPage />
                  </RequireRole>
                }
              />
              <Route
                path="practice"
                element={
                  <RequireRole allowed={["individual_learner", "student"]}>
                    <PracticePage />
                  </RequireRole>
                }
              />
              <Route
                path="practice/flashcards"
                element={
                  <RequireRole allowed={["individual_learner", "student"]}>
                    <FlashcardsPage />
                  </RequireRole>
                }
              />
              <Route
                path="question-bank"
                element={
                  <RequireRole allowed={["platform_admin"]}>
                    <QuestionBankPage />
                  </RequireRole>
                }
              />
              <Route
                path="content"
                element={
                  <RequireRole allowed={["platform_admin", "school_admin", "teacher"]}>
                    <ContentLibraryPage />
                  </RequireRole>
                }
              />
              <Route
                path="content/:contentId"
                element={
                  <RequireRole allowed={["platform_admin", "school_admin", "teacher"]}>
                    <ContentDetailPage />
                  </RequireRole>
                }
              />
              <Route
                path="generate"
                element={
                  <RequireRole allowed={["platform_admin"]}>
                    <GeneratePage />
                  </RequireRole>
                }
              />
              <Route path="curriculum" element={<CurriculumPage />} />
              <Route
                path="learn"
                element={
                  <RequireRole allowed={["platform_admin", "student", "individual_learner", "teacher", "school_admin"]}>
                    <LearnPage />
                  </RequireRole>
                }
              />
              <Route
                path="learn/subjects/:subjectId"
                element={
                  <RequireRole allowed={["platform_admin", "student", "individual_learner", "teacher", "school_admin"]}>
                    <LearnSubjectPage />
                  </RequireRole>
                }
              />
              <Route
                path="learn/chapters/:chapterId"
                element={
                  <RequireRole allowed={["platform_admin", "student", "individual_learner", "teacher", "school_admin"]}>
                    <LearnChapterPage />
                  </RequireRole>
                }
              />
              <Route
                path="report-card"
                element={
                  <RequireRole allowed={["student", "individual_learner"]}>
                    <ReportCardPage />
                  </RequireRole>
                }
              />
              <Route
                path="school-report"
                element={
                  <RequireRole allowed={["school_admin"]}>
                    <SchoolReportPage />
                  </RequireRole>
                }
              />
              <Route
                path="chat/:sessionId"
                element={
                  <RequireRole allowed={["student", "individual_learner"]}>
                    <ChatPage />
                  </RequireRole>
                }
              />
              <Route
                path="ai-chat-admin"
                element={
                  <RequireRole allowed={["platform_admin"]}>
                    <AiChatAdminPage />
                  </RequireRole>
                }
              />
              <Route
                path="content-bundle-upload"
                element={
                  <RequireRole allowed={["platform_admin"]}>
                    <ContentBundleUploadPage />
                  </RequireRole>
                }
              />
              <Route
                path="tenants"
                element={
                  <RequireRole allowed={["platform_admin"]}>
                    <TenantsPage />
                  </RequireRole>
                }
              />
              <Route
                path="tenants/schools/:schoolId"
                element={
                  <RequireRole allowed={["platform_admin"]}>
                    <TenantSchoolDetailPage />
                  </RequireRole>
                }
              />
              <Route
                path="tenants/learners/:userId"
                element={
                  <RequireRole allowed={["platform_admin"]}>
                    <TenantLearnerDetailPage />
                  </RequireRole>
                }
              />
              <Route
                path="manage"
                element={
                  <RequireRole allowed={["school_admin"]}>
                    <ManageSchoolPage />
                  </RequireRole>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
          <Toaster richColors position="top-right" />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
