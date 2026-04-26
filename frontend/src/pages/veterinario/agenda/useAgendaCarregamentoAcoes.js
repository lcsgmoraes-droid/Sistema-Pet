import { useCallback } from "react";

import { vetApi } from "../vetApi";
import { listarAgendamentosDia, sugerirHoraLivreAgenda } from "./agendaFormUtils";
import { addDias, fimMes, inicioMes, isoDate } from "./agendaUtils";

export function useAgendaCarregamentoAcoes({
  agendamentos,
  dataRef,
  fimSemana,
  inicioSemana,
  modo,
  setAgendamentos,
  setCarregando,
  setDataRef,
  setErro,
}) {
  const carregar = useCallback(async () => {
    const dataInicioConsulta = modo === "mes" ? inicioMes(dataRef) : inicioSemana;
    const dataFimConsulta = modo === "mes" ? fimMes(dataRef) : fimSemana;

    try {
      setCarregando(true);
      setErro(null);
      const res = await vetApi.listarAgendamentos({
        data_inicio: isoDate(dataInicioConsulta),
        data_fim: isoDate(dataFimConsulta),
      });
      const data = res.data;
      setAgendamentos(Array.isArray(data) ? data : data.items ?? []);
    } catch {
      setErro("Erro ao carregar agenda.");
    } finally {
      setCarregando(false);
    }
  }, [dataRef, fimSemana, inicioSemana, modo, setAgendamentos, setCarregando, setErro]);

  const nav = useCallback(
    (direcao) => {
      if (modo === "mes") {
        setDataRef((d) => new Date(d.getFullYear(), d.getMonth() + direcao, 1));
        return;
      }
      const delta = modo === "dia" ? 1 : 7;
      setDataRef((d) => addDias(d, direcao * delta));
    },
    [modo, setDataRef]
  );

  const agsDia = useCallback((data) => listarAgendamentosDia(agendamentos, data), [agendamentos]);

  const sugerirHoraLivre = useCallback(
    (data) => sugerirHoraLivreAgenda(listarAgendamentosDia(agendamentos, data)),
    [agendamentos]
  );

  return {
    agsDia,
    carregar,
    nav,
    sugerirHoraLivre,
  };
}
