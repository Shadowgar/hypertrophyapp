export type WorkloadMode = "flexible" | "authored" | "customized" | "unknown";

/** Only these response identities establish Authored source authority. */
export function workloadMode(programId: string | null | undefined, customized = false): WorkloadMode {
  if (customized) return "customized";
  if (programId === "pure_bodybuilding_phase_1_full_body" || programId === "pure_bodybuilding_phase_2_full_body") return "authored";
  if (programId === "full_body_v1" || programId === "customized_full_body_v1") return "customized";
  return "unknown";
}

type WorkoutWorkloadProps = {
  exercises: Array<{ sets: number }>;
  timeBudgetMinutes?: number | null;
  mode?: WorkloadMode;
};

/** Factual planned dose and time uncertainty; this is not a duration estimator. */
export function WorkoutWorkload({ exercises, timeBudgetMinutes, mode = "unknown" }: WorkoutWorkloadProps) {
  const workingSets = exercises.reduce((total, exercise) => total + exercise.sets, 0);
  const hasTimeGoal = typeof timeBudgetMinutes === "number" && Number.isFinite(timeBudgetMinutes) && timeBudgetMinutes > 0;

  const goalLabel = hasTimeGoal ? `Your session-time goal: ${timeBudgetMinutes} minutes.`
    : timeBudgetMinutes === null ? "No session-time goal saved." : "Session-time goal unavailable.";

  return <div className="space-y-2 rounded-md border border-amber-600/40 p-3 text-sm" aria-label="Workout workload and time">
    <p className="font-semibold">{exercises.length} {exercises.length === 1 ? "exercise" : "exercises"} · {workingSets} planned working sets</p>
    <p>{goalLabel} Duration is unknown; these counts are not a calibrated time estimate.</p>
    <p className="text-amber-300">Review this workload before starting: it may exceed your available time.</p>
    {mode === "flexible" ? <><p>Pause and Resume the same source workout across days. Its original exercises and sets stay intact; expected frequency does not regroup them.</p><p>Finish requires all required working sets. End Early records the exact missing work as incomplete before advancing.</p></> : mode === "authored" ? <>
      <p>Before starting any workout this week, review more selected visits to spread all source exercises and working sets while preserving their order and relationships.</p>
      <p><a className="underline" href="/week">Review 2–5 selected visits in Week</a>. Preview and confirm a feasible placement before it replaces your schedule.</p>
      <p className="text-xs text-zinc-400">This option cannot split a started workout or carry unfinished work into another week.</p>
    </> : mode === "customized" ? <p><a className="underline" href="/customize">Review Customized planning</a> for date changes or an explicitly confirmed replacement.</p>
      : <p><a className="underline" href="/week">Review your saved plan in Week</a> before choosing how to change dates or replace a program.</p>}
  </div>;
}
