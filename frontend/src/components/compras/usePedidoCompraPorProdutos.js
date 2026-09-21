import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import api from "../../api";

function extrairProdutos(response) {
  const produtos = Array.isArray(response?.data)
    ? response.data
    : response?.data?.items || response?.data?.produtos || [];
  return produtos.filter((produto) => produto.tipo_produto !== "PAI");
}

export default function usePedidoCompraPorProdutos({
  carregarProdutosFornecedor,
  formData,
  mostrarForm,
  produtoTexto,
  setItemForm,
  itemFormInicial,
  setMostrarSugestoesProduto,
  setProdutoTexto,
  setProdutos,
}) {
  const [modoMontagem, setModoMontagem] = useState("fornecedor");
  const [filtroProdutosPedido, setFiltroProdutosPedido] = useState("estoque_baixo");
  const [loadingProdutosPedido, setLoadingProdutosPedido] = useState(false);
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
            page: 1,
          page_size: 80,
          include_variations: true,
          busca_completa: true,
          estoque_baixo: !produtoTexto.trim() && filtroProdutosPedido === "estoque_baixo",
          };
          if (produtoTexto.trim()) params.busca = produtoTexto.trim();
          const response = await api.get("/produtos/", { params });
          if (!cancelado) setProdutos(extrairProdutos(response));
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
  }, [filtroProdutosPedido, modoMontagem, mostrarForm, produtoTexto, setProdutos]);

  const alterarModoMontagem = (modo) => {
    setModoMontagem(modo);
    setProdutoTexto("");
    setItemForm(itemFormInicial);
    setMostrarSugestoesProduto(false);
    if (modo === "fornecedor") {
      if (formData.fornecedor_id) carregarProdutosFornecedor(formData.fornecedor_id);
      else setProdutos([]);
    }
  };

  const resetarModoMontagem = () => {
    setModoMontagem("fornecedor");
    setFiltroProdutosPedido("estoque_baixo");
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
    alterarModoMontagem,
    alternarProdutoVinculo,
    alternarTodosProdutosVinculo,
    filtroProdutosPedido,
    loadingProdutosPedido,
    modoMontagem,
    produtosVinculoSelecionados,
    resetarModoMontagem,
    setFiltroProdutosPedido,
    setModoMontagem,
    setVinculoComoPrincipal,
    vincularProdutosFornecedorPedido,
    vinculandoProdutos,
    vinculoComoPrincipal,
  };
}
