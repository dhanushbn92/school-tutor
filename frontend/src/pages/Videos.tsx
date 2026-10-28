import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ChevronRight, PlayCircle } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Empty } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { useFeaturedVideos } from "@/lib/queries";
import {
  subjectTheme,
  subjectVar,
  subjectVarForeground,
} from "@/lib/subjectTheme";
import { cn } from "@/lib/utils";

interface SubjectGroup {
  id: number;
  name: string;
  videos: number;
  chapters: {
    chapter_id: number;
    chapter_number: number;
    chapter_title: string;
    video_count: number;
  }[];
}

/**
 * Every video lesson the signed-in user can watch, by subject and chapter.
 *
 * This is the one place that scales as videos arrive for more subjects: pick a
 * subject, then a chapter, and the chapter opens on its Videos tab. It only
 * lists what the server says this user can see (their class and board).
 */
export function VideosPage() {
  const { data, isLoading, isError } = useFeaturedVideos();
  const [params, setParams] = useSearchParams();

  const groups = useMemo<SubjectGroup[]>(() => {
    const byId = new Map<number, SubjectGroup>();
    for (const c of data?.chapters ?? []) {
      const g = byId.get(c.subject_id) ?? {
        id: c.subject_id,
        name: c.subject_name,
        videos: 0,
        chapters: [],
      };
      g.videos += c.video_count;
      g.chapters.push(c);
      byId.set(c.subject_id, g);
    }
    return [...byId.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [data]);

  const requested = Number(params.get("subject"));
  const selected = groups.find((g) => g.id === requested) ?? groups[0];
  const theme = subjectTheme(selected?.name);
  const themeColor = subjectVar(theme);
  const themeFg = subjectVarForeground(theme);

  return (
    <ThemedPage themeColor={themeColor} className="mx-auto max-w-4xl">
      <PageHeader
        title="Video lessons"
        description="Pick a subject, then a chapter. Each chapter opens on its videos, so you can watch the lesson and then practise."
      />

      {isLoading ? (
        <div className="space-y-3" aria-busy="true">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : isError ? (
        <Empty
          icon={<PlayCircle className="h-6 w-6" />}
          title="Couldn't load the video lessons"
          description="Check your connection and refresh the page."
        />
      ) : !selected ? (
        <Empty
          icon={<PlayCircle className="h-6 w-6" />}
          title="No video lessons yet"
          description="Videos for your class will show up here as soon as they are ready."
        />
      ) : (
        <div className="space-y-5">
          {groups.length > 1 && (
            <div
              role="tablist"
              aria-label="Subjects"
              className="flex flex-wrap gap-2"
            >
              {groups.map((g) => {
                const active = g.id === selected.id;
                return (
                  <button
                    key={g.id}
                    role="tab"
                    type="button"
                    aria-selected={active}
                    onClick={() =>
                      setParams({ subject: String(g.id) }, { replace: true })
                    }
                    className={cn(
                      "flex min-h-11 items-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium transition-colors",
                      active
                        ? "border-transparent bg-(--color-primary) text-(--color-primary-foreground) shadow-md"
                        : "border-(--color-border) bg-(--color-card) hover:bg-(--color-muted)",
                    )}
                  >
                    {g.name}
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs",
                        active
                          ? "bg-white/25"
                          : "bg-(--color-muted) text-(--color-muted-foreground)",
                      )}
                    >
                      {g.videos}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          <p className="text-sm text-(--color-muted-foreground)">
            {selected.name}: {selected.videos}{" "}
            {selected.videos === 1 ? "video" : "videos"} in{" "}
            {selected.chapters.length}{" "}
            {selected.chapters.length === 1 ? "chapter" : "chapters"}
          </p>

          <ul className="space-y-3">
            {selected.chapters.map((c) => (
              <li key={c.chapter_id}>
                <Link
                  to={`/learn/chapters/${c.chapter_id}?tab=videos`}
                  className="group block rounded-2xl focus-visible:outline-2"
                >
                  <Card className="flex items-center gap-4 p-4 transition-shadow group-hover:shadow-md">
                    <span
                      aria-hidden
                      className="grid h-12 w-12 shrink-0 place-items-center rounded-xl font-display text-lg font-semibold"
                      style={{ background: themeColor, color: themeFg }}
                    >
                      {c.chapter_number}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-base font-semibold leading-relaxed">
                        {c.chapter_title}
                      </span>
                      <span className="mt-0.5 flex items-center gap-1.5 text-sm text-(--color-muted-foreground)">
                        <PlayCircle className="h-4 w-4" aria-hidden />
                        {c.video_count}{" "}
                        {c.video_count === 1 ? "video" : "videos"}
                      </span>
                    </span>
                    <Badge
                      variant="secondary"
                      className="hidden shrink-0 sm:inline-flex"
                    >
                      Watch
                    </Badge>
                    <ChevronRight
                      className="h-5 w-5 shrink-0 text-(--color-muted-foreground) transition-transform group-hover:translate-x-0.5"
                      aria-hidden
                    />
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </ThemedPage>
  );
}
