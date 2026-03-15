/**
 * lib/api.ts — Client HTTP centralisé vers le backend FastAPI.
 *
 * Toutes les fonctions retournent des données typées.
 * Le token JWT est lu depuis localStorage (stocké à la connexion).
 */

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Entry {
  id:           string;
  origin:       "reddit" | "hackernews" | "github" | "rss";
  link:         string;
  title:        string;
  description:  string;
  keywords:     string[];
  published_at: string;
  sources:      Record<string, Record<string, string>>;
  scraped_at:   string;
  is_read:      boolean;
  is_saved:     boolean;
  is_hidden:    boolean;
  tags:         string[];
  read_at:      string | null;
  saved_at:     string | null;
}

export interface FeedPage {
  items:       Entry[];
  has_more:    boolean;
  next_cursor: string | null;
  count:       number;
}

export interface User {
  id:            string;
  username:      string;
  created_at:    string;
  last_login_at: string | null;
}

export interface FeedParams {
  cursor?:      string;
  limit?:       number;
  origin?:      string;
  only_unread?: boolean;
  only_saved?:  boolean;
  keyword?:     string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Erreur API");
  }
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function register(username: string, password: string): Promise<string> {
  const data = await request<{ access_token: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  return data.access_token;
}

export async function login(username: string, password: string): Promise<string> {
  const data = await request<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  return data.access_token;
}

export function getGoogleLoginUrl(): string {
  return `${API}/auth/google`;
}

export async function getMe(): Promise<User> {
  return request<User>("/auth/me");
}

// ── Entries ───────────────────────────────────────────────────────────────────

export async function getFeed(params: FeedParams = {}): Promise<FeedPage> {
  const qs = new URLSearchParams();
  if (params.cursor)      qs.set("cursor",      params.cursor);
  if (params.limit)       qs.set("limit",        String(params.limit));
  if (params.origin)      qs.set("origin",       params.origin);
  if (params.only_unread) qs.set("only_unread",  "true");
  if (params.only_saved)  qs.set("only_saved",   "true");
  if (params.keyword)     qs.set("keyword",      params.keyword);
  return request<FeedPage>(`/entries?${qs}`);
}

// ── Keywords ──────────────────────────────────────────────────────────────────

export async function getKeywords(): Promise<string[]> {
  const data = await request<{ keywords: string[] }>("/keywords");
  return data.keywords;
}

export async function addKeyword(keyword: string): Promise<void> {
  await request("/keywords", { method: "POST", body: JSON.stringify({ keyword }) });
}

export async function removeKeyword(keyword: string): Promise<void> {
  await request(`/keywords/${encodeURIComponent(keyword)}`, { method: "DELETE" });
}

// ── Status ────────────────────────────────────────────────────────────────────

export async function markRead(entryId: string, value: boolean): Promise<void> {
  await request(`/entries/${entryId}/read`, {
    method: "PATCH",
    body: JSON.stringify({ value }),
  });
}

export async function markSaved(entryId: string, value: boolean): Promise<void> {
  await request(`/entries/${entryId}/saved`, {
    method: "PATCH",
    body: JSON.stringify({ value }),
  });
}

export async function markHidden(entryId: string): Promise<void> {
  await request(`/entries/${entryId}/hidden`, {
    method: "PATCH",
    body: JSON.stringify({ value: true }),
  });
}

export async function addTag(entryId: string, tag: string): Promise<void> {
  await request(`/entries/${entryId}/tags`, {
    method: "POST",
    body: JSON.stringify({ tag }),
  });
}
