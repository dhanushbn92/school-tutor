import { useEffect, useState } from "react";
import { BookOpenText, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
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
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { BoardContextBar, labelForSubject } from "@/components/BoardContextBar";
import {
  useChapters,
  useClasses,
  useCurriculumContext,
  useSubjects,
} from "@/lib/queries";

export function CurriculumPage() {
  const classesQ = useClasses();
  const [classLevel, setClassLevel] = useState<number | undefined>(undefined);
  const subjectsQ = useSubjects(classLevel);
  const [subjectId, setSubjectId] = useState<number | undefined>(undefined);
  const chaptersQ = useChapters({ class_level: classLevel, subject_id: subjectId });
  const [chapterId, setChapterId] = useState<number | undefined>(undefined);
  const contextQ = useCurriculumContext(chapterId);

  useEffect(() => {
    if (!classLevel && classesQ.data?.length) {
      const six = classesQ.data.find((c) => c.level === 6) ?? classesQ.data[0];
      setClassLevel(six.level);
    }
  }, [classLevel, classesQ.data]);
  useEffect(() => {
    // Reset / pick a subject from the *current* class's subjects only. Without
    // the second half of this guard, a subjectId picked from a stale fetch
    // (e.g. another class's "Science") would silently survive a class change
    // and the chapters query would then return [] because the (class, subject)
    // pair doesn't exist.
    const subjects = subjectsQ.data;
    if (!subjects || subjects.length === 0) return;
    const stillValid =
      subjectId !== undefined && subjects.some((s) => s.id === subjectId);
    if (stillValid) return;
    setSubjectId(
      subjects.find((s) => s.name === "Science")?.id ?? subjects[0].id,
    );
  }, [subjectId, subjectsQ.data]);
  useEffect(() => {
    setChapterId(chaptersQ.data?.[0]?.id);
  }, [chaptersQ.data]);

  return (
    <ThemedPage>
      <PageHeader
        title="Curriculum"
        description="Browse the NCERT textbook by chapter and see the learning outcomes attached."
        actions={
          <div className="flex items-center gap-2">
            <div className="w-32">
              <Select
                value={classLevel !== undefined ? String(classLevel) : ""}
                onValueChange={(v) => {
                  setClassLevel(Number(v));
                  setSubjectId(undefined);
                  setChapterId(undefined);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Class" />
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
            <div className="w-40">
              <Select
                value={subjectId !== undefined ? String(subjectId) : ""}
                onValueChange={(v) => {
                  setSubjectId(Number(v));
                  setChapterId(undefined);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Subject" />
                </SelectTrigger>
                <SelectContent>
                  {subjectsQ.data?.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {labelForSubject(s)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        }
      />

      {/* Board context strip — disambiguates CBSE vs NIOS once a subject
          is picked. Renders nothing during partial selection. */}
      <BoardContextBar
        classLevel={classLevel}
        subjectName={subjectsQ.data?.find((s) => s.id === subjectId)?.name}
        board={subjectsQ.data?.find((s) => s.id === subjectId)?.board}
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <Card>
          <CardHeader>
            <CardTitle>Chapters</CardTitle>
            <CardDescription>
              {chaptersQ.data?.length ?? 0} chapters available.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 pr-2">
            {chaptersQ.isLoading ? (
              <Loading />
            ) : !chaptersQ.data || chaptersQ.data.length === 0 ? (
              <Empty title="No chapters" className="border-0 py-6" />
            ) : (
              chaptersQ.data.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setChapterId(c.id)}
                  className={
                    "flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors " +
                    (chapterId === c.id
                      ? "bg-(--color-muted) font-medium text-(--color-primary)"
                      : "hover:bg-(--color-muted)")
                  }
                >
                  <span className="flex items-baseline gap-2 truncate">
                    <span className="text-xs text-(--color-muted-foreground)">
                      Ch {c.chapter_number}
                    </span>
                    <span className="truncate">{c.title}</span>
                  </span>
                  {c.page_count && (
                    <Badge variant="outline" className="shrink-0">
                      {c.page_count} pages
                    </Badge>
                  )}
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              {contextQ.data
                ? `Ch ${contextQ.data.chapter_number}. ${contextQ.data.chapter_title}`
                : "Select a chapter"}
            </CardTitle>
            <CardDescription>
              {contextQ.data
                ? `${contextQ.data.outcomes.length} learning outcomes · ${contextQ.data.chapter_text.length.toLocaleString()} characters of source text`
                : "Learning outcomes and a preview of the chapter text."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {contextQ.isLoading ? (
              <Loading />
            ) : !contextQ.data ? (
              <Empty
                icon={<BookOpenText className="h-6 w-6" />}
                title="Pick a chapter"
                description="Use the list on the left to explore outcomes and text."
                className="border-0"
              />
            ) : (
              <div className="space-y-6">
                <div>
                  <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-(--color-muted-foreground)">
                    Learning outcomes
                  </h3>
                  <ul className="space-y-2">
                    {contextQ.data.outcomes.map((o) => (
                      <li
                        key={o.code}
                        className="rounded-md border border-(--color-border) p-3 text-sm"
                      >
                        <div className="flex flex-wrap items-center gap-2 text-xs text-(--color-muted-foreground)">
                          <Badge variant="outline">{o.code}</Badge>
                          <Badge variant="secondary">{o.bloom_level}</Badge>
                        </div>
                        <p className="mt-1">{o.description}</p>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-(--color-muted-foreground)">
                    Chapter preview
                  </h3>
                  <div className="max-h-96 overflow-y-auto rounded-md border border-(--color-border) bg-(--color-muted)/40 p-4 text-sm leading-relaxed">
                    {contextQ.data.chapter_text.slice(0, 4000)}
                    {contextQ.data.chapter_text.length > 4000 && "…"}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </ThemedPage>
  );
}

function Loading() {
  return (
    <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
      <Loader2 className="h-4 w-4 animate-spin" /> Loading...
    </div>
  );
}
