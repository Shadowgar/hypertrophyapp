import type { WorkoutExercise } from "@/lib/api";

export function authoredRelationshipLabels(exercise: Pick<WorkoutExercise, "source_relationships">): string[] {
  return (exercise.source_relationships ?? []).flatMap((relation) => {
    if (relation.kind === "superset") return [`Superset ${relation.role}`];
    if (relation.kind === "primer") return [relation.role === "primer" ? "Primer for next exercise" : "Follows primer"];
    return [];
  });
}
