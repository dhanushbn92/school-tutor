import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Layers, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty } from "@/components/ui/empty";
import {
  useChapters,
  useClasses,
  useSubjects,
} from "@/lib/queries";
import {
  subjectIcon,
  subjectTheme,
  subjectVar,
  subjectVarForeground,
  subjectVarSoft,
} from "@/lib/subjectTheme";

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

  const backLink = classLevel ? `/learn?class=${classLevel}` : "/learn";

  // Resolve subject colour and bind direct CSS-var references for inline
  // styling. We use inline styles (not Tailwind `bg-(--theme)`) because
  // the theme tokens are now declared on :root and inline styling is the
  // most reliable way to consume them.
  const theme = subjectTheme(subject?.name);
  const SubjectIcon = subjectIcon(theme);
  const themeColor = subjectVar(theme);
  const themeFg = subjectVarForeground(theme);
  const themeSoft = subjectVarSoft(theme);

  return (
    <div className="-mx-4 -my-4 md:-mx-6 md:-my-6">
      {/* Subject-tinted page wash — fades from a soft theme tint at the
          top to transparent over the chapter grid. Establishes "you're
          in <subject>" before the user reads anything. */}
      <div
        className="px-4 py-4 md:px-6 md:py-6"
        style={{
          background: `linear-gradient(180deg, ${themeSoft} 0%, transparent 460px)`,
        }}
      >
        {/* Subject hero — bigger, with floating decorative blobs in the
            subject colour. Mirrors the chapter Learn hero so navigation
            between the two feels continuous. */}
        <div
          className="relative mb-6 overflow-hidden rounded-3xl border border-(--color-border) shadow-lg"
          style={{
            background: `linear-gradient(135deg, ${themeSoft} 0%, var(--color-card) 60%)`,
          }}
        >
          {/* Decorative blobs in the subject colour, each drifting on
              its own period so the hero feels alive when idle. */}
          <div
            aria-hidden
            className="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full opacity-30 blur-3xl animate-float-slow"
            style={{ background: themeColor }}
          />
          <div
            aria-hidden
            className="pointer-events-none absolute right-12 top-6 h-32 w-32 rounded-full opacity-25 blur-2xl animate-float-medium"
            style={{ background: themeColor }}
          />
          <div
            aria-hidden
            className="pointer-events-none absolute -bottom-16 right-44 h-40 w-40 rounded-full opacity-20 blur-2xl animate-float-fast"
            style={{ background: themeColor }}
          />

          <div className="relative px-6 py-8 md:px-10 md:py-10">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex min-w-0 items-start gap-4 md:gap-6">
                <div
                  className="flex h-20 w-20 flex-shrink-0 items-center justify-center rounded-3xl shadow-xl ring-2 ring-white/30 md:h-24 md:w-24"
                  style={{
                    background: `linear-gradient(135deg, ${themeColor}, color-mix(in oklab, ${themeColor} 70%, black))`,
                    color: themeFg,
                  }}
                >
                  <SubjectIcon className="h-9 w-9 md:h-11 md:w-11" />
                </div>
                <div className="min-w-0 pt-1">
                  <h1 className="text-3xl font-bold leading-[1.05] tracking-tight md:text-5xl">
                    {subject ? subject.name : "Subject"}
                  </h1>
                  <p className="mt-3 flex flex-wrap items-center gap-2 text-base text-(--color-muted-foreground) md:text-lg">
                    {subject ? (
                      <>
                        {/* Board chip — disambiguates CBSE / NIOS / ... at
                            the top of every chapter listing. */}
                        {subject.board && (
                          <Badge className="text-[11px] font-bold uppercase tracking-wide">
                            {subject.board}
                          </Badge>
                        )}
                        <span>
                          Class {classLevel ?? "—"} ·{" "}
                          {chaptersQ.data?.length ?? 0} chapters
                        </span>
                      </>
                    ) : (
                      "Pick a chapter to start learning."
                    )}
                  </p>
                </div>
              </div>
              <Button asChild variant="outline" className="rounded-full">
                <Link to={backLink}>
                  <ArrowLeft className="h-4 w-4" />
                  All subjects
                </Link>
              </Button>
            </div>
          </div>
        </div>

        {chaptersQ.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading chapters…
          </div>
        ) : !chaptersQ.data || chaptersQ.data.length === 0 ? (
          <Empty
            scene="compass"
            accent={themeColor}
            title="No chapters yet"
            description="Once chapters are added to this subject, they'll show up here ready to explore."
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {chaptersQ.data.map((c) => (
              <Link
                key={c.id}
                to={`/learn/chapters/${c.id}`}
                className="group block focus:outline-none"
              >
                {/* Chapter card with a thick subject-coloured left
                    edge as the visual anchor. Hover lifts the card
                    slightly. The chapter-number chip uses the subject
                    colour as a filled pill rather than a flat outline
                    badge — much more visible. */}
                <Card
                  className="overflow-hidden rounded-2xl shadow-sm transition-all duration-150 group-hover:-translate-y-0.5 group-hover:shadow-lg"
                  style={{ borderLeft: `4px solid ${themeColor}` }}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <span
                          className="mb-2 inline-flex items-center rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide shadow-sm"
                          style={{
                            background: themeColor,
                            color: themeFg,
                          }}
                        >
                          Chapter {c.chapter_number}
                        </span>
                        <CardTitle className="text-lg leading-snug md:text-xl">
                          {c.title}
                        </CardTitle>
                        <CardDescription className="mt-1.5 flex items-center gap-1 text-xs">
                          <Layers className="h-3 w-3" />
                          Topics, summary, practice
                        </CardDescription>
                      </div>
                      <ArrowRight className="h-5 w-5 shrink-0 text-(--color-muted-foreground) transition-transform group-hover:translate-x-1" />
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0 text-sm text-(--color-muted-foreground)">
                    {c.page_count ? `${c.page_count} pages` : null}
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
