"use client";

import type { Entry } from "@/lib/api";
import { useTheme, palette } from "@/lib/theme";

const ORIGIN_CONFIG: Record<string, { label: string; color: string }> = {
  hackernews: { label: "HN",     color: "#f97316" },
  reddit:     { label: "Reddit", color: "#ef4444" },
  github:     { label: "GitHub", color: "#8b5cf6" },
  rss:        { label: "RSS",    color: "#06b6d4" },
};

interface Props {
  entry:           Entry | null;
  keywords:        string[];
  onSave:          () => void;
  onHide:          () => void;
  onRead:          () => void;
  onToggleKeyword: (kw: string) => void;   // ← ajoute ou retire de la liste
}

export default function DetailPanel({ entry, keywords, onSave, onHide, onRead, onToggleKeyword }: Props) {
  const { theme } = useTheme();
  const t         = palette(theme);

  if (!entry) return (
    <div style={{
      height: "100%", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      color: t.textFaint, gap: 10,
    }}>
      <span style={{ fontSize: 32, opacity: 0.4 }}>◈</span>
      <span style={{ fontFamily: "monospace", fontSize: 13, color: t.textMuted }}>
        Sélectionne un article
      </span>
    </div>
  );

  const origin = ORIGIN_CONFIG[entry.origin] ?? { label: entry.origin, color: "#6b7280" };

  const ActionBtn = ({ label, active, color, onClick }: {
    label: string; active: boolean; color: string; onClick: () => void;
  }) => (
    <button
      onClick={onClick}
      style={{
        padding: "9px 16px", borderRadius: 7, cursor: "pointer",
        border:     `1px solid ${active ? color : t.border}`,
        background: active ? `${color}18` : "transparent",
        color:      active ? color : t.textSub,
        fontSize: 13, fontFamily: "inherit", fontWeight: active ? 600 : 400,
      }}
    >
      {label}
    </button>
  );

  return (
    <div style={{ padding: "28px 28px", maxWidth: 760 }}>

      {/* Header */}
      <div style={{ marginBottom: 22 }}>
        <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12 }}>
          <span style={{
            fontSize: 11, fontFamily: "monospace", fontWeight: 700, letterSpacing: "0.07em",
            color: origin.color, background: `${origin.color}18`,
            border: `1px solid ${origin.color}38`, padding: "3px 9px", borderRadius: 5,
          }}>
            {origin.label.toUpperCase()}
          </span>
          <span style={{ fontSize: 13, color: t.textMuted, fontFamily: "monospace" }}>
            {new Date(entry.published_at).toLocaleDateString("fr-FR", {
              day: "2-digit", month: "short", year: "numeric",
              hour: "2-digit", minute: "2-digit",
            })}
          </span>
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: t.text, lineHeight: 1.4, margin: 0 }}>
          {entry.title}
        </h2>
      </div>

      {/* Description */}
      <div style={{
        fontSize: 15, lineHeight: 1.85, color: t.textSub,
        marginBottom: 28, padding: "18px 20px",
        background: t.bgDetail, borderRadius: 8,
        border: `1px solid ${t.border}`,
      }}>
        {entry.description}
      </div>

      {/* Mots-clés cliquables */}
      <div style={{ marginBottom: 28 }}>
        <div style={{
          fontSize: 11, color: t.textMuted, fontFamily: "monospace",
          letterSpacing: "0.12em", marginBottom: 10,
          display: "flex", alignItems: "center", gap: 8,
        }}>
          MOTS-CLÉS
          <span style={{ fontSize: 11, color: t.textMuted, fontWeight: 400, letterSpacing: 0, fontFamily: "inherit" }}>
            — cliquer pour ajouter / retirer de vos sujets
          </span>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
          {entry.keywords.map(kw => {
            const inList = keywords.includes(kw);
            return (
              <span
                key={kw}
                onClick={() => onToggleKeyword(kw)}
                title={inList ? `Retirer "${kw}" de mes sujets` : `Ajouter "${kw}" à mes sujets`}
                style={{
                  fontSize: 13, fontFamily: "monospace",
                  padding: "5px 11px", borderRadius: 6,
                  background:  inList ? t.accentBg  : t.kwBg,
                  color:       inList ? t.accent    : t.kwColor,
                  border:      inList ? `1px solid ${t.accentBorder}` : `1px solid ${t.kwBorder}`,
                  fontWeight:  inList ? 600 : 400,
                  cursor:      "pointer",
                  userSelect:  "none",
                  transition:  "all 0.12s",
                }}
              >
                {inList
                  ? <><span style={{ marginRight: 5, fontSize: 10 }}>◆</span>{kw} ×</>
                  : <><span style={{ marginRight: 5, fontSize: 10, opacity: 0.5 }}>+</span>{kw}</>
                }
              </span>
            );
          })}
        </div>
      </div>

      {/* Sources */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, color: t.textMuted, fontFamily: "monospace", letterSpacing: "0.12em", marginBottom: 10 }}>
          SOURCES
        </div>
        {Object.entries(entry.sources).map(([src, meta]) => (
          <div key={src} style={{
            padding: "11px 14px", marginBottom: 6,
            background: t.bgDetail, borderRadius: 7,
            border: `1px solid ${t.border}`,
            fontSize: 12, fontFamily: "monospace", color: t.textMuted,
          }}>
            <span style={{ color: ORIGIN_CONFIG[src]?.color ?? "#6b7280", marginRight: 10, fontWeight: 700 }}>
              {src}
            </span>
            {Object.entries(meta)
              .filter(([k]) => !["hn_id", "author", "is_draft"].includes(k))
              .map(([k, v]) => (
                <span key={k} style={{ marginRight: 12 }}>
                  {k}: <span style={{ color: t.textSub }}>{v}</span>
                </span>
              ))}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <ActionBtn label={entry.is_read ? "✓ Lu" : "Marquer lu"} active={entry.is_read}  color={t.unread} onClick={onRead} />
        <ActionBtn label={entry.is_saved ? "⬟ Sauvegardé" : "Sauvegarder"} active={entry.is_saved} color={t.saved} onClick={onSave} />
        <ActionBtn label="Masquer" active={false} color={t.textMuted} onClick={onHide} />
        <a
          href={entry.link}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            padding: "9px 16px", borderRadius: 7,
            border: `1px solid ${t.open}50`,
            color: t.open, fontSize: 13, fontFamily: "inherit",
            display: "inline-flex", alignItems: "center", gap: 5,
          }}
        >
          ↗ Ouvrir l'article
        </a>
      </div>
    </div>
  );
}
