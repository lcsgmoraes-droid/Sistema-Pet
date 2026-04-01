import { useEffect, useState } from "react";
import api from "../api";
import { buscarClientePorId, buscarClientes } from "../api/clientes";

export function usePDVCliente({ vendaAtual, setVendaAtual }) {
  const [buscarCliente, setBuscarCliente] = useState("");
  const [clientesSugeridos, setClientesSugeridos] = useState([]);
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

  function buscarClientePorCodigoExato(termo) {
    const termoLimpo = String(termo || "").trim().toLowerCase();
    if (!termoLimpo) return null;

    const porId = clientesSugeridos.find(
      (cliente) => String(cliente?.id || "").trim().toLowerCase() === termoLimpo,
    );
    if (porId) return porId;

    return clientesSugeridos.find(
      (cliente) =>
        String(cliente?.codigo || "").trim().toLowerCase() === termoLimpo,
    );
  }

  const selecionarCliente = async (cliente) => {
    setVendaAtual((prev) => ({ ...prev, cliente, pet: null }));
    setBuscarCliente("");
    setClientesSugeridos([]);
    setSaldoCampanhas(null);

    try {
      const clienteCompleto = await buscarClientePorId(cliente.id);
      if (clienteCompleto) {
        setVendaAtual((prev) => ({
          ...prev,
          cliente: {
            ...prev.cliente,
            ...clienteCompleto,
          },
        }));
      }
    } catch {
      // Segue com os dados resumidos para nao travar o fluxo do caixa.
    }

    await carregarVendasEmAbertoCliente(cliente.id);
    await carregarSaldoCampanhasCliente(cliente.id);
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

  const handleClienteCriadoRapido = async (cliente) => {
    await selecionarCliente(cliente);
  };

  const recarregarVendasEmAbertoClienteAtual = async () => {
    await carregarVendasEmAbertoCliente(vendaAtual.cliente?.id);
  };

  useEffect(() => {
    if (buscarCliente.length < 1) {
      setClientesSugeridos([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const termoOriginal = buscarCliente.trim();
        const termoDigitos = termoOriginal.replace(/\D/g, "");
        const termoBusca =
          termoDigitos.length >= 8 ? termoDigitos : termoOriginal;
        const clientes = await buscarClientes({
          search: termoBusca,
          limit: 20,
        });
        setClientesSugeridos(clientes || []);
      } catch (error) {
        console.error("Erro ao buscar clientes:", error);
        setClientesSugeridos([]);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [buscarCliente]);

  return {
    buscarCliente,
    setBuscarCliente,
    clientesSugeridos,
    copiadoClienteCampo,
    vendasEmAbertoInfo,
    saldoCampanhas,
    setSaldoCampanhas,
    buscarClientePorCodigoExato,
    selecionarCliente,
    selecionarPet,
    copiarCampoCliente,
    limparClienteSelecionado,
    handleClienteCriadoRapido,
    recarregarVendasEmAbertoClienteAtual,
  };
}
