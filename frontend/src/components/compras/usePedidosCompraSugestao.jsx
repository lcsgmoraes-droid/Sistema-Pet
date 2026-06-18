import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import api from "../../api";
import { useEscapeToClose } from "../../utils/modalEscape";
import { clonarItensPedido, consolidarItensPedido, textoContemTokens } from "./pedidoCompraUtils";

export default function usePedidosCompraSugestao({
  formData,
  setFormData,
  produtos,
  obterParametrosGrupoFornecedor,
}) {
  const [mostrarSugestao, setMostrarSugestao] = useState(false);
  const [sugestoes, setSugestoes] = useState([]);
  const [loadingSugestao, setLoadingSugestao] = useState(false);
  const [loadingPrepararSugestao, setLoadingPrepararSugestao] = useState(false);
  const [periodoSugestao, setPeriodoSugestao] = useState(90);
  const [diasCobertura, setDiasCobertura] = useState(30);
  const [apenasCriticos, setApenasCriticos] = useState(false);
  const [incluirAlerta, setIncluirAlerta] = useState(true);
  const [produtosSelecionados, setProdutosSelecionados] = useState([]);
  const [quantidadesEditadas, setQuantidadesEditadas] = useState({});
  const [filtroSugestao, setFiltroSugestao] = useState("");
  const [mostrarSoPreenchidos, setMostrarSoPreenchidos] = useState(false);
  const [marcasSelecionadas, setMarcasSelecionadas] = useState([]);
  const [mostrarFiltroMarcas, setMostrarFiltroMarcas] = useState(false);
  const [produtoEditandoQuantidade, setProdutoEditandoQuantidade] = useState(null);
  const [mostrarModalRascunhoSugestao, setMostrarModalRascunhoSugestao] = useState(false);
  const [contextoRascunhoSugestao, setContextoRascunhoSugestao] = useState(null);
  const [modoAplicacaoSugestao, setModoAplicacaoSugestao] = useState("merge");
  const [estrategiaMesclaItens, setEstrategiaMesclaItens] = useState("somar");
  const [apenasFornecedorPrincipal, setApenasFornecedorPrincipal] = useState(true);

  const cabecalhoTabelaSugestaoRef = useRef(null);
  const corpoTabelaSugestaoRef = useRef(null);
  const filtroMarcasRef = useRef(null);

  const limparEstadosSugestao = () => {
    setSugestoes([]);
    setProdutosSelecionados([]);
    setQuantidadesEditadas({});
    setFiltroSugestao("");
    setMostrarSoPreenchidos(false);
    setMarcasSelecionadas([]);
    setMostrarFiltroMarcas(false);
    setProdutoEditandoQuantidade(null);
    setModoAplicacaoSugestao("merge");
  };

  const buscarSugestoes = async (fornecedorIdOverride = null) => {
    const fornecedorId = fornecedorIdOverride || formData.fornecedor_id;

    if (!fornecedorId) {
      toast.error("Selecione um fornecedor primeiro");
      return;
    }

    setLoadingSugestao(true);
    try {
      const response = await api.get(`/pedidos-compra/sugestao/${fornecedorId}`, {
        params: {
          periodo_dias: periodoSugestao,
          dias_cobertura: diasCobertura,
          apenas_criticos: apenasCriticos,
          incluir_alerta: incluirAlerta,
          apenas_fornecedor_principal: apenasFornecedorPrincipal,
          marca_ids: marcasSelecionadas,
          ...obterParametrosGrupoFornecedor(fornecedorId),
        },
        timeout: 60000,
      });

      const novasSugestoes = response.data.sugestoes || [];
      setSugestoes(novasSugestoes);
      setProdutosSelecionados([]);
      setQuantidadesEditadas({});

      if (novasSugestoes.length === 0) {
        toast("Nenhuma sugestao encontrada com os filtros aplicados");
      } else {
        toast.success(`${novasSugestoes.length} produtos analisados`);
      }
    } catch (error) {
      console.error("Erro ao buscar sugestoes:", error);
      toast.error("Erro ao gerar sugestoes");
    } finally {
      setLoadingSugestao(false);
    }
  };

  const abrirModalSugestao = async (fornecedorId, modo = "merge") => {
    setModoAplicacaoSugestao(modo);
    setMostrarSugestao(true);
    await buscarSugestoes(fornecedorId);
  };

  const toggleSelecionarProduto = (produtoId) => {
    setProdutosSelecionados((prev) =>
      prev.includes(produtoId) ? prev.filter((id) => id !== produtoId) : [...prev, produtoId],
    );
  };

  const sanitizarQuantidadeInteira = (valor) => {
    const somenteDigitos = String(valor ?? "").replace(/\D+/g, "");
    return somenteDigitos ? parseInt(somenteDigitos, 10) : 0;
  };

  const atualizarQuantidadeSugerida = (produtoId, novaQuantidade) => {
    setQuantidadesEditadas((prev) => ({
      ...prev,
      [produtoId]: sanitizarQuantidadeInteira(novaQuantidade),
    }));
  };

  const obterQuantidadeFinal = (sugestao) =>
    quantidadesEditadas[sugestao.produto_id] !== undefined
      ? quantidadesEditadas[sugestao.produto_id]
      : sugestao.quantidade_sugerida;

  const obterQuantidadeInteira = (sugestao) =>
    Math.max(0, Math.ceil(obterQuantidadeFinal(sugestao)));

  const formatarQuantidadeCurta = (valor, casas = 2) => {
    const numero = Number(valor || 0);
    return numero.toLocaleString("pt-BR", {
      minimumFractionDigits: numero % 1 === 0 ? 0 : Math.min(casas, 1),
      maximumFractionDigits: casas,
    });
  };

  const obterVendaJanelaSugestao = (sugestao, dias) => {
    const janelas = sugestao?.vendas_janelas || {};
    return Number(janelas[String(dias)] ?? janelas[dias] ?? sugestao?.[`vendas_${dias}d`] ?? 0);
  };

  const montarTooltipGiroSugestao = (sugestao) => {
    const vendas = [7, 15, 30, 60, 90]
      .map(
        (dias) => `${dias}d: ${formatarQuantidadeCurta(obterVendaJanelaSugestao(sugestao, dias))}`,
      )
      .join(" | ");
    const granel = sugestao?.granel_consumo || {};
    const granelKg = Number(granel?.kg_periodo || 0);
    const granelPacotes = Number(granel?.pacotes_equivalentes_periodo || 0);
    const granelItens = Array.isArray(granel?.itens)
      ? granel.itens
          .filter((item) => Number(item?.kg || 0) > 0)
          .map(
            (item) =>
              `${item.produto_nome || "Granel"}: ${formatarQuantidadeCurta(item.kg)} kg (${formatarQuantidadeCurta(item.pacotes_equivalentes, 3)} pacote eq.)`,
          )
          .join(" | ")
      : "";
    const origens = Array.isArray(sugestao?.origens_venda)
      ? sugestao.origens_venda
          .filter((origem) => Number(origem?.quantidade || 0) > 0)
          .map((origem) => `${origem.canal}: ${formatarQuantidadeCurta(origem.quantidade)}`)
          .join(" | ")
      : "";
    const consumoObservado = Number(
      sugestao?.consumo_diario_observado ?? sugestao?.consumo_diario ?? 0,
    );
    const consumoAjustado = Number(
      sugestao?.consumo_diario_ajustado ?? sugestao?.consumo_diario ?? 0,
    );
    const coberturaAlvo = Number(sugestao?.dias_total_cobertura || 0);
    const reposicao = Number(sugestao?.dias_reposicao || 0);
    const leadIncluido = Boolean(sugestao?.lead_time_incluido_no_alvo);
    const linhas = [
      `Vendas por janela: ${vendas}`,
      `Consumo observado: ${formatarQuantidadeCurta(consumoObservado, 3)}/dia`,
      consumoAjustado > consumoObservado * 1.05
        ? `Consumo ajustado: ${formatarQuantidadeCurta(consumoAjustado, 3)}/dia`
        : "",
      coberturaAlvo
        ? leadIncluido
          ? `Cobertura alvo: ${formatarQuantidadeCurta(coberturaAlvo, 1)} dias (cobertura ${diasCobertura} + reposicao ${formatarQuantidadeCurta(reposicao, 1)})`
          : `Cobertura alvo: ${formatarQuantidadeCurta(coberturaAlvo, 1)} dias (estoque ja cobre a reposicao; alvo = cobertura ${diasCobertura})`
        : "",
      granelKg > 0
        ? `Consumo granel: ${formatarQuantidadeCurta(granelKg)} kg (${formatarQuantidadeCurta(granelPacotes, 3)} pacote(s) equivalentes)`
        : "",
      granelItens ? `Itens granel: ${granelItens}` : "",
      sugestao?.teve_ruptura
        ? `Ruptura no periodo: ${formatarQuantidadeCurta(sugestao.dias_sem_estoque || 0, 1)} dia(s) sem estoque`
        : "",
      sugestao?.ruptura_ajuste_motivo || "",
      sugestao?.estoque_derivado ? "Estoque derivado por KIT/variacao virtual" : "",
      origens ? `Origens consideradas: ${origens}` : "",
    ];

    return linhas.filter(Boolean).join("\n");
  };

  const consumoFoiAjustado = (sugestao) => {
    if (sugestao?.ruptura_ajuste_aplicado !== undefined) {
      return Boolean(sugestao.ruptura_ajuste_aplicado);
    }
    return (
      Number(sugestao?.consumo_diario_ajustado || 0) >
      Number(sugestao?.consumo_diario_observado || sugestao?.consumo_diario || 0) * 1.05
    );
  };

  const sugestoesFiltradas = useMemo(() => {
    return sugestoes.filter((s) => {
      const textoBusca = [
        s.produto_nome,
        s.produto_sku,
        s.produto_codigo_barras,
        s.marca_nome,
        s.fornecedor_nome,
      ]
        .filter(Boolean)
        .join(" ");
      const passaBusca = textoContemTokens(textoBusca, filtroSugestao);

      if (!passaBusca) {
        return false;
      }

      if (!mostrarSoPreenchidos) {
        return true;
      }

      if (produtoEditandoQuantidade === s.produto_id) {
        return true;
      }

      return obterQuantidadeInteira(s) > 0;
    });
  }, [
    sugestoes,
    filtroSugestao,
    mostrarSoPreenchidos,
    quantidadesEditadas,
    produtoEditandoQuantidade,
  ]);

  const marcasFornecedor = useMemo(() => {
    const mapa = new Map();
    const registrarMarca = (origem) => {
      const marcaId = Number(origem?.marca_id);
      if (!Number.isFinite(marcaId) || marcaId <= 0) {
        return;
      }

      const nomeMarca = String(
        origem?.marca_nome || origem?.marca?.nome || origem?.marca || "",
      ).trim();

      if (!nomeMarca) {
        return;
      }

      if (!mapa.has(marcaId)) {
        mapa.set(marcaId, { id: marcaId, nome: nomeMarca });
      }
    };

    produtos.forEach(registrarMarca);
    sugestoes.forEach(registrarMarca);

    return Array.from(mapa.values()).sort((a, b) => a.nome.localeCompare(b.nome));
  }, [produtos, sugestoes]);

  const selecionadosComQuantidade = useMemo(
    () =>
      sugestoes
        .filter((s) => produtosSelecionados.includes(s.produto_id))
        .filter((s) => obterQuantidadeInteira(s) > 0),
    [sugestoes, produtosSelecionados, quantidadesEditadas],
  );

  const resumoMarcasSelecionadas = useMemo(() => {
    if (marcasSelecionadas.length === 0 || marcasSelecionadas.length === marcasFornecedor.length) {
      return "Todas";
    }

    if (marcasSelecionadas.length === 1) {
      return (
        marcasFornecedor.find((marca) => marca.id === marcasSelecionadas[0])?.nome || "1 marca"
      );
    }

    return `${marcasSelecionadas.length} marcas`;
  }, [marcasFornecedor, marcasSelecionadas]);

  const fecharModalSugestao = () => {
    setMostrarSugestao(false);
    setProdutosSelecionados([]);
    setQuantidadesEditadas({});
    setFiltroSugestao("");
    setMostrarSoPreenchidos(false);
    setMarcasSelecionadas([]);
    setMostrarFiltroMarcas(false);
    setProdutoEditandoQuantidade(null);
    setModoAplicacaoSugestao("merge");
  };

  useEscapeToClose({
    isOpen: mostrarSugestao,
    onClose: () => {
      if (mostrarFiltroMarcas) {
        setMostrarFiltroMarcas(false);
        return;
      }

      fecharModalSugestao();
    },
  });

  useEffect(() => {
    if (!mostrarSugestao || !mostrarFiltroMarcas) {
      return undefined;
    }

    const handleClickFora = (event) => {
      if (!filtroMarcasRef.current?.contains(event.target)) {
        setMostrarFiltroMarcas(false);
      }
    };

    window.addEventListener("mousedown", handleClickFora);
    return () => window.removeEventListener("mousedown", handleClickFora);
  }, [mostrarSugestao, mostrarFiltroMarcas]);

  useEffect(() => {
    if (!mostrarSugestao) {
      return undefined;
    }

    const cabecalho = cabecalhoTabelaSugestaoRef.current;
    const corpo = corpoTabelaSugestaoRef.current;
    if (!cabecalho || !corpo) {
      return undefined;
    }

    const sincronizarScrollHorizontal = () => {
      if (cabecalho.scrollLeft !== corpo.scrollLeft) {
        cabecalho.scrollLeft = corpo.scrollLeft;
      }
    };

    sincronizarScrollHorizontal();
    corpo.addEventListener("scroll", sincronizarScrollHorizontal, { passive: true });
    window.addEventListener("resize", sincronizarScrollHorizontal);

    return () => {
      corpo.removeEventListener("scroll", sincronizarScrollHorizontal);
      window.removeEventListener("resize", sincronizarScrollHorizontal);
    };
  }, [mostrarSugestao, sugestoesFiltradas.length]);

  const selecionarTodosCriticos = () => {
    const criticos = sugestoes
      .filter((s) => s.prioridade === "CR\u00cdTICO" && obterQuantidadeInteira(s) > 0)
      .map((s) => s.produto_id);
    setProdutosSelecionados(criticos);
  };

  const selecionarPreenchidosVisiveis = () => {
    const preenchidos = sugestoesFiltradas
      .filter((s) => obterQuantidadeInteira(s) > 0)
      .map((s) => s.produto_id);
    setProdutosSelecionados(preenchidos);
  };

  const desmarcarVisiveis = () => {
    const idsVisiveis = new Set(sugestoesFiltradas.map((s) => s.produto_id));
    setProdutosSelecionados((prev) => prev.filter((id) => !idsVisiveis.has(id)));
  };

  const alternarMarcaSelecionada = (marcaId) => {
    setMarcasSelecionadas((marcasAtuais) => {
      if (marcasAtuais.length === 0) {
        return [marcaId];
      }

      const jaSelecionada = marcasAtuais.includes(marcaId);
      const proximasMarcas = jaSelecionada
        ? marcasAtuais.filter((id) => id !== marcaId)
        : [...marcasAtuais, marcaId].sort((a, b) => a - b);

      if (proximasMarcas.length === 0 || proximasMarcas.length === marcasFornecedor.length) {
        return [];
      }

      return proximasMarcas;
    });
  };

  const classeCabecalhoTabelaSugestao =
    "border-b border-slate-200 bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.04em] text-slate-600 whitespace-nowrap shadow-[inset_0_-1px_0_rgba(203,213,225,0.9)]";
  const classeTabelaSugestao = "w-full min-w-[1180px] table-fixed border-separate border-spacing-0";
  const renderColGroupSugestao = () => (
    <colgroup>
      <col style={{ width: "3%" }} />
      <col style={{ width: "8%" }} />
      <col style={{ width: "34%" }} />
      <col style={{ width: "7%" }} />
      <col style={{ width: "8%" }} />
      <col style={{ width: "8%" }} />
      <col style={{ width: "9%" }} />
      <col style={{ width: "8%" }} />
      <col style={{ width: "8%" }} />
      <col style={{ width: "7%" }} />
    </colgroup>
  );

  const adicionarSugestoesAoPedido = () => {
    if (produtosSelecionados.length === 0) {
      toast.error("Selecione pelo menos um produto");
      return;
    }

    const produtosParaAdicionar = sugestoes
      .filter((s) => produtosSelecionados.includes(s.produto_id))
      .map((sugestao) => ({
        sugestao,
        quantidade: obterQuantidadeInteira(sugestao),
      }))
      .filter((item) => item.quantidade > 0);

    if (produtosParaAdicionar.length === 0) {
      toast.error(
        "Os produtos selecionados estao com quantidade 0. Preencha pelo menos 1 unidade.",
      );
      return;
    }

    const novosItens = produtosParaAdicionar.map(({ sugestao, quantidade }) => ({
      produto_id: sugestao.produto_id,
      produto_nome: sugestao.produto_nome,
      produto_codigo: sugestao.produto_sku || "",
      quantidade_pedida: quantidade,
      preco_unitario: sugestao.preco_unitario,
      desconto_item: 0,
      total: quantidade * sugestao.preco_unitario,
    }));

    const itensAtualizados =
      modoAplicacaoSugestao === "replace"
        ? clonarItensPedido(novosItens)
        : consolidarItensPedido(formData.itens, novosItens, estrategiaMesclaItens);

    setFormData({
      ...formData,
      itens: itensAtualizados,
    });

    toast.success(
      modoAplicacaoSugestao === "replace"
        ? `${novosItens.length} produtos aplicados substituindo o rascunho atual`
        : `${novosItens.length} produtos consolidados no pedido`,
    );
    fecharModalSugestao();
  };

  return {
    mostrarSugestao,
    sugestoes,
    loadingSugestao,
    loadingPrepararSugestao,
    periodoSugestao,
    setPeriodoSugestao,
    diasCobertura,
    setDiasCobertura,
    apenasCriticos,
    setApenasCriticos,
    incluirAlerta,
    setIncluirAlerta,
    produtosSelecionados,
    setProdutosSelecionados,
    filtroSugestao,
    setFiltroSugestao,
    mostrarSoPreenchidos,
    setMostrarSoPreenchidos,
    marcasSelecionadas,
    setMarcasSelecionadas,
    mostrarFiltroMarcas,
    setMostrarFiltroMarcas,
    mostrarModalRascunhoSugestao,
    setMostrarModalRascunhoSugestao,
    contextoRascunhoSugestao,
    setContextoRascunhoSugestao,
    modoAplicacaoSugestao,
    setModoAplicacaoSugestao,
    estrategiaMesclaItens,
    setEstrategiaMesclaItens,
    apenasFornecedorPrincipal,
    setApenasFornecedorPrincipal,
    cabecalhoTabelaSugestaoRef,
    corpoTabelaSugestaoRef,
    filtroMarcasRef,
    limparEstadosSugestao,
    buscarSugestoes,
    abrirModalSugestao,
    toggleSelecionarProduto,
    atualizarQuantidadeSugerida,
    obterQuantidadeInteira,
    formatarQuantidadeCurta,
    obterVendaJanelaSugestao,
    montarTooltipGiroSugestao,
    consumoFoiAjustado,
    sugestoesFiltradas,
    marcasFornecedor,
    selecionadosComQuantidade,
    resumoMarcasSelecionadas,
    fecharModalSugestao,
    selecionarTodosCriticos,
    selecionarPreenchidosVisiveis,
    desmarcarVisiveis,
    alternarMarcaSelecionada,
    classeCabecalhoTabelaSugestao,
    classeTabelaSugestao,
    renderColGroupSugestao,
    adicionarSugestoesAoPedido,
    setLoadingPrepararSugestao,
    setProdutoEditandoQuantidade,
  };
}
