import { useEffect } from "react";

export function usePDVInicializacao({
  searchParams,
  carregarVendaEspecifica,
  handleClienteCriadoRapidoHook,
  setMostrarModalCliente,
  recarregarVendasEmAbertoClienteAtual,
  setVendaAtual,
  setMostrarModalAdicionarCredito,
  limparVenda,
}) {
  useEffect(() => {
    const vendaId =
      searchParams.get("venda") ||
      searchParams.get("vendaId") ||
      searchParams.get("venda_id");

    if (vendaId) {
      carregarVendaEspecifica(Number.parseInt(vendaId, 10));
    }
  }, [searchParams, carregarVendaEspecifica]);

  useEffect(() => {
    const vendaId = sessionStorage.getItem("abrirVenda");
    const abrirModal = sessionStorage.getItem("abrirModalPagamento");

    if (vendaId && abrirModal === "true") {
      sessionStorage.removeItem("abrirVenda");
      sessionStorage.removeItem("abrirModalPagamento");
      carregarVendaEspecifica(Number.parseInt(vendaId, 10), true);
    }
  }, [carregarVendaEspecifica]);

  const handleNovaVenda = () => {
    if (window.confirm("Descartar venda atual sem salvar?")) {
      limparVenda();
    }
  };

  const handleClienteCriadoRapido = async (cliente) => {
    await handleClienteCriadoRapidoHook(cliente);
    setMostrarModalCliente(false);
  };

  const handleVendasEmAbertoSucesso = () => {
    void recarregarVendasEmAbertoClienteAtual();
  };

  const handleConfirmarCreditoCliente = (novoSaldo) => {
    setVendaAtual((prev) => ({
      ...prev,
      cliente: { ...prev.cliente, credito: novoSaldo },
    }));
    setMostrarModalAdicionarCredito(false);
  };

  return {
    handleNovaVenda,
    handleClienteCriadoRapido,
    handleVendasEmAbertoSucesso,
    handleConfirmarCreditoCliente,
  };
}
