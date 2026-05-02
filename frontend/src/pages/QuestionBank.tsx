import { useEffect, useState } from "react";
import { Check, Filter, Loader2, NotebookPen, Undo2, X } from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { BoardContextBar, labelForSubject } from "@/components/BoardContextBar";
import { api, humanError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useClasses, useQuestions, useSubjects } from "@/lib/queries";
import type {
  BloomLevel,
  CognitiveBucket,
  Question,
  QuestionStatus,
} from "@/lib/types";
import { BLOOM_LABEL, BLOOM_TO_BUCKET, BUCKET_LABEL } from "@/lib/types";

const STATUS_OPTIONS: { value: QuestionStatus | "ALL"; label: string }[] = [
  { value: "DRAFT", label: "Draft" },
  { value: "APPROVED", label: "Approved" },
  { value: "REJECTED", label: "Rejected" },
  { value: "RETIRED", label: "Retired" },
  { value: "ALL", label: "All" },
];

const COGNITIVE_OPTIONS: { value: BloomLevel | "ALL"; label: string }[] = [
  { value: "ALL", label: "All Bloom levels" },
  { value: "remember", label: "Remember (Factual)" },
  { value: "understand", label: "Understand (Understanding)" },
  { value: "apply", label: "Apply (Application)" },
  { value: "analyze", label: "Analyze (Application)" },
  { value: "evaluate", label: "Evaluate (Application)" },
  { value: "create", label: "Create (Application)" },
];

type Kind = "ALL" | "objective" | "subjective";
const KIND_OPTIONS: { value: Kind; label: string; hint: string }[] = [
  { value: "ALL",         label: "All kinds",   hint: "" },
  { value: "objective",   label: "Objective",   hint: "MCQ · True/False · Fill-blank" },
  { value: "subjective",  label: "Subjective",  hint: "Short · Long answer · Case-based" },
];

const ALL_VALUE = "ALL" as const;

const BUCKET_BADGE_VARIANT: Record<
  CognitiveBucket,
  "outline" | "secondary" | "warning"
> = {
  FACTUAL: "outline",
  UNDERSTANDING: "secondary",
  APPLICATION: "warning",
};

export function QuestionBankPage() {
  const { user } = useAuth();
  const isPlatformAdmin = user?.role === "platform_admin";

  // Filter state. Class -> Subject is cascading; the others are independent.
  const [classLevel, setClassLevel] = useState<number | "ALL">(ALL_VALUE);
  const [subjectId, setSubjectId] = useState<number | "ALL">(ALL_VALUE);
  const [kind, setKind] = useState<Kind>("ALL");
  const [cognitive, setCognitive] = useState<BloomLevel | "ALL">("ALL");
  const [status, setStatus] = useState<QuestionStatus | "ALL">(
    isPlatformAdmin ? "DRAFT" : "APPROVED",
  );

  const classesQ = useClasses();
  const subjectsQ = useSubjects(classLevel === ALL_VALUE ? undefined : classLevel);

  // Cascade: when class changes, the previous subject pick may no longer be
  // valid for the new class. Reset rather than show a stale chip.
  useEffect(() => {
    setSubjectId(ALL_VALUE);
  }, [classLevel]);

  const questionsQ = useQuestions({
    class_level: classLevel === ALL_VALUE ? undefined : classLevel,
    subject_id: subjectId === ALL_VALUE ? undefined : subjectId,
    kind: kind === "ALL" ? undefined : kind,
    status: status === "ALL" ? undefined : status,
    cognitive_level: cognitive === "ALL" ? undefined : cognitive,
    limit: 200,
  });

  const defaultStatus: QuestionStatus | "ALL" = isPlatformAdmin ? "DRAFT" : "APPROVED";
  const anyFilterActive =
    classLevel !== ALL_VALUE ||
    subjectId !== ALL_VALUE ||
    kind !== "ALL" ||
    cognitive !== "ALL" ||
    status !== defaultStatus;

  function clearFilters() {
    setClassLevel(ALL_VALUE);
    setSubjectId(ALL_VALUE);
    setKind("ALL");
    setCognitive("ALL");
    setStatus(defaultStatus);
  }

  return (
    <ThemedPage>
      <PageHeader
        title="Question bank"
        description={
          isPlatformAdmin
            ? "Approve, edit, or reject AI-generated questions before they reach the catalog."
            : "Browse the approved question catalog. New quizzes sample randomly from this pool."
        }
      />

      {/* Board context — visible once a class + subject are picked.
          Helps disambiguate CBSE vs NIOS questions in a multi-board
          deployment. Hidden when filters are still partial. */}
      <BoardContextBar
        classLevel={classLevel === ALL_VALUE ? undefined : classLevel}
        subjectName={
          subjectId === ALL_VALUE
            ? undefined
            : subjectsQ.data?.find((s) => s.id === subjectId)?.name
        }
        board={
          subjectId === ALL_VALUE
            ? undefined
            : subjectsQ.data?.find((s) => s.id === subjectId)?.board
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
              <X className="h-3.5 w-3.5" /> Clear all
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
            <FilterField label="Class">
              <Select
                value={String(classLevel)}
                onValueChange={(v) =>
                  setClassLevel(v === ALL_VALUE ? ALL_VALUE : Number(v))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_VALUE}>All classes</SelectItem>
                  {classesQ.data?.map((c) => (
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
                onValueChange={(v) =>
                  setSubjectId(v === ALL_VALUE ? ALL_VALUE : Number(v))
                }
                disabled={classLevel === ALL_VALUE || !subjectsQ.data?.length}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      classLevel === ALL_VALUE
                        ? "Pick a class first"
                        : "All subjects"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_VALUE}>All subjects</SelectItem>
                  {subjectsQ.data?.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {labelForSubject(s)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterField>

            <FilterField label="Kind">
              <Select value={kind} onValueChange={(v) => setKind(v as Kind)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {KIND_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      <span className="flex flex-col">
                        <span>{o.label}</span>
                        {o.hint && (
                          <span className="text-[10px] text-(--color-muted-foreground)">
                            {o.hint}
                          </span>
                        )}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterField>

            <FilterField label="Bloom level">
              <Select
                value={cognitive}
                onValueChange={(v) => setCognitive(v as BloomLevel | "ALL")}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {COGNITIVE_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterField>

            {isPlatformAdmin && (
              <FilterField label="Status">
                <Select
                  value={status}
                  onValueChange={(v) => setStatus(v as QuestionStatus | "ALL")}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUS_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FilterField>
            )}
          </div>
        </CardContent>
      </Card>

      {questionsQ.isLoading ? (
        <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading...
        </div>
      ) : !questionsQ.data || questionsQ.data.length === 0 ? (
        <Empty
          icon={<NotebookPen className="h-6 w-6" />}
          title={status === "DRAFT" ? "No drafts to review" : "No questions"}
          description={
            status === "DRAFT"
              ? "When new content is generated the questions land here for your review."
              : "Try widening the filters above."
          }
        />
      ) : (
        <>
          <div className="mb-3 text-xs text-(--color-muted-foreground)">
            Showing {questionsQ.data.length} question
            {questionsQ.data.length === 1 ? "" : "s"}
            {questionsQ.data.length === 200 && " (capped — narrow the filters to see more)"}.
          </div>
          <div className="space-y-3">
            {questionsQ.data.map((q) => (
              <QuestionRow key={q.id} q={q} canModerate={isPlatformAdmin} />
            ))}
          </div>
        </>
      )}
    </ThemedPage>
  );
}

function FilterField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
        {label}
      </Label>
      {children}
    </div>
  );
}

function QuestionRow({ q, canModerate }: { q: Question; canModerate: boolean }) {
  const qc = useQueryClient();
  const approve = useMutation({
    mutationFn: () => api.post(`/questions/${q.id}/approve`, {}),
    onSuccess: () => {
      toast.success(`Question #${q.id} approved`);
      qc.invalidateQueries({ queryKey: ["questions"] });
    },
    onError: (e) => toast.error(humanError(e)),
  });
  const reject = useMutation({
    mutationFn: () => api.post(`/questions/${q.id}/reject`, {}),
    onSuccess: () => {
      toast.success(`Question #${q.id} rejected`);
      qc.invalidateQueries({ queryKey: ["questions"] });
    },
    onError: (e) => toast.error(humanError(e)),
  });

  const choices = q.options?.choices ?? [];
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-xs text-(--color-muted-foreground)">
            <Badge variant="outline">{q.type}</Badge>
            <Badge variant="secondary">{q.difficulty}</Badge>
            {q.cognitive_level && (
              <Badge
                variant={BUCKET_BADGE_VARIANT[BLOOM_TO_BUCKET[q.cognitive_level]]}
                title={`Bloom: ${BLOOM_LABEL[q.cognitive_level]} → ${BUCKET_LABEL[BLOOM_TO_BUCKET[q.cognitive_level]]}`}
              >
                {BUCKET_LABEL[BLOOM_TO_BUCKET[q.cognitive_level]]} · {BLOOM_LABEL[q.cognitive_level]}
              </Badge>
            )}
            <Badge
              variant={
                q.status === "APPROVED"
                  ? "success"
                  : q.status === "DRAFT"
                    ? "warning"
                    : q.status === "REJECTED"
                      ? "destructive"
                      : "outline"
              }
            >
              {q.status}
            </Badge>
            {q.outcome_code && <Badge variant="outline">{q.outcome_code}</Badge>}
            <span>{q.marks} marks</span>
          </div>
          <CardTitle className="mt-2 text-base font-medium leading-snug">
            Q{q.id}. {q.text}
          </CardTitle>
        </div>
        <div className="flex gap-2">
          {!canModerate ? null : q.status === "DRAFT" ? (
            <>
              <Button
                size="sm"
                onClick={() => approve.mutate()}
                disabled={approve.isPending}
              >
                {approve.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                Approve
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => reject.mutate()}
                disabled={reject.isPending}
              >
                <X className="h-4 w-4" /> Reject
              </Button>
            </>
          ) : q.status === "REJECTED" ? (
            <Button
              size="sm"
              variant="outline"
              onClick={() => approve.mutate()}
              disabled={approve.isPending}
            >
              <Undo2 className="h-4 w-4" /> Restore
            </Button>
          ) : null}
        </div>
      </CardHeader>
      {choices.length > 0 || q.correct_answer ? (
        <CardContent className="pt-0">
          {choices.length > 0 && (
            <div className="grid gap-1 text-sm">
              {choices.map((opt) => {
                const correct = opt === q.correct_answer;
                return (
                  <div
                    key={opt}
                    className={
                      correct
                        ? "flex items-center gap-2 rounded-md border border-(--color-success) bg-[color-mix(in_oklab,var(--color-success)_10%,transparent)] px-3 py-1.5"
                        : "flex items-center gap-2 rounded-md border border-(--color-border) px-3 py-1.5"
                    }
                  >
                    <span className={correct ? "text-(--color-success)" : "text-(--color-muted-foreground)"}>
                      {correct ? <Check className="h-3.5 w-3.5" /> : "·"}
                    </span>
                    {opt}
                  </div>
                );
              })}
            </div>
          )}
          {choices.length === 0 && (
            <CardDescription>
              <span className="text-xs uppercase tracking-wide">Answer</span>
              <div className="mt-1 rounded-md bg-(--color-muted) p-3 text-sm text-(--color-foreground)">
                {q.correct_answer}
              </div>
            </CardDescription>
          )}
          {q.explanation && (
            <p className="mt-3 text-xs text-(--color-muted-foreground)">
              <span className="font-medium">Explanation: </span>
              {q.explanation}
            </p>
          )}
        </CardContent>
      ) : null}
    </Card>
  );
}
