import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  BookOpenText,
  ChartColumn,
  Layers,
  PlayCircle,
  RotateCcw,
  Target,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useMyMistakes } from "@/lib/queries";

interface Action {
  to: string;
  label: string;
  hint: string;
  icon: ReactNode;
  /** Small count shown on the right, e.g. questions waiting. */
  badge?: number;
}

/**
 * What the learning buddy offers when it is clicked: the places a learner
 * most often wants to go next, in one tap.
 */
export function MascotMenu({
  onClose,
  onHide,
}: {
  onClose: () => void;
  onHide: () => void;
}) {
  const { user } = useAuth();
  const mistakesQ = useMyMistakes({ limit: 1 });
  const waiting = mistakesQ.data?.total_active ?? 0;
  const firstName = (user?.full_name ?? "").split(/\s+/)[0];
  const isStudent = user?.role === "student";

  const actions: Action[] = [
    isStudent
      ? { to: "/assessments", label: "My quizzes", hint: "Quizzes from your teacher", icon: <Target className="h-4 w-4" /> }
      : { to: "/quick-quiz", label: "Start a quiz", hint: "Pick a chapter and practise", icon: <Target className="h-4 w-4" /> },
    { to: "/learn", label: "Continue learning", hint: "Chapters, summaries, worksheets", icon: <BookOpenText className="h-4 w-4" /> },
    { to: "/videos", label: "Watch a video lesson", hint: "Learn it, then practise it", icon: <PlayCircle className="h-4 w-4" /> },
    { to: "/me/mistakes", label: "Review mistakes", hint: "Fix them to improve fastest", icon: <RotateCcw className="h-4 w-4" />, badge: waiting },
    { to: "/practice", label: "Practise your way", hint: "Flashcards and surprise questions", icon: <Layers className="h-4 w-4" /> },
    { to: "/report-card", label: "My progress", hint: "See how far you have come", icon: <ChartColumn className="h-4 w-4" /> },
  ];

  return (
    <div
      role="dialog"
      aria-label="Quick actions"
      className="pointer-events-auto mr-1 w-72 max-w-[calc(100vw-1.5rem)] rounded-2xl border border-(--color-border) bg-(--color-card) p-2 shadow-xl"
    >
      <div className="px-3 pt-2 pb-2">
        <div className="font-display text-base font-bold">
          {firstName ? `Hi, ${firstName}!` : "Hi there!"}
        </div>
        <div className="text-sm text-(--color-muted-foreground)">What shall we do?</div>
      </div>
      <ul className="space-y-0.5">
        {actions.map((a) => (
          <li key={a.to}>
            <Link
              to={a.to}
              onClick={onClose}
              className="flex items-center gap-3 rounded-xl px-3 py-2 transition-colors hover:bg-(--color-muted) focus-visible:bg-(--color-muted)"
            >
              <span
                aria-hidden
                className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-(--color-primary)/10 text-(--color-primary)"
              >
                {a.icon}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold leading-tight">{a.label}</span>
                <span className="block truncate text-xs text-(--color-muted-foreground)">{a.hint}</span>
              </span>
              {a.badge ? (
                <span className="rounded-full bg-[#F7931E] px-2 py-0.5 text-xs font-bold text-[#2B1700]">
                  {a.badge}
                </span>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
      <div className="mt-1 border-t border-(--color-border) pt-1">
        <button
          type="button"
          onClick={onHide}
          className="w-full rounded-xl px-3 py-2 text-left text-xs text-(--color-muted-foreground) hover:bg-(--color-muted) hover:text-(--color-foreground)"
        >
          Hide for now (it comes back on your next visit)
        </button>
      </div>
    </div>
  );
}
