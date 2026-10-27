import { useEffect, useRef, useState } from "react";
import { buscarClientePorId, buscarClientes } from "../api/clientes";
import { obterCodigoPessoaPublico } from "../utils/codigosPublicos";
import { ordenarSugestoesEntidade } from "../utils/buscaEntidades";

export function usePDVClienteBusca({ setVendaAtual, setSaldoCampanhas }) {
  const [buscarCliente, setBuscarCliente] = useState("");
  const [clientesSugeridos, setClientesSugeridos] = useState([]);
  const selecaoAtualRef = useRef(null);

  function buscarClientePorCodigoExato(termo) {
    const termoLimpo = String(termo || "")
      .trim()
      .toLowerCase();
    if (!termoLimpo) return null;

    return clientesSugeridos.find(
      (cliente) => obterCodigoPessoaPublico(cliente).trim().toLowerCase() === termoLimpo,
    );
  }

  const selecionarCliente = async (cliente) => {
    selecaoAtualRef.current = cliente.id;
    setVendaAtual((prev) => ({ ...prev, cliente, pet: null }));
    setBuscarCliente("");
    setClientesSugeridos([]);
    setSaldoCampanhas(null);

    try {
      const clienteCompleto = await buscarClientePorId(cliente.id);
      if (clienteCompleto && selecaoAtualRef.current === cliente.id) {
        setVendaAtual((prev) => ({
          ...prev,
          cliente:
            prev.cliente?.id === cliente.id
              ? {
                  ...prev.cliente,
                  ...clienteCompleto,
                }
              : prev.cliente,
        }));
      }
    } catch {
      // Segue com os dados resumidos para nao travar o fluxo do caixa.
    }

    // O contexto acompanha cliente.id no hook próprio; não repetir consultas aqui.
  };

  const handleClienteCriadoRapido = async (cliente) => {
    await selecionarCliente(cliente);
  };

  useEffect(() => {
    let ativo = true;
    const controller = new AbortController();
    if (buscarCliente.length < 1) {
      setClientesSugeridos([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const termoOriginal = buscarCliente.trim();
        const termoDigitos = termoOriginal.replace(/\D/g, "");
        const termoBusca =
          termoDigitos.length >= 8 && !/\p{L}/u.test(termoOriginal) ? termoDigitos : termoOriginal;
        const clientes = await buscarClientes(
          {
            search: termoBusca,
            limit: 20,
          },
          { signal: controller.signal },
        );
        if (ativo) setClientesSugeridos(ordenarSugestoesEntidade(clientes || [], termoOriginal));
      } catch (error) {
        if (ativo && error?.code !== "ERR_CANCELED") setClientesSugeridos([]);
      }
    }, 300);

    return () => {
      ativo = false;
      clearTimeout(timer);
      controller.abort();
    };
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
