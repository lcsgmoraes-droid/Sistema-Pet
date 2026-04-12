import { useCallback, useEffect, useState } from "react";
import api from "../api";

export function useClientesNovoListagem({ tipoFiltro, setError }) {
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [carregamentoInicialConcluido, setCarregamentoInicialConcluido] =
    useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [totalRegistros, setTotalRegistros] = useState(0);
  const [registrosPorPagina, setRegistrosPorPagina] = useState(20);
  const [searchTermAplicado, setSearchTermAplicado] = useState("");

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
      const paginaDesejada = options.paginaAtual ?? paginaAtual;
      const limiteDesejado = options.registrosPorPagina ?? registrosPorPagina;
      const termoBusca =
        typeof options.searchTerm === "string"
          ? options.searchTerm.trim()
          : searchTermAplicado;

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

        const response = await api.get(`/clientes/?${params.toString()}`);

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
        setError("Erro ao carregar pessoas");
        console.error(err);
        return [];
      } finally {
        setLoading(false);
        setCarregamentoInicialConcluido(true);
      }
    },
    [
      paginaAtual,
      registrosPorPagina,
      searchTermAplicado,
      setError,
      tipoFiltro,
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
        clientes.find(
          (cliente) => String(cliente?.codigo || "").trim() === termoNormalizado,
        ) || null
      );
    },
    [clientes],
  );

  return {
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
