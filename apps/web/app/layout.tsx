import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./appearances.css";
import "./unified.css";
import localFont from "next/font/local";
import { AppearanceProvider } from "@/components/appearance-provider";
const dmSans = localFont({
  src: "./fonts/DM-Sans.ttf",
  weight: "100 1000",
  display: "swap",
  variable: "--font-dm-sans",
});

import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: "FERRAVIS — Strength, Engineered.",
  applicationName: "FERRAVIS",
  description: "Personal strength and hypertrophy training. Plan, train and follow your progress with FERRAVIS.",
  manifest: "/manifest.json",
  icons: {
    icon: [{ url: "/ferravis-mark.svg", type: "image/svg+xml" }, { url: "/favicon-32.png", type: "image/png", sizes: "32x32" }],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  appleWebApp: { capable: true, title: "FERRAVIS", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  width: "device-width", initialScale: 1, viewportFit: "cover",
  themeColor: "#171719",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      data-theme="classic"
      data-appearance="dark"
      className={dmSans.variable}
      suppressHydrationWarning
    >
      <body>
        <AppearanceProvider>
          <AppShell>{children}</AppShell>
        </AppearanceProvider>
      </body>
    </html>
  );
}
