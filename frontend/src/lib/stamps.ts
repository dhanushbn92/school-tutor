import { BRAND_ARROW_COLORS } from "@/lib/brand";
import type { StampKind } from "@/lib/types";

/**
 * Per-kind stamp presentation — colour + label + description + tier + tagline + icon name.
 *
 * Lives in a `.ts` (not `.tsx`) so it can be imported by both the
 * dashboard PracticeCard and the StampBook page without tripping
 * Vite's react-refresh "components only" rule, which fires when a
 * .tsx file exports a non-component value.
 *
 * Colours come from the brand arrow palette so stamps feel like they
 * belong to the same world as the logo.
 *
 * The visual rendering lives in `@/components/StampBadge` — it reads
 * the `tier` to pick a shape (circle for bronze, shield for silver,
 * shield-with-starburst for gold, medallion-with-halo for platinum)
 * and `iconName` to pick the lucide icon to put at the centre. The
 * `tagline` is the short prideful phrase shown on the ribbon below
 * a featured badge.
 */
export type StampTier = "bronze" | "silver" | "gold" | "platinum";

export type StampIconName =
  | "Trophy"
  | "Crown"
  | "Star"
  | "Flame"
  | "Target"
  | "BookCheck"
  | "Lightbulb"
  | "Compass"
  | "Zap"
  | "Dice5"
  | "Layers"
  | "CalendarCheck"
  | "Sun"
  | "ClipboardCheck";

export interface StampDesign {
  label: string;
  color: string;
  description: string;
  tier: StampTier;
  /** Short prideful phrase shown on the ribbon under a featured badge. 2-3 words. */
  tagline: string;
  /** Name of the lucide icon to render at the centre of the badge. */
  iconName: StampIconName;
}

export const STAMP_PRESENTATION: Record<StampKind, StampDesign> = {
  // ─── High-volume daily / always-on stamps (bronze) ──────────────────
  QUIZ_COMPLETED: {
    label: "Quiz completed",
    color: BRAND_ARROW_COLORS.navy,
    description: "You finished a quiz.",
    tier: "bronze",
    tagline: "Quiz done",
    iconName: "ClipboardCheck",
  },
  PERFECT_SCORE: {
    label: "Perfect score",
    color: BRAND_ARROW_COLORS.yellow,
    description: "All marks on the auto-graded questions.",
    tier: "bronze",
    tagline: "Bullseye",
    iconName: "Star",
  },
  PRACTICE_DAY: {
    label: "Practice day",
    color: BRAND_ARROW_COLORS.green,
    description: "Your first quiz of the day — practice ritual kept.",
    tier: "bronze",
    tagline: "Daily drill",
    iconName: "Sun",
  },
  WEEKLY_GOAL_MET: {
    label: "Weekly goal met",
    color: BRAND_ARROW_COLORS.magenta,
    description: "You hit your weekly practice-days goal.",
    tier: "bronze",
    tagline: "Goal getter",
    iconName: "CalendarCheck",
  },

  // ─── Streak milestones (bronze → platinum) ─────────────────────────
  STREAK_3_DAYS: {
    label: "3-day streak",
    color: BRAND_ARROW_COLORS.orange,
    description: "Three days of practice in a row.",
    tier: "bronze",
    tagline: "Hot streak",
    iconName: "Flame",
  },
  STREAK_7_DAYS: {
    label: "7-day streak",
    color: BRAND_ARROW_COLORS.orange,
    description: "A whole week of practice in a row.",
    tier: "silver",
    tagline: "Week champion",
    iconName: "Flame",
  },
  STREAK_14_DAYS: {
    label: "14-day streak",
    color: BRAND_ARROW_COLORS.orange,
    description: "Two weeks of practice in a row.",
    tier: "gold",
    tagline: "Two weeks strong",
    iconName: "Flame",
  },
  STREAK_30_DAYS: {
    label: "30-day streak",
    color: BRAND_ARROW_COLORS.orange,
    description: "A full month of daily practice.",
    tier: "platinum",
    tagline: "Unstoppable",
    iconName: "Flame",
  },

  // ─── Volume milestones (bronze → platinum) ──────────────────────────
  FIRST_QUIZ: {
    label: "First quiz",
    color: BRAND_ARROW_COLORS.green,
    description: "Your very first quiz — welcome to the journey.",
    tier: "bronze",
    tagline: "First step",
    iconName: "Trophy",
  },
  TEN_QUIZZES: {
    label: "10 quizzes",
    color: BRAND_ARROW_COLORS.green,
    description: "Ten quizzes done. Building real practice volume.",
    tier: "bronze",
    tagline: "Off the mark",
    iconName: "Trophy",
  },
  FIFTY_QUIZZES: {
    label: "50 quizzes",
    color: BRAND_ARROW_COLORS.teal,
    description: "Fifty quizzes — serious commitment.",
    tier: "silver",
    tagline: "Veteran",
    iconName: "Trophy",
  },
  HUNDRED_QUIZZES: {
    label: "100 quizzes",
    color: BRAND_ARROW_COLORS.purple,
    description: "A hundred quizzes. That's mastery in motion.",
    tier: "gold",
    tagline: "Centurion",
    iconName: "Trophy",
  },
  TWO_FIFTY_QUIZZES: {
    label: "250 quizzes",
    color: BRAND_ARROW_COLORS.magenta,
    description: "Two hundred and fifty. Genuine dedication.",
    tier: "platinum",
    tagline: "Legend",
    iconName: "Crown",
  },

  // ─── Perfect-score tiers (bronze → platinum) ────────────────────────
  FIVE_PERFECT_SCORES: {
    label: "5 perfect scores",
    color: BRAND_ARROW_COLORS.yellow,
    description: "Five quizzes nailed without a single missed mark.",
    tier: "silver",
    tagline: "Sharpshooter",
    iconName: "Star",
  },
  TEN_PERFECT_SCORES: {
    label: "10 perfect scores",
    color: BRAND_ARROW_COLORS.yellow,
    description: "Ten flawless runs. Precision practice.",
    tier: "platinum",
    tagline: "Flawless ten",
    iconName: "Crown",
  },

  // ─── Mistake mastery (bronze → platinum) ────────────────────────────
  MISTAKE_CLEARED: {
    label: "Mistake cleared",
    color: BRAND_ARROW_COLORS.green,
    description: "Turned a mistake around — twice right in a row.",
    tier: "silver",
    tagline: "Bounced back",
    iconName: "Target",
  },
  TEN_MISTAKES_CLEARED: {
    label: "10 mistakes cleared",
    color: BRAND_ARROW_COLORS.green,
    description: "Ten mistakes turned into mastery. That's how it's done.",
    tier: "platinum",
    tagline: "Comeback king",
    iconName: "Target",
  },

  // ─── Chapter mastery (gold) ─────────────────────────────────────────
  CHAPTER_MASTERED: {
    label: "Chapter mastered",
    color: BRAND_ARROW_COLORS.green,
    description: "A whole chapter mastered. Onwards.",
    tier: "gold",
    tagline: "Chapter conquered",
    iconName: "BookCheck",
  },

  // ─── Learning exploration (silver / bronze / platinum) ──────────────
  DEEPER_LEARNER: {
    label: "Deeper learner",
    color: BRAND_ARROW_COLORS.purple,
    description: "Asked 'tell me more' five times. Curious mind.",
    tier: "silver",
    tagline: "Curious mind",
    iconName: "Lightbulb",
  },
  TRIED_SPEEDRUN: {
    label: "Speedrun starter",
    color: BRAND_ARROW_COLORS.orange,
    description: "First speedrun completed.",
    tier: "bronze",
    tagline: "Need for speed",
    iconName: "Zap",
  },
  TRIED_SURPRISE: {
    label: "Dice roller",
    color: BRAND_ARROW_COLORS.purple,
    description: "First 'Surprise me' question rolled.",
    tier: "bronze",
    tagline: "Dice roller",
    iconName: "Dice5",
  },
  TRIED_FLASHCARDS: {
    label: "Flashcard flipper",
    color: BRAND_ARROW_COLORS.teal,
    description: "First flashcards deck explored.",
    tier: "bronze",
    tagline: "Card flipper",
    iconName: "Layers",
  },
  EXPLORER: {
    label: "Explorer",
    color: BRAND_ARROW_COLORS.magenta,
    description: "Tried every practice mode — speedrun, surprise, and flashcards.",
    tier: "platinum",
    tagline: "Adventurer",
    iconName: "Compass",
  },
};

/**
 * Ordering used by the StampBook tally row — rarer / more prestigious
 * kinds first so a learner's eye lands on their flagship achievements.
 */
export const STAMP_KIND_ORDER: StampKind[] = [
  // Platinum (rarest, prestige)
  "TWO_FIFTY_QUIZZES",
  "STREAK_30_DAYS",
  "TEN_PERFECT_SCORES",
  "TEN_MISTAKES_CLEARED",
  "EXPLORER",
  // Gold
  "HUNDRED_QUIZZES",
  "STREAK_14_DAYS",
  "CHAPTER_MASTERED",
  // Silver
  "FIFTY_QUIZZES",
  "STREAK_7_DAYS",
  "FIVE_PERFECT_SCORES",
  "MISTAKE_CLEARED",
  "DEEPER_LEARNER",
  // Bronze
  "STREAK_3_DAYS",
  "TEN_QUIZZES",
  "FIRST_QUIZ",
  "WEEKLY_GOAL_MET",
  "TRIED_SPEEDRUN",
  "TRIED_SURPRISE",
  "TRIED_FLASHCARDS",
  // High-volume / always-on
  "PERFECT_SCORE",
  "PRACTICE_DAY",
  "QUIZ_COMPLETED",
];
