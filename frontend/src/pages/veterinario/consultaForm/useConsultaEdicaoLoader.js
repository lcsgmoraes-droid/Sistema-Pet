import { useEffect, useState } from "react";

import { vetApi } from "../vetApi";
import { mapConsultaParaForm } from "./consultaFormState";

export default function useConsultaEdicaoLoader({
  isEdicao,
  consultaId,
  setForm,
  setErro,
}) {
  const [finalizado, setFinalizado] = useState(false);
  const [carregando, setCarregando] = useState(isEdicao);

  useEffect(() => {
    if (!isEdicao) return;
    vetApi
      .obterConsulta(consultaId)
      .then((res) => {
        const consulta = res.data;
        setForm((prev) => ({ ...prev, ...mapConsultaParaForm(consulta) }));
        if (consulta.status === "finalizada") setFinalizado(true);
      })
      .catch(() => setErro("Não foi possível carregar a consulta."))
      .finally(() => setCarregando(false));
  }, [consultaId, isEdicao, setErro, setForm]);

  return {
    carregando,
    finalizado,
    setFinalizado,
  };
}
