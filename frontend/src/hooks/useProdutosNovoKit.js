import { useCallback, useEffect, useState } from "react";
import api from "../api";

const produtoPodeSerComponente = (produto, produtoAtualId) => {
  const tipoProduto = produto?.tipo_produto || "SIMPLES";
  const produtoId = Number(produto?.id);
  const atualId = Number(produtoAtualId);

  if (atualId && produtoId === atualId) {
    return false;
  }

  if (
    produto?.e_granel ||
    String(produto?.nome || "")
      .toLowerCase()
      .includes("granel")
  ) {
    return false;
  }

  return ["SIMPLES", "VARIACAO"].includes(tipoProduto);
};

export default function useProdutosNovoKit({ abaAtiva, formData, setFormData }) {
  const [produtosDisponiveis, setProdutosDisponiveis] = useState([]);
  const [produtoKitSelecionado, setProdutoKitSelecionado] = useState("");
  const [quantidadeKit, setQuantidadeKit] = useState("");
  const [estoqueVirtualKit, setEstoqueVirtualKit] = useState(0);
  const [buscaComponente, setBuscaComponente] = useState("");
  const [dropdownComponenteVisivel, setDropdownComponenteVisivel] = useState(false);
  const [loadingComponentes, setLoadingComponentes] = useState(false);

  const calcularEstoqueVirtualKit = (composicao) => {
    if (!composicao || composicao.length === 0) {
      setEstoqueVirtualKit(0);
      return;
    }

    const possibilidades = composicao.map((item) => {
      const estoqueComponente = item.estoque_componente || 0;
      const quantidadeNecessaria = item.quantidade || 1;
      return Math.floor(estoqueComponente / quantidadeNecessaria);
    });

    const estoqueMin = Math.min(...possibilidades);
    setEstoqueVirtualKit(estoqueMin >= 0 ? estoqueMin : 0);
  };

  const carregarProdutosDisponiveis = useCallback(
    async (termo = "") => {
      try {
        setLoadingComponentes(true);
        const response = await api.get("/produtos/", {
          params: {
            ativo: true,
            busca: termo || undefined,
            include_variations: true,
            page: 1,
            page_size: termo ? 80 : 100,
          },
        });

        const produtos = (response.data.items || []).filter((produto) =>
          produtoPodeSerComponente(produto, formData.id),
        );

        setProdutosDisponiveis(produtos);
      } catch (error) {
        console.error("Erro ao carregar produtos:", error);
        setProdutosDisponiveis([]);
      } finally {
        setLoadingComponentes(false);
      }
    },
    [formData.id],
  );

  const adicionarProdutoKit = () => {
    if (!produtoKitSelecionado || !quantidadeKit || quantidadeKit <= 0) {
      alert("Selecione um produto e informe a quantidade!");
      return;
    }

    const produtoId = parseInt(produtoKitSelecionado, 10);
    const jaExiste = formData.composicao_kit.find((item) => item.produto_id === produtoId);

    if (jaExiste) {
      alert("Este produto já foi adicionado ao kit!");
      return;
    }

    const produtoSelecionado = produtosDisponiveis.find((produto) => produto.id === produtoId);
    if (!produtoSelecionado) {
      alert("Produto selecionado não encontrado.");
      return;
    }

    const novoItem = {
      produto_componente_id: produtoSelecionado.id,
      produto_id: produtoSelecionado.id,
      produto_nome: produtoSelecionado.nome,
      produto_sku: produtoSelecionado.codigo,
      quantidade: parseFloat(quantidadeKit),
      estoque_componente: produtoSelecionado.estoque_atual || 0,
    };

    const novaComposicao = [...formData.composicao_kit, novoItem];
    setFormData((prev) => ({
      ...prev,
      composicao_kit: novaComposicao,
    }));

    setProdutoKitSelecionado("");
    setQuantidadeKit("");
    setBuscaComponente("");
    calcularEstoqueVirtualKit(novaComposicao);
  };

  const removerProdutoKit = (produtoId) => {
    const novaComposicao = formData.composicao_kit.filter((item) => item.produto_id !== produtoId);

    setFormData((prev) => ({
      ...prev,
      composicao_kit: novaComposicao,
    }));

    calcularEstoqueVirtualKit(novaComposicao);
  };

  useEffect(() => {
    if (formData.composicao_kit && formData.composicao_kit.length > 0) {
      calcularEstoqueVirtualKit(formData.composicao_kit);
      return;
    }

    setEstoqueVirtualKit(0);
  }, [formData.composicao_kit]);

  useEffect(() => {
    const ehKit =
      formData.tipo_produto === "KIT" ||
      (formData.tipo_produto === "VARIACAO" && formData.tipo_kit);

    if (abaAtiva !== 9 || !ehKit || produtoKitSelecionado) {
      return undefined;
    }

    const termo = buscaComponente.trim();
    const termoApi = termo.length >= 2 ? termo : "";
    const timer = setTimeout(
      () => {
        carregarProdutosDisponiveis(termoApi);
      },
      termoApi ? 250 : 0,
    );

    return () => clearTimeout(timer);
  }, [
    abaAtiva,
    buscaComponente,
    carregarProdutosDisponiveis,
    formData.tipo_kit,
    formData.tipo_produto,
    produtoKitSelecionado,
  ]);

  return {
    produtosDisponiveis,
    produtoKitSelecionado,
    setProdutoKitSelecionado,
    quantidadeKit,
    setQuantidadeKit,
    estoqueVirtualKit,
    buscaComponente,
    setBuscaComponente,
    dropdownComponenteVisivel,
    setDropdownComponenteVisivel,
    loadingComponentes,
    adicionarProdutoKit,
    removerProdutoKit,
  };
}
