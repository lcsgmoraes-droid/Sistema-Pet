import { useCallback, useEffect, useMemo, useState } from "react";

import { isoDate } from "../agenda/agendaUtils";
import { filtrarAgendamentosClinicosAbertos } from "../fluxoConsultaAgendamentoUtils";
import { vetApi } from "../vetApi";
import {
  CONSULTAS_POR_PAGINA,
  filtrarConsultas,
  removerConsultasSelecionadas,
  todasConsultasVisiveisSelecionadas,
  toggleConsultaSelecionada,
  toggleTodasConsultasSelecionadas,
} from "./consultasUtils";

export function useVetConsultas() {
  const [consultas, setConsultas] = useState([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [agendamentosHoje, setAgendamentosHoje] = useState([]);
  const [carregandoAgendaHoje, setCarregandoAgendaHoje] = useState(true);
  const [erroAgendaHoje, setErroAgendaHoje] = useState(null);
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");
  const [consultasSelecionadas, setConsultasSelecionadas] = useState([]);
  const [excluindoConsultas, setExcluindoConsultas] = useState(false);
  const [erroExclusao, setErroExclusao] = useState(null);

  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      setErro(null);
      const res = await vetApi.listarConsultas({
        skip: (pagina - 1) * CONSULTAS_POR_PAGINA,
        limit: CONSULTAS_POR_PAGINA,
        status: filtroStatus || undefined,
      });
      const data = res.data;

      if (Array.isArray(data)) {
        setConsultas(data);
        setTotal(data.length);
        setConsultasSelecionadas((atuais) => atuais.filter((id) => data.some((consulta) => Number(consulta.id) === id)));
      } else {
        const items = data.items ?? [];
        setConsultas(items);
        setTotal(data.total ?? 0);
        setConsultasSelecionadas((atuais) => atuais.filter((id) => items.some((consulta) => Number(consulta.id) === id)));
      }
    } catch {
      setErro("Nao foi possivel carregar as consultas.");
    } finally {
      setCarregando(false);
    }
  }, [pagina, filtroStatus]);

  const carregarAgendamentosHoje = useCallback(async () => {
    try {
      setCarregandoAgendaHoje(true);
      setErroAgendaHoje(null);
      const hoje = isoDate(new Date());
      const res = await vetApi.listarAgendamentos({ data_inicio: hoje, data_fim: hoje });
      setAgendamentosHoje(filtrarAgendamentosClinicosAbertos(res.data));
    } catch {
      setErroAgendaHoje("Nao foi possivel carregar os agendamentos de hoje.");
    } finally {
      setCarregandoAgendaHoje(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEffect(() => {
    carregarAgendamentosHoje();
  }, [carregarAgendamentosHoje]);

  const consultasFiltradas = useMemo(
    () => filtrarConsultas(consultas, busca),
    [busca, consultas]
  );
  const totalPaginas = Math.ceil(total / CONSULTAS_POR_PAGINA);
  const todasSelecionadas = useMemo(
    () => todasConsultasVisiveisSelecionadas(consultasSelecionadas, consultasFiltradas),
    [consultasFiltradas, consultasSelecionadas]
  );

  function alterarStatus(status) {
    setFiltroStatus(status);
    setPagina(1);
    setConsultasSelecionadas([]);
  }

  function alternarConsultaSelecionada(consultaId) {
    setConsultasSelecionadas((atuais) => toggleConsultaSelecionada(atuais, consultaId));
  }

  function alternarTodasConsultasSelecionadas() {
    setConsultasSelecionadas((atuais) => toggleTodasConsultasSelecionadas(atuais, consultasFiltradas));
  }

  const excluirConsultasSelecionadas = useCallback(async () => {
    if (consultasSelecionadas.length === 0) return;

    const totalSelecionado = consultasSelecionadas.length;
    const confirmado = window.confirm(
      `Deseja excluir ${totalSelecionado} consulta${totalSelecionado > 1 ? "s" : ""} selecionada${totalSelecionado > 1 ? "s" : ""}?`
    );
    if (!confirmado) return;

    try {
      setExcluindoConsultas(true);
      setErroExclusao(null);
      const idsParaExcluir = [...consultasSelecionadas];
      await Promise.all(idsParaExcluir.map((id) => vetApi.removerConsulta(id)));
      setConsultas((atuais) => removerConsultasSelecionadas(atuais, idsParaExcluir));
      setTotal((atual) => Math.max((atual ?? 0) - idsParaExcluir.length, 0));
      setConsultasSelecionadas([]);
      await carregar();
      await carregarAgendamentosHoje();
    } catch (error) {
      setErroExclusao(error?.response?.data?.detail ?? "Nao foi possivel excluir as consultas selecionadas.");
    } finally {
      setExcluindoConsultas(false);
    }
  }, [carregar, carregarAgendamentosHoje, consultasSelecionadas]);

  return {
    alterarStatus,
    agendamentosHoje,
    busca,
    carregando,
    carregandoAgendaHoje,
    consultasFiltradas,
    consultasSelecionadas,
    erro,
    erroAgendaHoje,
    erroExclusao,
    excluindoConsultas,
    excluirConsultasSelecionadas,
    filtroStatus,
    pagina,
    recarregarAgendaHoje: carregarAgendamentosHoje,
    recarregarConsultas: carregar,
    selecionarConsulta: alternarConsultaSelecionada,
    selecionarTodasConsultas: alternarTodasConsultasSelecionadas,
    setBusca,
    setPagina,
    todasSelecionadas,
    total,
    totalPaginas,
  };
}
