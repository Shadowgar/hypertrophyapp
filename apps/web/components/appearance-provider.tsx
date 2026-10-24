"use client";
import { createContext, useContext, useEffect, useRef, useState } from "react";
import { api, getToken, type InterfacePreferences } from "@/lib/api";
import {
  accountScope,
  defaultPreferences,
  resolvedAppearance,
} from "@/lib/appearance";

type Values = Omit<InterfacePreferences, "revision">;
type Context = {
  preferences: InterfacePreferences;
  ready: boolean;
  error: string;
  reload: () => Promise<void>;
  save: (values: Values, revision: number) => Promise<void>;
  preview: (values: Values | null) => void;
};
const AppearanceContext = createContext<Context>({
  preferences: defaultPreferences,
  ready: false,
  error: "",
  reload: async () => {},
  save: async () => {},
  preview: () => {},
});
export const useAppearance = () => useContext(AppearanceContext);

export function AppearanceProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [preferences, setPreferences] = useState(defaultPreferences);
  const [preview, setPreview] = useState<Values | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [deviceDark, setDeviceDark] = useState(true);
  const generation = useRef(0);
  const identity = useRef<string | null>(null);
  async function reload() {
    const version = ++generation.current;
    const token = getToken();
    const account = accountScope(token);
    if (identity.current !== account) {
      setPreferences(defaultPreferences);
      setPreview(null);
      identity.current = account;
    }
    if (!token) {
      setReady(false);
      setError("");
      return;
    }
    setReady(false);
    setError("");
    try {
      const result = await api.getInterfacePreferences();
      if (version !== generation.current || getToken() !== token) return;
      setPreferences(result);
      setReady(true);
    } catch {
      if (version === generation.current)
        setError(
          "Saved appearance could not be loaded. Retry before changing it.",
        );
    }
  }
  useEffect(() => {
    void reload();
    const sync = () => void reload();
    window.addEventListener("hypertrophy:auth-token-changed", sync);
    const storageSync = (event: StorageEvent) => {
      if (event.key === "hypertrophy_token" || event.key === null)
        void reload();
    };
    window.addEventListener("storage", storageSync);
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const change = () => setDeviceDark(media.matches);
    change();
    media.addEventListener("change", change);
    return () => {
      ++generation.current;
      window.removeEventListener("hypertrophy:auth-token-changed", sync);
      window.removeEventListener("storage", storageSync);
      media.removeEventListener("change", change);
    };
  }, []);
  const shown = preview ?? preferences;
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = shown.theme_family;
    root.dataset.appearance = resolvedAppearance(shown.appearance, deviceDark);
    root.style.colorScheme = root.dataset.appearance;
  }, [shown.theme_family, shown.appearance, deviceDark]);
  async function save(values: Values, revision: number) {
    const token = getToken();
    const version = generation.current;
    const result = await api.saveInterfacePreferences({
      theme_family: values.theme_family,
      appearance: values.appearance,
      weight_unit: values.weight_unit,
      expected_revision: revision,
    });
    if (version !== generation.current || token !== getToken())
      throw new Error("Account changed. Reload saved preferences.");
    setPreferences(result);
    setPreview(null);
    setReady(true);
  }
  return (
    <AppearanceContext.Provider
      value={{ preferences, ready, error, reload, save, preview: setPreview }}
    >
      {children}
    </AppearanceContext.Provider>
  );
}
