const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE_URL) {
  throw new Error("VITE_API_BASE_URL não definida");
}

export async function createBucket(payload: any, token: string) {
  const response = await fetch(`${API_BASE_URL}/buckets`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "Erro ao criar bucket");
  }

  return response.json();
}
