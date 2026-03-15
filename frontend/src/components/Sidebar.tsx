"use client";

import { useState } from "react";
import type { Entry, User } from "@/lib/api";
import { useTheme, palette } from "@/lib/theme";

interface Props {
  filter:          string;
  setFilter:       (f: any) => void;
  keywords:        string[];
  entries:         Entry[];
  user:            User;
  onAddKeyword:    (kw: string) => void;
  onRemoveKeyword: (kw: string) => void;
  onLogout:        () => void;
}

const ORIGIN_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  hackernews: { label: "Hacker News", color: "#f97316", icon: "▲" },
  reddit:     { label: "Reddit",      color: "#ef4444", icon: "◉" },
  github:     { label: "GitHub",      color: "#8b5cf6", icon: "◆" },
};

export default function Sidebar({
  filter, setFilter, keywords, entries, user, onAddKeyword, onRemoveKeyword, onLogout,
}: Props) {
  const { theme, toggle } = useTheme();
  const t = palette(theme);
  const [newKw, setNewKw] = useState("");

  const unread   = entries.filter(e => !e.is_read).length;
  const saved    = entries.filter(e => e.is_saved).length;
  const filtered = entries.filter(e => e.keywords.some(kw => keywords.includes(kw))).length;

  const NavItem = ({ id, label, icon, count, color }: {
    id: string; label: string; icon: string; count: number; color?: string;
  }) => {
    const active   = filter === id;
    const fg       = color ?? t.accent;
    return (
      <div
        onClick={() => setFilter(id)}
        style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "10px 18px", cursor: "pointer",
          background:  active ? (color ? `${color}12` : t.accentBg) : "transparent",
          borderLeft:  active ? `2px solid ${fg}` : "2px solid transparent",
          transition:  "background 0.12s",
        }}
      >
        <span style={{ fontSize: 12, color: active ? fg : t.textMuted, width: 14, textAlign: "center" }}>
          {icon}
        </span>
        <span style={{ fontSize: 14, color: active ? t.text : t.textSub, flex: 1, fontWeight: active ? 600 : 400 }}>
          {label}
        </span>
        <span style={{
          fontSize: 11, fontFamily: "monospace",
          color: active ? fg : t.textMuted,
          background: t.bgMeta,
          border: `1px solid ${t.border}`,
          padding: "1px 7px", borderRadius: 4,
          minWidth: 24, textAlign: "center",
        }}>
          {count}
        </span>
      </div>
    );
  };

  const handleAddKw = () => {
    const kw = newKw.trim().toLowerCase();
    if (!kw || keywords.includes(kw)) return;
    onAddKeyword(kw);
    setNewKw("");
  };

  return (
    <div style={{
      width: 290, flexShrink: 0,
      background: t.bgSidebar,
      borderRight: `1px solid ${t.border}`,
      display: "flex", flexDirection: "column",
      overflowY: "auto",
    }}>

      {/* Header / Logo */}
      <div style={{
        padding: "22px 18px 18px",
        borderBottom: `1px solid ${t.border}`,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div>
          <div style={{
            fontSize: 22, fontWeight: 800, letterSpacing: "-0.04em",
            color: t.text, lineHeight: 1,
          }}>
            Le<span style={{ color: t.accent }}>Fil</span>
          </div>
          <div style={{ fontSize: 11, color: t.textMuted, fontFamily: "monospace", marginTop: 3 }}>
            {user.username}
          </div>
        </div>
        <button
          onClick={toggle}
          title={theme === "dark" ? "Passer en mode clair" : "Passer en mode sombre"}
          style={{
            width: 34, height: 34, borderRadius: 8,
            background: t.bgMeta, border: `1px solid ${t.border}`,
            color: t.textSub, fontSize: 16, cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
        >
          {theme === "dark" ? "☀" : "☾"}
        </button>
      </div>

      {/* Vues */}
      <div style={{ paddingTop: 14 }}>
        <div style={{ fontSize: 10, color: t.textFaint, fontFamily: "monospace", letterSpacing: "0.13em", padding: "0 18px 6px" }}>
          VUES
        </div>
        <NavItem id="all"      label="Général"     icon="◈" count={entries.length} />
        <NavItem id="filtered" label="Mes sujets"  icon="◆" count={filtered} />
        <NavItem id="unread"   label="Non lus"     icon="●" count={unread} />
        <NavItem id="saved"    label="Sauvegardés" icon="⬟" count={saved} />
      </div>

      {/* Sources */}
      <div style={{ paddingTop: 18 }}>
        <div style={{ fontSize: 10, color: t.textFaint, fontFamily: "monospace", letterSpacing: "0.13em", padding: "0 18px 6px" }}>
          SOURCES
        </div>
        {Object.entries(ORIGIN_CONFIG).map(([src, cfg]) => (
          <NavItem
            key={src}
            id={src}
            label={cfg.label}
            icon={cfg.icon}
            count={entries.filter(e => e.origin === src).length}
            color={cfg.color}
          />
        ))}
      </div>

      {/* Mots-clés */}
      <div style={{ flex: 1, paddingTop: 18 }}>
        <div style={{ fontSize: 10, color: t.textFaint, fontFamily: "monospace", letterSpacing: "0.13em", padding: "0 18px 10px" }}>
          MES SUJETS
        </div>

        <div style={{ padding: "0 14px", marginBottom: 10, display: "flex", gap: 6 }}>
          <input
            value={newKw}
            onChange={e => setNewKw(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleAddKw()}
            placeholder="Ajouter un sujet..."
            style={{
              flex: 1, padding: "8px 10px",
              background: t.bgInput,
              border: `1px solid ${t.border}`, borderRadius: 6,
              color: t.text, fontSize: 13, fontFamily: "inherit", outline: "none",
            }}
          />
          <button
            onClick={handleAddKw}
            style={{
              padding: "8px 12px",
              background: t.accentBg, border: `1px solid ${t.accentBorder}`,
              borderRadius: 6, color: t.accent, fontSize: 18, lineHeight: 1,
            }}
          >
            +
          </button>
        </div>

        <div style={{ padding: "0 14px", display: "flex", flexWrap: "wrap", gap: 6 }}>
          {keywords.map(kw => (
            <span
              key={kw}
              onClick={() => onRemoveKeyword(kw)}
              title="Cliquer pour supprimer"
              style={{
                fontSize: 12, fontFamily: "monospace",
                padding: "4px 9px", borderRadius: 5,
                background: t.accentBg, color: t.accent,
                border: `1px solid ${t.accentBorder}`,
                cursor: "pointer", userSelect: "none",
              }}
            >
              {kw} ×
            </span>
          ))}
          {keywords.length === 0 && (
            <span style={{ fontSize: 12, color: t.textMuted, fontStyle: "italic" }}>
              Aucun sujet défini
            </span>
          )}
        </div>
      </div>

      {/* Logout */}
      <div style={{ padding: "14px" }}>
        <button
          onClick={onLogout}
          style={{
            width: "100%", padding: "10px",
            background: "transparent", border: `1px solid ${t.border}`, borderRadius: 7,
            color: t.textMuted, fontSize: 13, fontFamily: "inherit", cursor: "pointer",
          }}
        >
          Déconnexion
        </button>
      </div>
    </div>
  );
}
