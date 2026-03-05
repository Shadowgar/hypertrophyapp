"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { MobileNav } from "@/components/mobile-nav";

const PUBLIC_ROUTES = new Set(["/", "/login", "/onboarding", "/reset-password"]);

function isPublicRoute(pathname: string): boolean {
  if (PUBLIC_ROUTES.has(pathname)) {
    return true;
  }
  return false;
}

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
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
    };
  }, []);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    if (!publicRoute && !token) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [hydrated, pathname, publicRoute, router, token]);

  if (!hydrated) {
    return <main className="motion-page-enter p-4" />;
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
    <>
      <main className="motion-page-enter p-4">{children}</main>
      {token && !publicRoute ? <MobileNav /> : null}
    </>
  );
}
