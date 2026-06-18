import { useEffect, useState } from "react";

import { vetApi } from "../vetApi";
import {
  mapConsultaParaForm,
  mapPrescricoesParaForm,
  mapProcedimentosParaForm,
} from "./consultaFormMappers";

export default function useConsultaEdicaoLoader({ isEdicao, consultaId, setForm, setErro }) {
  const [finalizado, setFinalizado] = useState(false);
  const [carregando, setCarregando] = useState(isEdicao);

  useEffect(() => {
    if (!isEdicao) return;

    async function carregarConsulta() {
      try {
        const res = await vetApi.obterConsulta(consultaId);
        const consulta = res.data;
        const formConsulta = mapConsultaParaForm(consulta);

        if (consulta.status === "finalizada") {
          const [prescricoesRes, procedimentosRes] = await Promise.all([
            vetApi.listarPrescricoes(consultaId),
            vetApi.listarProcedimentosConsulta(consultaId),
          ]);
          formConsulta.prescricao_itens = mapPrescricoesParaForm(prescricoesRes.data);
          formConsulta.procedimentos_realizados = mapProcedimentosParaForm(procedimentosRes.data);
          setFinalizado(true);
        }

        setForm((prev) => ({ ...prev, ...formConsulta }));
      } catch {
        setErro("Nao foi possivel carregar a consulta.");
      } finally {
        setCarregando(false);
      }
    }

    carregarConsulta();
  }, [consultaId, isEdicao, setErro, setForm]);

  return {
    carregando,
    finalizado,
    setFinalizado,
  };
}
