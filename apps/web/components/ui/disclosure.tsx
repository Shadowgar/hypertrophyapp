"use client";

import { useState } from "react";

type Props = Readonly<{
  title: string;
  defaultOpen?: boolean;
  badge?: string | null;
  children: React.ReactNode;
}>;

export function Disclosure({ title, defaultOpen = false, badge, children }: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 overflow-hidden">
      <button
        type="button"
        className="flex min-h-[44px] w-full items-center justify-between gap-2 px-3 py-2.5 text-left text-sm font-medium text-zinc-200 transition-colors hover:bg-zinc-800/50"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          {title}
          {badge ? (
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] font-normal text-zinc-400">
              {badge}
            </span>
          ) : null}
        </span>
        <svg
          className={`h-4 w-4 flex-shrink-0 text-zinc-500 transition-transform duration-150 ${open ? "rotate-180" : ""}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>
      {open ? <div className="border-t border-zinc-800/60 px-3 pb-3 pt-2">{children}</div> : null}
    </div>
  );
}
