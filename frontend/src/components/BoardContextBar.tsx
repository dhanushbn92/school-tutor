/**
 * Visible-at-a-glance "Working on" strip — once a class + subject are
 * picked, the resolved board (CBSE / NIOS / ICSE / ...) is the single
 * most important piece of context to surface. Without this strip, an
 * admin or teacher staring at a "Class 10 Maths" listing has no way
 * to tell whether they're looking at CBSE Maths or NIOS Maths.
 *
 * Originally lived inline inside Generate.tsx; promoted to a shared
 * component so every multi-board surface (Dashboard, Learn,
 * QuestionBank, ContentLibrary, Curriculum) renders the same chip.
 *
 * Renders nothing when `subjectName` or `board` is undefined — keeps
 * the bar invisible during partial selection so it doesn't flicker.
 */
import { Badge } from "@/components/ui/badge";

export function BoardContextBar({
  classLevel,
  subjectName,
  board,
  extra,
}: {
  classLevel?: number;
  subjectName?: string;
  board?: string;
  /** Optional extra label (book or chapter title) appended after subject. */
  extra?: string;
}) {
  if (!subjectName || !board) return null;
  return (
    <div
      className="mb-4 flex flex-wrap items-center gap-2 rounded-md border-l-4 border-(--color-primary) px-3 py-2"
      style={{
        background:
          "color-mix(in oklab, var(--color-primary) 6%, transparent)",
      }}
    >
      <span className="text-[11px] font-semibold uppercase tracking-[0.06em] text-(--color-muted-foreground)">
        Working on
      </span>
      {/* Board chip is the most prominent — uppercase, filled, the
          single most important piece of context to surface. */}
      <Badge className="text-xs font-bold uppercase">{board}</Badge>
      {classLevel !== undefined && (
        <>
          <span className="text-(--color-muted-foreground)">·</span>
          <span className="text-sm font-medium">Class {classLevel}</span>
        </>
      )}
      <span className="text-(--color-muted-foreground)">·</span>
      <span className="text-sm font-medium">{subjectName}</span>
      {extra && (
        <>
          <span className="text-(--color-muted-foreground)">·</span>
          <span className="text-sm text-(--color-muted-foreground) truncate max-w-[200px]">
            {extra}
          </span>
        </>
      )}
    </div>
  );
}

/**
 * Helper for `<option>` labels in subject dropdowns: prefixes the
 * board so admins can tell `[CBSE] Mathematics` from `[NIOS]
 * Mathematics` at a glance. Use:
 *
 *   <option value={s.id}>{labelForSubject(s)}</option>
 *
 * where `s` has at least `name` and `board` fields.
 */
export function labelForSubject(s: { name: string; board?: string }): string {
  if (!s.board) return s.name;
  return `[${s.board}] ${s.name}`;
}
