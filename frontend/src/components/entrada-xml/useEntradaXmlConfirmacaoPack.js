import { useState } from "react";
import {
  obterChavePackItem,
  obterConfiguracaoPackItem,
  obterCustoAquisicaoItem,
} from "./entradaXmlUtils";

export default function useEntradaXmlConfirmacaoPack({ multiplicadoresPack, toast }) {
  const [confirmacoesPack, setConfirmacoesPack] = useState({});
  const [pendenciaConfirmacaoPack, setPendenciaConfirmacaoPack] = useState(null);

  const chaveConfirmacao = (notaId, itemId) => `${notaId}:${itemId}`;
  const obterAssinatura = (nota, item, overrides) => {
    const pack = obterConfiguracaoPackItem(item, overrides);
    return JSON.stringify([
      nota.id,
      obterChavePackItem(item),
      item.produto_id,
      Number(item.quantidade),
      Number(item.valor_total),
      obterCustoAquisicaoItem(item),
      pack.multiplicador,
      pack.multiplicadorDetectado,
    ]);
  };

  const obterConfirmacaoPackItem = (nota, item, overrides = multiplicadoresPack) => {
    const pack = obterConfiguracaoPackItem(item, overrides);
    const necessaria =
      nota?.status === "pendente" &&
      (pack.sugestaoAutomaticaDiferenteDoPadrao || pack.multiplicador > 1);
    const confirmada =
      confirmacoesPack[chaveConfirmacao(nota.id, obterChavePackItem(item))] ===
      obterAssinatura(nota, item, overrides);
    return { necessaria, confirmada };
  };

  const confirmarPackItem = (nota, item) => {
    setConfirmacoesPack((prev) => ({
      ...prev,
      [chaveConfirmacao(nota.id, obterChavePackItem(item))]: obterAssinatura(
        nota,
        item,
        multiplicadoresPack,
      ),
    }));
    setPendenciaConfirmacaoPack((prev) =>
      prev?.notaId === nota.id && prev?.itemId === obterChavePackItem(item) ? null : prev,
    );
  };

  const invalidarConfirmacaoPackItem = (notaId, itemId) => {
    setConfirmacoesPack((prev) => {
      const proximo = { ...prev };
      delete proximo[chaveConfirmacao(notaId, itemId)];
      return proximo;
    });
  };

  const limparConfirmacoesPack = () => setConfirmacoesPack({});

  const validarConfirmacoesPack = (nota, overrides = multiplicadoresPack) => {
    const pendentes = (nota.itens || []).filter((item) => {
      const { necessaria, confirmada } = obterConfirmacaoPackItem(nota, item, overrides);
      return necessaria && !confirmada;
    });
    if (!pendentes.length) return true;

    setPendenciaConfirmacaoPack((prev) => ({
      notaId: nota.id,
      itemId: obterChavePackItem(pendentes[0]),
      tentativa: (prev?.tentativa || 0) + 1,
    }));
    toast.error(
      `Falta dar OK no rateio de ${pendentes.length} item(ns). Confira as unidades por caixa.`,
    );
    return false;
  };

  return {
    confirmarPackItem,
    invalidarConfirmacaoPackItem,
    limparConfirmacoesPack,
    obterConfirmacaoPackItem,
    pendenciaConfirmacaoPack,
    validarConfirmacoesPack,
  };
}
