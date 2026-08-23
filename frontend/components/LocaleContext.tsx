"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  CATEGORIES, CLAIMS, DATE_LOCALE, DIMENSIONS, DIRECTIONS, LEANS, translate, type Locale,
} from "@/lib/i18n";

type Ctx = {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
  dimension: (key: string) => string;
  direction: (value: number) => string;
  claim: (key: string) => string;
  category: (key: string) => string;
  lean: (key: string) => string;
  formatDate: (iso: string, opts?: Intl.DateTimeFormatOptions) => string;
};

const LocaleCtx = createContext<Ctx | null>(null);
const STORAGE_KEY = "plnews-locale";

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "bg" || stored === "en") setLocaleState(stored);
    } catch {
      // Private windows and blocked site data both throw here; English is a fine default.
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    try {
      localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* not worth failing the toggle over */
    }
  }, []);

  const value = useMemo<Ctx>(
    () => ({
      locale,
      setLocale,
      t: (key, vars) => translate(locale, key, vars),
      dimension: (key) => DIMENSIONS[locale][key] ?? key.replace(/_/g, " "),
      direction: (value) => DIRECTIONS[locale][Math.round(value)] ?? DIRECTIONS[locale][0],
      claim: (key) => CLAIMS[locale][key] ?? key,
      category: (key) => CATEGORIES[locale][key] ?? key,
      lean: (key) => LEANS[locale][key] ?? "?",
      formatDate: (iso, opts) =>
        new Date(iso).toLocaleDateString(DATE_LOCALE[locale], opts ?? {
          weekday: "long", day: "numeric", month: "long", year: "numeric",
        }),
    }),
    [locale, setLocale],
  );

  return <LocaleCtx.Provider value={value}>{children}</LocaleCtx.Provider>;
}

export function useLocale(): Ctx {
  const ctx = useContext(LocaleCtx);
  if (!ctx) throw new Error("useLocale must be used inside <LocaleProvider>");
  return ctx;
}
