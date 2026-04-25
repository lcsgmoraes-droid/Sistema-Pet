import { useCallback, useEffect, useRef, useState } from "react";

import { vetApi } from "./vetApi";

export function useInternacaoOperacional({ setErro }) {
  const [agendaProcedimentos, setAgendaProcedimentos] = useState([]);
  const [totalBaias, setTotalBaias] = useState(12);
  const [agendaCarregando, setAgendaCarregando] = useState(false);
  const [configInternacaoCarregada, setConfigInternacaoCarregada] = useState(false);
  const configBaiasInicializadaRef = useRef(false);

  const carregarAgendaProcedimentos = useCallback(async () => {
    setAgendaCarregando(true);
    try {
      const res = await vetApi.listarProcedimentosAgendaInternacao({ status: "ativos" });
      setAgendaProcedimentos(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      setAgendaProcedimentos([]);
      setErro(e?.response?.data?.detail ?? "Erro ao carregar agenda de procedimentos da internacao.");
    } finally {
      setAgendaCarregando(false);
    }
  }, [setErro]);

  useEffect(() => {
    carregarAgendaProcedimentos();
  }, [carregarAgendaProcedimentos]);

  useEffect(() => {
    let ativo = true;

    async function carregarConfigInternacao() {
      try {
        const res = await vetApi.obterConfigInternacao();
        const total = Number.parseInt(res.data?.total_baias ?? "12", 10);
        if (ativo && Number.isFinite(total) && total > 0) {
          setTotalBaias(Math.max(1, Math.min(200, total)));
        }
      } catch (e) {
        if (ativo) {
          setErro(e?.response?.data?.detail ?? "Erro ao carregar configuracao de baias da internacao.");
        }
      } finally {
        if (ativo) setConfigInternacaoCarregada(true);
      }
    }

    carregarConfigInternacao();
    return () => {
      ativo = false;
    };
  }, [setErro]);

  useEffect(() => {
    if (!configInternacaoCarregada) return undefined;
    if (!configBaiasInicializadaRef.current) {
      configBaiasInicializadaRef.current = true;
      return undefined;
    }

    const timer = setTimeout(async () => {
      try {
        await vetApi.atualizarConfigInternacao({ total_baias: totalBaias });
      } catch (e) {
        setErro(e?.response?.data?.detail ?? "Erro ao salvar total de baias da internacao.");
      }
    }, 600);

    return () => clearTimeout(timer);
  }, [configInternacaoCarregada, setErro, totalBaias]);

  return {
    agendaCarregando,
    agendaProcedimentos,
    carregarAgendaProcedimentos,
    setAgendaProcedimentos,
    setTotalBaias,
    totalBaias,
  };
}
