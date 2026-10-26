import type { ReactNode } from 'react';
import styles from './setup-flow.module.css';

export { styles as setupStyles };

export function SetupCard({ title, children }: { title: string; children: ReactNode }) {
  return <section className={styles.card}><h2>{title}</h2>{children}</section>;
}

export function SetupFlow({ title, subtitle, eyebrow = 'Account', aside, children }: {
  title: string; subtitle: string; eyebrow?: string; aside?: ReactNode; children: ReactNode;
}) {
  return <div className={styles.page}>
    <section className={styles.content}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>{eyebrow}</p>
        <h1>{title}</h1>
        <p className={styles.subtitle}>{subtitle}</p>
      </header>
      {children}
    </section>
    <aside className={styles.aside} aria-label="Setup information">
      <SetupCard title="WorkoutApp"><p>Your setup</p></SetupCard>
      {aside}
    </aside>
  </div>;
}
