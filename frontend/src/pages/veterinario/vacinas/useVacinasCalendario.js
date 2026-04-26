import { useState } from "react";

import { vetApi } from "../vetApi";

export function useVacinasCalendario() {
  const [calendario, setCalendario] = useState([]);
  const [especieCalendario, setEspecieCalendario] = useState("");
  const [carregandoCalendario, setCarregandoCalendario] = useState(false);

  async function carregarCalendarioPreventivo() {
    setCarregandoCalendario(true);

    try {
      const res = await vetApi.calendarioPreventivo(especieCalendario || undefined);
      setCalendario(res.data?.items ?? []);
    } catch {
      setCalendario([]);
    } finally {
      setCarregandoCalendario(false);
    }
  }

  return {
    calendario,
    carregarCalendarioPreventivo,
    carregandoCalendario,
    especieCalendario,
    setEspecieCalendario,
  };
}
