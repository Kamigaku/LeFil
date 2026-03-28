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
type MobileView = "sidebar" | "feed" | "detail";

const FILTER_LABELS: Record<Filter, string> = {
  all:        "Général",
  filtered:   "Mes sujets",
  unread:     "Non lus",
  saved:      "Sauvegardés",
  hackernews: "Hacker News",
  reddit:     "Reddit",
  github:     "GitHub",
};

// Hook de détection mobile
function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);
  return isMobile;
}

export default function Dashboard() {
  const router                              = useRouter();
  const { user, loading: authLoading, logout } = useAuth();
  const { theme }                           = useTheme();
  const t                                   = palette(theme);
  const isMobile                            = useIsMobile();
  const [filter, setFilter]                 = useState<Filter>("unread"); // ← Non lus par défaut
  const [selected, setSelected]             = useState<Entry | null>(null);
  const [keywords, setKeywords]             = useState<string[]>([]);
  const [mobileView, setMobileView]         = useState<MobileView>("feed");

  useEffect(() => {
    if (!authLoading && !user) router.replace("/auth");
  }, [authLoading, user]);

  useEffect(() => {
    if (user) getKeywords().then(setKeywords);
  }, [user]);

  const feedParams = {
    origin:      ["hackernews", "reddit", "github"].includes(filter) ? filter : undefined,
    only_unread: filter === "unread",
    only_saved:  filter === "saved",
  };

  const { entries: rawEntries, hasMore, loading, loadingMore, load, loadMore, loaderRef, updateEntry, removeEntry } =
    useInfiniteFeed(feedParams);

  const entries = filter === "filtered"
    ? rawEntries.filter(e => e.keywords.some(kw => keywords.includes(kw)))
    : rawEntries;

  useEffect(() => { if (user) load(); }, [filter, user]);

  // ── IntersectionObserver — créé une fois, lit loadMore via ref ──────────────
  const loadMoreRef = useRef(loadMore);
  loadMoreRef.current = loadMore;

  useEffect(() => {
    const sentinel = loaderRef.current;
    if (!sentinel) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) loadMoreRef.current(); },
      { rootMargin: "400px" },
    );
    obs.observe(sentinel);
    return () => obs.disconnect();
  }, [entries.length]); // re-attache quand la liste grandit (sentinel toujours présent)

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
    if (selected?.id === entry.id) { setSelected(null); if (isMobile) setMobileView("feed"); }
    await markHidden(entry.id);
  };

  const handleAddKeyword    = async (kw: string) => { setKeywords(k => [...k, kw]); await addKeyword(kw); };
  const handleRemoveKeyword = async (kw: string) => { setKeywords(k => k.filter(x => x !== kw)); await removeKeyword(kw); };
  const handleToggleKeyword = async (kw: string) => keywords.includes(kw) ? handleRemoveKeyword(kw) : handleAddKeyword(kw);

  const handleSelectEntry = (entry: Entry) => {
    setSelected(selected?.id === entry.id ? null : entry);
    if (!entry.is_read) handleRead(entry);
    if (isMobile) setMobileView("detail");
  };

  const handleFilterChange = (f: Filter) => {
    setFilter(f);
    if (isMobile) setMobileView("feed");
  };

  if (authLoading || !user) return null;

  // ── Feed panel (partagé desktop + mobile) ─────────────────────────────────

  const FeedPanel = () => (
    <div style={{
      display: "flex", flexDirection: "column",
      height: "100%", overflow: "hidden",
      flex: isMobile ? "1" : "0 0 460px",
      borderRight: isMobile ? "none" : `1px solid ${t.border}`,
    }}>
      {/* Header */}
      <div style={{
        padding: "14px 16px 12px",
        borderBottom: `1px solid ${t.border}`,
        display: "flex", alignItems: "center", gap: 10, flexShrink: 0,
      }}>
        {/* Bouton sidebar sur mobile */}
        {isMobile && (
          <button
            onClick={() => setMobileView("sidebar")}
            style={{
              background: "none", border: "none", color: t.textSub,
              fontSize: 20, cursor: "pointer", padding: "0 4px",
            }}
          >
            ☰
          </button>
        )}
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
      </div>

      {/* Articles */}
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px" }}>
        {loading ? (
          <div style={{ padding: 48, textAlign: "center", color: t.textMuted, fontSize: 13 }}>Chargement...</div>
        ) : entries.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center", color: t.textMuted, fontSize: 13 }}>Aucun article dans cette vue</div>
        ) : (
          <>
            {entries.map(entry => (
              <EntryCard
                key={entry.id}
                entry={entry}
                keywords={keywords}
                isSelected={selected?.id === entry.id}
                onClick={() => handleSelectEntry(entry)}
                onSave={() => handleSave(entry)}
                onHide={() => handleHide(entry)}
              />
            ))}

            {/* Sentinel callback ref — s'attache dès que l'élément est dans le DOM */}
            <div ref={loaderRef} style={{ height: 1 }} />

            {loadingMore && (
              <div style={{ padding: 16, textAlign: "center", color: t.textMuted, fontSize: 12 }}>Chargement...</div>
            )}
            {!hasMore && entries.length > 0 && (
              <div style={{ padding: 24, textAlign: "center", color: t.textFaint, fontSize: 11, fontFamily: "monospace", letterSpacing: "0.1em" }}>
                ─ FIN DU FEED ─
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );

  // ── Layout mobile : un seul panneau visible à la fois ────────────────────

  if (isMobile) {
    return (
      <div style={{ height: "100vh", overflow: "hidden", background: t.bg, color: t.text, fontFamily: "'DM Sans', sans-serif" }}>

        {mobileView === "sidebar" && (
          <Sidebar
            filter={filter} setFilter={handleFilterChange}
            keywords={keywords} entries={rawEntries} user={user}
            onAddKeyword={handleAddKeyword} onRemoveKeyword={handleRemoveKeyword}
            onLogout={logout} isMobile={true}
          />
        )}

        {mobileView === "feed" && (
          <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
            <FeedPanel />
          </div>
        )}

        {mobileView === "detail" && (
          <div style={{ height: "100%", overflowY: "auto", background: t.bg }}>
            {/* Bouton retour */}
            <div style={{
              padding: "12px 16px", borderBottom: `1px solid ${t.border}`,
              display: "flex", alignItems: "center", gap: 10, position: "sticky", top: 0,
              background: t.bg, zIndex: 10,
            }}>
              <button
                onClick={() => setMobileView("feed")}
                style={{ background: "none", border: "none", color: t.accent, fontSize: 14, cursor: "pointer", fontFamily: "inherit" }}
              >
                ← Retour
              </button>
            </div>
            <DetailPanel
              entry={selected} keywords={keywords}
              onSave={() => selected && handleSave(selected)}
              onHide={() => selected && handleHide(selected)}
              onRead={() => selected && handleRead(selected)}
              onToggleKeyword={handleToggleKeyword}
            />
          </div>
        )}
      </div>
    );
  }

  // ── Layout desktop : 3 colonnes ──────────────────────────────────────────

  return (
    <div style={{
      display: "flex", height: "100vh", overflow: "hidden",
      background: t.bg, color: t.text, fontFamily: "'DM Sans', sans-serif",
    }}>
      <Sidebar
        filter={filter} setFilter={setFilter}
        keywords={keywords} entries={rawEntries} user={user}
        onAddKeyword={handleAddKeyword} onRemoveKeyword={handleRemoveKeyword}
        onLogout={logout} isMobile={false}
      />
      <FeedPanel />
      <div style={{ flex: 1, overflowY: "auto", background: t.bg }}>
        <DetailPanel
          entry={selected} keywords={keywords}
          onSave={() => selected && handleSave(selected)}
          onHide={() => selected && handleHide(selected)}
          onRead={() => selected && handleRead(selected)}
          onToggleKeyword={handleToggleKeyword}
        />
      </div>
    </div>
  );
}