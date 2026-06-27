import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import api from "../api";
import ClienteFinanceiroView from "./clienteFinanceiro/ClienteFinanceiroView";

const filtrosIniciais = {
  page: 1,
  per_page: 20,
  data_inicio: "",
  data_fim: "",
  tipo: "",
  status: "",
};

const ClienteFinanceiro = () => {
  const { clienteId } = useParams();
  const navigate = useNavigate();

  const [cliente, setCliente] = useState(null);
  const [resumo, setResumo] = useState(null);
  const [historico, setHistorico] = useState([]);
  const [paginacao, setPaginacao] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedRows, setExpandedRows] = useState({});
  const [detalhesVendas, setDetalhesVendas] = useState({});
  const [loadingDetalhes, setLoadingDetalhes] = useState({});
  const [filtros, setFiltros] = useState(filtrosIniciais);

  const carregarDados = async () => {
    try {
      setLoading(true);
      setError("");

      const params = new URLSearchParams();
      params.append("page", filtros.page);
      params.append("per_page", filtros.per_page);

      if (filtros.data_inicio) params.append("data_inicio", filtros.data_inicio);
      if (filtros.data_fim) params.append("data_fim", filtros.data_fim);
      if (filtros.tipo) params.append("tipo", filtros.tipo);
      if (filtros.status) params.append("status", filtros.status);

      const response = await api.get(`/financeiro/cliente/${clienteId}?${params.toString()}`);

      setCliente(response.data.cliente);
      setResumo(response.data.resumo);
      setHistorico(response.data.historico);
      setPaginacao(response.data.paginacao);
    } catch (err) {
      console.error("Erro ao carregar historico financeiro:", err);
      setError(err.response?.data?.detail || "Erro ao carregar historico financeiro");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (clienteId) {
      carregarDados();
    }
  }, [clienteId, filtros]);

  const mudarPagina = (novaPagina) => {
    setFiltros({ ...filtros, page: novaPagina });
  };

  const aplicarFiltros = (novosFiltros) => {
    setFiltros({ ...filtros, ...novosFiltros, page: 1 });
  };

  const limparFiltros = () => {
    setFiltros(filtrosIniciais);
  };

  const carregarDetalhesVenda = async (vendaId) => {
    if (!vendaId) return;

    try {
      setLoadingDetalhes({ ...loadingDetalhes, [vendaId]: true });
      const response = await api.get(`/vendas/${vendaId}`);
      setDetalhesVendas({ ...detalhesVendas, [vendaId]: response.data });
    } catch (err) {
      console.error("Erro ao carregar detalhes da venda:", err);
    } finally {
      setLoadingDetalhes({ ...loadingDetalhes, [vendaId]: false });
    }
  };

  const toggleExpansao = async (transacao, index) => {
    const key = `${transacao.tipo}-${index}`;

    if (expandedRows[key]) {
      setExpandedRows({ ...expandedRows, [key]: false });
      return;
    }

    setExpandedRows({ ...expandedRows, [key]: true });

    const vendaId = transacao.detalhes?.venda_id;
    if (transacao.tipo === "venda" && !detalhesVendas[vendaId]) {
      await carregarDetalhesVenda(vendaId);
    }
  };

  const navegarParaVenda = (vendaId) => {
    if (vendaId) {
      navigate(`/pdv?venda=${vendaId}`);
    }
  };

  return (
    <ClienteFinanceiroView
      cliente={cliente}
      detalhesVendas={detalhesVendas}
      error={error}
      expandedRows={expandedRows}
      filtros={filtros}
      historico={historico}
      loading={loading}
      loadingDetalhes={loadingDetalhes}
      onAplicarFiltros={aplicarFiltros}
      onLimparFiltros={limparFiltros}
      onMudarPagina={mudarPagina}
      onNavegarParaVenda={navegarParaVenda}
      onToggleExpansao={toggleExpansao}
      onVoltarClientes={() => navigate("/clientes")}
      paginacao={paginacao}
      resumo={resumo}
    />
  );
};

export default ClienteFinanceiro;
