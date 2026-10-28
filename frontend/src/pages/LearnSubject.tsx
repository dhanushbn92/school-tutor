import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ChevronRight, Loader2, PlayCircle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Empty } from "@/components/ui/empty";
import {
  useChapters,
  useClasses,
  useFeaturedVideos,
  useSubjects,
} from "@/lib/queries";
import { subjectTheme, subjectVar, subjectVarSoft } from "@/lib/subjectTheme";

/** The chapters of one subject, as a calm numbered list. */
export function LearnSubjectPage() {
  const { subjectId: subjectIdParam } = useParams();
  const subjectId = subjectIdParam ? Number(subjectIdParam) : undefined;

  // Fetch all subjects (no class filter) so we can find this subject regardless
  // of the viewer's role/section. Previously this page derived classLevel from
  // useMySections()[0]?.class_level, which broke for school admins browsing a
  // class their first section doesn't belong to. We opt in to the cross-class
  // fetch — by default useSubjects(undefined) is gated.
  const subjectsQ = useSubjects(undefined, { fetchAllWhenUndefined: true });
  const classesQ = useClasses();
  const subject = subjectsQ.data?.find((s) => s.id === subjectId);
  const classLevel = classesQ.data?.find((c) => c.id === subject?.class_id)?.level;

  // subject_id is sufficient — chapters are uniquely keyed under a subject —
  // so we don't need to also pass class_level here.
  const chaptersQ = useChapters({ subject_id: subjectId });
  const featuredQ = useFeaturedVideos();
  const videosByChapter = useMemo(() => {
    const m = new Map<number, number>();
    for (const c of featuredQ.data?.chapters ?? []) m.set(c.chapter_id, c.video_count);
    return m;
  }, [featuredQ.data]);

  const backLink = classLevel ? `/learn?class=${classLevel}` : "/learn";
  const theme = subjectTheme(subject?.name);
  const chapterCount = chaptersQ.data?.length ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <Link
          to={backLink}
          className="inline-flex items-center gap-1.5 text-sm text-(--color-muted-foreground) hover:text-(--color-foreground)"
        >
          <ArrowLeft className="h-4 w-4" />
          All subjects
        </Link>
        <h1 className="mt-1.5 font-display text-3xl font-extrabold tracking-tight">
          {subject ? subject.name : "Subject"}
        </h1>
        <p className="mt-1.5 flex flex-wrap items-center gap-2 text-base text-(--color-muted-foreground)">
          {subject ? (
            <>
              {subject.board && (
                <span className="rounded-full bg-(--color-primary)/10 px-3 py-0.5 text-xs font-bold text-(--color-primary)">
                  {subject.board}
                </span>
              )}
              <span>
                Class {classLevel ?? "—"} · {chapterCount} {chapterCount === 1 ? "chapter" : "chapters"}
              </span>
            </>
          ) : (
            "Pick a chapter to start learning."
          )}
        </p>
      </div>

      {chaptersQ.isLoading ? (
        <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading chapters…
        </div>
      ) : !chaptersQ.data || chaptersQ.data.length === 0 ? (
        <Empty
          scene="compass"
          accent={subjectVar(theme)}
          title="No chapters yet"
          description="Once chapters are added to this subject, they'll show up here ready to explore."
        />
      ) : (
        <Card className="overflow-hidden rounded-2xl">
          <ul className="divide-y divide-(--color-border)">
            {chaptersQ.data.map((c) => {
              const videos = videosByChapter.get(c.id) ?? 0;
              return (
                <li key={c.id}>
                  <Link
                    to={`/learn/chapters/${c.id}`}
                    className="group flex items-center gap-4 px-5 py-4 transition-colors hover:bg-(--color-muted)"
                  >
                    <span
                      aria-hidden
                      className="grid h-10 w-10 shrink-0 place-items-center rounded-full font-display text-sm font-bold"
                      style={{ background: subjectVarSoft(theme), color: subjectVar(theme) }}
                    >
                      {c.chapter_number}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-base font-semibold leading-snug [overflow-wrap:anywhere]">
                        {c.title}
                      </span>
                      {c.page_count ? (
                        <span className="text-xs text-(--color-muted-foreground)">
                          {c.page_count} pages
                        </span>
                      ) : null}
                    </span>
                    {videos > 0 && (
                      <span className="hidden shrink-0 items-center gap-1.5 rounded-full bg-(--color-primary)/10 px-3 py-1 text-xs font-semibold text-(--color-primary) sm:inline-flex">
                        <PlayCircle className="h-3.5 w-3.5" aria-hidden />
                        {videos} {videos === 1 ? "video" : "videos"}
                      </span>
                    )}
                    <ChevronRight
                      className="h-5 w-5 shrink-0 text-(--color-muted-foreground) transition-transform group-hover:translate-x-0.5"
                      aria-hidden
                    />
                  </Link>
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </div>
  );
}
