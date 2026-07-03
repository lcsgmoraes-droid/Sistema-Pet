import { toast } from "react-hot-toast";
import api from "../../api";
import {
  calcularQuantidadeTotalUnidadesPedido,
  normalizarQuantidadePorEmbalagemPedido,
  normalizarUnidadeCompraPedido,
  numeroSeguro,
} from "./pedidoCompraUtils";

export function createPedidosCompraItemController({
  formData,
  itemForm,
  itemFormInicial,
  produtos,
  setFormData,
  setItemForm,
  setMostrarSugestoesProduto,
  setProdutos,
  setProdutoTexto,
}) {
  const selecionarProduto = (produto) => {
    preencherPreco(produto.id.toString());
    setMostrarSugestoesProduto(false);
  };

  const carregarProdutosFornecedor = async (fornecedorId, opcoes = {}) => {
    if (!fornecedorId) {
      setProdutos([]);
      return;
    }
    try {
      const params = new URLSearchParams({ fornecedor_id: fornecedorId });
      if (opcoes.fornecedorGrupoId) {
        params.set("fornecedor_grupo_id", opcoes.fornecedorGrupoId);
      }

      const response = await api.get(`/produtos/?${params.toString()}`);

      // API pode retornar array direto ou objeto paginado
      let produtosData;
      if (Array.isArray(response.data)) {
        produtosData = response.data;
      } else if (response.data.items) {
        produtosData = response.data.items;
      } else if (response.data.produtos) {
        produtosData = response.data.produtos;
      } else {
        produtosData = [];
      }

      if (produtosData.length === 0) {
        toast(
          "⚠️ Este fornecedor não possui produtos vinculados. Edite os produtos para vincular ao fornecedor.",
        );
      }

      setProdutos(produtosData);
    } catch (error) {
      console.error("Erro ao carregar produtos:", error);
      toast.error("Erro ao carregar produtos do fornecedor");
    }
  };

  const preencherPreco = (produtoId) => {
    const produto = produtos.find((p) => p.id === parseInt(produtoId));
    if (produto) {
      const unidadeCompra = normalizarUnidadeCompraPedido(itemForm.unidade_compra);
      const quantidadePorEmbalagemProduto = produto.itens_por_caixa
        ? String(produto.itens_por_caixa)
        : "";
      const quantidadePorEmbalagem =
        unidadeCompra === "UN"
          ? "1"
          : itemForm.quantidade_por_embalagem || quantidadePorEmbalagemProduto;

      setProdutoTexto(produto.nome);
      if (produto.preco_custo) {
        setItemForm({
          ...itemForm,
          produto_id: produtoId,
          quantidade_por_embalagem: quantidadePorEmbalagem,
          preco_unitario: produto.preco_custo.toFixed(2),
        });
      } else {
        setItemForm({
          ...itemForm,
          produto_id: produtoId,
          quantidade_por_embalagem: quantidadePorEmbalagem,
        });
      }
    }
  };

  const adicionarItem = () => {
    if (!itemForm.produto_id || !itemForm.quantidade_pedida || !itemForm.preco_unitario) {
      toast.error("Preencha todos os campos do item");
      return;
    }

    const produto = produtos.find((p) => p.id === parseInt(itemForm.produto_id));
    const quantidade = parseFloat(itemForm.quantidade_pedida);
    const preco = parseFloat(itemForm.preco_unitario);
    const produtoId = parseInt(itemForm.produto_id);
    const produtoCodigo = produto?.codigo || produto?.sku || "";
    const unidadeCompra = normalizarUnidadeCompraPedido(itemForm.unidade_compra);
    const quantidadePorEmbalagem = normalizarQuantidadePorEmbalagemPedido(
      unidadeCompra,
      itemForm.quantidade_por_embalagem,
    );
    const quantidadeTotalUnidades = calcularQuantidadeTotalUnidadesPedido({
      quantidade_pedida: quantidade,
      unidade_compra: unidadeCompra,
      quantidade_por_embalagem: quantidadePorEmbalagem,
    });

    // Verificar se produto já existe no pedido
    const itemExistenteIndex = formData.itens.findIndex(
      (item) =>
        item.produto_id === produtoId &&
        normalizarUnidadeCompraPedido(item.unidade_compra) === unidadeCompra &&
        normalizarQuantidadePorEmbalagemPedido(
          item.unidade_compra,
          item.quantidade_por_embalagem,
        ) === quantidadePorEmbalagem,
    );

    if (itemExistenteIndex !== -1) {
      // Produto já existe - perguntar ao usuário
      const itemExistente = formData.itens[itemExistenteIndex];
      const confirmar = window.confirm(
        `⚠️ O produto "${produto.nome}" já está no pedido!\n\n` +
          `Quantidade atual: ${itemExistente.quantidade_pedida}\n` +
          `Preço atual: R$ ${itemExistente.preco_unitario.toFixed(2)}\n\n` +
          `Nova quantidade: ${quantidade}\n` +
          `Novo preço: R$ ${preco.toFixed(2)}\n\n` +
          `Deseja SOMAR a quantidade ao item existente?\n\n` +
          `✅ OK = Somar quantidade (${itemExistente.quantidade_pedida} + ${quantidade} = ${itemExistente.quantidade_pedida + quantidade})\n` +
          `❌ CANCELAR = Não adicionar`,
      );

      if (confirmar) {
        // Somar quantidade ao item existente
        const novosItens = [...formData.itens];
        const quantidadeSomada = itemExistente.quantidade_pedida + quantidade;
        const quantidadeTotalSomada = calcularQuantidadeTotalUnidadesPedido({
          quantidade_pedida: quantidadeSomada,
          unidade_compra: unidadeCompra,
          quantidade_por_embalagem: quantidadePorEmbalagem,
        });
        novosItens[itemExistenteIndex] = {
          ...itemExistente,
          produto_codigo: itemExistente.produto_codigo || produtoCodigo,
          quantidade_pedida: quantidadeSomada,
          unidade_compra: unidadeCompra,
          quantidade_por_embalagem: quantidadePorEmbalagem,
          quantidade_total_unidades: quantidadeTotalSomada,
          preco_unitario: preco, // Atualiza com o novo preço
          total: quantidadeTotalSomada * preco,
        };

        setFormData({
          ...formData,
          itens: novosItens,
        });

        toast.success(
          `✅ Quantidade somada! Total: ${itemExistente.quantidade_pedida + quantidade}`,
        );
      } else {
        toast("Adição cancelada");
      }

      // Limpar form
      setProdutoTexto("");
      setMostrarSugestoesProduto(false);
      setItemForm(itemFormInicial);
      return;
    }

    // Produto novo - adicionar normalmente
    setFormData({
      ...formData,
      itens: [
        ...formData.itens,
        {
          produto_id: produtoId,
          produto_nome: produto.nome,
          produto_codigo: produtoCodigo,
          quantidade_pedida: quantidade,
          unidade_compra: unidadeCompra,
          quantidade_por_embalagem: quantidadePorEmbalagem,
          quantidade_total_unidades: quantidadeTotalUnidades,
          preco_unitario: preco,
          desconto_item: 0,
          total: quantidadeTotalUnidades * preco,
        },
      ],
    });

    // Limpar apenas os campos do item, mantendo o texto do produto limpo
    setProdutoTexto("");
    setMostrarSugestoesProduto(false);
    setItemForm(itemFormInicial);
  };

  const removerItem = (index) => {
    setFormData({
      ...formData,
      itens: formData.itens.filter((_, i) => i !== index),
    });
  };

  const atualizarItemPedido = (index, campo, valor) => {
    setFormData((prev) => {
      const itens = prev.itens.map((item, itemIndex) => {
        if (itemIndex !== index) {
          return item;
        }

        const proximoItem = {
          ...item,
          [campo]: numeroSeguro(valor),
        };
        const quantidade = numeroSeguro(proximoItem.quantidade_pedida);
        const unidadeCompra = normalizarUnidadeCompraPedido(proximoItem.unidade_compra);
        const quantidadePorEmbalagem = normalizarQuantidadePorEmbalagemPedido(
          unidadeCompra,
          proximoItem.quantidade_por_embalagem,
        );
        const quantidadeTotalUnidades = calcularQuantidadeTotalUnidadesPedido({
          quantidade_pedida: quantidade,
          unidade_compra: unidadeCompra,
          quantidade_por_embalagem: quantidadePorEmbalagem,
        });
        const preco = numeroSeguro(proximoItem.preco_unitario);
        const desconto = numeroSeguro(proximoItem.desconto_item);

        return {
          ...proximoItem,
          quantidade_pedida: quantidade,
          unidade_compra: unidadeCompra,
          quantidade_por_embalagem: quantidadePorEmbalagem,
          quantidade_total_unidades: quantidadeTotalUnidades,
          preco_unitario: preco,
          desconto_item: desconto,
          total: (preco - desconto) * quantidadeTotalUnidades,
        };
      });

      return {
        ...prev,
        itens,
      };
    });
  };

  const obterSkuItemPedido = (item) => {
    if (item?.produto_codigo) {
      return item.produto_codigo;
    }

    const produto = produtos.find((produtoAtual) => produtoAtual.id === Number(item?.produto_id));
    return produto?.codigo || produto?.sku || "";
  };

  const copiarSkuSugestao = async (sugestao) => {
    const sku = sugestao?.produto_sku || sugestao?.sku || sugestao?.codigo || "";

    if (!sku) {
      toast.error("SKU não disponível para este produto");
      return;
    }

    try {
      await navigator.clipboard.writeText(String(sku));
      toast.success(`SKU ${sku} copiado`);
    } catch (_error) {
      toast.error("Não foi possível copiar o SKU");
    }
  };

  const calcularTotal = () => {
    const subtotal = formData.itens.reduce((sum, item) => sum + item.total, 0);
    const frete = parseFloat(formData.valor_frete || 0);
    const desconto = parseFloat(formData.valor_desconto || 0);
    return subtotal + frete - desconto;
  };

  return {
    carregarProdutosFornecedor,
    selecionarProduto,
    adicionarItem,
    removerItem,
    atualizarItemPedido,
    obterSkuItemPedido,
    copiarSkuSugestao,
    calcularTotal,
  };
}
