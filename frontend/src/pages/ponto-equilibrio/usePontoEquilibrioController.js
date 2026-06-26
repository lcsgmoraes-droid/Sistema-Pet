import { useMemo, useState, useEffect } from "react";
import api from "../../api";
import {
  calcularImpactoPontoEquilibrio,
  montarAnaliseCustosPontoEquilibrio,
} from "../pontoEquilibrioImpactoUtils";
import {
  DEFAULT_IMPACTO_FORM,
  PONTO_EQUILIBRIO_REQUEST_TIMEOUT_MS,
} from "./pontoEquilibrioConstants";
import {
  buildInitialFilters,
  getStatusResumo,
  montarParametrosPontoEquilibrio,
} from "./pontoEquilibrioUtils";

export default function usePontoEquilibrioController() {
  const [filtros, setFiltros] = useState(buildInitialFilters);
  const [impactoForm, setImpactoForm] = useState(DEFAULT_IMPACTO_FORM);
  const [abaAtiva, setAbaAtiva] = useState("resumo");
  const [porteAnalise, setPorteAnalise] = useState("pequeno");
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");
  const [linhaDetalhe, setLinhaDetalhe] = useState(null);
  const [detalhesLinha, setDetalhesLinha] = useState(null);
  const [loadingDetalhes, setLoadingDetalhes] = useState(false);

  const percentualAtingido = Math.min(Number(dados?.percentual_atingido || 0), 100);
  const margemUsadaPercentual = Number(
    dados?.margem_usada_percentual ?? dados?.margem_contribuicao_percentual ?? 0,
  );
  const margemPeriodoPercentual = Number(
    dados?.margem_periodo_percentual ?? dados?.margem_contribuicao_percentual ?? 0,
  );
  const impactoValor = Number(impactoForm.valor || 0);

  const impactoSimulado = useMemo(() => {
    if (!dados) return null;
    return calcularImpactoPontoEquilibrio({
      despesasFixas: dados.despesas_fixas,
      pontoEquilibrio: dados.ponto_equilibrio,
      margemContribuicaoPercentual:
        dados.margem_usada_percentual ?? dados.margem_contribuicao_percentual,
      faturamento: dados.faturamento,
      faturamentoProjetado: impactoForm.faturamento,
      ticketMedio: dados.ticket_medio_usado ?? dados.ticket_medio,
      impactoCustoFixo: impactoValor,
    });
  }, [dados, impactoForm.faturamento, impactoValor]);

  const analiseCustos = useMemo(() => {
    if (!dados) return null;
    return montarAnaliseCustosPontoEquilibrio({
      dados,
      porte: porteAnalise,
      faturamentoProjetado: impactoForm.faturamento,
      impactoCustoFixo: impactoValor,
      impactoDescricao: impactoForm.descricao,
    });
  }, [dados, impactoForm.descricao, impactoForm.faturamento, impactoValor, porteAnalise]);

  const statusResumo = useMemo(() => getStatusResumo(dados), [dados]);

  function fecharDetalhesPontoEquilibrio() {
    setLinhaDetalhe(null);
    setDetalhesLinha(null);
    setLoadingDetalhes(false);
  }

  const carregarDados = async () => {
    setLoading(true);
    setErro("");
    fecharDetalhesPontoEquilibrio();
    try {
      const response = await api.get("/financeiro/ponto-equilibrio", {
        params: montarParametrosPontoEquilibrio(filtros),
        timeout: PONTO_EQUILIBRIO_REQUEST_TIMEOUT_MS,
      });
      setDados(response.data);
    } catch (error) {
      console.error("Erro ao carregar ponto de equilibrio:", error);
      setErro(error.response?.data?.detail || "Nao foi possivel carregar o ponto de equilibrio.");
    } finally {
      setLoading(false);
    }
  };

  const abrirDetalhesPontoEquilibrio = async (linha, page = 1) => {
    if (!linha?.grupo) return;

    setLinhaDetalhe(linha);
    setLoadingDetalhes(true);
    setErro("");
    try {
      const response = await api.get("/financeiro/ponto-equilibrio/detalhes", {
        params: montarParametrosPontoEquilibrio(filtros, {
          grupo: linha.grupo,
          page,
          page_size: 30,
        }),
        timeout: PONTO_EQUILIBRIO_REQUEST_TIMEOUT_MS,
      });
      setDetalhesLinha(response.data);
    } catch (error) {
      console.error("Erro ao carregar detalhes do ponto de equilibrio:", error);
      setErro(error.response?.data?.detail || "Nao foi possivel carregar os detalhes desta linha.");
    } finally {
      setLoadingDetalhes(false);
    }
  };

  useEffect(() => {
    carregarDados();
  }, []);

  return {
    abaAtiva,
    abrirDetalhesPontoEquilibrio,
    analiseCustos,
    carregarDados,
    dados,
    detalhesLinha,
    erro,
    fecharDetalhesPontoEquilibrio,
    filtros,
    impactoForm,
    impactoSimulado,
    impactoValor,
    linhaDetalhe,
    loading,
    loadingDetalhes,
    margemPeriodoPercentual,
    margemUsadaPercentual,
    percentualAtingido,
    porteAnalise,
    setAbaAtiva,
    setFiltros,
    setImpactoForm,
    setPorteAnalise,
    statusResumo,
  };
}
