import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { contarRacoes, ehRacao } from "../helpers/deteccaoRacao";
import { debugLog } from "../utils/debug";

export function usePDVCaixaRacao({ vendaAtual, destaqueAbrirCaixa }) {
  const [mostrarModalAbrirCaixa, setMostrarModalAbrirCaixa] = useState(false);
  const [caixaKey, setCaixaKey] = useState(0);
  const [temCaixaAberto, setTemCaixaAberto] = useState(false);
  const [mostrarCalculadoraRacao, setMostrarCalculadoraRacao] = useState(false);
  const [racaoIdFechada, setRacaoIdFechada] = useState(null);

  useEffect(() => {
    void verificarCaixaAberto();

    const intervalId = setInterval(() => {
      void verificarCaixaAberto();
    }, 30000);

    return () => clearInterval(intervalId);
  }, [caixaKey]);

  useEffect(() => {
    if (destaqueAbrirCaixa && !temCaixaAberto && !mostrarModalAbrirCaixa) {
      setMostrarModalAbrirCaixa(true);
    }
  }, [destaqueAbrirCaixa, temCaixaAberto, mostrarModalAbrirCaixa]);

  const verificarCaixaAberto = async () => {
    try {
      const response = await api.get("/caixas/aberto");
      setTemCaixaAberto(!!response.data);
    } catch {
      setTemCaixaAberto(false);
    }
  };

  const abrirCalculadoraRacao = () => {
    debugLog("🔍 Debug - Itens no carrinho:", vendaAtual.itens);
    debugLog("🔍 Debug - Verificando rações...");

    vendaAtual.itens.forEach((item, index) => {
      debugLog(`  Item ${index + 1}: ${item.produto_nome}`);
      debugLog(`    - peso_embalagem: ${item.peso_embalagem}`);
      debugLog(`    - classificacao_racao: ${item.classificacao_racao}`);
      debugLog(`    - categoria_id: ${item.categoria_id}`);
      debugLog(`    - categoria_nome: ${item.categoria_nome}`);
      debugLog(`    - É ração?: ${ehRacao(item)}`);
    });

    const racoes = contarRacoes(vendaAtual.itens);
    debugLog(`📊 Total de rações encontradas: ${racoes}`);

    if (racoes === 0) {
      toast.error("Nenhuma ração no carrinho");
      return;
    }

    setRacaoIdFechada(null);
    setMostrarCalculadoraRacao(true);
  };

  const fecharCalculadoraRacao = () => {
    const racoes = vendaAtual.itens.filter((item) => {
      const nomeCategoria = (item.categoria_nome || "").toLowerCase();
      return (
        nomeCategoria.includes("ração") || nomeCategoria.includes("racao")
      );
    });

    if (racoes.length > 0) {
      setRacaoIdFechada(racoes[racoes.length - 1].produto_id);
    }

    setMostrarCalculadoraRacao(false);
  };

  const handleAbrirCaixaSucesso = () => {
    setMostrarModalAbrirCaixa(false);
    setCaixaKey((prev) => prev + 1);
    setTemCaixaAberto(true);
  };

  return {
    mostrarModalAbrirCaixa,
    setMostrarModalAbrirCaixa,
    caixaKey,
    temCaixaAberto,
    mostrarCalculadoraRacao,
    racaoIdFechada,
    abrirCalculadoraRacao,
    fecharCalculadoraRacao,
    handleAbrirCaixaSucesso,
  };
}
