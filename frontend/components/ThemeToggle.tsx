"use client";

import { useEffect, useState } from "react";

type Mode = "system" | "light" | "dark";
const NEXT: Record<Mode, Mode> = { system: "light", light: "dark", dark: "system" };
const LABEL: Record<Mode, string> = { system: "auto", light: "paper", dark: "night" };

/** Paper by day, instrument panel by night. Third state follows the OS. */
export default function ThemeToggle() {
  const [mode, setMode] = useState<Mode>("system");

  useEffect(() => {
    const stored = (localStorage.getItem("plnews-theme") as Mode | null) ?? "system";
    setMode(stored);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (mode === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", mode);
    localStorage.setItem("plnews-theme", mode);
  }, [mode]);

  return (
    <button className="chip" onClick={() => setMode(NEXT[mode])} title="Switch appearance">
      {LABEL[mode]}
    </button>
  );
}
