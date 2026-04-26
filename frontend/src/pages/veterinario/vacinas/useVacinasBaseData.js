import { useCallback, useEffect, useState } from "react";

import { api } from "../../../services/api";
import { vetApi } from "../vetApi";
import { normalizarVacinas } from "./vacinaUtils";

export function useVacinasBaseData() {
  const [pets, setPets] = useState([]);
  const [veterinarios, setVeterinarios] = useState([]);
  const [vacinasVencendo, setVacinasVencendo] = useState([]);
  const [protocolos, setProtocolos] = useState([]);

  const carregarVencendo = useCallback(async () => {
    try {
      const res = await vetApi.vacinasVencendo(30);
      setVacinasVencendo(normalizarVacinas(res.data));
    } catch {}
  }, []);

  useEffect(() => {
    api.get("/pets", { params: { limit: 500 } })
      .then((res) => setPets(res.data?.items ?? res.data ?? []))
      .catch(() => {});

    vetApi.listarVeterinarios()
      .then((res) => setVeterinarios(Array.isArray(res.data) ? res.data : []))
      .catch(() => setVeterinarios([]));

    vetApi.listarProtocolosVacinas()
      .then((res) => setProtocolos(Array.isArray(res.data) ? res.data : []))
      .catch(() => setProtocolos([]));

    carregarVencendo();
  }, [carregarVencendo]);

  return {
    carregarVencendo,
    pets,
    protocolos,
    vacinasVencendo,
    veterinarios,
  };
}
