import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8001",
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;

    if (status === 401) {
      console.warn("Sessão inválida ou tenant não selecionado");

      localStorage.removeItem("access_token");
      localStorage.removeItem("tenants");

      window.location.href = "/login";
    }

    if (status === 403) {
      console.warn("Acesso negado para este tenant");
    }

    return Promise.reject(error);
  }
);
