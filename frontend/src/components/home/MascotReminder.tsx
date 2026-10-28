import { useEffect } from "react";
import { useMascot } from "@/lib/mascotContext";
import { useMyMistakes, usePracticeSummary } from "@/lib/queries";

const SESSION_KEY = "st.mascot.reminder";

/**
 * The learning buddy's gentle nudge, shown once per browser session when the
 * learner lands on the home page: questions waiting to be reviewed first,
 * otherwise how many practice days are left this week. It renders nothing.
 */
export function MascotReminder() {
  const { reactWith } = useMascot();
  const mistakesQ = useMyMistakes({ limit: 1 });
  const summaryQ = usePracticeSummary();

  const waiting = mistakesQ.data?.total_active;
  const summary = summaryQ.data;
  const ready = waiting !== undefined && summary !== undefined;
  const daysLeft = summary
    ? Math.max(0, summary.target_days - summary.practice_days_count_this_week)
    : 0;

  useEffect(() => {
    if (!ready) return;
    let seen = false;
    try {
      seen = sessionStorage.getItem(SESSION_KEY) === "1";
    } catch {
      // Storage can be blocked; fall through and show the nudge once per mount.
    }
    if (seen) return;

    let message: string | null = null;
    let icon: "bell" | "calendar" = "bell";
    if (waiting > 0) {
      message = `You have ${waiting} ${waiting === 1 ? "question" : "questions"} to review. Shall we?`;
    } else if (daysLeft > 0) {
      message = `${daysLeft} more practice ${daysLeft === 1 ? "day" : "days"} to hit your weekly goal.`;
      icon = "calendar";
    }
    if (!message) return;

    reactWith("REMINDER", { message, icon, autoResetMs: 9000 });
    try {
      sessionStorage.setItem(SESSION_KEY, "1");
    } catch {
      // Not fatal: the nudge may repeat on the next visit to the home page.
    }
  }, [ready, waiting, daysLeft, reactWith]);

  return null;
}
