/**
 * hooks/useInfiniteFeed.ts — Hook de pagination infinie.
 *
 * Utilise un mutex (isLoadingRef) pour garantir qu'on ne peut jamais
 * avoir load() et loadMore() qui tournent en même temps, et que
 * loadMore() utilise toujours setState fonctionnel pour ne jamais
 * écraser les entrées existantes.
 */

import { useState, useCallback, useRef } from "react";
import { getFeed, Entry, FeedParams } from "@/lib/api";

export function useInfiniteFeed(params: Omit<FeedParams, "cursor"> = {}) {
  const [entries,     setEntries]     = useState<Entry[]>([]);
  const [hasMore,     setHasMore]     = useState(true);
  const [loading,     setLoading]     = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error,       setError]       = useState<string | null>(null);

  const cursorRef    = useRef<string | null>(null);
  const paramsRef    = useRef(params);
  paramsRef.current  = params;

  // Mutex : empêche load() et loadMore() de se chevaucher
  const isLoadingRef = useRef(false);
  // Refs pour l'observer (évite les closures périmées)
  const hasMoreRef   = useRef(true);
  hasMoreRef.current = hasMore;

  // ── Charge la première page ──────────────────────────────────────────────

  const load = useCallback(async () => {
    if (isLoadingRef.current) return;
    isLoadingRef.current = true;
    setLoading(true);
    setError(null);
    cursorRef.current = null;

    try {
      const page = await getFeed({ ...paramsRef.current, limit: 20 });
      cursorRef.current = page.next_cursor;
      setEntries(page.items);          // ← seul endroit où on REMPLACE
      setHasMore(page.has_more);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
      isLoadingRef.current = false;
    }
  }, []);

  // ── Charge la page suivante ───────────────────────────────────────────────

  const loadMore = useCallback(async () => {
    // Triple garde : mutex + cursor + hasMore
    if (isLoadingRef.current || !cursorRef.current || !hasMoreRef.current) return;
    isLoadingRef.current = true;
    setLoadingMore(true);

    try {
      const page = await getFeed({
        ...paramsRef.current,
        cursor: cursorRef.current,
        limit:  20,
      });
      cursorRef.current = page.next_cursor;
      // setState fonctionnel : toujours basé sur la valeur la plus récente
      // → impossible d'écraser des entrées déjà présentes
      setEntries(prev => [...prev, ...page.items]);
      setHasMore(page.has_more);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingMore(false);
      isLoadingRef.current = false;
    }
  }, []);

  // ── Ref stable pour loadMore (lue par l'observer) ────────────────────────

  const loadMoreRef = useRef(loadMore);
  loadMoreRef.current = loadMore;

  // ── Sentinel ref : simple useRef, l'observer est créé dans le composant ──

  const loaderRef = useRef<HTMLDivElement | null>(null);

  // ── Optimistic updates ───────────────────────────────────────────────────

  const updateEntry = useCallback((id: string, patch: Partial<Entry>) => {
    setEntries(prev => prev.map(e => e.id === id ? { ...e, ...patch } : e));
  }, []);

  const removeEntry = useCallback((id: string) => {
    setEntries(prev => prev.filter(e => e.id !== id));
  }, []);

  return {
    entries, hasMore, loading, loadingMore, error,
    load, loadMore, loaderRef, updateEntry, removeEntry,
  };
}