import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { debugLog, debugWarn } from "../utils/debug";

export function usePDVEntregadores(vendaAtual, setVendaAtual) {
  const [entregadores, setEntregadores] = useState([]);
  const [entregadorSelecionado, setEntregadorSelecionado] = useState(null);
  const [custoOperacionalEntrega, setCustoOperacionalEntrega] = useState(0);

  useEffect(() => {
    const novoEntregadorId = entregadorSelecionado?.id || null;

    setVendaAtual((prev) => {
      if (prev.entregador_id === novoEntregadorId) {
        return prev;
      }

      if (novoEntregadorId) {
        debugLog("Sincronizando entregador_id:", novoEntregadorId);
      }

      return {
        ...prev,
        entregador_id: novoEntregadorId,
      };
    });
  }, [entregadorSelecionado, setVendaAtual]);

  useEffect(() => {
    void carregarEntregadores();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (vendaAtual.tem_entrega && entregadorSelecionado) {
      void calcularCustoOperacional(entregadorSelecionado);
    } else {
      setCustoOperacionalEntrega(0);
    }
  }, [entregadorSelecionado, vendaAtual.tem_entrega]); // eslint-disable-line react-hooks/exhaustive-deps

  const calcularCustoOperacional = async (entregador) => {
    if (!entregador) {
      setCustoOperacionalEntrega(0);
      return;
    }

    let custo = 0;

    if (
      entregador.modelo_custo_entrega === "taxa_fixa" &&
      entregador.taxa_fixa_entrega
    ) {
      custo = Number(entregador.taxa_fixa_entrega);
    } else if (
      entregador.modelo_custo_entrega === "por_km" &&
      entregador.valor_por_km_entrega
    ) {
      custo = 0;
    } else if (
      entregador.modelo_custo_entrega === "rateio_rh" &&
      entregador.controla_rh
    ) {
      try {
        const response = await api.get(
          `/entregadores/${entregador.id}/custo-operacional`,
        );
        custo = response.data.custo_por_entrega || 0;
      } catch (error) {
        console.error("Erro ao buscar custo RH:", error);
        custo = entregador.custo_rh_ajustado || 0;
      }
    } else {
      try {
        const response = await api.get("/configuracoes/entregas");
        custo = response.data.taxa_fixa || 0;
      } catch (error) {
        console.error("Erro ao buscar configuracao de entrega:", error);
        custo = 10;
      }
    }

    setCustoOperacionalEntrega(custo);
  };

  const selecionarEntregador = (entregador) => {
    setEntregadorSelecionado(entregador || null);
    setVendaAtual((prev) => ({
      ...prev,
      entregador_id: entregador?.id || null,
    }));

    if (entregador) {
      void calcularCustoOperacional(entregador);
    } else {
      setCustoOperacionalEntrega(0);
    }
  };

  const carregarEntregadores = async () => {
    try {
      const response = await api.get("/clientes/", {
        params: {
          is_entregador: true,
          incluir_inativos: false,
          limit: 100,
        },
      });

      let entregadoresList =
        response.data.items || response.data.clientes || response.data || [];

      if (!Array.isArray(entregadoresList)) {
        console.error("Resposta da API nao e um array:", entregadoresList);
        entregadoresList = [];
      }

      setEntregadores(entregadoresList);

      const entregadorPadrao = entregadoresList.find(
        (entregador) => entregador.entregador_padrao === true,
      );

      if (entregadorPadrao) {
        selecionarEntregador(entregadorPadrao);
      }
    } catch (error) {
      console.error("Erro ao carregar entregadores:", error);
      toast.error("Erro ao carregar lista de entregadores");
    }
  };

  const sincronizarEntregadorDaVenda = async (entregadorId) => {
    if (!entregadorId) {
      debugLog("Venda sem entregador_id - limpando entregadorSelecionado");
      selecionarEntregador(null);
      return;
    }

    debugLog("Venda tem entregador_id:", entregadorId);

    try {
      const responseEntregador = await api.get(`/clientes/${entregadorId}`);
      const entregadorCarregado = responseEntregador.data;

      if (entregadorCarregado && entregadorCarregado.is_entregador) {
        debugLog("Entregador carregado:", entregadorCarregado.nome);
        selecionarEntregador(entregadorCarregado);
        return;
      }

      debugWarn(
        "Cliente ID",
        entregadorId,
        "nao e um entregador valido",
      );
    } catch (error) {
      console.error("Erro ao carregar entregador:", error);
    }

    const entregadorFallback = entregadores.find(
      (entregador) => entregador.id === Number(entregadorId),
    );

    if (entregadorFallback) {
      debugLog(
        "Entregador encontrado no array (fallback):",
        entregadorFallback.nome,
      );
      selecionarEntregador(entregadorFallback);
    }
  };

  return {
    entregadores,
    entregadorSelecionado,
    custoOperacionalEntrega,
    sincronizarEntregadorDaVenda,
    selecionarEntregador,
  };
}
