// src/components/GroupsList.tsx
import { useEffect, useState, useRef } from "react";

type MemberOfItem = {
  id: string | null;
  displayName: string | null;
  odata_type: string | null;
};

type Props = {
  onSelect?: (item: MemberOfItem | MemberOfItem[] | null) => void;
  multiSelect?: boolean;
  onAuthError?: () => void;
  autoFetch?: boolean;
};

export default function GroupsList({
  onSelect,
  multiSelect = false,
  onAuthError,
  autoFetch = true,
}: Props) {
  const [items, setItems] = useState<MemberOfItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (autoFetch) fetchGroups();
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchGroups() {
    setLoading(true);
    setError(null);

    const abort = new AbortController();
    abortRef.current = abort;

    try {
      const token = localStorage.getItem("api_token");
      const base = import.meta.env.VITE_API_BASE || "";
      const res = await fetch(`${base}/user/groups`, {
        method: "GET",
        headers: {
          "Authorization": token ? `Bearer ${token}` : "",
          "Accept": "application/json",
        },
        signal: abort.signal,
      });

      if (res.status === 401 || res.status === 403) {
        const txt = await res.text().catch(() => "");
        setError("Não autorizado. Faça login novamente.");
        if (onAuthError) onAuthError();
        else console.warn("Auth error calling /user/groups:", txt);
        setItems([]);
        return;
      }

      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Erro ${res.status}: ${txt}`);
      }

      const data = await res.json();
      const list = Array.isArray(data.memberOf) ? data.memberOf : [];

      // === AQUI A LÓGICA DO FILTRO ===
      const filteredList = list.filter((it: MemberOfItem) => {
        const name = (it.displayName || "").toLowerCase().trim();
        const id = (it.id || "").toLowerCase().trim();
        return name.startsWith("oci-administrators") || name.startsWith("gcp-administrators") || id.startsWith("oci-administrators") || id.startsWith("gcp-administrators");
      });

      setItems(filteredList);

      // reset selection se necessário
      setSelectedIds(prev => {
        const newSet = new Set(
          Array.from(prev).filter(id => !!filteredList.find((it: any) => (it.id || it.displayName) === id))
        );
        triggerOnSelect(newSet, filteredList);
        return newSet;
      });

    } catch (err: any) {
      if (err.name === "AbortError") {
        console.log("fetchGroups aborted");
      } else {
        console.error(err);
        setError(err.message || String(err));
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }

  function getItemKey(it: MemberOfItem) {
    return it.id || it.displayName || JSON.stringify(it);
  }

  function toggleSelect(it: MemberOfItem) {
    const id = it.id || it.displayName || "";
    if (!id) return;

    if (multiSelect) {
      setSelectedIds(prev => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        triggerOnSelect(next, items);
        return next;
      });
    } else {
      const next = new Set<string>();
      next.add(id);
      setSelectedIds(next);
      triggerOnSelect(next, items);
    }
  }

  function triggerOnSelect(selectedSet: Set<string>, sourceList: MemberOfItem[]) {
    if (!onSelect) return;
    if (multiSelect) {
      const selectedArr = sourceList.filter(it => {
        const key = it.id || it.displayName || "";
        return key && selectedSet.has(key);
      });
      onSelect(selectedArr);
    } else {
      const sel = sourceList.find(it => (it.id || it.displayName || "") === Array.from(selectedSet)[0]);
      onSelect(sel || null);
    }
  }

  const filtered = items.filter(it => {
    if (!filter) return true;
    const needle = filter.toLowerCase();
    const name = (it.displayName || "").toLowerCase();
    const id = (it.id || "").toLowerCase();
    return name.includes(needle) || id.includes(needle);
  });

  return (
    <div style={{ maxWidth: 800, margin: "1rem 0", padding: 12, borderRadius: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Grupos / Perfis</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button onClick={() => fetchGroups()} disabled={loading} title="Atualizar lista">
            Atualizar
          </button>
          <span style={{ color: "#666", fontSize: 13 }}>
            {loading ? "Carregando..." : `${items.length} items`}
          </span>
        </div>
      </div>

      <div style={{ marginBottom: 8 }}>
        <input
          type="search"
          placeholder="Filtrar por nome ou id..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{ width: "100%", padding: 8, boxSizing: "border-box" }}
        />
      </div>

      {error && <div style={{ color: "crimson", marginBottom: 8 }}>{error}</div>}

      {!error && (
        <ul style={{ listStyleType: "disc", paddingLeft: 20, maxHeight: 360, overflow: "auto" }}>
          {filtered.length === 0 && <li>{loading ? "Carregando..." : "Nenhum grupo encontrado"}</li>}
          {filtered.map((it) => {
            const key = getItemKey(it);
            const checked = selectedIds.has(it.id || it.displayName || "");
            return (
              <li key={key} style={{ marginBottom: 6 }}>
                <label style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
                  <input
                    type={multiSelect ? "checkbox" : "radio"}
                    name="group"
                    checked={checked}
                    onChange={() => toggleSelect(it)}
                  />
                  <div>
                    <div style={{ fontWeight: 600 }}>{it.displayName || "<sem nome>"}</div>
                    <div style={{ fontSize: 12, color: "#666" }}>{it.id ? it.id : it.odata_type}</div>
                  </div>
                </label>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
