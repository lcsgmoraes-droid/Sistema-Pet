import { useState } from "react";

export default function useEntradaXmlRateio({ api, toast }) {
  const [tipoRateio, setTipoRateio] = useState("loja");
  const [quantidadesOnline, setQuantidadesOnline] = useState({});
  const [multiplicadoresPack, setMultiplicadoresPack] = useState({});

  const salvarTipoRateio = async (notaId, tipo, aplicarNotaSelecionada) => {
    try {
      await api.post(`/notas-entrada/${notaId}/rateio`, {
        tipo_rateio: tipo,
      });

      let descricaoTipo = "Rateio Parcial";
      if (tipo === "online") descricaoTipo = "100% Online";
      if (tipo === "loja") descricaoTipo = "100% Loja Fisica";
      toast.success(`Nota configurada: ${descricaoTipo}`);

      const response = await api.get(`/notas-entrada/${notaId}`);
      aplicarNotaSelecionada(response.data);
    } catch (error) {
      console.error("Erro ao salvar tipo de rateio:", error);
      toast.error(error.response?.data?.detail || "Erro ao salvar tipo de rateio");
    }
  };

  const salvarQuantidadeOnlineItem = async (
    notaId,
    itemId,
    quantidadeOnline,
    setNotaSelecionada,
  ) => {
    try {
      const quantidadeNormalizada = Number.parseFloat(quantidadeOnline) || 0;
      const response = await api.post(`/notas-entrada/${notaId}/itens/${itemId}/rateio`, {
        quantidade_online: quantidadeNormalizada,
      });

      toast.success("Quantidade online configurada!");

      const totais = response.data.nota_totais;
      toast.success(
        `Nota: ${totais.percentual_online.toFixed(1)}% Online (R$ ${totais.valor_online.toFixed(2)}) | ` +
          `${totais.percentual_loja.toFixed(1)}% Loja (R$ ${totais.valor_loja.toFixed(2)})`,
      );

      setNotaSelecionada((prev) => ({
        ...prev,
        percentual_online: totais.percentual_online,
        percentual_loja: totais.percentual_loja,
        valor_online: totais.valor_online,
        valor_loja: totais.valor_loja,
        itens: prev.itens.map((item) =>
          item.id === itemId ? { ...item, quantidade_online: quantidadeNormalizada } : item,
        ),
      }));

      setQuantidadesOnline((prev) => ({
        ...prev,
        [itemId]: quantidadeNormalizada,
      }));
    } catch (error) {
      console.error("Erro ao salvar quantidade online:", error);
      toast.error(error.response?.data?.detail || "Erro ao salvar");
    }
  };

  return {
    multiplicadoresPack,
    quantidadesOnline,
    salvarQuantidadeOnlineItem,
    salvarTipoRateio,
    setMultiplicadoresPack,
    setQuantidadesOnline,
    setTipoRateio,
    tipoRateio,
  };
}
