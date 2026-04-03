import { useCallback, useEffect, useState } from "react";
import api from "../api";

export function useCampanhasConsultas({ createDefaultPremio, hoje, primeiroDiaMes }) {
  const [aba, setAba] = useState("dashboard");

  const [campanhas, setCampanhas] = useState([]);
  const [loadingCampanhas, setLoadingCampanhas] = useState(true);

  const [dashboard, setDashboard] = useState(null);
  const [loadingDashboard, setLoadingDashboard] = useState(true);

  const [retencaoRegras, setRetencaoRegras] = useState([]);
  const [loadingRetencao, setLoadingRetencao] = useState(false);

  const [ranking, setRanking] = useState(null);
  const [loadingRanking, setLoadingRanking] = useState(false);
  const [filtroNivel, setFiltroNivel] = useState("todos");

  const [cupons, setCupons] = useState([]);
  const [loadingCupons, setLoadingCupons] = useState(true);
  const [filtroCupomStatus, setFiltroCupomStatus] = useState("active");
  const [filtroCupomBusca, setFiltroCupomBusca] = useState("");
  const [filtroCupomDataInicio, setFiltroCupomDataInicio] = useState("");
  const [filtroCupomDataFim, setFiltroCupomDataFim] = useState("");
  const [filtroCupomCampanha, setFiltroCupomCampanha] = useState("");
  const [cupomDetalhes, setCupomDetalhes] = useState(null);

  const [destaque, setDestaque] = useState(null);
  const [loadingDestaque, setLoadingDestaque] = useState(false);
  const [premiosPorVencedor, setPremiosPorVencedor] = useState({});
  const [vencedoresSelecionados, setVencedoresSelecionados] = useState({});

  const [sorteios, setSorteios] = useState([]);
  const [loadingSorteios, setLoadingSorteios] = useState(false);
  const [codigosOffline, setCodigosOffline] = useState([]);
  const [loadingCodigosOffline, setLoadingCodigosOffline] = useState(false);

  const [sugestoes, setSugestoes] = useState([]);
  const [loadingSugestoes, setLoadingSugestoes] = useState(false);

  const [relatorio, setRelatorio] = useState(null);
  const [loadingRelatorio, setLoadingRelatorio] = useState(false);
  const [relDataInicio, setRelDataInicio] = useState(primeiroDiaMes || hoje);
  const [relDataFim, setRelDataFim] = useState(hoje);
  const [relTipo, setRelTipo] = useState("todos");

  const [rankingConfig, setRankingConfig] = useState(null);
  const [rankingConfigLoading, setRankingConfigLoading] = useState(false);

  const [schedulerConfig, setSchedulerConfig] = useState(null);
  const [schedulerConfigLoading, setSchedulerConfigLoading] = useState(false);

  const carregarDashboard = useCallback(async () => {
    setLoadingDashboard(true);
    try {
      const res = await api.get("/campanhas/dashboard");
      setDashboard(res.data);
    } catch (e) {
      console.error("Erro ao carregar dashboard:", e);
    } finally {
      setLoadingDashboard(false);
    }
  }, []);

  const carregarCampanhas = useCallback(async () => {
    setLoadingCampanhas(true);
    try {
      try {
        await api.post("/campanhas/seed");
      } catch {
        // seed é idempotente
      }
      const res = await api.get("/campanhas");
      setCampanhas(res.data);
    } catch (e) {
      console.error("Erro ao carregar campanhas:", e);
    } finally {
      setLoadingCampanhas(false);
    }
  }, []);

  const carregarRanking = useCallback(async () => {
    setLoadingRanking(true);
    try {
      const params = filtroNivel !== "todos" ? `?nivel=${filtroNivel}` : "";
      const res = await api.get(`/campanhas/ranking${params}`);
      setRanking(res.data);
    } catch (e) {
      console.error("Erro ao carregar ranking:", e);
    } finally {
      setLoadingRanking(false);
    }
  }, [filtroNivel]);

  const carregarCupons = useCallback(async () => {
    setLoadingCupons(true);
    try {
      const params = new URLSearchParams();
      if (filtroCupomStatus !== "todos") params.set("status", filtroCupomStatus);
      if (filtroCupomBusca.trim()) params.set("busca", filtroCupomBusca.trim());
      if (filtroCupomDataInicio) params.set("data_inicio", filtroCupomDataInicio);
      if (filtroCupomDataFim) params.set("data_fim", filtroCupomDataFim);
      if (filtroCupomCampanha) params.set("campaign_id", filtroCupomCampanha);
      const qs = params.toString() ? `?${params.toString()}` : "";
      const res = await api.get(`/campanhas/cupons${qs}`);
      setCupons(res.data);
    } catch (e) {
      console.error("Erro ao carregar cupons:", e);
    } finally {
      setLoadingCupons(false);
    }
  }, [
    filtroCupomStatus,
    filtroCupomBusca,
    filtroCupomDataInicio,
    filtroCupomDataFim,
    filtroCupomCampanha,
  ]);

  const carregarRelatorio = useCallback(async () => {
    setLoadingRelatorio(true);
    try {
      const params = new URLSearchParams();
      if (relDataInicio) params.set("data_inicio", relDataInicio);
      if (relDataFim) params.set("data_fim", relDataFim);
      if (relTipo !== "todos") params.set("tipo", relTipo);
      const res = await api.get(`/campanhas/relatorio?${params}`);
      setRelatorio(res.data);
    } catch (e) {
      console.error("Erro ao carregar relatório:", e);
    } finally {
      setLoadingRelatorio(false);
    }
  }, [relDataInicio, relDataFim, relTipo]);

  const carregarDestaque = useCallback(async () => {
    setLoadingDestaque(true);
    try {
      const res = await api.get("/campanhas/destaque-mensal");
      setDestaque(res.data);
      const inicial = {};
      const selecionados = {};
      for (const cat of Object.keys(res.data.vencedores || {})) {
        inicial[cat] = createDefaultPremio();
        selecionados[cat] = true;
      }
      setPremiosPorVencedor(inicial);
      setVencedoresSelecionados(selecionados);
    } catch (e) {
      console.error("Erro ao carregar destaque:", e);
    } finally {
      setLoadingDestaque(false);
    }
  }, [createDefaultPremio]);

  const carregarSorteios = useCallback(async () => {
    setLoadingSorteios(true);
    try {
      const res = await api.get("/campanhas/sorteios");
      setSorteios(res.data);
    } catch (e) {
      console.error("Erro ao carregar sorteios:", e);
    } finally {
      setLoadingSorteios(false);
    }
  }, []);

  const carregarSugestoes = useCallback(async () => {
    setLoadingSugestoes(true);
    try {
      const res = await api.get("/campanhas/unificacao/sugestoes");
      setSugestoes(res.data);
    } catch (e) {
      console.error("Erro ao carregar sugestões:", e);
    } finally {
      setLoadingSugestoes(false);
    }
  }, []);

  const carregarRetencao = useCallback(async () => {
    setLoadingRetencao(true);
    try {
      const res = await api.get("/campanhas/retencao");
      setRetencaoRegras(res.data);
    } catch (e) {
      console.error("Erro ao carregar regras de retenção", e);
    } finally {
      setLoadingRetencao(false);
    }
  }, []);

  const carregarRankingConfig = useCallback(async () => {
    setRankingConfigLoading(true);
    try {
      const res = await api.get("/campanhas/ranking/config");
      setRankingConfig(res.data);
    } catch (e) {
      console.error("Erro ao carregar config de ranking:", e);
    } finally {
      setRankingConfigLoading(false);
    }
  }, []);

  const carregarSchedulerConfig = useCallback(async () => {
    setSchedulerConfigLoading(true);
    try {
      const res = await api.get("/campanhas/config/horarios");
      setSchedulerConfig(res.data);
    } catch (e) {
      console.error("Erro ao carregar config de horários:", e);
    } finally {
      setSchedulerConfigLoading(false);
    }
  }, []);

  useEffect(() => {
    carregarDashboard();
  }, [carregarDashboard]);

  useEffect(() => {
    carregarCampanhas();
  }, [carregarCampanhas]);

  useEffect(() => {
    if (aba === "ranking") {
      carregarRanking();
      carregarRankingConfig();
    }
  }, [aba, carregarRanking, carregarRankingConfig]);

  useEffect(() => {
    if (aba === "config") carregarSchedulerConfig();
  }, [aba, carregarSchedulerConfig]);

  useEffect(() => {
    if (aba === "destaque") carregarDestaque();
  }, [aba, carregarDestaque]);

  useEffect(() => {
    if (aba === "sorteios") carregarSorteios();
  }, [aba, carregarSorteios]);

  useEffect(() => {
    if (aba === "unificacao") carregarSugestoes();
  }, [aba, carregarSugestoes]);

  useEffect(() => {
    carregarCupons();
  }, [carregarCupons]);

  useEffect(() => {
    if (aba === "relatorios") carregarRelatorio();
  }, [aba, carregarRelatorio]);

  useEffect(() => {
    if (aba === "retencao") carregarRetencao();
  }, [aba, carregarRetencao]);

  return {
    aba,
    setAba,
    campanhas,
    setCampanhas,
    loadingCampanhas,
    dashboard,
    loadingDashboard,
    retencaoRegras,
    setRetencaoRegras,
    loadingRetencao,
    ranking,
    setRanking,
    loadingRanking,
    filtroNivel,
    setFiltroNivel,
    cupons,
    setCupons,
    loadingCupons,
    filtroCupomStatus,
    setFiltroCupomStatus,
    filtroCupomBusca,
    setFiltroCupomBusca,
    filtroCupomDataInicio,
    setFiltroCupomDataInicio,
    filtroCupomDataFim,
    setFiltroCupomDataFim,
    filtroCupomCampanha,
    setFiltroCupomCampanha,
    cupomDetalhes,
    setCupomDetalhes,
    destaque,
    setDestaque,
    loadingDestaque,
    premiosPorVencedor,
    setPremiosPorVencedor,
    vencedoresSelecionados,
    setVencedoresSelecionados,
    sorteios,
    setSorteios,
    loadingSorteios,
    codigosOffline,
    setCodigosOffline,
    loadingCodigosOffline,
    setLoadingCodigosOffline,
    sugestoes,
    setSugestoes,
    loadingSugestoes,
    relatorio,
    setRelatorio,
    loadingRelatorio,
    relDataInicio,
    setRelDataInicio,
    relDataFim,
    setRelDataFim,
    relTipo,
    setRelTipo,
    rankingConfig,
    setRankingConfig,
    rankingConfigLoading,
    schedulerConfig,
    setSchedulerConfig,
    schedulerConfigLoading,
    carregarCampanhas,
    carregarCupons,
    carregarRetencao,
    carregarRanking,
    carregarDestaque,
    carregarSorteios,
    carregarSugestoes,
    carregarRelatorio,
    carregarRankingConfig,
    carregarSchedulerConfig,
  };
}
