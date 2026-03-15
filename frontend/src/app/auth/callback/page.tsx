"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";

/**
 * Page de callback Google OAuth.
 * Le backend FastAPI redirige ici avec ?token=xxx après l'authentification Google.
 * On stocke le token et on redirige vers le dashboard.
 */
export default function AuthCallback() {
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

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", background: "#060609",
      color: "#6b7280", fontFamily: "monospace", fontSize: 13,
    }}>
      Connexion en cours...
    </div>
  );
}
