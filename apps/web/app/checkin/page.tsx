"use client";
import Link from "next/link";
import { useState } from "react";
import { CheckinEntry } from "@/components/checkin-entry";
import WeeklyReview from "@/components/weekly-review";

export default function CheckinPage() {
  const [openedReview, setOpenedReview] = useState(false);
  return <div className="ux-page-stack">
    <header><p className="ux-eyebrow">Check-In</p><h1>How has your week been?</h1><p className="ux-muted">A short, optional record of what happened. Your workout is ready whenever you are.</p></header>
    <div className="ux-content-grid"><CheckinEntry /><aside className="ux-card space-y-3"><h2>Your next session</h2><p>Check-in does not change your selected dates or replace your program.</p><Link className="ux-button ux-button-secondary px-4" href="/week">Review your training week</Link><p className="ux-muted">Unreported sleep, stress, nutrition and recovery remain unknown.</p></aside></div>
    <details className="ux-card" onToggle={event => { if (event.currentTarget.open) setOpenedReview(true); }}><summary className="min-h-11 cursor-pointer py-2">Detailed weekly review and nutrition targets</summary>{openedReview ? <WeeklyReview /> : null}</details>
  </div>;
}
