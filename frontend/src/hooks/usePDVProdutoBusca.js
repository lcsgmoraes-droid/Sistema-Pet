import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { getProdutosVendaveis } from "../api/produtos";
import {
  calcularItemEtiquetaBalanca,
  lerEtiquetaBalanca,
  produtoAceitaEtiquetaBalanca,
} from "../utils/pdvEtiquetaBalanca";
import {
  deveAdicionarProdutoAutomaticamente,
  encontrarProdutoPorCodigo,
  normalizarCodigoProdutoBusca,
} from "../utils/pdvProdutoBuscaUtils";

function isBuscaCancelada(error) {
  return (
    error?.code === "ERR_CANCELED" ||
    error?.name === "CanceledError" ||
    error?.name === "AbortError"
  );
}

const BUSCA_PRODUTO_CACHE_MS = 2000;
const BUSCA_PRODUTO_CACHE_MAX = 20;

export function usePDVProdutoBusca({
  modoVisualizacao,
  adicionarProdutoAoCarrinho,
  vendaContextKey,
}) {
  const [buscarProduto, setBuscarProduto] = useState("");
  const [produtosSugeridos, setProdutosSugeridos] = useState([]);
  const [mostrarSugestoesProduto, setMostrarSugestoesProduto] = useState(false);

  const inputProdutoRef = useRef(null);
  const buscaProdutoContainerRef = useRef(null);
  const ultimoAutoAddProdutoRef = useRef("");
  const ultimoEventoTeclaProdutoMsRef = useRef(0);
  const sequenciaRapidaProdutoRef = useRef(0);
  const leituraScannerDetectadaRef = useRef(false);
  const adicionandoProdutoPorEnterRef = useRef(false);
  const processandoEtiquetaBalancaRef = useRef(false);
  const ultimoErroEtiquetaRef = useRef("");
  const buscaProdutoAtualRef = useRef("");
  const focoProdutoTimeoutRef = useRef(null);
  const adicionarProdutoAoCarrinhoRef = useRef(adicionarProdutoAoCarrinho);
  const buscaProdutoPendenteRef = useRef(null);
  const buscaProdutoCacheRef = useRef(new Map());

  useEffect(() => {
    adicionarProdutoAoCarrinhoRef.current = adicionarProdutoAoCarrinho;
  }, [adicionarProdutoAoCarrinho]);

  const cancelarBuscaProdutoPendente = () => {
    if (buscaProdutoPendenteRef.current) {
      buscaProdutoPendenteRef.current.controller.abort();
      buscaProdutoPendenteRef.current = null;
    }
  };

  const buscarProdutosAtualizados = async (termo) => {
    const termoNormalizado = String(termo || "").trim();
    const chaveBusca = termoNormalizado.toLocaleLowerCase("pt-BR");
    const cacheAtual = buscaProdutoCacheRef.current.get(chaveBusca);

    if (cacheAtual && Date.now() - cacheAtual.criadoEm < BUSCA_PRODUTO_CACHE_MS) {
      return cacheAtual.produtos;
    }

    if (buscaProdutoPendenteRef.current?.chaveBusca === chaveBusca) {
      return buscaProdutoPendenteRef.current.promise;
    }

    cancelarBuscaProdutoPendente();
    const controller = new AbortController();
    const promise = (async () => {
      const response = await getProdutosVendaveis(
        {
          busca: termoNormalizado,
          page_size: 12,
          contar_total: false,
          incluir_imagens: false,
        },
        {
          signal: controller.signal,
        },
      );
      const produtos = response.data.items || [];
      const cache = buscaProdutoCacheRef.current;

      if (cache.size >= BUSCA_PRODUTO_CACHE_MAX && !cache.has(chaveBusca)) {
        cache.delete(cache.keys().next().value);
      }
      cache.set(chaveBusca, { criadoEm: Date.now(), produtos });
      return produtos;
    })();
    buscaProdutoPendenteRef.current = { chaveBusca, controller, promise };

    try {
      return await promise;
    } finally {
      if (buscaProdutoPendenteRef.current?.controller === controller) {
        buscaProdutoPendenteRef.current = null;
      }
    }
  };

  const focarInputProduto = () => {
    const aplicarFoco = () => {
      const input = inputProdutoRef.current;
      if (!input) return;
      input.focus();
      if (typeof input.select === "function") {
        input.select();
      }
    };

    if (focoProdutoTimeoutRef.current) {
      clearTimeout(focoProdutoTimeoutRef.current);
    }

    if (typeof window !== "undefined" && window.requestAnimationFrame) {
      window.requestAnimationFrame(() => {
        aplicarFoco();
        window.requestAnimationFrame(aplicarFoco);
      });
      return;
    }

    focoProdutoTimeoutRef.current = setTimeout(aplicarFoco, 0);
  };

  const resetScannerState = () => {
    ultimoAutoAddProdutoRef.current = "";
    leituraScannerDetectadaRef.current = false;
    sequenciaRapidaProdutoRef.current = 0;
  };

  const limparSugestoesProduto = () => {
    setProdutosSugeridos((prev) => (prev.length > 0 ? [] : prev));
    setMostrarSugestoesProduto((prev) => (prev ? false : prev));
  };

  const limparBuscaProduto = ({ focarInput = false } = {}) => {
    setBuscarProduto("");
    limparSugestoesProduto();
    resetScannerState();

    if (focarInput) {
      focarInputProduto();
    }
  };

  const adicionarProduto = (produto, options) => {
    const adicionou = adicionarProdutoAoCarrinhoRef.current?.(
      produto,
      options?.etiquetaBalanca || null,
    );

    if (adicionou === false) {
      return false;
    }

    limparBuscaProduto(options);
    return true;
  };

  const mostrarErroEtiqueta = (etiqueta, mensagem) => {
    if (ultimoErroEtiquetaRef.current === etiqueta.codigo) return;
    ultimoErroEtiquetaRef.current = etiqueta.codigo;
    toast.error(mensagem);
  };

  const processarEtiquetaBalanca = async (etiqueta) => {
    if (processandoEtiquetaBalancaRef.current) return true;
    if (etiqueta.erro) {
      mostrarErroEtiqueta(etiqueta, etiqueta.erro);
      return true;
    }

    processandoEtiquetaBalancaRef.current = true;
    try {
      // Preserva produtos comuns cujo EAN tambem comeca com 2.
      const produtosCodigoCompleto = await buscarProdutosAtualizados(etiqueta.codigo);
      const produtoCodigoCompleto = encontrarProdutoPorCodigo(
        produtosCodigoCompleto,
        etiqueta.codigo,
      );
      if (produtoCodigoCompleto && !produtoAceitaEtiquetaBalanca(produtoCodigoCompleto)) {
        if (!modoVisualizacao) adicionarProduto(produtoCodigoCompleto, { focarInput: true });
        return true;
      }

      const produtos = await buscarProdutosAtualizados(etiqueta.codigoProdutoSemZeros);
      const candidatos = produtos.filter(
        (produto) =>
          encontrarProdutoPorCodigo([produto], etiqueta.codigoProduto) ||
          encontrarProdutoPorCodigo([produto], etiqueta.codigoProdutoSemZeros),
      );
      if (candidatos.length !== 1) {
        mostrarErroEtiqueta(
          etiqueta,
          candidatos.length > 1
            ? "Mais de um produto usa o codigo desta etiqueta. Corrija o cadastro."
            : `Produto ${etiqueta.codigoProdutoSemZeros} nao encontrado para esta etiqueta.`,
        );
        return true;
      }

      const produto = candidatos[0];
      if (!produtoAceitaEtiquetaBalanca(produto)) {
        mostrarErroEtiqueta(
          etiqueta,
          "O produto desta etiqueta precisa estar marcado como granel e com unidade KG.",
        );
        return true;
      }

      const itemEtiqueta = calcularItemEtiquetaBalanca(etiqueta, produto);
      if (itemEtiqueta.erro) {
        mostrarErroEtiqueta(etiqueta, itemEtiqueta.erro);
        return true;
      }

      if (!modoVisualizacao) {
        adicionarProduto(produto, { focarInput: true, etiquetaBalanca: itemEtiqueta });
      }
      return true;
    } finally {
      processandoEtiquetaBalancaRef.current = false;
    }
  };

  useEffect(() => {
    setBuscarProduto("");
    limparSugestoesProduto();
    resetScannerState();
  }, [vendaContextKey]);

  useEffect(() => {
    const termoAtual = String(buscarProduto || "").trim();
    buscaProdutoAtualRef.current = termoAtual;

    if (termoAtual.length >= 2) {
      setMostrarSugestoesProduto(true);
      const timer = setTimeout(async () => {
        try {
          const etiqueta = lerEtiquetaBalanca(termoAtual);
          if (etiqueta) {
            await processarEtiquetaBalanca(etiqueta);
            return;
          }

          const produtos = await buscarProdutosAtualizados(termoAtual);

          if (buscaProdutoAtualRef.current !== termoAtual) {
            return;
          }

          const matchExato = encontrarProdutoPorCodigo(produtos, termoAtual);

          if (
            deveAdicionarProdutoAutomaticamente({
              matchExato,
              termo: termoAtual,
              leituraScannerDetectada: leituraScannerDetectadaRef.current,
              modoVisualizacao,
              ultimoAutoAddProduto: ultimoAutoAddProdutoRef.current,
            })
          ) {
            ultimoAutoAddProdutoRef.current = normalizarCodigoProdutoBusca(termoAtual);
            adicionarProduto(matchExato, { focarInput: true });
            return;
          }

          setProdutosSugeridos(produtos);
        } catch (error) {
          if (isBuscaCancelada(error)) {
            return;
          }
          console.error("Erro ao buscar produtos:", error);
          setProdutosSugeridos([]);
        }
      }, 300);

      return () => {
        clearTimeout(timer);
        cancelarBuscaProdutoPendente();
      };
    }

    limparSugestoesProduto();
    resetScannerState();
    return undefined;
  }, [buscarProduto, modoVisualizacao]);

  useEffect(() => {
    const handleCliqueFora = (event) => {
      if (!buscaProdutoContainerRef.current) return;
      if (!buscaProdutoContainerRef.current.contains(event.target)) {
        setMostrarSugestoesProduto(false);
      }
    };

    document.addEventListener("mousedown", handleCliqueFora);
    return () => document.removeEventListener("mousedown", handleCliqueFora);
  }, []);

  useEffect(
    () => () => {
      if (focoProdutoTimeoutRef.current) {
        clearTimeout(focoProdutoTimeoutRef.current);
      }
      cancelarBuscaProdutoPendente();
    },
    [],
  );

  const registrarPossivelLeituraScanner = (evento) => {
    if (evento.key.length !== 1 || evento.ctrlKey || evento.altKey || evento.metaKey) {
      return;
    }

    const agora = Date.now();
    const delta = agora - ultimoEventoTeclaProdutoMsRef.current;
    ultimoEventoTeclaProdutoMsRef.current = agora;

    if (delta > 0 && delta <= 45) {
      sequenciaRapidaProdutoRef.current += 1;
    } else {
      sequenciaRapidaProdutoRef.current = 1;
    }

    leituraScannerDetectadaRef.current = sequenciaRapidaProdutoRef.current >= 6;
  };

  const adicionarProdutoViaEnter = async (termoOverride) => {
    const termo = String(termoOverride ?? buscarProduto ?? "").trim();
    if (!termo || modoVisualizacao || adicionandoProdutoPorEnterRef.current) {
      return;
    }

    adicionandoProdutoPorEnterRef.current = true;
    try {
      const etiqueta = lerEtiquetaBalanca(termo);
      if (etiqueta) {
        await processarEtiquetaBalanca(etiqueta);
        return;
      }

      const produtos = await buscarProdutosAtualizados(termo);
      const produtoSelecionado = encontrarProdutoPorCodigo(produtos, termo) || produtos[0] || null;

      if (produtoSelecionado) {
        adicionarProduto(produtoSelecionado, { focarInput: true });
      }
    } catch (error) {
      if (isBuscaCancelada(error)) {
        return;
      }
      console.error("Erro ao adicionar produto via Enter:", error);
    } finally {
      leituraScannerDetectadaRef.current = false;
      sequenciaRapidaProdutoRef.current = 0;
      adicionandoProdutoPorEnterRef.current = false;
    }
  };

  const handleBuscarProdutoChange = (valor) => {
    if (String(valor || "").trim() !== ultimoErroEtiquetaRef.current) {
      ultimoErroEtiquetaRef.current = "";
    }
    setBuscarProduto(valor);
    if (!String(valor || "").trim()) {
      limparSugestoesProduto();
    }
  };

  const handleBuscarProdutoFocus = () => {
    const termo = String(buscarProduto || "").trim();

    if (termo.length < 2) {
      return;
    }

    setMostrarSugestoesProduto(true);

    void (async () => {
      try {
        buscaProdutoAtualRef.current = termo;
        const produtos = await buscarProdutosAtualizados(termo);

        if (buscaProdutoAtualRef.current !== termo) {
          return;
        }

        setProdutosSugeridos(produtos);
      } catch (error) {
        if (isBuscaCancelada(error)) {
          return;
        }
        console.error("Erro ao atualizar sugestoes de produtos:", error);
      }
    })();
  };

  const handleBuscarProdutoKeyDown = async (event) => {
    registrarPossivelLeituraScanner(event);

    if (event.key === "Enter") {
      event.preventDefault();
      await adicionarProdutoViaEnter(event.currentTarget?.value);
    }
  };

  const selecionarProdutoSugerido = (produto) => {
    adicionarProduto(produto, { focarInput: true });
  };

  return {
    buscaProduto: buscarProduto,
    buscaProdutoContainerRef,
    inputProdutoRef,
    mostrarSugestoesProduto,
    produtosSugeridos,
    adicionarProduto,
    handleBuscarProdutoChange,
    handleBuscarProdutoFocus,
    handleBuscarProdutoKeyDown,
    limparBuscaProduto,
    selecionarProdutoSugerido,
  };
}
