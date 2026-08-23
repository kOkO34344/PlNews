"use client";

import { LOCALES } from "@/lib/i18n";
import { useLocale } from "./LocaleContext";

export default function LocaleToggle() {
  const { locale, setLocale } = useLocale();
  return (
    <div className="langswitch" role="group" aria-label="Language / Език">
      {LOCALES.map((l) => (
        <button
          key={l.code}
          className="chip"
          aria-pressed={locale === l.code}
          onClick={() => setLocale(l.code)}
          title={l.label}
        >
          {l.short}
        </button>
      ))}
    </div>
  );
}
