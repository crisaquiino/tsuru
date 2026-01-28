// src/components/Login.tsx
import React, { useState } from "react";
import api from "../api/client";

type Props = {
  onSuccess: (token: string, email: string) => void;
};

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login({ onSuccess }: Props) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setError(null);

    if (!email || !emailRegex.test(email)) {
      setError("Digite um email válido (ex.: usuario@dominio.com)");
      return;
    }

    setLoading(true);
    try {
      const res = await api.post("/login", { email });
      // backend esperado: { access_token: "...", token_type: "bearer" }
      const token = res.data?.access_token;
      if (token) {
        onSuccess(token, email);
      } else {
        setError("Resposta inválida do servidor. Tente novamente.");
      }
    } catch (err: any) {
      console.error(err);
      if (err.response?.data?.detail) {
        setError(String(err.response.data.detail));
      } else {
        setError("Erro ao conectar com o servidor.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 520, margin: "2rem auto", padding: 20, border: "1px solid #eee", borderRadius: 8 }}>
      <h2 style={{ marginBottom: 8 }}>Acessar — informe seu email</h2>
      <form onSubmit={submit}>
        <label style={{ display: "block", marginBottom: 6 }}>
          E-mail
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="seu@exemplo.com"
            style={{ width: "100%", padding: 8, marginTop: 6, boxSizing: "border-box" }}
            disabled={loading}
            required
          />
        </label>

        {error && (
          <div style={{ color: "crimson", marginBottom: 8 }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 8 }}>
          <button type="submit" disabled={loading} style={{ padding: "8px 12px" }}>
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </div>
      </form>

      <p style={{ marginTop: 12, color: "#666", fontSize: 13 }}>
        Ao entrar você receberá um token que será usado para acessar os endpoints protegidos.
      </p>
    </div>
  );
}
