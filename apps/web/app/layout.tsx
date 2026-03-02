import type { Metadata } from "next";
import "./globals.css";

import { MobileNav } from "@/components/mobile-nav";

export const metadata: Metadata = {
  title: "Rocco's HyperTrophy Plan",
  description: "Deterministic hypertrophy workout planner and runner",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className="mx-auto min-h-screen max-w-md pb-20">
        <main className="p-4">{children}</main>
        <MobileNav />
      </body>
    </html>
  );
}
