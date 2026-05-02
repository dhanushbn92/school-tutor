/**
 * Syllabus boards supported by the platform. Mirrors
 * `app/core/boards.py` on the backend — adding a new board is a paired
 * change in both files. Order is the dropdown's display order so most
 * common (CBSE) sits at the top.
 */
export const VALID_BOARDS = [
  "CBSE",
  "NIOS",
  "ICSE",
  "State Board",
  "Other",
] as const;

export type Board = (typeof VALID_BOARDS)[number];
