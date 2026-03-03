"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { cn } from "@/lib/utils";

const items = [
  { href: "/today", label: "Workout", icon: "◉" },
  { href: "/week", label: "Plan", icon: "◈" },
  { href: "/history", label: "Analytics", icon: "▤" },
  { href: "/checkin", label: "Body", icon: "◎" },
  { href: "/settings", label: "Settings", icon: "⌬" },
];

function resolveMode(pathname: string): "workout" | "plan" | "analytics" | "body" | "system" {
  if (pathname.startsWith("/today")) return "workout";
  if (pathname.startsWith("/week") || pathname.startsWith("/guides") || pathname.startsWith("/programs")) return "plan";
  if (pathname.startsWith("/history")) return "analytics";
  if (pathname.startsWith("/checkin")) return "body";
  return "system";
}

export function MobileNav() {
  const pathname = usePathname();
  const mode = resolveMode(pathname);

  useEffect(() => {
    document.body.dataset.uiMode = mode;
  }, [mode]);

  return (
    <nav className="command-dock-wrap fixed bottom-0 left-0 right-0 p-3">
      <ul className="command-dock mx-auto grid max-w-md grid-cols-5 gap-1">
        {items.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              title={item.label}
              className={cn(
                "dock-btn block rounded-md px-2 py-2 text-center",
                pathname === item.href ? "dock-btn--active" : "dock-btn--idle"
              )}
            >
              <span aria-hidden="true" className="text-base leading-none">{item.icon}</span>
              <span className="sr-only">{item.label}</span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
