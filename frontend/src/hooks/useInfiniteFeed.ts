/**
 * hooks/useInfiniteFeed.ts — Hook de pagination infinie.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { getFeed, Entry, FeedParams } from "@/lib/api";

interface FeedState {
  entries:     Entry[];
  hasMore:     boolean;
  loading:     boolean;
  loadingMore: boolean;
  error:       string | null;
}

export function useInfiniteFeed(params: Omit<FeedParams, "cursor"> = {}) {
  const [state, setState] = useState<FeedState>({
    entries:     [],
    hasMore:     true,
    loading:     true,
    loadingMore: false,
    error:       null,
  });

  const cursorRef     = useRef<string | null>(null);
  const paramsRef     = useRef(params);
  paramsRef.current   = params;

  // Refs stables pour éviter les captures de closure périmées dans l'observer
  const hasMoreRef     = useRef(true);
  const loadingMoreRef = useRef(false);

  hasMoreRef.current     = state.hasMore;
  loadingMoreRef.current = state.loadingMore;

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
        entries:     [...s.entries, ...page.items],   // ← append, jamais replace
        hasMore:     page.has_more,
        loadingMore: false,
      }));
    } catch (e: any) {
      setState(s => ({ ...s, loadingMore: false, error: e.message }));
    }
  }, []);

  // Ref stable vers loadMore pour l'observer
  const loadMoreRef = useRef(loadMore);
  loadMoreRef.current = loadMore;

  // Expose une ref stable pour le sentinel — l'observer lit hasMore/loadingMore
  // depuis les refs, pas depuis des closures capturées, ce qui évite les
  // déclenchements parasites qui appelaient load() au lieu de loadMore()
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    if (observerRef.current) observerRef.current.disconnect();

    observerRef.current = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && hasMoreRef.current && !loadingMoreRef.current) {
          loadMoreRef.current();
        }
      },
      { rootMargin: "300px" },
    );

    if (sentinelRef.current) {
      observerRef.current.observe(sentinelRef.current);
    }

    return () => { observerRef.current?.disconnect(); };
  }, []); // ← dépendances vides : l'observer est créé une seule fois

  // Callback ref passé au sentinel dans le JSX
  const loaderRef = useCallback((node: HTMLDivElement | null) => {
    sentinelRef.current = node;
    if (node && observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current.observe(node);
    }
  }, []);

  const updateEntry = useCallback((id: string, patch: Partial<Entry>) => {
    setState(s => ({
      ...s,
      entries: s.entries.map(e => e.id === id ? { ...e, ...patch } : e),
    }));
  }, []);

  const removeEntry = useCallback((id: string) => {
    setState(s => ({
      ...s,
      entries: s.entries.filter(e => e.id !== id),
    }));
  }, []);

  return { ...state, load, loadMore, loaderRef, updateEntry, removeEntry };
}