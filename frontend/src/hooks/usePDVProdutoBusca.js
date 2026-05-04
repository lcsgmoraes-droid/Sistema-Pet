import { useEffect, useRef, useState } from "react";
import { getProdutosVendaveis } from "../api/produtos";

function encontrarProdutoPorCodigo(produtos, termo) {
  const termoLower = String(termo || "").toLowerCase();

  return (
    produtos.find((produto) => {
      const codigo = String(produto.codigo || "").toLowerCase();
      const codigoBarras = String(produto.codigo_barras || "").toLowerCase();
      return codigo === termoLower || codigoBarras === termoLower;
    }) || null
  );
}

function isBuscaCancelada(error) {
  return (
    error?.code === "ERR_CANCELED" ||
    error?.name === "CanceledError" ||
    error?.name === "AbortError"
  );
}

export function usePDVProdutoBusca({
  modoVisualizacao,
  adicionarProdutoAoCarrinho,
  vendaContextKey,
}) {
  const [buscarProduto, setBuscarProduto] = useState("");
  const [produtosSugeridos, setProdutosSugeridos] = useState([]);
  const [mostrarSugestoesProduto, setMostrarSugestoesProduto] =
    useState(false);

  const inputProdutoRef = useRef(null);
  const buscaProdutoContainerRef = useRef(null);
  const ultimoAutoAddProdutoRef = useRef("");
  const ultimoEventoTeclaProdutoMsRef = useRef(0);
  const sequenciaRapidaProdutoRef = useRef(0);
  const leituraScannerDetectadaRef = useRef(false);
  const adicionandoProdutoPorEnterRef = useRef(false);
  const buscaProdutoAtualRef = useRef("");
  const focoProdutoTimeoutRef = useRef(null);
  const adicionarProdutoAoCarrinhoRef = useRef(adicionarProdutoAoCarrinho);
  const buscaProdutoAbortControllerRef = useRef(null);

  useEffect(() => {
    adicionarProdutoAoCarrinhoRef.current = adicionarProdutoAoCarrinho;
  }, [adicionarProdutoAoCarrinho]);

  const cancelarBuscaProdutoPendente = () => {
    if (buscaProdutoAbortControllerRef.current) {
      buscaProdutoAbortControllerRef.current.abort();
      buscaProdutoAbortControllerRef.current = null;
    }
  };

  const buscarProdutosAtualizados = async (termo) => {
    cancelarBuscaProdutoPendente();
    const controller = new AbortController();
    buscaProdutoAbortControllerRef.current = controller;

    try {
      const response = await getProdutosVendaveis({
        busca: termo,
        page_size: 12,
        _ts: Date.now(),
      }, {
        signal: controller.signal,
      });

      return response.data.items || [];
    } finally {
      if (buscaProdutoAbortControllerRef.current === controller) {
        buscaProdutoAbortControllerRef.current = null;
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
    const adicionou = adicionarProdutoAoCarrinhoRef.current?.(produto);

    if (adicionou === false) {
      return false;
    }

    limparBuscaProduto(options);
    return true;
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
          const produtos = await buscarProdutosAtualizados(termoAtual);

          if (buscaProdutoAtualRef.current !== termoAtual) {
            return;
          }

          const matchExato = encontrarProdutoPorCodigo(produtos, termoAtual);

          if (
            matchExato &&
            ultimoAutoAddProdutoRef.current !== termoAtual.toLowerCase() &&
            leituraScannerDetectadaRef.current &&
            !modoVisualizacao
          ) {
            ultimoAutoAddProdutoRef.current = termoAtual.toLowerCase();
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
    if (
      evento.key.length !== 1 ||
      evento.ctrlKey ||
      evento.altKey ||
      evento.metaKey
    ) {
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

  const adicionarProdutoViaEnter = async () => {
    const termo = String(buscarProduto || "").trim();
    if (!termo || modoVisualizacao || adicionandoProdutoPorEnterRef.current) {
      return;
    }

    adicionandoProdutoPorEnterRef.current = true;
    try {
      const produtos = await buscarProdutosAtualizados(termo);
      const produtoSelecionado =
        encontrarProdutoPorCodigo(produtos, termo) || produtos[0] || null;

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
      await adicionarProdutoViaEnter();
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
