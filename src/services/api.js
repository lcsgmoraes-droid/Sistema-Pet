import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
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

export default api;
