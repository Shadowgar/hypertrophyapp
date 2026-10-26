"use client";

import Link from "next/link";
import { useCallback } from "react";
import { api } from "@/lib/api";
import { useGuideResource } from "./guide-resource";
import { exerciseGuidePath, GuideReturnLinks, GuideShell, programGuidePath, ReadState, SourceDetails, type Crumb } from "./guide-ui";
import styles from "./guides.module.css";

export function DayGuide({ programId, dayParam, phaseId }: { programId?: string; dayParam?: string; phaseId?: string }) {
  const dayIndex = Number(dayParam);
  const valid = Boolean(programId) && Number.isSafeInteger(dayIndex) && dayIndex > 0 && (!phaseId || phaseId === "main");
  const load = useCallback(() => api.getProgramDayGuide(programId!, dayIndex), [programId, dayIndex]);
  const { resource, retry } = useGuideResource(valid ? JSON.stringify([programId, phaseId, dayIndex]) : null, load);
  const day = resource.status === "ready" ? resource.value : null;
  const base = programGuidePath(programId ?? "");
  const crumbs: Crumb[] = [{ label: "Program guide", href: base }, { label: "Main Phase", href: `${base}/phase/main` }, { label: `Day ${dayParam ?? "guide"}` }];
  return <GuideShell title="Day guide" crumbs={crumbs}>
    <ReadState resource={resource} retry={retry} />
    {day ? <div className={styles.layout}><div className={styles.stack}>
      <h2>Day {day.day_index}: {day.day_name}</h2>
      {day.exercises.length ? day.exercises.map((exercise) => <article className={styles.card} key={exercise.id}>
        <h3>{exercise.name}</h3>{exercise.notes ? <p className={styles.instructions}>{exercise.notes}</p> : null}
        <Link className={styles.action} href={exerciseGuidePath(programId!, exercise.primary_exercise_id ?? exercise.id, day.day_index, phaseId)}>Open exercise guide</Link>
      </article>) : <p>No exercises are available in this day guide.</p>}
      <SourceDetails value={day} />
    </div><GuideReturnLinks /></div> : null}
  </GuideShell>;
}
