"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const items = [
  { href: "/today", label: "Today" },
  { href: "/week", label: "Week" },
  { href: "/checkin", label: "Check-In" },
  { href: "/history", label: "History" },
  { href: "/settings", label: "Settings" },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 border-t border-zinc-800 bg-black/95 p-2">
      <ul className="mx-auto grid max-w-md grid-cols-5 gap-1">
        {items.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              className={cn(
                "block rounded-md px-2 py-2 text-center text-xs",
                pathname === item.href ? "bg-accent text-white" : "text-zinc-300"
              )}
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
