import { useCallback, useEffect, useRef, useState } from "react";
import api from "../api";

export function useClientesNovoListagem({
  tipoFiltro,
  visaoDashboard = "",
  setError,
  initialSearchTerm = "",
  initialPaginaAtual = 1,
  initialRegistrosPorPagina = 20,
}) {
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [carregamentoInicialConcluido, setCarregamentoInicialConcluido] = useState(false);
  const [searchTerm, setSearchTerm] = useState(initialSearchTerm);
  const [paginaAtual, setPaginaAtual] = useState(initialPaginaAtual);
  const [totalRegistros, setTotalRegistros] = useState(0);
  const [registrosPorPagina, setRegistrosPorPagina] = useState(initialRegistrosPorPagina);
  const [searchTermAplicado, setSearchTermAplicado] = useState(initialSearchTerm.trim());
  const [filtrosOrigem, setFiltrosOrigem] = useState({ origem: "", inicio: "", fim: "" });
  const [resumoOrigens, setResumoOrigens] = useState([]);
  const requisicaoAtual = useRef(0);
  const alterarFiltrosOrigem = (filtros) => {
    setPaginaAtual(1);
    setFiltrosOrigem(filtros);
  };

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setSearchTermAplicado(searchTerm.trim());
    }, 250);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [searchTerm]);

  const loadClientes = useCallback(
    async (options = {}) => {
      const requisicao = ++requisicaoAtual.current;
      const paginaDesejada = options.paginaAtual ?? paginaAtual;
      const limiteDesejado = options.registrosPorPagina ?? registrosPorPagina;
      const termoBusca =
        typeof options.searchTerm === "string" ? options.searchTerm.trim() : searchTermAplicado;

      try {
        setLoading(true);
        const skip = (paginaDesejada - 1) * limiteDesejado;
        const params = new URLSearchParams({
          skip: skip.toString(),
          limit: limiteDesejado.toString(),
        });

        if (tipoFiltro !== "todos") {
          params.append("tipo_cadastro", tipoFiltro);
        }

        if (termoBusca) {
          params.append("search", termoBusca);
        }

        if (visaoDashboard) {
          params.append("visao_dashboard", visaoDashboard);
        }
        if (tipoFiltro === "cliente") {
          params.append("resumo_por_origem", "true");
          if (filtrosOrigem.origem) params.append("origem_cliente", filtrosOrigem.origem);
          if (filtrosOrigem.inicio) params.append("cadastro_inicio", filtrosOrigem.inicio);
          if (filtrosOrigem.fim) params.append("cadastro_fim", filtrosOrigem.fim);
        }

        const response = await api.get(`/clientes/?${params.toString()}`);
        if (requisicao !== requisicaoAtual.current) return [];
        setError("");
        setResumoOrigens(response.data.resumo_origens || []);

        if (response.data.items) {
          setClientes(response.data.items);
          setTotalRegistros(response.data.total);
          return response.data.items;
        }

        const listaClientes = Array.isArray(response.data) ? response.data : [];
        setClientes(listaClientes);
        setTotalRegistros(listaClientes.length);
        return listaClientes;
      } catch (err) {
        if (requisicao !== requisicaoAtual.current) return [];
        const detalhe = err?.response?.data?.detail;
        setError(typeof detalhe === "string" ? detalhe : "Erro ao carregar pessoas");
        setClientes([]);
        setTotalRegistros(0);
        setResumoOrigens([]);
        console.error(err);
        return [];
      } finally {
        if (requisicao === requisicaoAtual.current) {
          setLoading(false);
          setCarregamentoInicialConcluido(true);
        }
      }
    },
    [
      paginaAtual,
      registrosPorPagina,
      searchTermAplicado,
      setError,
      tipoFiltro,
      visaoDashboard,
      filtrosOrigem,
    ],
  );

  useEffect(() => {
    loadClientes();
  }, [loadClientes]);

  const getClientePorCodigoExato = useCallback(
    (termo) => {
      const termoNormalizado = String(termo || "").trim();
      if (!termoNormalizado) {
        return null;
      }

      return (
        clientes.find((cliente) => String(cliente?.codigo || "").trim() === termoNormalizado) ||
        null
      );
    },
    [clientes],
  );

  return {
    filtrosOrigem,
    alterarFiltrosOrigem,
    resumoOrigens,
    clientes,
    loading,
    carregamentoInicialConcluido,
    searchTerm,
    setSearchTerm,
    paginaAtual,
    setPaginaAtual,
    totalRegistros,
    registrosPorPagina,
    setRegistrosPorPagina,
    filteredClientes: clientes,
    loadClientes,
    getClientePorCodigoExato,
  };
}
