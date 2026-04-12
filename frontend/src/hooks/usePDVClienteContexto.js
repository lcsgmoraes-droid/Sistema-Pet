import { useEffect, useState } from "react";
import api from "../api";

export function usePDVClienteContexto({ vendaAtual, setVendaAtual }) {
  const [copiadoClienteCampo, setCopiadoClienteCampo] = useState("");
  const [vendasEmAbertoInfo, setVendasEmAbertoInfo] = useState(null);
  const [saldoCampanhas, setSaldoCampanhas] = useState(null);

  const carregarVendasEmAbertoCliente = async (clienteId) => {
    if (!clienteId) {
      setVendasEmAbertoInfo(null);
      return;
    }

    try {
      const response = await api.get(`/clientes/${clienteId}/vendas-em-aberto`);
      if (response.data.resumo.total_vendas > 0) {
        setVendasEmAbertoInfo(response.data.resumo);
      } else {
        setVendasEmAbertoInfo(null);
      }
    } catch (error) {
      console.error("Erro ao verificar vendas em aberto:", error);
      setVendasEmAbertoInfo(null);
    }
  };

  const carregarSaldoCampanhasCliente = async (clienteId) => {
    if (!clienteId) {
      setSaldoCampanhas(null);
      return;
    }

    try {
      const response = await api.get(`/campanhas/clientes/${clienteId}/saldo`);
      setSaldoCampanhas(response.data);
    } catch {
      setSaldoCampanhas(null);
    }
  };

  const limparClienteSelecionado = () => {
    setVendaAtual((prev) => ({
      ...prev,
      cliente: null,
      pet: null,
    }));
    setSaldoCampanhas(null);
    setVendasEmAbertoInfo(null);
  };

  const selecionarPet = (pet) => {
    setVendaAtual((prev) => ({ ...prev, pet }));
  };

  const copiarCampoCliente = (valor, campo) => {
    if (!valor) return;
    navigator.clipboard.writeText(String(valor));
    setCopiadoClienteCampo(campo);
    setTimeout(() => setCopiadoClienteCampo(""), 2000);
  };

  const recarregarVendasEmAbertoClienteAtual = async () => {
    await carregarVendasEmAbertoCliente(vendaAtual.cliente?.id);
  };

  const recarregarSaldoCampanhasClienteAtual = async () => {
    await carregarSaldoCampanhasCliente(vendaAtual.cliente?.id);
  };

  const recarregarContextoClientePorId = async (clienteId) => {
    if (!clienteId) {
      setSaldoCampanhas(null);
      setVendasEmAbertoInfo(null);
      return;
    }
    await Promise.all([
      carregarVendasEmAbertoCliente(clienteId),
      carregarSaldoCampanhasCliente(clienteId),
    ]);
  };

  const recarregarContextoClienteAtual = async () => {
    await recarregarContextoClientePorId(vendaAtual.cliente?.id);
  };

  useEffect(() => {
    const clienteId = vendaAtual.cliente?.id;
    if (!clienteId) {
      setSaldoCampanhas(null);
      setVendasEmAbertoInfo(null);
      return;
    }

    void recarregarContextoClientePorId(clienteId);
  }, [vendaAtual.cliente?.id]);

  return {
    copiadoClienteCampo,
    vendasEmAbertoInfo,
    saldoCampanhas,
    setSaldoCampanhas,
    carregarVendasEmAbertoCliente,
    carregarSaldoCampanhasCliente,
    limparClienteSelecionado,
    selecionarPet,
    copiarCampoCliente,
    recarregarVendasEmAbertoClienteAtual,
    recarregarSaldoCampanhasClienteAtual,
    recarregarContextoClientePorId,
    recarregarContextoClienteAtual,
  };
}
