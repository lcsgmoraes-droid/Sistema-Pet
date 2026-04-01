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
      inputProdutoRef.current?.focus();
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
    const termoAtual = String(buscarProduto || "").trim();
    buscaProdutoAtualRef.current = termoAtual;

    if (termoAtual.length >= 2) {
      setMostrarSugestoesProduto(true);
      const timer = setTimeout(async () => {
        try {
          const response = await getProdutosVendaveis({ busca: termoAtual });

          if (buscaProdutoAtualRef.current !== termoAtual) {
            return;
          }

          const produtos = response.data.items || [];
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
      let produtoSelecionado = null;

      if (produtosSugeridos.length > 0) {
        produtoSelecionado =
          encontrarProdutoPorCodigo(produtosSugeridos, termo) ||
          produtosSugeridos[0];
      }

      if (!produtoSelecionado) {
        const response = await getProdutosVendaveis({ busca: termo });
        const produtos = response.data.items || [];
        produtoSelecionado =
          encontrarProdutoPorCodigo(produtos, termo) || produtos[0] || null;
      }

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
    if (
      String(buscarProduto || "").trim().length >= 2 &&
      produtosSugeridos.length > 0
    ) {
      setMostrarSugestoesProduto(true);
    }
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
