"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useTheme, palette } from "@/lib/theme";
import { useInfiniteFeed } from "@/hooks/useInfiniteFeed";
import { getKeywords, addKeyword, removeKeyword, markRead, markSaved, markHidden } from "@/lib/api";
import type { Entry } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import EntryCard from "@/components/EntryCard";
import DetailPanel from "@/components/DetailPanel";

type Filter = "all" | "filtered" | "unread" | "saved" | "hackernews" | "reddit" | "github";

const FILTER_LABELS: Record<Filter, string> = {
  all:        "Général",
  filtered:   "Mes sujets",
  unread:     "Non lus",
  saved:      "Sauvegardés",
  hackernews: "Hacker News",
  reddit:     "Reddit",
  github:     "GitHub",
};

export default function Dashboard() {
  const router                              = useRouter();
  const { user, loading: authLoading, logout } = useAuth();
  const { theme }                           = useTheme();
  const t                                   = palette(theme);
  const [filter, setFilter]                 = useState<Filter>("all");
  const [selected, setSelected]             = useState<Entry | null>(null);
  const [keywords, setKeywords]             = useState<string[]>([]);
  const loaderRef                           = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/auth");
  }, [authLoading, user]);

  useEffect(() => {
    if (user) getKeywords().then(setKeywords);
  }, [user]);

  // La vue "filtered" charge tout puis filtre côté client,
  // les autres vues utilisent les paramètres API.
  const feedParams = {
    origin:      ["hackernews", "reddit", "github"].includes(filter) ? filter : undefined,
    only_unread: filter === "unread",
    only_saved:  filter === "saved",
  };

  const { entries: rawEntries, hasMore, loading, loadingMore, load, loadMore, updateEntry, removeEntry } =
    useInfiniteFeed(feedParams);

  // Filtre côté client pour la vue "Mes sujets"
  const entries = filter === "filtered"
    ? rawEntries.filter(e => e.keywords.some(kw => keywords.includes(kw)))
    : rawEntries;

  useEffect(() => { if (user) load(); }, [filter, user]);

  // IntersectionObserver — infinite scroll
  useEffect(() => {
    if (!loaderRef.current) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting && hasMore && !loadingMore) loadMore(); },
      { rootMargin: "200px" },
    );
    obs.observe(loaderRef.current);
    return () => obs.disconnect();
  }, [hasMore, loadingMore, loadMore]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleRead = async (entry: Entry) => {
    const next = !entry.is_read;
    updateEntry(entry.id, { is_read: next });
    await markRead(entry.id, next);
  };

  const handleSave = async (entry: Entry) => {
    const next = !entry.is_saved;
    updateEntry(entry.id, { is_saved: next });
    if (selected?.id === entry.id) setSelected(e => e ? { ...e, is_saved: next } : e);
    await markSaved(entry.id, next);
  };

  const handleHide = async (entry: Entry) => {
    removeEntry(entry.id);
    if (selected?.id === entry.id) setSelected(null);
    await markHidden(entry.id);
  };

  const handleAddKeyword = async (kw: string) => {
    setKeywords(k => [...k, kw]);
    await addKeyword(kw);
  };

  const handleRemoveKeyword = async (kw: string) => {
    setKeywords(k => k.filter(x => x !== kw));
    await removeKeyword(kw);
  };

  // Clic sur un mot-clé dans le détail : toggle (ajoute ou retire)
  const handleToggleKeyword = async (kw: string) => {
    if (keywords.includes(kw)) {
      await handleRemoveKeyword(kw);
    } else {
      await handleAddKeyword(kw);
    }
  };

  if (authLoading || !user) return null;

  return (
    <div style={{
      display: "flex", height: "100vh", overflow: "hidden",
      background: t.bg, color: t.text, fontFamily: "'DM Sans', sans-serif",
    }}>

      {/* Sidebar */}
      <Sidebar
        filter={filter}
        setFilter={setFilter}
        keywords={keywords}
        entries={rawEntries}
        user={user}
        onAddKeyword={handleAddKeyword}
        onRemoveKeyword={handleRemoveKeyword}
        onLogout={logout}
      />

      {/* Feed */}
      <div style={{
        flex: "0 0 460px",
        borderRight: `1px solid ${t.border}`,
        display: "flex", flexDirection: "column",
        overflow: "hidden",
      }}>
        {/* Feed header */}
        <div style={{
          padding: "16px 18px 13px",
          borderBottom: `1px solid ${t.border}`,
          display: "flex", alignItems: "center", gap: 10,
        }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: t.text }}>
            {FILTER_LABELS[filter]}
          </span>
          <span style={{
            fontSize: 11, fontFamily: "monospace", color: t.textMuted,
            background: t.bgMeta, border: `1px solid ${t.border}`,
            padding: "2px 8px", borderRadius: 5,
          }}>
            {entries.length}
          </span>
          {filter === "filtered" && keywords.length === 0 && (
            <span style={{ fontSize: 12, color: t.textMuted, fontStyle: "italic" }}>
              — ajoutez des sujets dans le menu
            </span>
          )}
        </div>

        {/* Articles */}
        <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px" }}>
          {loading ? (
            <div style={{ padding: 48, textAlign: "center", color: t.textMuted, fontSize: 13 }}>
              Chargement...
            </div>
          ) : entries.length === 0 ? (
            <div style={{ padding: 48, textAlign: "center", color: t.textMuted, fontSize: 13 }}>
              Aucun article dans cette vue
            </div>
          ) : (
            <>
              {entries.map(entry => (
                <EntryCard
                  key={entry.id}
                  entry={entry}
                  keywords={keywords}
                  isSelected={selected?.id === entry.id}
                  onClick={() => {
                    setSelected(selected?.id === entry.id ? null : entry);
                    if (!entry.is_read) handleRead(entry);
                  }}
                  onSave={() => handleSave(entry)}
                  onHide={() => handleHide(entry)}
                />
              ))}

              <div ref={loaderRef} style={{ height: 1 }} />

              {loadingMore && (
                <div style={{ padding: 16, textAlign: "center", color: t.textMuted, fontSize: 12 }}>
                  Chargement...
                </div>
              )}
              {!hasMore && entries.length > 0 && (
                <div style={{
                  padding: 24, textAlign: "center",
                  color: t.textFaint, fontSize: 11,
                  fontFamily: "monospace", letterSpacing: "0.1em",
                }}>
                  ─ FIN DU FEED ─
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Détail */}
      <div style={{ flex: 1, overflowY: "auto", background: t.bg }}>
        <DetailPanel
          entry={selected}
          keywords={keywords}
          onSave={() => selected && handleSave(selected)}
          onHide={() => selected && handleHide(selected)}
          onRead={() => selected && handleRead(selected)}
          onToggleKeyword={handleToggleKeyword}
        />
      </div>
    </div>
  );
}
