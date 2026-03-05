import type { Metadata } from "next";
import "./globals.css";

import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: "Rocco's HyperTrophy Plan",
  description: "Deterministic hypertrophy workout planner and runner",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className="hyperdrive-body mx-auto min-h-screen max-w-md pb-24">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
