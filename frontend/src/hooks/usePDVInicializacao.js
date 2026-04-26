import { useEffect, useRef } from "react";

function normalizarVendaId(valor) {
  const vendaId = Number.parseInt(valor, 10);
  return Number.isFinite(vendaId) && vendaId > 0 ? vendaId : null;
}

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
  const carregarVendaRef = useRef(carregarVendaEspecifica);
  const ultimaVendaUrlCarregadaRef = useRef(null);
  carregarVendaRef.current = carregarVendaEspecifica;

  const vendaIdUrl =
    searchParams.get("venda") ||
    searchParams.get("vendaId") ||
    searchParams.get("venda_id");

  useEffect(() => {
    const vendaId = normalizarVendaId(vendaIdUrl);
    if (vendaId) {
      if (ultimaVendaUrlCarregadaRef.current === vendaId) return;
      ultimaVendaUrlCarregadaRef.current = vendaId;
      void carregarVendaRef.current(vendaId);
      return;
    }

    ultimaVendaUrlCarregadaRef.current = null;
  }, [vendaIdUrl]);

  useEffect(() => {
    const vendaId = sessionStorage.getItem("abrirVenda");
    const abrirModal = sessionStorage.getItem("abrirModalPagamento");

    if (vendaId && abrirModal === "true") {
      sessionStorage.removeItem("abrirVenda");
      sessionStorage.removeItem("abrirModalPagamento");
      const vendaIdNormalizado = normalizarVendaId(vendaId);
      if (vendaIdNormalizado) {
        void carregarVendaRef.current(vendaIdNormalizado, true);
      }
    }
  }, []);

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
