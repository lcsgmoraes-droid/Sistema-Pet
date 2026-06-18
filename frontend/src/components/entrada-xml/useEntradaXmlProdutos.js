import { useEffect, useRef, useState } from "react";
import { aplicarMultiplicadorPackAoItem, obterCustoAquisicaoItem } from "./entradaXmlUtils";

const FORM_PRODUTO_INICIAL = {
  sku: "",
  nome: "",
  descricao: "",
  preco_custo: "",
  preco_venda: "",
  margem_lucro: "",
  estoque_minimo: 10,
  estoque_maximo: 100,
};

export default function useEntradaXmlProdutos({
  api,
  aplicarNotaSelecionada,
  carregarDados,
  multiplicadoresPack,
  notaSelecionada,
  setLoading,
  toast,
}) {
  const [mostrarModalCriarProduto, setMostrarModalCriarProduto] = useState(false);
  const [itemSelecionadoParaCriar, setItemSelecionadoParaCriar] = useState(null);
  const [sugestaoSku, setSugestaoSku] = useState(null);
  const [carregandoSugestao, setCarregandoSugestao] = useState(false);
  const [formProduto, setFormProduto] = useState(FORM_PRODUTO_INICIAL);
  const [filtroProduto, setFiltroProduto] = useState({});
  const [resultadosBuscaProduto, setResultadosBuscaProduto] = useState({});
  const [buscandoProduto, setBuscandoProduto] = useState({});
  const buscaProdutoTimersRef = useRef({});

  useEffect(() => {
    return () => {
      Object.values(buscaProdutoTimersRef.current).forEach((timerId) => {
        if (timerId) clearTimeout(timerId);
      });
      buscaProdutoTimersRef.current = {};
    };
  }, []);

  const buscarProdutosParaVinculo = async (itemId, termo) => {
    const textoBusca = (termo || "").trim();

    if (textoBusca.length < 2) {
      setResultadosBuscaProduto((prev) => ({ ...prev, [itemId]: [] }));
      setBuscandoProduto((prev) => ({ ...prev, [itemId]: false }));
      return;
    }

    setBuscandoProduto((prev) => ({ ...prev, [itemId]: true }));

    try {
      const palavras = textoBusca.toLowerCase().split(/\s+/).filter(Boolean);
      const palavrasServidor = [...palavras].sort((a, b) => b.length - a.length).slice(0, 4);

      const promises = [];
      palavrasServidor.forEach((palavra) => {
        const params = { busca: palavra, ativo: null, page: 1, page_size: 300 };
        promises.push(api.get("/produtos/", { params }));
        promises.push(api.get("/produtos/", { params: { ...params, tipo_produto: "VARIACAO" } }));
      });

      const respostas = await Promise.all(promises);
      const mapaPorId = new Map();
      respostas.forEach((res) => {
        (res.data?.items || []).forEach((p) => mapaPorId.set(p.id, p));
      });

      const encontrados = Array.from(mapaPorId.values()).filter((p) => {
        const campos = [
          p.nome?.toLowerCase() || "",
          p.codigo?.toLowerCase() || "",
          p.codigo_barras?.toLowerCase() || "",
          p.descricao?.toLowerCase() || "",
        ].join(" ");
        return palavras.every((palavra) => campos.includes(palavra));
      });

      encontrados.sort((a, b) => {
        if (a.ativo !== b.ativo) return a.ativo ? -1 : 1;
        const na = (a.nome || "").toLowerCase();
        const nb = (b.nome || "").toLowerCase();
        const scoreA = palavras.filter((w) => na.includes(w)).length;
        const scoreB = palavras.filter((w) => nb.includes(w)).length;
        if (scoreA !== scoreB) return scoreB - scoreA;
        return na.localeCompare(nb);
      });

      setResultadosBuscaProduto((prev) => ({ ...prev, [itemId]: encontrados.slice(0, 60) }));
    } catch (error) {
      console.error("Erro ao buscar produtos para vinculo:", error);
      setResultadosBuscaProduto((prev) => ({ ...prev, [itemId]: [] }));
    } finally {
      setBuscandoProduto((prev) => ({ ...prev, [itemId]: false }));
    }
  };

  const atualizarFiltroProduto = (itemId, valor) => {
    setFiltroProduto((prev) => ({ ...prev, [itemId]: valor }));

    if (buscaProdutoTimersRef.current[itemId]) {
      clearTimeout(buscaProdutoTimersRef.current[itemId]);
    }

    if ((valor || "").trim().length < 2) {
      setResultadosBuscaProduto((prev) => ({ ...prev, [itemId]: [] }));
      setBuscandoProduto((prev) => ({ ...prev, [itemId]: false }));
      return;
    }

    buscaProdutoTimersRef.current[itemId] = setTimeout(() => {
      buscarProdutosParaVinculo(itemId, valor);
    }, 250);
  };

  const vincularProduto = async (notaId, itemId, produtoId) => {
    try {
      await api.post(
        `/notas-entrada/${notaId}/itens/${itemId}/vincular?produto_id=${Number.parseInt(produtoId)}`,
      );

      toast.success("Produto vinculado com sucesso!");

      const response = await api.get(`/notas-entrada/${notaId}`);
      aplicarNotaSelecionada(response.data);
    } catch (error) {
      console.error("Erro ao vincular produto:", error);
      toast.error(error.response?.data?.detail || "Erro ao vincular produto");
    }
  };

  const desvincularProduto = async (notaId, itemId) => {
    try {
      await api.post(`/notas-entrada/${notaId}/itens/${itemId}/desvincular`);

      toast.success("Produto desvinculado!");

      const response = await api.get(`/notas-entrada/${notaId}`);
      aplicarNotaSelecionada(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao desvincular produto");
    }
  };

  const fecharModalCriarProduto = () => {
    setMostrarModalCriarProduto(false);
    setItemSelecionadoParaCriar(null);
    setSugestaoSku(null);
  };

  const abrirModalCriarProduto = async (item) => {
    const itemAjustado = aplicarMultiplicadorPackAoItem(item, multiplicadoresPack);

    setItemSelecionadoParaCriar(itemAjustado);
    setMostrarModalCriarProduto(true);
    setCarregandoSugestao(true);
    setFormProduto(FORM_PRODUTO_INICIAL);

    try {
      const response = await api.get(
        `/notas-entrada/${notaSelecionada.id}/itens/${itemAjustado.id}/sugerir-sku`,
      );

      setSugestaoSku(response.data);

      let skuParaUsar =
        response.data.sku_proposto || itemAjustado.codigo_produto || `PROD-${itemAjustado.id}`;

      if (
        response.data.ja_existe &&
        response.data.sugestoes &&
        response.data.sugestoes.length > 0
      ) {
        const sugestaoRecomendada =
          response.data.sugestoes.find((s) => s.padrao) || response.data.sugestoes[0];
        skuParaUsar = sugestaoRecomendada.sku;
      }

      const custoBase = obterCustoAquisicaoItem(itemAjustado);
      setFormProduto({
        sku: skuParaUsar,
        nome: itemAjustado.descricao || itemAjustado.descricao_produto || "Produto sem nome",
        descricao: itemAjustado.descricao || itemAjustado.descricao_produto || "",
        preco_custo: custoBase.toString(),
        preco_venda: (custoBase * 1.5).toFixed(2),
        margem_lucro: "50",
        estoque_minimo: 10,
        estoque_maximo: 100,
      });

      console.log("Formulario preenchido:", {
        sku: skuParaUsar,
        nome: itemAjustado.descricao,
        preco_custo: custoBase,
      });
    } catch (error) {
      toast.error("Erro ao buscar sugestões de SKU");
      console.error("Erro ao buscar SKU:", error);

      const custoBase = obterCustoAquisicaoItem(itemAjustado);
      setFormProduto({
        sku: itemAjustado.codigo_produto || `PROD-${itemAjustado.id}`,
        nome: itemAjustado.descricao || "Produto sem nome",
        descricao: itemAjustado.descricao || "",
        preco_custo: custoBase.toString(),
        preco_venda: (custoBase * 1.5).toFixed(2),
        margem_lucro: "50",
        estoque_minimo: 10,
        estoque_maximo: 100,
      });
    } finally {
      setCarregandoSugestao(false);
    }
  };

  const criarProdutoNovo = async () => {
    try {
      setLoading(true);
      const dadosProduto = {
        ...formProduto,
        preco_custo: Number.parseFloat(formProduto.preco_custo) || 0,
        preco_venda: Number.parseFloat(formProduto.preco_venda) || 0,
        margem_lucro: Number.parseFloat(formProduto.margem_lucro) || 0,
        estoque_minimo: Number.parseInt(formProduto.estoque_minimo) || 10,
        estoque_maximo: Number.parseInt(formProduto.estoque_maximo) || 100,
      };

      const response = await api.post(
        `/notas-entrada/${notaSelecionada.id}/itens/${itemSelecionadoParaCriar.id}/criar-produto`,
        dadosProduto,
      );

      toast.success(
        response.data.message || `Produto ${response.data.produto.codigo} criado e vinculado!`,
      );

      fecharModalCriarProduto();
      await carregarDados();

      const notaResponse = await api.get(`/notas-entrada/${notaSelecionada.id}`);
      aplicarNotaSelecionada(notaResponse.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao criar produto");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const criarTodosProdutosNaoVinculados = async () => {
    const itensNaoVinculados = notaSelecionada.itens.filter((item) => !item.produto_id);

    if (itensNaoVinculados.length === 0) {
      toast.success("Todos os produtos ja estão vinculados!");
      return;
    }

    const confirmacao = globalThis.confirm(
      `Criar ${itensNaoVinculados.length} produto(s) automaticamente?\n\n` +
        `Padrões aplicados:\n` +
        `• Estoque mínimo: 10\n` +
        `• Estoque máximo: 100\n` +
        `• Margem de lucro: 50%\n\n` +
        `Você poderá editar os produtos depois no cadastro.`,
    );

    if (!confirmacao) return;

    try {
      setLoading(true);
      let sucessos = 0;
      let erros = 0;

      const loadingToast = toast.loading(`Criando ${itensNaoVinculados.length} produtos...`);

      for (const item of itensNaoVinculados) {
        try {
          const skuResponse = await api.get(
            `/notas-entrada/${notaSelecionada.id}/itens/${item.id}/sugerir-sku`,
          );

          let skuParaUsar =
            skuResponse.data.sku_proposto || item.codigo_produto || `PROD-${item.id}`;

          if (skuResponse.data.ja_existe && skuResponse.data.sugestoes?.length > 0) {
            const sugestaoRecomendada =
              skuResponse.data.sugestoes.find((s) => s.padrao) || skuResponse.data.sugestoes[0];
            skuParaUsar = sugestaoRecomendada.sku;
          }

          const custoBase = obterCustoAquisicaoItem(item);
          const dadosProduto = {
            sku: skuParaUsar,
            nome: item.descricao || "Produto sem nome",
            descricao: item.descricao || "",
            preco_custo: custoBase,
            preco_venda: Number.parseFloat((custoBase * 1.5).toFixed(2)),
            margem_lucro: 50,
            estoque_minimo: 10,
            estoque_maximo: 100,
          };

          await api.post(
            `/notas-entrada/${notaSelecionada.id}/itens/${item.id}/criar-produto`,
            dadosProduto,
          );

          sucessos++;
        } catch (error) {
          console.error(`Erro ao criar produto do item ${item.id}:`, error);
          erros++;
        }
      }

      toast.dismiss(loadingToast);

      if (sucessos > 0) {
        toast.success(`${sucessos} produto(s) criado(s) com sucesso!`);
      }

      if (erros > 0) {
        toast.error(`${erros} erro(s) ao criar produtos`);
      }

      await carregarDados();

      const notaResponse = await api.get(`/notas-entrada/${notaSelecionada.id}`);
      aplicarNotaSelecionada(notaResponse.data);
    } catch (error) {
      toast.error("Erro ao criar produtos em lote");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const calcularMargemLucro = (custo, venda) => {
    if (custo === 0) return 0;
    return (((venda - custo) / custo) * 100).toFixed(2);
  };

  return {
    abrirModalCriarProduto,
    atualizarFiltroProduto,
    buscandoProduto,
    calcularMargemLucro,
    carregandoSugestao,
    criarProdutoNovo,
    criarTodosProdutosNaoVinculados,
    desvincularProduto,
    fecharModalCriarProduto,
    filtroProduto,
    formProduto,
    itemSelecionadoParaCriar,
    mostrarModalCriarProduto,
    resultadosBuscaProduto,
    setFiltroProduto,
    setFormProduto,
    setResultadosBuscaProduto,
    sugestaoSku,
    vincularProduto,
  };
}
