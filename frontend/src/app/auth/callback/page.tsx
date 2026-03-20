"use client";
 
import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
 
const loadingStyle = {
  minHeight: "100vh", display: "flex", alignItems: "center",
  justifyContent: "center", background: "#060609",
  color: "#6b7280", fontFamily: "monospace", fontSize: 13,
} as const;
 
/**
 * Composant interne qui utilise useSearchParams().
 * Doit être enfant d'un <Suspense> — obligation Next.js 14.
 */
function CallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { setToken } = useAuth();
 
  useEffect(() => {
    const token = params.get("token");
    if (token) {
      setToken(token);
      router.replace("/dashboard");
    } else {
      router.replace("/auth");
    }
  }, []);
 
  return <div style={loadingStyle}>Connexion en cours...</div>;
}
 
/**
 * Page de callback Google OAuth.
 * Le backend FastAPI redirige ici avec ?token=xxx après l'authentification Google.
 */
export default function AuthCallback() {
  return (
    <Suspense fallback={<div style={loadingStyle}>Chargement...</div>}>
      <CallbackInner />
    </Suspense>
  );
}