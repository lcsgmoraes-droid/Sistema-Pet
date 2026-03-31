import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { debugLog, debugWarn } from "../utils/debug";

const criarEntregaVazia = () => ({
  endereco_completo: "",
  taxa_entrega_total: 0,
  taxa_loja: 0,
  taxa_entregador: 0,
  observacoes_entrega: "",
});

const recalcularTotalComEntrega = (subtotal, taxaEntrega) =>
  parseFloat((Number(subtotal || 0) + Number(taxaEntrega || 0)).toFixed(2));

export function usePDVEntrega(vendaAtual, setVendaAtual) {
  const [entregadores, setEntregadores] = useState([]);
  const [entregadorSelecionado, setEntregadorSelecionado] = useState(null);
  const [custoOperacionalEntrega, setCustoOperacionalEntrega] = useState(0);

  useEffect(() => {
    const novoEntregadorId = entregadorSelecionado?.id || null;
    if (!novoEntregadorId) {
      return;
    }

    debugLog("🔄 Sincronizando entregador_id:", novoEntregadorId);
    setVendaAtual((prev) => {
      if (prev.entregador_id === novoEntregadorId) {
        return prev;
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
        console.error("❌ Resposta da API não é um array:", entregadoresList);
        entregadoresList = [];
      }

      setEntregadores(entregadoresList);

      const entregadorPadrao = entregadoresList.find(
        (entregador) => entregador.entregador_padrao === true,
      );

      if (entregadorPadrao) {
        setEntregadorSelecionado(entregadorPadrao);
        setVendaAtual((prev) => ({
          ...prev,
          entregador_id: entregadorPadrao.id,
        }));
        await calcularCustoOperacional(entregadorPadrao);
      }
    } catch (error) {
      console.error("Erro ao carregar entregadores:", error);
      toast.error("Erro ao carregar lista de entregadores");
    }
  };

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
        console.error("Erro ao buscar configuração de entrega:", error);
        custo = 10;
      }
    }

    setCustoOperacionalEntrega(custo);
  };

  const sincronizarEntregadorDaVenda = async (entregadorId) => {
    if (!entregadorId) {
      debugLog("ℹ️ Venda sem entregador_id - limpando entregadorSelecionado");
      setEntregadorSelecionado(null);
      return;
    }

    debugLog("🔍 Venda tem entregador_id:", entregadorId);

    try {
      const responseEntregador = await api.get(`/clientes/${entregadorId}`);
      const entregadorCarregado = responseEntregador.data;

      if (entregadorCarregado && entregadorCarregado.is_entregador) {
        debugLog("✅ Entregador carregado:", entregadorCarregado.nome);
        setEntregadorSelecionado(entregadorCarregado);
        await calcularCustoOperacional(entregadorCarregado);
        return;
      }

      debugWarn(
        "⚠️ Cliente ID",
        entregadorId,
        "não é um entregador válido",
      );
    } catch (error) {
      console.error("❌ Erro ao carregar entregador:", error);
    }

    const entregadorFallback = entregadores.find(
      (entregador) => entregador.id === Number(entregadorId),
    );

    if (entregadorFallback) {
      debugLog(
        "✅ Entregador encontrado no array (fallback):",
        entregadorFallback.nome,
      );
      setEntregadorSelecionado(entregadorFallback);
      await calcularCustoOperacional(entregadorFallback);
    }
  };

  const handleToggleTemEntrega = (temEntrega) => {
    setVendaAtual((prev) => {
      const taxaEntrega = temEntrega ? prev.entrega?.taxa_entrega_total || 0 : 0;

      return {
        ...prev,
        tem_entrega: temEntrega,
        total: recalcularTotalComEntrega(prev.subtotal, taxaEntrega),
        entrega: temEntrega ? prev.entrega : criarEntregaVazia(),
      };
    });
  };

  const handleSelecionarEnderecoEntrega = (enderecoCompleto) => {
    setVendaAtual((prev) => ({
      ...prev,
      entrega: {
        ...prev.entrega,
        endereco_completo: enderecoCompleto,
      },
    }));
  };

  const handleEnderecoEntregaChange = (valor) => {
    setVendaAtual((prev) => ({
      ...prev,
      entrega: {
        ...prev.entrega,
        endereco_completo: valor,
      },
    }));
  };

  const handleSelecionarEntregador = (entregadorId) => {
    const entregador = entregadores.find(
      (item) => item.id === parseInt(entregadorId, 10),
    );

    setEntregadorSelecionado(entregador || null);
    setVendaAtual((prev) => ({
      ...prev,
      entregador_id: entregador?.id || null,
    }));

    if (entregador) {
      void calcularCustoOperacional(entregador);
    }
  };

  const handleTaxaEntregaTotalChange = (valor) => {
    const total = parseFloat(valor) || 0;
    const totalArredondado = parseFloat(total.toFixed(2));

    setVendaAtual((prev) => {
      const taxaLojaAtual = prev.entrega?.taxa_loja || 0;
      const taxaEntregadorCalculada = parseFloat(
        (totalArredondado - taxaLojaAtual).toFixed(2),
      );

      return {
        ...prev,
        total: recalcularTotalComEntrega(
          prev.subtotal,
          prev.tem_entrega ? totalArredondado : 0,
        ),
        entrega: {
          ...prev.entrega,
          taxa_entrega_total: totalArredondado,
          taxa_loja: parseFloat(taxaLojaAtual.toFixed(2)),
          taxa_entregador: taxaEntregadorCalculada,
        },
      };
    });
  };

  const handleTaxaLojaChange = (valor) => {
    const taxaLoja = parseFloat(valor) || 0;
    const taxaLojaArredondada = parseFloat(taxaLoja.toFixed(2));

    setVendaAtual((prev) => {
      const total = prev.entrega?.taxa_entrega_total || 0;
      const taxaEntregadorArredondada = parseFloat(
        (total - taxaLojaArredondada).toFixed(2),
      );

      return {
        ...prev,
        entrega: {
          ...prev.entrega,
          taxa_loja: taxaLojaArredondada,
          taxa_entregador: taxaEntregadorArredondada,
        },
      };
    });
  };

  const handleTaxaEntregadorChange = (valor) => {
    const taxaEntregador = parseFloat(valor) || 0;
    const taxaEntregadorArredondada = parseFloat(taxaEntregador.toFixed(2));

    setVendaAtual((prev) => {
      const total = prev.entrega?.taxa_entrega_total || 0;
      const taxaLojaArredondada = parseFloat(
        (total - taxaEntregadorArredondada).toFixed(2),
      );

      return {
        ...prev,
        entrega: {
          ...prev.entrega,
          taxa_entregador: taxaEntregadorArredondada,
          taxa_loja: taxaLojaArredondada,
        },
      };
    });
  };

  const handleObservacoesEntregaChange = (valor) => {
    setVendaAtual((prev) => ({
      ...prev,
      entrega: {
        ...prev.entrega,
        observacoes_entrega: valor,
      },
    }));
  };

  return {
    entregadores,
    entregadorSelecionado,
    custoOperacionalEntrega,
    sincronizarEntregadorDaVenda,
    handleToggleTemEntrega,
    handleSelecionarEnderecoEntrega,
    handleEnderecoEntregaChange,
    handleSelecionarEntregador,
    handleTaxaEntregaTotalChange,
    handleTaxaLojaChange,
    handleTaxaEntregadorChange,
    handleObservacoesEntregaChange,
  };
}
