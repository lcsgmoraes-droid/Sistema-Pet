import { useCallback, useEffect, useMemo, useState } from "react";

import { vetApi } from "../vetApi";
import { calcularTotaisRepasse, periodoInicial } from "./repasseUtils";

export function useVetRepasse() {
  const periodo = periodoInicial();
  const [dataInicio, setDataInicio] = useState(periodo.primeiroDiaMes);
  const [dataFim, setDataFim] = useState(periodo.hoje);
  const [filtroStatus, setFiltroStatus] = useState("");
  const [filtroTipo, setFiltroTipo] = useState("");
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [baixando, setBaixando] = useState(null);
  const [estornando, setEstornando] = useState(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const params = {};
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;
      if (filtroStatus) params.status = filtroStatus;
      const res = await vetApi.relatorioRepasse(params);
      setDados(res.data);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao carregar relatorio de repasse.");
    } finally {
      setCarregando(false);
    }
  }, [dataInicio, dataFim, filtroStatus]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const darBaixa = useCallback(
    async (contaId) => {
      const confirmado = window.confirm(
        "Confirmar o recebimento integral deste lançamento na data de hoje?",
      );
      if (!confirmado) return;
      setBaixando(contaId);
      try {
        await vetApi.baixarRepasse(contaId);
        await carregar();
      } catch (e) {
        setErro(e?.response?.data?.detail ?? "Erro ao dar baixa no lancamento.");
      } finally {
        setBaixando(null);
      }
    },
    [carregar],
  );

  const estornarBaixa = useCallback(
    async (contaId) => {
      const confirmado = window.confirm(
        "Estornar esta baixa? O lançamento voltará para o status pendente.",
      );
      if (!confirmado) return;
      setEstornando(contaId);
      setErro(null);
      try {
        await vetApi.estornarBaixaRepasse(contaId);
        await carregar();
      } catch (e) {
        setErro(e?.response?.data?.detail ?? "Erro ao estornar a baixa.");
      } finally {
        setEstornando(null);
      }
    },
    [carregar],
  );

  const itensFiltrados = useMemo(
    () => (dados?.items ?? []).filter((item) => !filtroTipo || item.tipo === filtroTipo),
    [dados?.items, filtroTipo],
  );

  const totais = useMemo(() => calcularTotaisRepasse(itensFiltrados), [itensFiltrados]);

  return {
    baixando,
    carregar,
    carregando,
    dados,
    darBaixa,
    estornarBaixa,
    estornando,
    dataFim,
    dataInicio,
    erro,
    filtroStatus,
    filtroTipo,
    itensFiltrados,
    setDataFim,
    setDataInicio,
    setFiltroStatus,
    setFiltroTipo,
    ...totais,
  };
}
