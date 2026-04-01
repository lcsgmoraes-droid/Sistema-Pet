import { useCallback, useEffect, useMemo, useState } from "react";
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

  const loadClientes = useCallback(async () => {
    try {
      setLoading(true);
      const skip = (paginaAtual - 1) * registrosPorPagina;
      const params = new URLSearchParams({
        skip: skip.toString(),
        limit: registrosPorPagina.toString(),
      });

      if (tipoFiltro !== "todos") {
        params.append("tipo_cadastro", tipoFiltro);
      }

      if (searchTerm && searchTerm.trim()) {
        params.append("search", searchTerm.trim());
      }

      const response = await api.get(`/clientes/?${params.toString()}`);

      if (response.data.items) {
        setClientes(response.data.items);
        setTotalRegistros(response.data.total);
      } else {
        setClientes(response.data);
        setTotalRegistros(response.data.length);
      }
    } catch (err) {
      setError("Erro ao carregar pessoas");
      console.error(err);
    } finally {
      setLoading(false);
      setCarregamentoInicialConcluido(true);
    }
  }, [paginaAtual, registrosPorPagina, searchTerm, setError, tipoFiltro]);

  useEffect(() => {
    loadClientes();
  }, [tipoFiltro, paginaAtual, registrosPorPagina]);

  const filteredClientes = useMemo(
    () =>
      clientes.filter(
        (cliente) =>
          cliente.codigo?.includes(searchTerm) ||
          cliente.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
          cliente.cpf?.includes(searchTerm) ||
          cliente.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          cliente.celular?.includes(searchTerm),
      ),
    [clientes, searchTerm],
  );

  const getClientePorCodigoExato = useCallback(
    (termo) => {
      const termoNormalizado = String(termo || "").trim();
      if (!termoNormalizado) {
        return null;
      }

      return (
        filteredClientes.find(
          (cliente) => String(cliente?.codigo || "").trim() === termoNormalizado,
        ) || null
      );
    },
    [filteredClientes],
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
    filteredClientes,
    loadClientes,
    getClientePorCodigoExato,
  };
}
