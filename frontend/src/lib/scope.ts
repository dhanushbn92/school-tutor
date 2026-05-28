import { useMemo } from "react";
import { useAuth } from "@/lib/auth";
import {
  useClasses,
  useMySections,
  useMyTeacherSubjects,
  useSubjects,
} from "@/lib/queries";
import type { SchoolClass, Subject } from "@/lib/types";


/**
 * For learner roles (student, individual_learner), returns the class level
 * the learner is actually enrolled in. For other roles, returns undefined.
 *
 * Used to scope Curriculum / Learn / Content pickers so a Class 10 student
 * doesn't see Class 12 material (or vice versa) in the dropdowns.
 */
export function useLearnerOwnClassLevel(): {
  classLevel: number | undefined;
  isLoading: boolean;
} {
  const { user } = useAuth();
  const isLearner = user?.role === "student" || user?.role === "individual_learner";
  const sectionsQ = useMySections();

  const classLevel = useMemo<number | undefined>(() => {
    if (!isLearner) return undefined;
    const first = sectionsQ.data?.[0];
    return first?.class_level ?? undefined;
  }, [isLearner, sectionsQ.data]);

  return { classLevel, isLoading: isLearner && sectionsQ.isLoading };
}

interface AvailableClasses {
  classes: SchoolClass[];
  isLoading: boolean;
  /**
   * True when the role is naturally scoped to a subset of classes (i.e. teacher).
   * Pages can use this to hide an "All classes" option and force a single-class
   * pick — picking "all" doesn't make sense if "all" already means "all of mine".
   */
  isScoped: boolean;
}

/**
 * Returns the list of curriculum classes the current viewer is allowed to
 * browse. For teachers this is derived from their explicit subject
 * assignments (via `/me/teacher-subjects`) — the unique class_ids of those
 * subjects. When a teacher has no explicit assignments the backend falls
 * back to "all subjects of classes I'm class teacher of"; we honour that
 * same fallback here automatically because the response already encodes it.
 *
 * Other roles (platform admin, school admin, individual learner) see the
 * full curriculum. Students don't browse via class pickers.
 */
export function useAvailableClasses(): AvailableClasses {
  const { user } = useAuth();
  const allClassesQ = useClasses();
  const isTeacher = user?.role === "teacher";
  const isLearner =
    user?.role === "student" || user?.role === "individual_learner";

  // Don't fire the teacher-subjects query for non-teacher roles.
  const teacherSubjectsQ = useMyTeacherSubjects(isTeacher);
  // Resolve learner's own enrolled class level so we can lock the picker.
  const ownLevel = useLearnerOwnClassLevel();

  // Teachers need *all* subjects loaded so we can map their subject_ids
  // back to class_ids. We opt in to the cross-class fetch — by default
  // useSubjects(undefined) is gated to avoid race-mismatches in pages like
  // Curriculum that pick a class first.
  const allSubjectsQ = useSubjects(undefined, {
    fetchAllWhenUndefined: isTeacher,
  });

  const isLoading =
    allClassesQ.isLoading ||
    (isTeacher &&
      (teacherSubjectsQ.isLoading || allSubjectsQ.isLoading)) ||
    (isLearner && ownLevel.isLoading);

  const classes = useMemo<SchoolClass[]>(() => {
    const all = allClassesQ.data ?? [];
    if (isLearner) {
      // Learners only ever see their own enrolled class — prevents a
      // Class 10 student from poking into Class 12 material.
      if (ownLevel.classLevel === undefined) return [];
      return all.filter((c) => c.level === ownLevel.classLevel);
    }
    if (!isTeacher) return all;
    const allowedSubjectIds = new Set(teacherSubjectsQ.data?.subject_ids ?? []);
    if (allowedSubjectIds.size === 0) return [];
    const allowedClassIds = new Set(
      (allSubjectsQ.data ?? [])
        .filter((s) => allowedSubjectIds.has(s.id))
        .map((s) => s.class_id),
    );
    return all.filter((c) => allowedClassIds.has(c.id));
  }, [
    allClassesQ.data,
    teacherSubjectsQ.data,
    allSubjectsQ.data,
    isTeacher,
    isLearner,
    ownLevel.classLevel,
  ]);

  return { classes, isLoading, isScoped: isTeacher || isLearner };
}

interface AvailableSubjects {
  subjects: Subject[];
  isLoading: boolean;
  /** True when the user is naturally scoped (i.e. teacher). */
  isScoped: boolean;
}

/**
 * Subjects in `classLevel` that the viewer is allowed to see.
 *
 * - Teacher: intersection of all-subjects-in-class with their assignment
 *   list (or fallback) from `/me/teacher-subjects`.
 * - Other roles: every subject of that class, unfiltered.
 *
 * Pass `classLevel = undefined` to get *all* assigned subjects across every
 * class (used by the Manage School "Subjects taught" preview).
 */
export function useAvailableSubjects(
  classLevel: number | undefined,
): AvailableSubjects {
  const { user } = useAuth();
  const isTeacher = user?.role === "teacher";
  const subjectsQ = useSubjects(classLevel);
  const teacherSubjectsQ = useMyTeacherSubjects(isTeacher);

  const isLoading =
    subjectsQ.isLoading || (isTeacher && teacherSubjectsQ.isLoading);

  const subjects = useMemo<Subject[]>(() => {
    const all = subjectsQ.data ?? [];
    if (!isTeacher) return all;
    const allowed = new Set(teacherSubjectsQ.data?.subject_ids ?? []);
    return all.filter((s) => allowed.has(s.id));
  }, [subjectsQ.data, teacherSubjectsQ.data, isTeacher]);

  return { subjects, isLoading, isScoped: isTeacher };
}
