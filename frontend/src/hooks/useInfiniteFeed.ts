/**
 * hooks/useInfiniteFeed.ts — Hook de pagination infinie.
 *
 * Gère l'accumulation des pages, le curseur et le chargement.
 * Utilisé par le composant Feed avec IntersectionObserver.
 */

import { useState, useCallback, useRef } from "react";
import { getFeed, Entry, FeedParams } from "@/lib/api";

interface FeedState {
  entries:    Entry[];
  hasMore:    boolean;
  loading:    boolean;
  loadingMore: boolean;
  error:      string | null;
}

export function useInfiniteFeed(params: Omit<FeedParams, "cursor"> = {}) {
  const [state, setState] = useState<FeedState>({
    entries:     [],
    hasMore:     true,
    loading:     true,
    loadingMore: false,
    error:       null,
  });

  const cursorRef    = useRef<string | null>(null);
  const paramsRef    = useRef(params);
  paramsRef.current  = params;

  // Charge la première page (ou recharge depuis le début)
  const load = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }));
    cursorRef.current = null;
    try {
      const page = await getFeed({ ...paramsRef.current, limit: 20 });
      cursorRef.current = page.next_cursor;
      setState({
        entries:     page.items,
        hasMore:     page.has_more,
        loading:     false,
        loadingMore: false,
        error:       null,
      });
    } catch (e: any) {
      setState(s => ({ ...s, loading: false, error: e.message }));
    }
  }, []);

  // Charge la page suivante (appelé par IntersectionObserver)
  const loadMore = useCallback(async () => {
    if (!cursorRef.current) return;
    setState(s => ({ ...s, loadingMore: true }));
    try {
      const page = await getFeed({
        ...paramsRef.current,
        cursor: cursorRef.current!,
        limit:  20,
      });
      cursorRef.current = page.next_cursor;
      setState(s => ({
        ...s,
        entries:     [...s.entries, ...page.items],
        hasMore:     page.has_more,
        loadingMore: false,
      }));
    } catch (e: any) {
      setState(s => ({ ...s, loadingMore: false, error: e.message }));
    }
  }, []);

  // Met à jour un article dans le state local (optimistic update)
  const updateEntry = useCallback((id: string, patch: Partial<Entry>) => {
    setState(s => ({
      ...s,
      entries: s.entries.map(e => e.id === id ? { ...e, ...patch } : e),
    }));
  }, []);

  // Retire un article du feed (masqué)
  const removeEntry = useCallback((id: string) => {
    setState(s => ({
      ...s,
      entries: s.entries.filter(e => e.id !== id),
    }));
  }, []);

  return { ...state, load, loadMore, updateEntry, removeEntry };
}
