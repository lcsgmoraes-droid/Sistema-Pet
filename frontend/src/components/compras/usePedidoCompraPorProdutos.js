import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import api from "../../api";
import { criarItemCatalogoPedido } from "./pedidoCompraPorProdutosUtils";

function extrairProdutos(response) {
  const payload = response?.data || {};
  const produtos = Array.isArray(payload) ? payload : payload.items || payload.produtos || [];
  const items = produtos.filter((produto) => produto.tipo_produto !== "PAI");
  return {
    items,
    paginacao: {
      total: Number(payload.total ?? items.length),
      page: Number(payload.page || 1),
      page_size: Number(payload.page_size || 25),
      pages: Number(payload.pages || (items.length ? 1 : 0)),
    },
  };
}

export default function usePedidoCompraPorProdutos({
  carregarProdutosFornecedor,
  formData,
  mostrarForm,
  produtoTexto,
  setFormData,
  setItemForm,
  itemFormInicial,
  setMostrarSugestoesProduto,
  setProdutoTexto,
  setProdutos,
}) {
  const [modoMontagem, setModoMontagem] = useState("produtos");
  const [filtroProdutosPedido, setFiltroProdutosPedido] = useState("estoque_baixo");
  const [loadingProdutosPedido, setLoadingProdutosPedido] = useState(false);
  const [paginaProdutosPedido, setPaginaProdutosPedido] = useState(1);
  const [paginacaoProdutosPedido, setPaginacaoProdutosPedido] = useState({
    total: 0,
    page: 1,
    page_size: 25,
    pages: 0,
  });
  const [produtosVinculoSelecionados, setProdutosVinculoSelecionados] = useState([]);
  const [vinculoComoPrincipal, setVinculoComoPrincipal] = useState(true);
  const [vinculandoProdutos, setVinculandoProdutos] = useState(false);
  const idsAnterioresRef = useRef(new Set());

  const idsItensPedido = useMemo(
    () => [...new Set(formData.itens.map((item) => Number(item.produto_id)).filter(Boolean))],
    [formData.itens],
  );

  useEffect(() => {
    const atuais = new Set(idsItensPedido);
    setProdutosVinculoSelecionados((selecionados) => {
      const proximos = new Set(selecionados.filter((id) => atuais.has(Number(id))));
      idsItensPedido.forEach((id) => {
        if (!idsAnterioresRef.current.has(id)) proximos.add(id);
      });
      return [...proximos];
    });
    idsAnterioresRef.current = atuais;
  }, [idsItensPedido]);

  useEffect(() => {
    if (!mostrarForm || modoMontagem !== "produtos") return undefined;

    let cancelado = false;
    const timer = setTimeout(
      async () => {
        setLoadingProdutosPedido(true);
        try {
          const params = {
            page: paginaProdutosPedido,
            page_size: 25,
            filtro: filtroProdutosPedido,
          };
          if (produtoTexto.trim()) params.busca = produtoTexto.trim();
          const response = await api.get("/pedidos-compra/catalogo-produtos", { params });
          if (!cancelado) {
            const resultado = extrairProdutos(response);
            setProdutos(resultado.items);
            setPaginacaoProdutosPedido(resultado.paginacao);
            if (resultado.paginacao.page !== paginaProdutosPedido) {
              setPaginaProdutosPedido(resultado.paginacao.page);
            }
          }
        } catch (error) {
          if (!cancelado) {
            console.error("Erro ao pesquisar produtos para o pedido:", error);
            toast.error("Erro ao pesquisar produtos");
          }
        } finally {
          if (!cancelado) setLoadingProdutosPedido(false);
        }
      },
      produtoTexto.trim() ? 250 : 0,
    );

    return () => {
      cancelado = true;
      clearTimeout(timer);
    };
  }, [
    filtroProdutosPedido,
    modoMontagem,
    mostrarForm,
    paginaProdutosPedido,
    produtoTexto,
    setProdutos,
  ]);

  const alterarFiltroProdutosPedido = (filtro) => {
    setFiltroProdutosPedido(filtro);
    setPaginaProdutosPedido(1);
  };

  const alterarTermoProdutosPedido = (termo) => {
    setProdutoTexto(termo);
    setPaginaProdutosPedido(1);
  };

  const alterarModoMontagem = (modo) => {
    setModoMontagem(modo);
    setProdutoTexto("");
    setPaginaProdutosPedido(1);
    setItemForm(itemFormInicial);
    setMostrarSugestoesProduto(false);
    if (modo === "fornecedor") {
      if (formData.fornecedor_id) carregarProdutosFornecedor(formData.fornecedor_id);
      else setProdutos([]);
    }
  };

  const adicionarProdutoCatalogo = (produto, quantidade, custoUnitario) => {
    if (Number(quantidade) <= 0) {
      toast.error("Informe uma quantidade maior que zero");
      return;
    }

    const produtoJaAdicionado = formData.itens.some(
      (item) => Number(item.produto_id) === Number(produto.id),
    );

    setFormData((atual) => {
      const itemIndex = atual.itens.findIndex(
        (item) => Number(item.produto_id) === Number(produto.id),
      );
      const itemAtual = itemIndex >= 0 ? atual.itens[itemIndex] : null;
      const proximoItem = criarItemCatalogoPedido({
        produto,
        quantidade,
        custoUnitario,
        itemAtual,
      });

      if (!proximoItem) return atual;

      const itens = [...atual.itens];
      if (itemIndex >= 0) itens[itemIndex] = proximoItem;
      else itens.push(proximoItem);

      return { ...atual, itens };
    });

    toast.success(
      produtoJaAdicionado ? "Produto atualizado no pedido" : "Produto adicionado ao pedido",
    );
  };

  const resetarModoMontagem = () => {
    setModoMontagem("fornecedor");
    setFiltroProdutosPedido("estoque_baixo");
    setPaginaProdutosPedido(1);
    setPaginacaoProdutosPedido({ total: 0, page: 1, page_size: 25, pages: 0 });
    setProdutosVinculoSelecionados([]);
    setVinculoComoPrincipal(true);
    idsAnterioresRef.current = new Set();
  };

  const alternarProdutoVinculo = (produtoId) => {
    const id = Number(produtoId);
    setProdutosVinculoSelecionados((atuais) =>
      atuais.includes(id) ? atuais.filter((item) => item !== id) : [...atuais, id],
    );
  };

  const alternarTodosProdutosVinculo = () => {
    setProdutosVinculoSelecionados((atuais) =>
      atuais.length === idsItensPedido.length ? [] : idsItensPedido,
    );
  };

  const vincularProdutosFornecedorPedido = async () => {
    if (!formData.fornecedor_id) {
      toast.error("Selecione ou cadastre um fornecedor para vincular os produtos");
      return;
    }
    const idsValidos = produtosVinculoSelecionados.filter((id) => idsItensPedido.includes(id));
    if (!idsValidos.length) {
      toast.error("Selecione pelo menos um produto do pedido");
      return;
    }

    setVinculandoProdutos(true);
    try {
      await api.patch("/produtos/atualizar-lote", {
        produto_ids: idsValidos,
        fornecedor_id: Number(formData.fornecedor_id),
        fornecedor_operacao: vinculoComoPrincipal ? "definir_principal" : "adicionar",
        fornecedor_remover_outros: false,
      });
      toast.success(
        `${idsValidos.length} produto${idsValidos.length === 1 ? " vinculado" : "s vinculados"} ao fornecedor`,
      );
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao vincular os produtos ao fornecedor");
    } finally {
      setVinculandoProdutos(false);
    }
  };

  return {
    adicionarProdutoCatalogo,
    alterarFiltroProdutosPedido,
    alterarModoMontagem,
    alterarTermoProdutosPedido,
    alternarProdutoVinculo,
    alternarTodosProdutosVinculo,
    filtroProdutosPedido,
    loadingProdutosPedido,
    modoMontagem,
    paginaProdutosPedido,
    paginacaoProdutosPedido,
    produtosVinculoSelecionados,
    resetarModoMontagem,
    setPaginaProdutosPedido,
    setModoMontagem,
    setVinculoComoPrincipal,
    vincularProdutosFornecedorPedido,
    vinculandoProdutos,
    vinculoComoPrincipal,
  };
}
