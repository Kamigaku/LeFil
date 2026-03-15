"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, register, getGoogleLoginUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const S = {
  page: {
    minHeight: "100vh", display: "flex", alignItems: "center",
    justifyContent: "center", background: "#060609",
    backgroundImage: "radial-gradient(ellipse at 20% 50%, rgba(251,191,36,0.04) 0%, transparent 60%)",
  } as React.CSSProperties,

  card: {
    width: 380, padding: "40px 36px",
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 12,
  } as React.CSSProperties,

  logo: {
    fontSize: 22, fontWeight: 800, fontFamily: "monospace",
    letterSpacing: "-0.02em", color: "#f9fafb", marginBottom: 6,
    textAlign: "center",
  } as React.CSSProperties,

  tagline: {
    fontSize: 11, color: "#4b5563", fontFamily: "monospace",
    textAlign: "center", marginBottom: 32,
  } as React.CSSProperties,

  tabs: {
    display: "flex", gap: 0, marginBottom: 28,
    border: "1px solid rgba(255,255,255,0.08)", borderRadius: 7, overflow: "hidden",
  } as React.CSSProperties,

  input: {
    width: "100%", padding: "10px 12px",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.08)", borderRadius: 7,
    color: "#f3f4f6", fontSize: 13, fontFamily: "inherit",
    outline: "none", marginBottom: 10,
  } as React.CSSProperties,

  btnPrimary: {
    width: "100%", padding: "11px",
    background: "#fbbf24", border: "none", borderRadius: 7,
    color: "#0a0a0b", fontSize: 13, fontWeight: 700,
    fontFamily: "monospace", letterSpacing: "0.04em",
    marginBottom: 10, transition: "opacity 0.15s",
  } as React.CSSProperties,

  btnGoogle: {
    width: "100%", padding: "10px",
    background: "transparent",
    border: "1px solid rgba(255,255,255,0.1)", borderRadius: 7,
    color: "#9ca3af", fontSize: 12, fontFamily: "monospace",
    display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
  } as React.CSSProperties,

  divider: {
    display: "flex", alignItems: "center", gap: 10,
    margin: "14px 0", color: "#374151", fontSize: 11, fontFamily: "monospace",
  } as React.CSSProperties,

  error: {
    fontSize: 12, color: "#ef4444", fontFamily: "monospace",
    marginBottom: 10, padding: "8px 10px",
    background: "rgba(239,68,68,0.08)", borderRadius: 6,
    border: "1px solid rgba(239,68,68,0.2)",
  } as React.CSSProperties,
};

export default function AuthPage() {
  const router = useRouter();
  const { setToken } = useAuth();
  const [mode, setMode]       = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!username.trim() || !password.trim()) return;
    setLoading(true);
    setError("");
    try {
      const token = mode === "login"
        ? await login(username.trim(), password)
        : await register(username.trim(), password);
      setToken(token);
      router.push("/dashboard");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const tabStyle = (active: boolean): React.CSSProperties => ({
    flex: 1, padding: "9px", border: "none",
    background: active ? "rgba(251,191,36,0.1)" : "transparent",
    color: active ? "#fbbf24" : "#6b7280",
    fontSize: 12, fontFamily: "monospace", fontWeight: active ? 700 : 400,
    letterSpacing: "0.05em", transition: "all 0.15s",
  });

  return (
    <div style={S.page}>
      <div style={S.card}>
        <div style={S.logo}>
          Le<span style={{ color: "#fbbf24" }}>Fil</span>
        </div>
        <div style={S.tagline}>agrégateur de news tech</div>

        {/* Tabs */}
        <div style={S.tabs}>
          <button style={tabStyle(mode === "login")}    onClick={() => setMode("login")}>CONNEXION</button>
          <button style={tabStyle(mode === "register")} onClick={() => setMode("register")}>INSCRIPTION</button>
        </div>

        {error && <div style={S.error}>{error}</div>}

        <input
          style={S.input}
          placeholder="Nom d'utilisateur"
          value={username}
          onChange={e => setUsername(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSubmit()}
          autoFocus
        />
        <input
          style={S.input}
          type="password"
          placeholder="Mot de passe"
          value={password}
          onChange={e => setPassword(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSubmit()}
        />

        <button
          style={{ ...S.btnPrimary, opacity: loading ? 0.6 : 1 }}
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? "..." : mode === "login" ? "SE CONNECTER" : "CRÉER UN COMPTE"}
        </button>

        {/* Divider */}
        <div style={S.divider}>
          <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
          <span>ou</span>
          <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
        </div>

        {/* Google */}
        <button
          style={S.btnGoogle}
          onClick={() => window.location.href = getGoogleLoginUrl()}
        >
          <svg width="16" height="16" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continuer avec Google
        </button>
      </div>
    </div>
  );
}
