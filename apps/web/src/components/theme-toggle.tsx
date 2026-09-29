"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

type Theme = "dark" | "light";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => typeof document === "undefined" ? "dark" : (document.documentElement.dataset.theme as Theme) || "dark");

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const saved = localStorage.getItem("satquery-theme") as Theme | null;
      const initial = saved ?? (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
      setTheme(initial);
      document.documentElement.dataset.theme = initial;
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    localStorage.setItem("satquery-theme", next);
  }

  return (
    <button className="theme-toggle" type="button" onClick={toggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
      {theme === "dark" ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
      <span>{theme === "dark" ? "Light" : "Dark"}</span>
    </button>
  );
}
