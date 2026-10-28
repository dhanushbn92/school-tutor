import type { MascotMood } from "@/lib/mascotContext";

/** What the eyes of the learning buddy are doing. */
export type EyeShape = "open" | "happy" | "wide";
/** What its mouth is doing. */
export type MouthShape = "smile" | "grin" | "flat" | "oh";
/** A small prop that floats near its head. */
export type MascotEffect =
  | "none"
  | "question"
  | "bulb"
  | "bell"
  | "sparkles"
  | "alert";
/** The body animation (a CSS class defined in MascotFigure). */
export type MascotMotion =
  | "float"
  | "float-slow"
  | "tilt"
  | "bounce"
  | "sway"
  | "jump"
  | "pulse"
  | "wiggle"
  | "pop";

export interface MascotPose {
  left: EyeShape;
  right: EyeShape;
  /** Where the pupils look, in screen units (x right, y down). */
  look: [number, number];
  mouth: MouthShape;
  effect: MascotEffect;
  motion: MascotMotion;
  /** What the pose shows, for assistive tech. */
  description: string;
}

/** One expression + motion + prop per mood. */
export const MOOD_POSES: Record<MascotMood, MascotPose> = {
  IDLE: {
    left: "open", right: "open", look: [0, 0], mouth: "smile",
    effect: "none", motion: "float", description: "ready to help",
  },
  DRAWN: {
    left: "open", right: "open", look: [9, -10], mouth: "flat",
    effect: "question", motion: "tilt", description: "thinking with you",
  },
  FIRES: {
    left: "happy", right: "happy", look: [0, 0], mouth: "smile",
    effect: "sparkles", motion: "bounce", description: "happy",
  },
  RESTRING: {
    left: "happy", right: "open", look: [0, 0], mouth: "smile",
    effect: "none", motion: "sway", description: "cheering you on",
  },
  VICTORY: {
    left: "happy", right: "happy", look: [0, 0], mouth: "grin",
    effect: "sparkles", motion: "jump", description: "celebrating",
  },
  HINT: {
    left: "open", right: "happy", look: [0, 0], mouth: "smile",
    effect: "bulb", motion: "pulse", description: "with a hint",
  },
  REMINDER: {
    left: "open", right: "open", look: [0, 0], mouth: "smile",
    effect: "bell", motion: "wiggle", description: "with a reminder",
  },
  READING: {
    left: "open", right: "open", look: [0, 11], mouth: "smile",
    effect: "none", motion: "float-slow", description: "reading along",
  },
  SURPRISED: {
    left: "wide", right: "wide", look: [0, 0], mouth: "oh",
    effect: "alert", motion: "pop", description: "surprised",
  },
};

/** Shown while the learner hovers over the buddy or has its menu open. */
export const GREETING_POSE: MascotPose = {
  left: "happy", right: "open", look: [0, 0], mouth: "grin",
  effect: "none", motion: "pop", description: "waiting for a click",
};
