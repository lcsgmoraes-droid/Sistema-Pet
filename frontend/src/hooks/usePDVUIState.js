import { useState } from "react";
import { usePersistentBooleanState } from "./usePersistentBooleanState";

export function usePDVUIState() {
  const [mostrarModalPagamento, setMostrarModalPagamento] = useState(false);
  const [mostrarModalCliente, setMostrarModalCliente] = useState(false);
  const [mostrarVendasEmAberto, setMostrarVendasEmAberto] = useState(false);
  const [mostrarHistoricoCliente, setMostrarHistoricoCliente] =
    useState(false);
  const [mostrarModalAdicionarCredito, setMostrarModalAdicionarCredito] =
    useState(false);
  const [mostrarPendenciasEstoque, setMostrarPendenciasEstoque] =
    useState(false);
  const [loading, setLoading] = useState(false);
  const [modoVisualizacao, setModoVisualizacao] = useState(false);
  const [searchVendaQuery, setSearchVendaQuery] = useState("");
  const [painelVendasAberto, setPainelVendasAberto] =
    usePersistentBooleanState("pdv_painel_vendas_aberto", false);
  const [painelClienteAberto, setPainelClienteAberto] =
    usePersistentBooleanState("pdv_painel_cliente_aberto", false);

  return {
    mostrarModalPagamento,
    setMostrarModalPagamento,
    mostrarModalCliente,
    setMostrarModalCliente,
    mostrarVendasEmAberto,
    setMostrarVendasEmAberto,
    mostrarHistoricoCliente,
    setMostrarHistoricoCliente,
    mostrarModalAdicionarCredito,
    setMostrarModalAdicionarCredito,
    mostrarPendenciasEstoque,
    setMostrarPendenciasEstoque,
    loading,
    setLoading,
    modoVisualizacao,
    setModoVisualizacao,
    searchVendaQuery,
    setSearchVendaQuery,
    painelVendasAberto,
    setPainelVendasAberto,
    painelClienteAberto,
    setPainelClienteAberto,
  };
}
