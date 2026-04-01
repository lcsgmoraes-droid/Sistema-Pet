import { useEffect, useState } from "react";
import { buscarClientePorId, buscarClientes } from "../api/clientes";

export function usePDVClienteBusca({
  setVendaAtual,
  setSaldoCampanhas,
  carregarVendasEmAbertoCliente,
  carregarSaldoCampanhasCliente,
}) {
  const [buscarCliente, setBuscarCliente] = useState("");
  const [clientesSugeridos, setClientesSugeridos] = useState([]);

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

  const handleClienteCriadoRapido = async (cliente) => {
    await selecionarCliente(cliente);
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
    buscarClientePorCodigoExato,
    selecionarCliente,
    handleClienteCriadoRapido,
  };
}
