import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || ""; // se usar proxy, deixe vazio; ou set VITE_API_BASE

const api = axios.create({
  baseURL: API_BASE,
  // timeout: 10000,
});

export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
  }
}

export default api;