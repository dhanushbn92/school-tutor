import { BRAND_ARROW_COLORS } from "@/lib/brand";
import type { StampKind } from "@/lib/types";

/**
 * Per-kind stamp presentation — colour + label + one-line description.
 *
 * Lives in a `.ts` (not `.tsx`) so it can be imported by both the
 * dashboard PracticeCard and the StampBook page without tripping
 * Vite's react-refresh "components only" rule, which fires when a
 * .tsx file exports a non-component value.
 *
 * Colours are pulled from the brand arrow palette so stamps feel
 * like they belong to the same world as the logo.
 */
export const STAMP_PRESENTATION: Record<
  StampKind,
  { label: string; color: string; description: string }
> = {
  QUIZ_COMPLETED: {
    label: "Quiz completed",
    color: BRAND_ARROW_COLORS.navy,
    description: "You finished a quiz.",
  },
  PERFECT_SCORE: {
    label: "Perfect score",
    color: BRAND_ARROW_COLORS.yellow,
    description: "All marks on the auto-graded questions.",
  },
  PRACTICE_DAY: {
    label: "Practice day",
    color: BRAND_ARROW_COLORS.green,
    description: "Your first quiz of the day — practice ritual kept.",
  },
  WEEKLY_GOAL_MET: {
    label: "Weekly goal met",
    color: BRAND_ARROW_COLORS.magenta,
    description: "You hit your weekly practice-days goal.",
  },
};
