"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import Link from "next/link";
import { accountScope } from "@/lib/appearance";
import { clearAuthToken } from "@/lib/api";
const links = [
  ["/", "Home"],
  ["/today", "Today"],
  ["/week", "Week"],
  ["/history", "History"],
  ["/history#analytics", "Analytics"],
  ["/programs", "Programs"],
  ["/checkin", "Check-In"],
  ["/guides", "Library"],
  ["/settings", "Settings"],
];

const PUBLIC_ROUTES = new Set([
  "/",
  "/login",
  "/onboarding",
  "/reset-password",
]);
const AUTH_TOKEN_EVENT = "hypertrophy:auth-token-changed";

function isPublicRoute(pathname: string): boolean {
  if (PUBLIC_ROUTES.has(pathname)) {
    return true;
  }
  return false;
}

export function AppShell({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();

  const [hydrated, setHydrated] = useState(false);
  const [token, setToken] = useState<string | null>(null);

  const publicRoute = useMemo(() => isPublicRoute(pathname), [pathname]);

  useEffect(() => {
    const syncToken = () => {
      setToken(localStorage.getItem("hypertrophy_token"));
    };

    syncToken();
    setHydrated(true);

    const onStorage = () => syncToken();
    const onFocus = () => syncToken();

    globalThis.addEventListener("storage", onStorage);
    globalThis.addEventListener("focus", onFocus);
    globalThis.addEventListener(AUTH_TOKEN_EVENT, onStorage);

    // Remove stale PWA workers to avoid serving outdated client bundles.
    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker.getRegistrations().then((registrations) => {
        registrations.forEach((registration) => {
          void registration.unregister();
        });
      });
      if ("caches" in globalThis) {
        void caches.keys().then((keys) => {
          keys.forEach((key) => {
            void caches.delete(key);
          });
        });
      }
    }

    return () => {
      globalThis.removeEventListener("storage", onStorage);
      globalThis.removeEventListener("focus", onFocus);
      globalThis.removeEventListener(AUTH_TOKEN_EVENT, onStorage);
    };
  }, []);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    if (!publicRoute && !token) {
      router.replace(
        `/login?next=${encodeURIComponent(`${pathname}${window.location.search}${window.location.hash}`)}`,
      );
    }
  }, [hydrated, pathname, publicRoute, router, token]);

  if (!hydrated) {
    return (
      <main className="ux-main" role="status">
        Loading WorkoutApp…
      </main>
    );
  }

  if (!publicRoute && !token) {
    return (
      <main className="motion-page-enter p-4">
        <div className="main-card main-card--module">
          <p className="telemetry-kicker">Authentication Required</p>
          <p className="telemetry-value">Redirecting to login...</p>
        </div>
      </main>
    );
  }

  return (
    <div className={token ? "ux-shell-auth" : "ux-shell-public"}>
      <a className="ux-skip" href="#main-content">
        Skip to content
      </a>
      {token ? (
        <nav className="ux-sidebar" aria-label="Main navigation">
          <Link className="ux-brand" href="/">
            WorkoutApp
          </Link>
          {links.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              aria-current={pathname === href ? "page" : undefined}
            >
              {label}
            </Link>
          ))}
          <button
            className="ux-button ux-button-ghost mt-auto"
            onClick={() => {
              clearAuthToken();
              router.replace("/login");
            }}
          >
            Sign out
          </button>
        </nav>
      ) : null}
      <header className="ux-header">
        <Link href="/" className="ux-brand">
          WorkoutApp
        </Link>
        {token ? (
          <Link href="/settings">Account</Link>
        ) : (
          <Link href="/login">Sign in</Link>
        )}
      </header>
      <main
        id="main-content"
        className="ux-main"
        key={accountScope(token) ?? "guest"}
      >
        {children}
      </main>
      {token ? (
        <nav className="ux-mobile-nav" aria-label="Main navigation">
          {[
            ["/", "Home"],
            ["/today", "Today"],
            ["/week", "Week"],
            ["/history", "History"],
            ["/more", "More"],
          ].map(([href, label]) => (
            <Link
              key={href}
              href={href}
              aria-current={pathname === href ? "page" : undefined}
            >
              {label}
            </Link>
          ))}
        </nav>
      ) : null}
    </div>
  );
}
