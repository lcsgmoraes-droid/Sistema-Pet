import { useEffect, useRef, useState } from "react";
import { getProdutosVendaveis } from "../api/produtos";
import { debugLog } from "../utils/debug";

export function usePDVProdutos({
  vendaAtual,
  setVendaAtual,
  modoVisualizacao,
  temCaixaAberto,
  recalcularTotais,
}) {
  const [buscarProduto, setBuscarProduto] = useState("");
  const [produtosSugeridos, setProdutosSugeridos] = useState([]);
  const [mostrarSugestoesProduto, setMostrarSugestoesProduto] =
    useState(false);
  const [copiadoCodigoItem, setCopiadoCodigoItem] = useState("");
  const [itensKitExpandidos, setItensKitExpandidos] = useState({});

  const inputProdutoRef = useRef(null);
  const buscaProdutoContainerRef = useRef(null);
  const ultimoAutoAddProdutoRef = useRef("");
  const ultimoEventoTeclaProdutoMsRef = useRef(0);
  const sequenciaRapidaProdutoRef = useRef(0);
  const leituraScannerDetectadaRef = useRef(false);
  const adicionandoProdutoPorEnterRef = useRef(false);
  const buscaProdutoAtualRef = useRef("");

  const adicionarProduto = (produto) => {
    if (!temCaixaAberto) {
      alert(
        "❌ Não é possível adicionar produtos sem caixa aberto. Abra um caixa primeiro.",
      );
      return;
    }

    debugLog("🛒 Produto sendo adicionado:", {
      nome: produto.nome,
      categoria_id: produto.categoria_id,
      categoria_nome: produto.categoria_nome,
      peso_embalagem: produto.peso_embalagem,
      classificacao_racao: produto.classificacao_racao,
    });

    const itemExistente = vendaAtual.itens.find(
      (item) => item.produto_id === produto.id,
    );

    let novosItens;
    if (itemExistente) {
      novosItens = vendaAtual.itens.map((item) =>
        item.produto_id === produto.id
          ? {
              ...item,
              quantidade: item.quantidade + 1,
              subtotal: (item.quantidade + 1) * item.preco_unitario,
            }
          : item,
      );
    } else {
      novosItens = [
        ...vendaAtual.itens,
        {
          tipo: "produto",
          produto_id: produto.id,
          produto_nome: produto.nome,
          produto_codigo: produto.codigo || null,
          quantidade: 1,
          preco_unitario: parseFloat(produto.preco_venda),
          desconto_item: 0,
          subtotal: parseFloat(produto.preco_venda),
          pet_id: vendaAtual.pet?.id || null,
          tipo_produto: produto.tipo_produto,
          tipo_kit: produto.tipo_kit,
          composicao_kit: produto.composicao_kit || [],
          categoria_id: produto.categoria_id,
          categoria_nome: produto.categoria_nome,
          peso_pacote_kg: produto.peso_liquido || produto.peso_bruto,
          peso_embalagem: produto.peso_embalagem,
          classificacao_racao: produto.classificacao_racao,
          estoque_atual: produto.estoque_atual,
          estoque_virtual: produto.estoque_virtual,
        },
      ];
    }

    recalcularTotais(novosItens);
    setBuscarProduto("");
    setProdutosSugeridos([]);
    setMostrarSugestoesProduto(false);
    inputProdutoRef.current?.focus();
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
          const termoLower = termoAtual.toLowerCase();
          const matchExato = produtos.find((p) => {
            const codigo = String(p.codigo || "").toLowerCase();
            const codigoBarras = String(p.codigo_barras || "").toLowerCase();
            return codigo === termoLower || codigoBarras === termoLower;
          });

          if (
            matchExato &&
            ultimoAutoAddProdutoRef.current !== termoLower &&
            leituraScannerDetectadaRef.current &&
            !modoVisualizacao
          ) {
            ultimoAutoAddProdutoRef.current = termoLower;
            adicionarProduto(matchExato);
            leituraScannerDetectadaRef.current = false;
            sequenciaRapidaProdutoRef.current = 0;
            setMostrarSugestoesProduto(false);
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

    ultimoAutoAddProdutoRef.current = "";
    leituraScannerDetectadaRef.current = false;
    sequenciaRapidaProdutoRef.current = 0;
    setProdutosSugeridos([]);
    setMostrarSugestoesProduto(false);
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

  function registrarPossivelLeituraScanner(evento) {
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
  }

  async function adicionarProdutoViaEnter() {
    const termo = String(buscarProduto || "").trim();
    if (!termo || modoVisualizacao || adicionandoProdutoPorEnterRef.current) {
      return;
    }

    adicionandoProdutoPorEnterRef.current = true;
    try {
      const termoLower = termo.toLowerCase();
      let produtoSelecionado = null;

      if (produtosSugeridos.length > 0) {
        produtoSelecionado =
          produtosSugeridos.find((p) => {
            const codigo = String(p.codigo || "").toLowerCase();
            const codigoBarras = String(p.codigo_barras || "").toLowerCase();
            return codigo === termoLower || codigoBarras === termoLower;
          }) || produtosSugeridos[0];
      }

      if (!produtoSelecionado) {
        const response = await getProdutosVendaveis({ busca: termo });
        const produtos = response.data.items || [];
        produtoSelecionado =
          produtos.find((p) => {
            const codigo = String(p.codigo || "").toLowerCase();
            const codigoBarras = String(p.codigo_barras || "").toLowerCase();
            return codigo === termoLower || codigoBarras === termoLower;
          }) || produtos[0] || null;
      }

      if (produtoSelecionado) {
        adicionarProduto(produtoSelecionado);
      }
    } catch (error) {
      console.error("Erro ao adicionar produto via Enter:", error);
    } finally {
      leituraScannerDetectadaRef.current = false;
      sequenciaRapidaProdutoRef.current = 0;
      adicionandoProdutoPorEnterRef.current = false;
    }
  }

  const copiarCodigoProdutoCarrinho = (codigo, chaveItem) => {
    if (!codigo) return;
    navigator.clipboard.writeText(String(codigo));
    setCopiadoCodigoItem(chaveItem);
    setTimeout(() => setCopiadoCodigoItem(""), 2000);
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
    adicionarProduto(produto);
    setMostrarSugestoesProduto(false);
  };

  const alterarQuantidade = (index, delta) => {
    const novosItens = vendaAtual.itens.map((item, itemIndex) => {
      if (itemIndex !== index) return item;

      const novaQuantidade = Math.max(1, item.quantidade + delta);
      const subtotalSemDesconto = novaQuantidade * item.preco_unitario;
      let novoDescontoValor = item.desconto_valor || 0;

      if (
        item.tipo_desconto_aplicado === "percentual" &&
        item.desconto_percentual > 0
      ) {
        novoDescontoValor =
          (subtotalSemDesconto * item.desconto_percentual) / 100;
      }

      return {
        ...item,
        quantidade: novaQuantidade,
        desconto_valor: novoDescontoValor,
        subtotal: subtotalSemDesconto - novoDescontoValor,
      };
    });

    recalcularTotais(novosItens);
  };

  const atualizarQuantidadeItem = (index, novaQuantidade) => {
    const novosItens = vendaAtual.itens.map((item, itemIndex) => {
      if (itemIndex !== index) return item;

      const subtotalSemDesconto = novaQuantidade * item.preco_unitario;
      let novoDescontoValor = item.desconto_valor || 0;

      if (
        item.tipo_desconto_aplicado === "percentual" &&
        item.desconto_percentual > 0
      ) {
        novoDescontoValor =
          (subtotalSemDesconto * item.desconto_percentual) / 100;
      }

      return {
        ...item,
        quantidade: novaQuantidade,
        desconto_valor: novoDescontoValor,
        subtotal: subtotalSemDesconto - novoDescontoValor,
      };
    });

    recalcularTotais(novosItens);
  };

  const atualizarPetDoItem = (index, petId) => {
    setVendaAtual((prev) => ({
      ...prev,
      itens: prev.itens.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              pet_id: petId,
            }
          : item,
      ),
    }));
  };

  const removerItem = (index) => {
    const novosItens = vendaAtual.itens.filter((_, itemIndex) => itemIndex !== index);
    recalcularTotais(novosItens);
  };

  const toggleKitExpansion = (index) => {
    setItensKitExpandidos((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const limparBuscaProduto = () => {
    setBuscarProduto("");
    setProdutosSugeridos([]);
    setMostrarSugestoesProduto(false);
  };

  return {
    buscaProduto: buscarProduto,
    buscaProdutoContainerRef,
    copiadoCodigoItem,
    inputProdutoRef,
    itensKitExpandidos,
    mostrarSugestoesProduto,
    produtosSugeridos,
    adicionarProduto,
    alterarQuantidade,
    atualizarPetDoItem,
    atualizarQuantidadeItem,
    copiarCodigoProdutoCarrinho,
    handleBuscarProdutoChange,
    handleBuscarProdutoFocus,
    handleBuscarProdutoKeyDown,
    limparBuscaProduto,
    removerItem,
    selecionarProdutoSugerido,
    toggleKitExpansion,
  };
}
