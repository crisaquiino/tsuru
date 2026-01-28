import { useState, useEffect } from "react";
import Login from "./components/Login";
import GroupsList from "./components/GroupsList";
import BucketActions from "./components/BucketActions";

type MemberOfItem = {
  id: string | null;
  displayName: string | null;
  odata_type: string | null;
};

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<MemberOfItem | null>(null);

  // "steps" depois do login: grupos ou buckets
  const [view, setView] = useState<"groups" | "buckets">("groups");

  // Carregar token/email armazenados ao abrir página
  useEffect(() => {
    const savedToken = localStorage.getItem("api_token");
    const savedEmail = localStorage.getItem("user_email");
    if (savedToken && savedEmail) {
      setToken(savedToken);
      setEmail(savedEmail);
    }
  }, []);

  function handleLoginSuccess(tok: string, em: string) {
    localStorage.setItem("api_token", tok);
    localStorage.setItem("user_email", em);
    setToken(tok);
    setEmail(em);
    setView("groups"); // sempre começa na tela de grupos após login
  }

  function logout() {
    localStorage.removeItem("api_token");
    localStorage.removeItem("user_email");
    setToken(null);
    setEmail(null);
    setSelectedGroup(null);
    setView("groups");
  }

  // Tela de Login
  if (!token) {
    return <Login onSuccess={handleLoginSuccess} />;
  }

  // Área protegida (após login)
  return (
    <div
      style={{
        maxWidth: 900,
        margin: "1rem auto",
        padding: 20,
        border: "1px solid #ddd",
        borderRadius: 8,
      }}
    >
      <h2>Bem-vindo</h2>
      <p>
        Você entrou como <strong>{email}</strong>
      </p>

      <button
        onClick={logout}
        style={{ marginBottom: 20, padding: "6px 12px" }}
      >
        Sair
      </button>

      <hr />

      {view === "groups" && (
        <>
          <h3>Selecione um grupo do Azure AD</h3>

          <GroupsList
            multiSelect={false}
            onSelect={(item) => {
              console.log("Grupo selecionado:", item);
              // como multiSelect = false, o onSelect recebe 1 item ou null
              if (item && !Array.isArray(item)) {
                setSelectedGroup(item);
              } else {
                setSelectedGroup(null);
              }
            }}
            onAuthError={() => {
              // Se o backend retornar 401/403
              logout();
            }}
          />

          {selectedGroup && (
            <div
              style={{
                marginTop: 20,
                padding: 12,
                border: "1px solid #ccc",
                borderRadius: 6,
              }}
            >
              <h4>Grupo selecionado:</h4>
              <p>
                <strong>{selectedGroup.displayName}</strong> <br />
                <small>ID: {selectedGroup.id}</small>
              </p>
            </div>
          )}

          <button
            style={{ marginTop: 20, padding: "6px 12px" }}
            disabled={!selectedGroup}
            onClick={() => {
              if (!selectedGroup) return;
              setView("buckets"); // vai para a tela de ações de bucket
            }}
          >
            Next
          </button>
        </>
      )}

      {view === "buckets" && (
        <>
          <h3>Ações de Bucket</h3>

          {!selectedGroup ? (
            <>
              <p>Nenhum grupo selecionado.</p>
              <button
                style={{ marginTop: 10, padding: "6px 12px" }}
                onClick={() => setView("groups")}
              >
                Voltar para seleção de grupo
              </button>
            </>
          ) : (
            <>
              <p>
                Grupo selecionado:{" "}
                <strong>{selectedGroup.displayName}</strong>
                <br />
                <small>ID: {selectedGroup.id}</small>
              </p>

              {/* Aqui o BucketActions pode usar o grupo e o token via props */}
              <BucketActions
                selectedGroup={selectedGroup}
                token={token!}
                email={email}
                onBack={() => setView("groups")}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}
