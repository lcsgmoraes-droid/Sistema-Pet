import { useEffect, useState } from "react";
import api from "../api";
import { useAuth } from "../contexts/AuthContext";

export function useVisaoComercial() {
  const { user } = useAuth();
  const [estado, setEstado] = useState({ user: null, visao: null, erro: "" });
  const [tentativa, setTentativa] = useState(0);
  useEffect(() => {
    let ativo = true;
    let controller;
    const carregar = async () => {
      controller?.abort();
      controller = new AbortController();
      const signal = controller.signal;
      try {
        const { data } = await api.get("/empresa/config/visao-comercial", { signal });
        if (ativo && !signal.aborted) setEstado({ user, visao: data.visao_comercial, erro: "" });
      } catch {
        if (ativo && !signal.aborted)
          setEstado({
            user,
            visao: null,
            erro: "Não foi possível carregar a preferência da empresa.",
          });
      }
    };
    carregar();
    globalThis.addEventListener("visao-comercial-atualizada", carregar);
    globalThis.addEventListener("focus", carregar);
    return () => {
      ativo = false;
      controller?.abort();
      globalThis.removeEventListener("visao-comercial-atualizada", carregar);
      globalThis.removeEventListener("focus", carregar);
    };
  }, [user, tentativa]);
  return {
    ...(estado.user === user ? estado : { visao: null, erro: "" }),
    tentarNovamente: () => setTentativa((n) => n + 1),
  };
}
