import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";

export function usePDVEstoqueFiscal({ vendaAtual, limparBuscaProduto }) {
  const [pendenciasCount, setPendenciasCount] = useState(0);
  const [pendenciasProdutoIds, setPendenciasProdutoIds] = useState([]);
  const [totalImpostos, setTotalImpostos] = useState(0);

  const carregarPendencias = async () => {
    if (!vendaAtual.cliente) {
      setPendenciasCount(0);
      setPendenciasProdutoIds([]);
      return;
    }

    try {
      const response = await api.get(
        `/pendencias-estoque/cliente/${vendaAtual.cliente.id}`,
      );
      const todas = Array.isArray(response.data?.pendencias)
        ? response.data.pendencias
        : [];
      const pendenciasAtivas = todas.filter(
        (pendencia) =>
          pendencia.status === "pendente" || pendencia.status === "notificado",
      );
      setPendenciasCount(pendenciasAtivas.length);
      setPendenciasProdutoIds(
        pendenciasAtivas.map((pendencia) => pendencia.produto_id),
      );
    } catch {
      setPendenciasCount(0);
      setPendenciasProdutoIds([]);
    }
  };

  const adicionarNaListaEsperaRapido = async (produto, event) => {
    event?.stopPropagation?.();

    if (!vendaAtual.cliente) {
      toast.error("Selecione um cliente primeiro");
      return;
    }

    try {
      await api.post("/pendencias-estoque/", {
        cliente_id: vendaAtual.cliente.id,
        produto_id: produto.id,
        quantidade_desejada: 1,
        prioridade: 1,
        observacoes: null,
      });
      toast.success(`"${produto.nome}" adicionado à lista de espera!`);
      limparBuscaProduto?.();
      await carregarPendencias();
    } catch (error) {
      toast.error(
        error.response?.data?.detail || "Erro ao adicionar à lista de espera",
      );
    }
  };

  useEffect(() => {
    if (vendaAtual.cliente) {
      void carregarPendencias();
      return;
    }

    setPendenciasCount(0);
    setPendenciasProdutoIds([]);
  }, [vendaAtual.cliente?.id]);

  useEffect(() => {
    if (vendaAtual.itens && vendaAtual.itens.length > 0) {
      sessionStorage.setItem(
        "pdv_calculadora_data",
        JSON.stringify({
          itens: vendaAtual.itens,
          clienteId: vendaAtual.cliente?.id || null,
        }),
      );
      return;
    }

    sessionStorage.removeItem("pdv_calculadora_data");
  }, [vendaAtual.itens, vendaAtual.cliente?.id]);

  useEffect(() => {
    let cancelado = false;

    async function recalcularFiscal() {
      let impostosTotais = 0;

      for (const item of vendaAtual.itens) {
        try {
          const payload = {
            produto_id: item.produto_id,
            preco_unitario: item.preco_unitario,
            quantidade: item.quantidade,
          };
          const { data } = await api.post("/pdv/fiscal/calcular", payload);
          if (!cancelado && data) {
            impostosTotais += Number(data.total_impostos);
          }
        } catch (error) {
          console.error("Erro ao calcular fiscal:", error);
        }
      }

      if (!cancelado) {
        setTotalImpostos(impostosTotais.toFixed(2));
      }
    }

    if (vendaAtual.itens && vendaAtual.itens.length > 0) {
      void recalcularFiscal();
    } else {
      setTotalImpostos(0);
    }

    return () => {
      cancelado = true;
    };
  }, [vendaAtual.itens]);

  return {
    pendenciasCount,
    pendenciasProdutoIds,
    totalImpostos,
    carregarPendencias,
    adicionarNaListaEsperaRapido,
  };
}
