import { SubjectCard } from "@/components/SubjectCard";
import type { SubjectRollup } from "@/lib/progress";

/** The home page's "Your subjects" row: one compact card per subject. */
export function SubjectCards({
  subjects,
  videosBySubject,
}: {
  subjects: SubjectRollup[];
  videosBySubject: Map<number, number>;
}) {
  if (subjects.length === 0) return null;
  return (
    <section aria-labelledby="home-subjects">
      <h2
        id="home-subjects"
        className="mb-3 font-display text-lg font-bold tracking-tight"
      >
        Your subjects
      </h2>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(12rem,1fr))] gap-4">
        {subjects.map((s) => (
          <SubjectCard
            key={s.key}
            name={s.subject_name}
            percent={s.percent}
            where={
              s.current
                ? `Chapter ${s.current.chapter_number} of ${s.chapters.length}`
                : `${s.chapters.length} ${s.chapters.length === 1 ? "chapter" : "chapters"}`
            }
            videos={s.subject_id !== null ? (videosBySubject.get(s.subject_id) ?? 0) : 0}
            to={
              s.current
                ? `/learn/chapters/${s.current.chapter_id}`
                : s.subject_id !== null
                  ? `/learn/subjects/${s.subject_id}`
                  : "/learn"
            }
            cta="Continue"
          />
        ))}
      </div>
    </section>
  );
}
