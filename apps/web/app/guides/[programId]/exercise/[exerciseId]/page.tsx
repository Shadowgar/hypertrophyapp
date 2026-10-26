"use client";

import Link from "next/link";
import { Suspense, useCallback } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useGuideResource } from "@/app/guides/guide-resource";
import { GuideReturnLinks, GuideShell, programGuidePath, ReadState, SourceDetails, type Crumb } from "@/app/guides/guide-ui";
import styles from "@/app/guides/guides.module.css";

function safeVideoUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try { const url = new URL(value); return url.protocol === "https:" || url.protocol === "http:" ? value : null; } catch { return null; }
}
function ExerciseGuide() {
  const params = useParams();
  const search = useSearchParams();
  const programId = params?.programId as string | undefined;
  const exerciseId = params?.exerciseId as string | undefined;
  const dayIndex = Number(search.get("day"));
  const phaseId = search.get("phase");
  const hasDay = Number.isSafeInteger(dayIndex) && dayIndex > 0 && (!phaseId || phaseId === "main");
  const load = useCallback(() => api.getProgramExerciseGuide(programId!, exerciseId!), [programId, exerciseId]);
  const { resource, retry } = useGuideResource(programId && exerciseId ? JSON.stringify([programId, exerciseId]) : null, load);
  const detail = resource.status === "ready" ? resource.value : null;
  const exercise = detail?.exercise;
  const base = programGuidePath(programId ?? "");
  const crumbs: Crumb[] = [{ label: "Program guide", href: base }, { label: "Main Phase", href: `${base}/phase/main` }];
  if (hasDay) crumbs.push({ label: `Day ${dayIndex}`, href: `${base}${phaseId === "main" ? "/phase/main" : ""}/day/${dayIndex}` });
  crumbs.push({ label: "Exercise" });
  const videoUrl = safeVideoUrl(exercise?.video_youtube_url);
  return <GuideShell title="Exercise guide" crumbs={crumbs}>
    <ReadState resource={resource} retry={retry} />
    {exercise ? <div className={styles.layout}><div className={styles.stack}>
      <h2>{exercise.name}</h2>
      <section className={styles.card} aria-labelledby="technique-heading"><h3 id="technique-heading">Technique &amp; setup</h3>
        {exercise.notes ? <p className={styles.instructions}>{exercise.notes}</p> : <p className={styles.muted}>No technique instructions are provided in this guide.</p>}
        {videoUrl ? <a className={styles.action} href={videoUrl} target="_blank" rel="noopener noreferrer">Watch source video <span className={styles.muted}>(opens a new tab)</span></a> : null}
      </section>
      <p className={styles.muted}>This is a program reference. Use Today for the prescription in your scheduled workout.</p>
      <SourceDetails value={detail} />
      <Link href="/today" className={`${styles.action} ${styles.primary}`}>Return to workout</Link>
    </div><GuideReturnLinks workout={false} /></div> : resource.status === "ready" ? <p>No exercise details are available in this guide.</p> : null}
  </GuideShell>;
}
export default function ExerciseGuidePage() {
  return <Suspense fallback={<p role="status">Loading exercise guide…</p>}><ExerciseGuide /></Suspense>;
}
