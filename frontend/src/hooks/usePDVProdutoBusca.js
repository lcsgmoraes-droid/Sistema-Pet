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

  const buscarProdutosAtualizados = async (termo) => {
    const response = await getProdutosVendaveis({
      busca: termo,
      _ts: Date.now(),
    });

    return response.data.items || [];
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

  const limparBuscaProduto = ({ focarInput = false } = {}) => {
    setBuscarProduto("");
    setProdutosSugeridos([]);
    setMostrarSugestoesProduto(false);
    resetScannerState();

    if (focarInput) {
      focarInputProduto();
    }
  };

  const adicionarProduto = (produto, options) => {
    const adicionou = adicionarProdutoAoCarrinho(produto);

    if (adicionou === false) {
      return false;
    }

    limparBuscaProduto(options);
    return true;
  };

  useEffect(() => {
    setBuscarProduto("");
    setProdutosSugeridos([]);
    setMostrarSugestoesProduto(false);
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
          console.error("Erro ao buscar produtos:", error);
          setProdutosSugeridos([]);
        }
      }, 300);

      return () => clearTimeout(timer);
    }

    setProdutosSugeridos([]);
    setMostrarSugestoesProduto(false);
    resetScannerState();
    return undefined;
  }, [adicionarProdutoAoCarrinho, buscarProduto, modoVisualizacao]);

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
      setProdutosSugeridos([]);
      setMostrarSugestoesProduto(false);
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
