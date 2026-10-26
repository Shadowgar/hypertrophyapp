"use client";

import Link from "next/link";
import { useCallback } from "react";
import { api } from "@/lib/api";
import { useGuideResource } from "./guide-resource";
import { exerciseGuidePath, GuideReturnLinks, GuideShell, programGuidePath, ReadState, SourceDetails, type Crumb } from "./guide-ui";
import styles from "./guides.module.css";

export function ProgramGuide({ programId, view, phaseId }: { programId?: string; view: "program" | "phase" | "detail"; phaseId?: string }) {
  const valid = Boolean(programId) && (view !== "phase" || phaseId === "main");
  const load = useCallback(() => api.getProgramGuide(programId!), [programId]);
  const { resource, retry } = useGuideResource(valid ? JSON.stringify([view, programId, phaseId]) : null, load);
  const program = resource.status === "ready" ? resource.value : null;
  const base = programGuidePath(programId ?? "");
  const crumbs: Crumb[] = view === "phase" ? [{ label: "Program guide", href: base }, { label: "Main Phase" }] : [{ label: "Program guide" }];
  return <GuideShell title={view === "phase" ? "Phase guide" : "Program guide"} crumbs={crumbs}>
    <ReadState resource={resource} retry={retry} />
    {program ? <div className={styles.layout}><div className={styles.stack}>
      <header className={styles.header}><h2>{program.name}</h2>{program.description ? <p className={styles.muted}>{program.description}</p> : null}</header>
      {program.days.length === 0 ? <p>No days are available in this program guide.</p> : view === "program" ?
        <section className={styles.card}><h3>Main Phase</h3><p className={styles.muted}>Days in phase: {program.days.map((day) => day.day_index).sort((a, b) => a - b).join(", ")}</p>
          <Link className={styles.action} href={`${base}/phase/main`}>Open phase guide</Link>
        </section> : <>
          {view === "detail" ? <Link className={styles.action} href={`${base}/phase/main`}>Open phase guide</Link> : null}
          {program.days.map((day) => <section className={styles.card} key={day.day_index}>
            <h3>Day {day.day_index}: {day.day_name}</h3><p className={styles.muted}>{day.exercise_count} exercises</p>
            <div className={styles.actions}>
              <Link className={styles.action} href={`${base}/phase/main/day/${day.day_index}`}>Open day guide</Link>
              {day.first_exercise_id ? <Link className={styles.action} href={exerciseGuidePath(programId!, day.first_exercise_id, day.day_index, "main")}>Open first exercise</Link> : null}
            </div>
          </section>)}
        </>}
      <SourceDetails value={program} />
    </div><GuideReturnLinks /></div> : null}
  </GuideShell>;
}
