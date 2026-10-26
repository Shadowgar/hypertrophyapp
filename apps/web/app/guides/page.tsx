"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useGuideResource } from "./guide-resource";
import { GuideReturnLinks, GuideShell, programGuidePath, ReadState } from "./guide-ui";
import styles from "./guides.module.css";

export default function GuidesIndex() {
  const { resource, retry } = useGuideResource("program-library", api.listGuidePrograms);
  return <GuideShell title="Program library">
    <p className={styles.muted}>Find program instructions and exercise guides.</p>
    <div className={styles.layout}><section className={styles.stack} aria-label="Available program guides">
      <ReadState resource={resource} retry={retry} label="program guides" />
      {resource.status === "ready" ? resource.value.length ? resource.value.map((program) =>
        <Link key={program.id} href={programGuidePath(program.id)} className={`${styles.card} ${styles.cardLink}`} aria-label={`Open guide for ${program.name}`}>
          <div className={styles.cardTitle}><h2>{program.name}</h2><span aria-hidden="true">›</span></div>
          {program.description ? <p className={styles.muted}>{program.description}</p> : <p className={styles.muted}>Read the program guide</p>}
        </Link>) : <p>No program guides are currently available. Try refreshing the library.</p> : null}
    </section><GuideReturnLinks /></div>
  </GuideShell>;
}
