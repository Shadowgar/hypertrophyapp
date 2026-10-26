import Link from "next/link";
import type { ReactNode } from "react";
import type { GuideResource } from "./guide-resource";
import styles from "./guides.module.css";

export const programGuidePath = (id: string) => `/guides/${encodeURIComponent(id)}`;
export const exerciseGuidePath = (programId: string, exerciseId: string, dayIndex: number, phaseId?: string) =>
  `${programGuidePath(programId)}/exercise/${encodeURIComponent(exerciseId)}?day=${dayIndex}${phaseId ? `&phase=${encodeURIComponent(phaseId)}` : ""}`;
export type Crumb = { label: string; href?: string };
export function GuideShell({ title, crumbs = [], children }: { title: string; crumbs?: Crumb[]; children: ReactNode }) {
  return <div className={styles.page}>
    <header className={styles.header}>
      <p className={styles.muted}>Library</p><h1>{title}</h1>
      <nav aria-label="Guide breadcrumbs"><ol className={styles.breadcrumbs}>
        <li><Link href="/guides">Program library</Link></li>
        {crumbs.map((crumb, index) => <li key={`${crumb.label}-${index}`}><span aria-hidden="true">›</span>{crumb.href ? <Link href={crumb.href}>{crumb.label}</Link> : <span aria-current="page">{crumb.label}</span>}</li>)}
      </ol></nav>
    </header>{children}
  </div>;
}
export function ReadState({ resource, retry, label = "guide" }: { resource: GuideResource<unknown>; retry: () => void; label?: string }) {
  return <div className={styles.stack}>
    <div role="status" aria-live="polite" className={styles.status}>
      {resource.status === "loading" ? `Loading ${label}…` : resource.status === "error" ? `Could not load ${label}. Please try again.` : resource.status === "not-found" ? "Guide not found. Return to the library to choose an available guide." : resource.status === "unauthorized" ? "This guide could not be accessed. Sign in or try again." : null}
    </div>
    <div className={styles.actions}>
      <button className={styles.action} aria-disabled={resource.status === "loading"} onClick={retry}>{resource.status === "error" || resource.status === "unauthorized" ? `Retry ${label}` : `Refresh ${label}`}</button>
      {resource.status === "unauthorized" ? <Link className={styles.action} href="/login?next=%2Fguides">Sign in</Link> : null}
    </div>
  </div>;
}
export function SourceDetails({ value }: { value: unknown }) {
  return <details className={styles.source}><summary>Source &amp; technical details</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>;
}
export function GuideReturnLinks({ workout = true }: { workout?: boolean }) {
  return <aside className={styles.stack}>
    {workout ? <Link href="/today" className={`${styles.card} ${styles.cardLink}`}><h2>Return to workout</h2><p className={styles.muted}>Open Today for your scheduled workout and its prescription.</p></Link> : null}
    <Link href="/programs" className={`${styles.card} ${styles.cardLink}`}><h2>Explore programs</h2><p className={styles.muted}>Review your program choices.</p></Link>
  </aside>;
}
