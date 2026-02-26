import axios from "axios";

const configuredApiUrl = import.meta.env.VITE_API_URL;
const baseURL = configuredApiUrl || "/api";

export const api = axios.create({
  baseURL,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token") || localStorage.getItem("token");

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
      console.warn("Sessao invalida ou tenant nao selecionado");

      localStorage.removeItem("access_token");
      localStorage.removeItem("token");
      localStorage.removeItem("tenants");

      window.location.href = "/login";
    }

    if (status === 403) {
      console.warn("Acesso negado para este tenant");
    }

    return Promise.reject(error);
  }
);
