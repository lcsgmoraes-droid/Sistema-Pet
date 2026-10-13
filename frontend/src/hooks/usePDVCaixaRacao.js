import { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { obterCaixaAberto } from "../api/caixa";
import { contarRacoes, ehRacao } from "../helpers/deteccaoRacao";
import { debugLog } from "../utils/debug";
import {
  criarEstadoCaixaAberto,
  criarMonitorCaixaAberto,
  publicarEventoCaixa,
} from "../utils/caixaAbertoMonitor";

export function usePDVCaixaRacao({ vendaAtual, destaqueAbrirCaixa, contextoCaixa }) {
  const [mostrarModalAbrirCaixa, setMostrarModalAbrirCaixa] = useState(false);
  const [caixaKey, setCaixaKey] = useState(0);
  const [consultaCaixa, setConsultaCaixa] = useState(criarEstadoCaixaAberto);
  const [mostrarCalculadoraRacao, setMostrarCalculadoraRacao] = useState(false);
  const [racaoIdFechada, setRacaoIdFechada] = useState(null);
  const monitorCaixaRef = useRef(null);
  const estadoCaixa =
    consultaCaixa.contexto === contextoCaixa ? consultaCaixa : criarEstadoCaixaAberto();
  const temCaixaAberto = Boolean(estadoCaixa.caixa);
  const atualizarCaixa = useCallback(
    (opcoes = {}) => monitorCaixaRef.current?.atualizar(opcoes),
    [],
  );

  useEffect(() => {
    const monitor = criarMonitorCaixaAberto({
      consultar: obterCaixaAberto,
      onEstado: (estado) => setConsultaCaixa({ ...estado, contexto: contextoCaixa }),
    });
    monitorCaixaRef.current = monitor;
    void monitor.atualizar();
    const consultarSeVisivel = () => {
      if (document.visibilityState !== "hidden") void monitor.atualizar();
    };
    const sincronizarCaixa = (event) => {
      if (event.key === "petshop_caixa_sync_event")
        void monitor.sincronizar(event.newValue, contextoCaixa);
    };
    const intervalId = setInterval(consultarSeVisivel, 60000);
    document.addEventListener("visibilitychange", consultarSeVisivel);
    window.addEventListener("online", consultarSeVisivel);
    window.addEventListener("storage", sincronizarCaixa);
    return () => {
      monitor.cancelar();
      clearInterval(intervalId);
      document.removeEventListener("visibilitychange", consultarSeVisivel);
      window.removeEventListener("online", consultarSeVisivel);
      window.removeEventListener("storage", sincronizarCaixa);
    };
  }, [contextoCaixa]);

  useEffect(() => {
    if (
      destaqueAbrirCaixa &&
      estadoCaixa.status === "pronto" &&
      !temCaixaAberto &&
      !mostrarModalAbrirCaixa
    ) {
      setMostrarModalAbrirCaixa(true);
    }
  }, [destaqueAbrirCaixa, estadoCaixa.status, temCaixaAberto, mostrarModalAbrirCaixa]);

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
      return nomeCategoria.includes("ração") || nomeCategoria.includes("racao");
    });

    if (racoes.length > 0) {
      setRacaoIdFechada(racoes[racoes.length - 1].produto_id);
    }

    setMostrarCalculadoraRacao(false);
  };

  const handleAbrirCaixaSucesso = () => {
    setMostrarModalAbrirCaixa(false);
    setCaixaKey((prev) => prev + 1);
    publicarEventoCaixa("abertura", { contextoCaixa });
    void atualizarCaixa({ invalidar: true });
  };

  return {
    mostrarModalAbrirCaixa,
    setMostrarModalAbrirCaixa,
    caixaKey,
    temCaixaAberto,
    contextoCaixa,
    caixaAberto: estadoCaixa.caixa,
    statusConsultaCaixa: estadoCaixa.status,
    atualizandoCaixa: estadoCaixa.atualizando,
    atualizarCaixa,
    mostrarCalculadoraRacao,
    racaoIdFechada,
    abrirCalculadoraRacao,
    fecharCalculadoraRacao,
    handleAbrirCaixaSucesso,
  };
}
