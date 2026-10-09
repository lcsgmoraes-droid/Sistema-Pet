import { useEffect, useState } from "react";
import api from "../api";
import { calcularCuponsVenda, obterCuponsVenda } from "../utils/pdvDescontosUtils";

export function usePDVCupom({ vendaAtual, recalcularTotais, prepararDescontos }) {
  const [codigoCupom, setCodigoCupom] = useState("");
  const [loadingCupom, setLoadingCupom] = useState(false);
  const [erroCupom, setErroCupom] = useState("");
  const cuponsAplicados = obterCuponsVenda(vendaAtual);

  useEffect(() => {
    setCodigoCupom("");
    setErroCupom("");
  }, [vendaAtual.id]);

  const cupomAplicado =
    cuponsAplicados.length > 0
      ? {
          code: cuponsAplicados.map((cupom) => cupom.code).join(","),
          discount_applied: Number(vendaAtual.cupom_discount_applied || 0),
          items: cuponsAplicados,
        }
      : null;

  const aplicarCupom = async () => {
    const code = codigoCupom.trim().toUpperCase();
    if (!code) return;
    if (vendaAtual.itens.length === 0) {
      setErroCupom("Adicione itens a venda antes de aplicar um cupom.");
      return;
    }
    if (cuponsAplicados.some((cupom) => cupom.code === code)) {
      setErroCupom("Este cupom ja foi aplicado nesta venda.");
      return;
    }
    if (cuponsAplicados.length >= 5) {
      setErroCupom("Use no maximo 5 cupons na mesma venda.");
      return;
    }
    const preparada = await prepararDescontos();
    if (!preparada) return;
    setLoadingCupom(true);
    setErroCupom("");
    try {
      const base = Math.max(
        0,
        Number(preparada.subtotal || 0) - Number(preparada.desconto_venda_valor || 0),
      );
      const anteriores = calcularCuponsVenda(base, obterCuponsVenda(preparada));
      const res = await api.post(`/campanhas/cupons/${code}/resgatar`, {
        venda_total: anteriores.restante,
        customer_id: preparada.cliente?.id || null,
      });
      const proximosCupons = [...anteriores.detalhes, res.data];
      setCodigoCupom("");
      recalcularTotais(preparada.itens, {
        ...preparada,
        cupom_code: proximosCupons.map((cupom) => cupom.code).join(","),
        cupons_detalhes: proximosCupons,
      });
    } catch (err) {
      setErroCupom(err?.response?.data?.detail || "Erro ao validar cupom");
    } finally {
      setLoadingCupom(false);
    }
  };

  const removerCupom = async (codigo) => {
    const preparada = await prepararDescontos();
    if (!preparada) return;
    const preparados = obterCuponsVenda(preparada);
    const cupomSelecionado = preparados.find((cupom) => cupom.code === codigo);
    const removerTodos = !codigo || cupomSelecionado?.persistido_sem_detalhe;
    const restantes = removerTodos ? [] : preparados.filter((cupom) => cupom.code !== codigo);
    setCodigoCupom("");
    setErroCupom(
      removerTodos && cuponsAplicados.length > 1
        ? "Os cupons salvos anteriormente foram removidos juntos. Aplique novamente os que desejar."
        : "",
    );
    recalcularTotais(preparada.itens, {
      ...preparada,
      cupom_code: restantes.map((cupom) => cupom.code).join(",") || null,
      cupom_discount_applied: null,
      cupons_detalhes: restantes,
    });
  };

  const handleCodigoCupomChange = (valor) => {
    setCodigoCupom(String(valor || "").toUpperCase());
    setErroCupom("");
  };

  const handleCodigoCupomKeyDown = (e) => {
    if (e.key === "Enter") void aplicarCupom();
  };

  return {
    codigoCupom,
    cupomAplicado,
    loadingCupom,
    erroCupom,
    aplicarCupom,
    removerCupom,
    handleCodigoCupomChange,
    handleCodigoCupomKeyDown,
  };
}
