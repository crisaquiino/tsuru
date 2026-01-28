import React, { useState } from "react";

type MemberOfItem = {
  id: string | null;
  displayName: string | null;
  odata_type: string | null;
};

type BucketActionsProps = {
  selectedGroup: MemberOfItem;
  token: string;          // vem do App.tsx (api_token)
  email: string | null;   // opcional
  onBack?: () => void;
};

const BucketActions: React.FC<BucketActionsProps> = ({
  selectedGroup,
  token,
  email,
  onBack,
}) => {
  const [output, setOutput] = useState<string>("");
  const [buckets, setBuckets] = useState<Array<{ name: string }>>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const base = import.meta.env.VITE_API_BASE || "";

  async function callApi(
    path: string,
    method: string = "GET",
    body?: unknown
  ) {
    if (!token) throw new Error("Token não encontrado (api_token)");

    const opts: RequestInit = {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
      },
    };

    if (body !== undefined && body !== null) {
      (opts.headers as any)["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }

    const res = await fetch(`${base}${path}`, opts);
    const text = await res.text().catch(() => "");
    let data: any = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { raw: text };
    }

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${JSON.stringify(data, null, 2)}`);
    }
    return data;
  }

  const appendOutput = (txt: string) => {
    setOutput((prev) => (prev ? `${prev}\n${txt}` : txt));
  };

  // util: extrai label cp-... caso queira enviar child (opcional)
  //const extractChildFromLabel = (label?: string | null) => {
  //  if (!label) return null;
  //  const m = label.match(/(cp[-_][A-Za-z0-9\-_]+)/i);
  //  return m ? m[1] : null;
  //};

  // -------- CREATE (mantive funcionalidade anterior, usa 'group') --------
  const handleCreate = async () => {
    const raw = window.prompt("Digite o nome do bucket que deseja criar:");
    if (!raw) return;

    const bucketName = raw.trim();
    if (!bucketName) {
      alert("Nome do bucket não pode ser vazio.");
      return;
    }

    setOutput(`Criando bucket '${bucketName}'...`);
    setLoading(true);

    try {
      const data = await callApi("/buckets", "POST", {
        name: bucketName,
        // enviamos 'group' porque o backend espera esse campo
        group: selectedGroup.displayName,
        groupId: selectedGroup.id,
        userEmail: email,
      });

      appendOutput("\n" + JSON.stringify(data, null, 2));
      // opcional: atualizar listagem automaticamente se já estiver mostrando
      if (buckets.length > 0) {
        await handleList(); // re-carrega a lista
      }
    } catch (err) {
      appendOutput("\nErro: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  };

  // -------- LIST --------
  const handleList = async () => {
    setOutput(`Listando buckets do grupo '${selectedGroup.displayName}'...`);
    setLoading(true);
    try {
      // usamos 'group' query param — backend extrai cp-... e resolve o OCID
      const q = `?group=${encodeURIComponent(selectedGroup.displayName || "")}`;
      const data = await callApi(`/buckets${q}`, "GET");
      // backend retorna { buckets: [...] }
      const list: any[] = data?.buckets || [];
      // normalizar para array de {name}
      const normalized = list.map((b) => ({ name: b.name || b?.storageNamespace || String(b) }));
      setBuckets(normalized);
      appendOutput("\n" + `Encontrados ${normalized.length} buckets.`);
    } catch (err) {
      setBuckets([]);
      appendOutput("\nErro: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  };

  // -------- DELETE --------
  const handleDelete = async (bucketName: string) => {
    const ok = confirm(`Confirma excluir o bucket '${bucketName}'?`);
    if (!ok) return;

    setOutput(`Deletando bucket '${bucketName}'...`);
    setLoading(true);
    try {
      // DELETE /buckets/{bucket}
      await callApi(`/buckets/${encodeURIComponent(bucketName)}`, "DELETE");
      appendOutput(`\nBucket '${bucketName}' deletado com sucesso.`);

      // remover da lista local
      setBuckets((prev) => prev.filter((b) => b.name !== bucketName));
    } catch (err) {
      appendOutput("\nErro: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 12, fontFamily: "sans-serif" }}>
      <h3>Ações de Bucket</h3>
      <div style={{ marginBottom: 8 }}>
        <button onClick={handleCreate} disabled={loading}>Criar bucket</button>{" "}
        <button onClick={handleList} disabled={loading}>Listar buckets</button>{" "}
        <button onClick={() => { setBuckets([]); setOutput(""); }} disabled={loading}>Limpar</button>{" "}
        {onBack ? <button onClick={onBack}>Voltar</button> : null}
      </div>

      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <strong>Buckets (grupo):</strong>
          <div style={{ marginTop: 6 }}>
            {buckets.length === 0 && <div style={{ color: "#666" }}>Nenhum bucket listado.</div>}
            <ul>
              {buckets.map((b) => (
                <li key={b.name} style={{ marginBottom: 6 }}>
                  <span style={{ marginRight: 12 }}>{b.name}</span>
                  <button onClick={() => handleDelete(b.name)} disabled={loading}>Deletar</button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div style={{ width: 420 }}>
          <strong>Output / Logs</strong>
          <pre style={{ whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto", background: "#f7f7f7", padding: 8 }}>
            {output}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default BucketActions;
