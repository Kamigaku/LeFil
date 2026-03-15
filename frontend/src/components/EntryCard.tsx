"use client";

import type { Entry } from "@/lib/api";
import { useTheme, palette } from "@/lib/theme";

const ORIGIN_CONFIG: Record<string, { label: string; color: string }> = {
  hackernews: { label: "HN",     color: "#f97316" },
  reddit:     { label: "Reddit", color: "#ef4444" },
  github:     { label: "GitHub", color: "#8b5cf6" },
  rss:        { label: "RSS",    color: "#06b6d4" },
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3_600_000);
  const d = Math.floor(h / 24);
  if (d > 0) return `${d}j`;
  if (h > 0) return `${h}h`;
  return "now";
}

interface Props {
  entry:      Entry;
  keywords:   string[];
  isSelected: boolean;
  onClick:    () => void;
  onSave:     () => void;
  onHide:     () => void;
}

export default function EntryCard({ entry, keywords, isSelected, onClick, onSave, onHide }: Props) {
  const { theme } = useTheme();
  const t         = palette(theme);
  const origin    = ORIGIN_CONFIG[entry.origin] ?? { label: entry.origin, color: "#6b7280" };
  const hasUserKw = entry.keywords.some(kw => keywords.includes(kw));
  const score     = entry.sources[entry.origin]?.score;

  return (
    <div
      onClick={onClick}
      style={{
        background:   isSelected ? t.bgCardSelect : entry.is_read ? t.bgCardRead : t.bgCard,
        border:       `1px solid ${isSelected ? t.borderSelect : t.border}`,
        borderLeft:   hasUserKw   ? `3px solid ${t.accent}`
                    : entry.is_saved ? `3px solid ${t.saved}`
                    : "3px solid transparent",
        borderRadius: 10,
        padding:      "16px 18px",
        cursor:       "pointer",
        marginBottom: 6,
        transition:   "background 0.12s, border-color 0.12s",
      }}
    >
      {/* Meta row */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 9 }}>
        <span style={{
          fontSize: 11, fontFamily: "monospace", fontWeight: 700, letterSpacing: "0.07em",
          color: origin.color,
          background: `${origin.color}18`, border: `1px solid ${origin.color}38`,
          padding: "2px 7px", borderRadius: 4,
        }}>
          {origin.label}
        </span>

        <span style={{ fontSize: 12, color: t.textMuted, fontFamily: "monospace" }}>
          {timeAgo(entry.published_at)}
        </span>

        {score && (
          <span style={{ fontSize: 12, color: t.textMuted, fontFamily: "monospace" }}>
            ↑ {parseInt(score).toLocaleString()}
          </span>
        )}

        <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
          {!entry.is_read && (
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: t.unread, display: "inline-block", flexShrink: 0 }} />
          )}
          {entry.is_saved && <span style={{ fontSize: 13, color: t.saved }}>⬟</span>}
          <span
            onClick={e => { e.stopPropagation(); onSave(); }}
            title={entry.is_saved ? "Désauvegarder" : "Sauvegarder"}
            style={{ fontSize: 14, color: entry.is_saved ? t.saved : t.textMuted, cursor: "pointer", padding: "0 2px" }}
          >
            {entry.is_saved ? "★" : "☆"}
          </span>
          <span
            onClick={e => { e.stopPropagation(); onHide(); }}
            title="Masquer"
            style={{ fontSize: 13, color: t.textMuted, cursor: "pointer", padding: "0 2px" }}
          >
            ✕
          </span>
        </div>
      </div>

      {/* Title */}
      <div style={{
        fontSize: 15,
        fontWeight: entry.is_read ? 400 : 600,
        color:     entry.is_read ? t.textSub : t.text,
        lineHeight: 1.4, marginBottom: 7,
      }}>
        {entry.title}
      </div>

      {/* Description — 2 lignes */}
      <div style={{
        fontSize: 13, color: t.textSub, lineHeight: 1.65,
        display: "-webkit-box", WebkitLineClamp: 2,
        WebkitBoxOrient: "vertical", overflow: "hidden",
        marginBottom: 10,
      }}>
        {entry.description}
      </div>

      {/* Keywords */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
        {entry.keywords.map(kw => {
          const hi = keywords.includes(kw);
          return (
            <span key={kw} style={{
              fontSize: 11, fontFamily: "monospace", padding: "2px 7px", borderRadius: 4,
              background: hi ? t.accentBg  : t.kwBg,
              color:      hi ? t.accent    : t.kwColor,
              border:     hi ? `1px solid ${t.accentBorder}` : `1px solid ${t.kwBorder}`,
              fontWeight: hi ? 600 : 400,
            }}>
              {hi && <span style={{ marginRight: 3, fontSize: 9 }}>◆</span>}
              {kw}
            </span>
          );
        })}
      </div>
    </div>
  );
}
