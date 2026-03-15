"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

type Theme = "dark" | "light";
interface ThemeCtx { theme: Theme; toggle: () => void; }
const Ctx = createContext<ThemeCtx>({ theme: "dark", toggle: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("dark");
  useEffect(() => {
    const stored = localStorage.getItem("lefil-theme") as Theme | null;
    if (stored) setTheme(stored);
  }, []);
  const toggle = () => setTheme(t => {
    const next = t === "dark" ? "light" : "dark";
    localStorage.setItem("lefil-theme", next);
    return next;
  });
  return <Ctx.Provider value={{ theme, toggle }}>{children}</Ctx.Provider>;
}

export const useTheme = () => useContext(Ctx);

export function palette(theme: Theme) {
  if (theme === "dark") return {
    bg:            "#07070b",
    bgSidebar:     "#050508",
    bgCard:        "rgba(255,255,255,0.028)",
    bgCardRead:    "transparent",
    bgCardSelect:  "rgba(255,255,255,0.065)",
    bgInput:       "rgba(255,255,255,0.05)",
    bgMeta:        "rgba(255,255,255,0.04)",
    bgDetail:      "rgba(255,255,255,0.03)",
    border:        "rgba(255,255,255,0.08)",
    borderSelect:  "rgba(255,255,255,0.16)",
    text:          "#f0f0f4",
    textSub:       "#9ca3af",
    textMuted:     "#4b5563",
    textFaint:     "#9ca3af",
    accent:        "#fbbf24",
    accentBg:      "rgba(251,191,36,0.1)",
    accentBorder:  "rgba(251,191,36,0.28)",
    saved:         "#8b5cf6",
    unread:        "#3b82f6",
    open:          "#10b981",
    kwBg:          "rgba(255,255,255,0.06)",
    kwBorder:      "rgba(255,255,255,0.09)",
    kwColor:       "#6b7280",
  };
  return {
    bg:            "#f5f4f0",
    bgSidebar:     "#edece7",
    bgCard:        "#ffffff",
    bgCardRead:    "#fafaf8",
    bgCardSelect:  "#fffdf5",
    bgInput:       "#ffffff",
    bgMeta:        "#f0efe9",
    bgDetail:      "#f7f6f1",
    border:        "rgba(0,0,0,0.09)",
    borderSelect:  "rgba(0,0,0,0.18)",
    text:          "#1a1a22",
    textSub:       "#52525b",
    textMuted:     "#a1a1aa",
    textFaint:     "#52525b",
    accent:        "#d97706",
    accentBg:      "rgba(217,119,6,0.09)",
    accentBorder:  "rgba(217,119,6,0.28)",
    saved:         "#7c3aed",
    unread:        "#2563eb",
    open:          "#059669",
    kwBg:          "rgba(0,0,0,0.05)",
    kwBorder:      "rgba(0,0,0,0.09)",
    kwColor:       "#71717a",
  };
}
