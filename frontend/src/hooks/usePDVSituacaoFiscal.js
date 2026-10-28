import { useEffect } from "react";
import { buscarVendaComSituacaoFiscal } from "../api/vendas";
import { mesclarSituacaoFiscalVenda } from "../utils/pdvFiscalRefresh";

export function usePDVSituacaoFiscal({ vendaAtual, modoVisualizacao, setVendaAtual }) {
  const vendaId = vendaAtual.id;
  const temNota = Boolean(vendaAtual.nfe_correlation_id || vendaAtual.nfe_bling_id);

  useEffect(() => {
    if (!vendaId || !temNota || !modoVisualizacao) return;
    let ativo = true;
    let consultando = false;

    const atualizar = async () => {
      if (document.visibilityState === "hidden" || consultando) return;
      consultando = true;
      try {
        const venda = await buscarVendaComSituacaoFiscal(vendaId);
        if (ativo) setVendaAtual((atual) => mesclarSituacaoFiscalVenda(atual, venda));
      } catch {
        if (ativo) {
          setVendaAtual((atual) =>
            String(atual.id) === String(vendaId)
              ? { ...atual, nfe_atualizacao_falhou: true }
              : atual,
          );
        }
      } finally {
        consultando = false;
      }
    };

    window.addEventListener("focus", atualizar);
    document.addEventListener("visibilitychange", atualizar);
    return () => {
      ativo = false;
      window.removeEventListener("focus", atualizar);
      document.removeEventListener("visibilitychange", atualizar);
    };
  }, [vendaId, temNota, modoVisualizacao, setVendaAtual]);
}
