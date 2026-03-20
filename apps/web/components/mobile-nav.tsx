"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { UiIcon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

const items = [
  { href: "/today", label: "Workout", icon: "workout" as const },
  { href: "/week", label: "Plan", icon: "plan" as const },
  { href: "/history", label: "Analytics", icon: "analytics" as const },
  { href: "/checkin", label: "Check-In", icon: "body" as const },
  { href: "/settings", label: "Settings", icon: "settings" as const },
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
  const [todayOverlayOpen, setTodayOverlayOpen] = useState(false);

  useEffect(() => {
    document.body.dataset.uiMode = mode;
  }, [mode]);

  useEffect(() => {
    const syncOverlayState = () => {
      setTodayOverlayOpen(document.body.dataset.todayOverlayOpen === "true");
    };
    syncOverlayState();
    globalThis.addEventListener("hypertrophy:today-overlay-changed", syncOverlayState);
    return () => {
      globalThis.removeEventListener("hypertrophy:today-overlay-changed", syncOverlayState);
    };
  }, []);

  const suppressDock = pathname.startsWith("/today") && todayOverlayOpen;

  return (
    <nav
      className={cn(
        "command-dock-wrap fixed bottom-0 left-0 right-0 p-3",
        suppressDock ? "pointer-events-none opacity-0" : "",
      )}
      aria-hidden={suppressDock}
    >
      <ul className="command-dock mx-auto grid max-w-md grid-cols-5 gap-1">
        {items.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              title={item.label}
              className={cn(
                "dock-btn flex min-h-11 flex-col items-center justify-center gap-0.5 rounded-md px-2 py-1.5 text-center",
                pathname === item.href ? "dock-btn--active" : "dock-btn--idle"
              )}
            >
              <UiIcon name={item.icon} className="ui-icon--nav" />
              <span className="text-[10px] leading-none tracking-wide">{item.label}</span>
            </Link>
          </li>
        ))}
      </ul>
      <p className="mx-auto mt-1.5 max-w-md text-center text-[10px] leading-none tracking-wider text-zinc-500">
        {process.env.NEXT_PUBLIC_APP_VERSION ?? "dev"}
      </p>
    </nav>
  );
}
