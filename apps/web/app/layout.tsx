import type { Metadata } from "next";
import "./globals.css";
import "./appearances.css";
import "./unified.css";
import localFont from "next/font/local";
import { AppearanceProvider } from "@/components/appearance-provider";
const dmSans = localFont({src:"./fonts/DM-Sans.ttf",weight:"100 1000",display:"swap",variable:"--font-dm-sans"});

import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: "WorkoutApp",
  description: "Deterministic hypertrophy workout planner and runner",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="classic" data-appearance="dark" className={dmSans.variable} suppressHydrationWarning>
      <body>
        <AppearanceProvider><AppShell>{children}</AppShell></AppearanceProvider>
      </body>
    </html>
  );
}
