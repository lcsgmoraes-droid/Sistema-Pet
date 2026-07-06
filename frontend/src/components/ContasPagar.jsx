import { useMemo, useState, useEffect } from "react";
import api from "../api";
import { toast } from "react-hot-toast";
import { safeArray } from "../utils/safeArray";
import ContasPagarView from "./contas-pagar/ContasPagarView";
import useContasPagarSelection from "./contas-pagar/useContasPagarSelection";
import { formatMoneyCellValue } from "./ui/MoneyCell";
import StatusBadge from "./ui/StatusBadge";
import {
  calcularIntervaloPeriodoRapido,
  criarFiltrosPadraoContasPagar,
  extrairMensagemErroPagamento,
  formatarDataISO,
} from "./contas-pagar/contasPagarHelpers";

const ContasPagar = () => {
  const [contas, setContas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState(criarFiltrosPadraoContasPagar);

  const [fornecedores, setFornecedores] = useState([]);
  const [categoriasFinanceiras, setCategoriasFinanceiras] = useState([]);
  const [subcategoriasDre, setSubcategoriasDre] = useState([]);
  const [tiposDespesa, setTiposDespesa] = useState([]);
  const [contaSelecionada, setContaSelecionada] = useState(null);
  const [mostrarModalPagamento, setMostrarModalPagamento] = useState(false);
  const [mostrarModalPagamentoLote, setMostrarModalPagamentoLote] = useState(false);
  const [mostrarModalNovaConta, setMostrarModalNovaConta] = useState(false);
  const [contaEdicao, setContaEdicao] = useState(null);
  const [mostrarModalClassificacao, setMostrarModalClassificacao] = useState(false);
  const [modalExclusaoRecorrencia, setModalExclusaoRecorrencia] = useState({
    aberto: false,
    conta: null,
    itens: [],
    loading: false,
  });
  const [recorrenciasSelecionadasExclusao, setRecorrenciasSelecionadasExclusao] = useState([]);
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [contasBancarias, setContasBancarias] = useState([]);
  const [mostrarModalNovaForma, setMostrarModalNovaForma] = useState(false);
  const [novaFormaData, setNovaFormaData] = useState({
    nome: "",
    tipo: "dinheiro",
    conta_bancaria_destino_id: null,
  });
  const [dadosClassificacao, setDadosClassificacao] = useState({
    categoria_id: null,
    dre_subcategoria_id: null,
    tipo_despesa_id: null,
    canal: "loja_fisica",
  });

  const [dadosPagamento, setDadosPagamento] = useState({
    valor_pago: 0,
    data_pagamento: new Date().toISOString().split("T")[0],
    forma_pagamento_id: "",
    conta_bancaria_id: "",
    valor_juros: 0,
    valor_multa: 0,
    valor_desconto: 0,
    observacoes: "",
  });
  const [dadosPagamentoLote, setDadosPagamentoLote] = useState({
    data_pagamento: formatarDataISO(new Date()),
    forma_pagamento_id: "",
    conta_bancaria_id: "",
    observacoes: "",
  });

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarFormasPagamento = async () => {
    const response = await api.get("/financeiro/formas-pagamento?apenas_ativas=true");
    return safeArray(response.data).map((forma) => ({
      id: forma.id,
      nome: forma.nome,
      tipo: forma.tipo || forma.nome?.toLowerCase()?.replace(/\s+/g, "_") || "outro",
      icone: forma.icone || "💳",
      conta_bancaria_destino_id: forma.conta_bancaria_destino_id || null,
    }));
  };

  const montarParamsFiltros = (filtrosParaAplicar = filtros) => {
    const params = new URLSearchParams();
    params.append("_t", Date.now());
    if (filtrosParaAplicar.status !== "todos") params.append("status", filtrosParaAplicar.status);
    if (filtrosParaAplicar.fornecedor_id)
      params.append("fornecedor_id", filtrosParaAplicar.fornecedor_id);
    if (filtrosParaAplicar.data_inicio)
      params.append("data_inicio", filtrosParaAplicar.data_inicio);
    if (filtrosParaAplicar.data_fim) params.append("data_fim", filtrosParaAplicar.data_fim);
    if (filtrosParaAplicar.apenas_vencidas) params.append("apenas_vencidas", "true");
    if (filtrosParaAplicar.apenas_vencer) params.append("apenas_vencer", "true");
    if (filtrosParaAplicar.ocultar_taxas_cartao) params.append("ocultar_taxas_cartao", "true");
    if (filtrosParaAplicar.apenas_taxas_cartao) params.append("apenas_taxas_cartao", "true");
    if (filtrosParaAplicar.numero_nf) params.append("numero_nf", filtrosParaAplicar.numero_nf);
    if (filtrosParaAplicar.tipo_custo !== "todos")
      params.append("tipo_custo", filtrosParaAplicar.tipo_custo);
    if (filtrosParaAplicar.origem !== "todos") params.append("origem", filtrosParaAplicar.origem);
    if (filtrosParaAplicar.busca) params.append("busca", filtrosParaAplicar.busca);
    if (filtrosParaAplicar.fornecedor_busca)
      params.append("fornecedor_nome", filtrosParaAplicar.fornecedor_busca);
    if (filtrosParaAplicar.data_campo) params.append("data_campo", filtrosParaAplicar.data_campo);
    if (filtrosParaAplicar.tipo_despesa_id)
      params.append("tipo_despesa_id", filtrosParaAplicar.tipo_despesa_id);
    return params;
  };

  const carregarDados = async () => {
    try {
      const [
        contasRes,
        fornecedoresRes,
        formasRes,
        bancariasRes,
        categoriasRes,
        subcategoriasRes,
        tiposRes,
      ] = await Promise.allSettled([
        api.get(`/contas-pagar/?${montarParamsFiltros(filtros)}`),
        api.get(`/clientes/?tipo_cadastro=fornecedor`),
        carregarFormasPagamento(),
        api.get(`/contas-bancarias?apenas_ativas=true`),
        api.get("/categorias-financeiras"),
        api.get("/dre/subcategorias"),
        api.get("/cadastros/tipo-despesa/"),
      ]);

      if (contasRes.status === "fulfilled") {
        setContas(safeArray(contasRes.value.data));
      } else {
        throw contasRes.reason;
      }

      if (fornecedoresRes.status === "fulfilled") {
        setFornecedores(safeArray(fornecedoresRes.value.data));
      } else {
        throw fornecedoresRes.reason;
      }

      if (formasRes.status === "fulfilled") {
        setFormasPagamento(safeArray(formasRes.value));
      } else {
        setFormasPagamento([]);
        console.warn("Nao foi possivel carregar formas de pagamento. Usando lista vazia.");
      }

      if (bancariasRes.status === "fulfilled") {
        setContasBancarias(safeArray(bancariasRes.value.data));
      } else {
        throw bancariasRes.reason;
      }

      setCategoriasFinanceiras(
        categoriasRes?.status === "fulfilled" ? safeArray(categoriasRes.value.data) : [],
      );
      setSubcategoriasDre(
        subcategoriasRes?.status === "fulfilled" ? safeArray(subcategoriasRes.value.data) : [],
      );
      setTiposDespesa(tiposRes?.status === "fulfilled" ? safeArray(tiposRes.value.data) : []);
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      toast.error("Erro ao carregar contas a pagar");
    } finally {
      setLoading(false);
    }
  };

  const filtrosPadrao = criarFiltrosPadraoContasPagar();

  const aplicarFiltros = async (filtrosParaAplicar = filtros) => {
    try {
      setLoading(true);
      const response = await api.get(`/contas-pagar/?${montarParamsFiltros(filtrosParaAplicar)}`);

      setContas(safeArray(response.data));
    } catch (error) {
      console.error("Erro ao filtrar:", error);
      toast.error("Erro ao aplicar filtros");
      setContas([]);
    } finally {
      setLoading(false);
    }
  };

  const filtrarDespesasCaixa = () => {
    const filtrosCaixa = {
      ...filtrosPadrao,
      status: "pago",
      origem: "caixa_pdv",
      data_campo: filtros.data_campo || "pagamento",
      data_inicio: filtros.data_inicio,
      data_fim: filtros.data_fim,
      periodo_rapido: filtros.periodo_rapido || "",
      ocultar_taxas_cartao: false,
      apenas_taxas_cartao: false,
    };
    setFiltros(filtrosCaixa);
    aplicarFiltros(filtrosCaixa);
  };

  const filtrarTaxasCartao = () => {
    const filtrosTaxas = {
      ...filtrosPadrao,
      data_inicio: filtros.data_inicio,
      data_fim: filtros.data_fim,
      data_campo: filtros.data_campo || "vencimento",
      periodo_rapido: filtros.periodo_rapido || "",
      ocultar_taxas_cartao: false,
      apenas_taxas_cartao: true,
    };
    setFiltros(filtrosTaxas);
    aplicarFiltros(filtrosTaxas);
  };

  const alternarOcultarTaxasCartao = (ocultar) => {
    const novosFiltros = {
      ...filtros,
      ocultar_taxas_cartao: ocultar,
      apenas_taxas_cartao: false,
    };
    setFiltros(novosFiltros);
    aplicarFiltros(novosFiltros);
  };

  const aplicarPeriodoRapido = (periodo) => {
    const intervalo = calcularIntervaloPeriodoRapido(periodo);
    const novosFiltros = {
      ...filtros,
      ...intervalo,
      periodo_rapido: periodo,
      apenas_vencidas: false,
      apenas_vencer: false,
    };

    setFiltros(novosFiltros);
    aplicarFiltros(novosFiltros);
  };

  const limparFiltros = () => {
    setFiltros(filtrosPadrao);
    aplicarFiltros(filtrosPadrao);
  };

  const abrirModalPagamento = (conta) => {
    setContaSelecionada(conta);
    // Buscar conta padrão da forma de pagamento se houver
    const formaDefault = formasPagamento.find((f) => f.id === conta.forma_pagamento_id);
    setDadosPagamento({
      valor_pago: conta.valor_final - conta.valor_pago,
      data_pagamento: formatarDataISO(new Date()),
      forma_pagamento_id: conta.forma_pagamento_id || "",
      conta_bancaria_id: formaDefault?.conta_bancaria_destino_id || "",
      valor_juros: 0,
      valor_multa: 0,
      valor_desconto: 0,
      observacoes: "",
    });
    setMostrarModalPagamento(true);
  };

  const abrirModalEdicao = async (conta) => {
    try {
      const response = await api.get(`/contas-pagar/${conta.id}`);
      setContaEdicao({
        ...conta,
        ...response.data,
        fornecedor_id: response.data?.fornecedor?.id ?? conta.fornecedor_id ?? null,
        categoria_id:
          response.data?.categoria_id ?? response.data?.categoria?.id ?? conta.categoria_id ?? null,
        dre_subcategoria_id:
          response.data?.dre_subcategoria_id ?? conta.dre_subcategoria_id ?? null,
        tipo_despesa_id: response.data?.tipo_despesa_id ?? conta.tipo_despesa_id ?? null,
        canal: response.data?.canal ?? conta.canal ?? "loja_fisica",
        valor_original: response.data?.valores?.original ?? conta.valor_original,
        data_emissao: response.data?.datas?.emissao ?? conta.data_emissao,
        data_vencimento: response.data?.datas?.vencimento ?? conta.data_vencimento,
        documento: response.data?.documento ?? conta.documento ?? "",
        observacoes: response.data?.observacoes ?? conta.observacoes ?? "",
      });
      setMostrarModalNovaConta(true);
    } catch (error) {
      console.error("Erro ao abrir edicao:", error);
      toast.error(error.response?.data?.detail || "Erro ao carregar conta para edicao");
    }
  };

  const carregarRecorrenciaExclusao = async (conta) => {
    setModalExclusaoRecorrencia({
      aberto: true,
      conta,
      itens: [],
      loading: true,
    });
    setRecorrenciasSelecionadasExclusao([]);

    try {
      const response = await api.get(`/contas-pagar/${conta.id}/recorrencia`);
      const itens = safeArray(response.data?.itens);
      setModalExclusaoRecorrencia({
        aberto: true,
        conta,
        itens,
        loading: false,
      });
      setRecorrenciasSelecionadasExclusao(
        itens.filter((item) => item.pode_excluir).map((item) => item.id),
      );
    } catch (error) {
      console.error("Erro ao carregar recorrencia:", error);
      toast.error(error.response?.data?.detail || "Erro ao carregar lancamentos recorrentes");
      setModalExclusaoRecorrencia({
        aberto: false,
        conta: null,
        itens: [],
        loading: false,
      });
    }
  };

  const alternarRecorrenciaExclusao = (itemId) => {
    setRecorrenciasSelecionadasExclusao((atuais) =>
      atuais.includes(itemId) ? atuais.filter((id) => id !== itemId) : [...atuais, itemId],
    );
  };

  const confirmarExclusaoRecorrencia = async () => {
    if (recorrenciasSelecionadasExclusao.length === 0) {
      toast.error("Selecione pelo menos um lancamento para excluir");
      return;
    }

    try {
      await api.post("/contas-pagar/recorrencias/excluir", {
        ids: recorrenciasSelecionadasExclusao,
      });
      toast.success("Lancamentos recorrentes excluidos com sucesso");
      setModalExclusaoRecorrencia({
        aberto: false,
        conta: null,
        itens: [],
        loading: false,
      });
      setRecorrenciasSelecionadasExclusao([]);
      carregarDados();
    } catch (error) {
      console.error("Erro ao excluir recorrencia:", error);
      toast.error(error.response?.data?.detail || "Erro ao excluir lancamentos recorrentes");
    }
  };

  const {
    algumasVisiveisSelecionadas,
    alternarSelecaoConta,
    cancelarContasSelecionadas,
    contaTemPagamento,
    contasSelecionadas,
    contasSelecionadasObjetos,
    contasVisiveis,
    editarContaSelecionada,
    estornarContasSelecionadas,
    excluirContasSelecionadas,
    haContaCancelavelSelecionada,
    haContaExcluivelSelecionada,
    haContaPagavelSelecionada,
    haContaPagaSelecionada,
    limparSelecaoContas,
    selecionarTodasContasVisiveis,
    todasVisiveisSelecionadas,
    totalSelecionadas,
  } = useContasPagarSelection({
    contas,
    carregarDados,
    abrirModalEdicao,
  });

  const contasParaPagamentoLote = useMemo(
    () =>
      safeArray(contasSelecionadasObjetos).filter(
        (conta) =>
          !["pago", "cancelado"].includes(conta.status) &&
          Number(conta.valor_final || 0) > Number(conta.valor_pago || 0),
      ),
    [contasSelecionadasObjetos],
  );

  const saldoTotalPagamentoLote = useMemo(
    () =>
      contasParaPagamentoLote.reduce(
        (total, conta) => total + (Number(conta.valor_final || 0) - Number(conta.valor_pago || 0)),
        0,
      ),
    [contasParaPagamentoLote],
  );

  const abrirPagamentoEmLote = () => {
    if (contasParaPagamentoLote.length === 0) {
      toast.error("Selecione pelo menos uma conta com saldo aberto para pagar");
      return;
    }

    setDadosPagamentoLote({
      data_pagamento: formatarDataISO(new Date()),
      forma_pagamento_id: "",
      conta_bancaria_id: "",
      observacoes: "",
    });
    setMostrarModalPagamentoLote(true);
  };

  const handleFormaPagamentoLoteChange = (formaId) => {
    const forma = formasPagamento.find((f) => f.id === parseInt(formaId, 10));
    setDadosPagamentoLote({
      ...dadosPagamentoLote,
      forma_pagamento_id: parseInt(formaId, 10) || "",
      conta_bancaria_id:
        forma?.conta_bancaria_destino_id || dadosPagamentoLote.conta_bancaria_id || "",
    });
  };

  const confirmarSaldoNegativoPagamentoEmLote = () => {
    const contaBancaria = safeArray(contasBancarias).find(
      (conta) => Number(conta.id) === Number(dadosPagamentoLote.conta_bancaria_id),
    );

    if (!contaBancaria || saldoTotalPagamentoLote <= Number(contaBancaria.saldo_atual || 0)) {
      return true;
    }

    const saldoDepois = Number(contaBancaria.saldo_atual || 0) - saldoTotalPagamentoLote;
    const mensagem = [
      `Saldo insuficiente na conta bancaria "${contaBancaria.nome}".`,
      "",
      `Saldo atual: ${formatarMoeda(contaBancaria.saldo_atual || 0)}`,
      `Pagamento em lote: ${formatarMoeda(saldoTotalPagamentoLote)}`,
      `A conta ficara negativa em ${formatarMoeda(Math.abs(saldoDepois))}.`,
      "",
      "Deseja baixar mesmo assim?",
    ].join("\n");

    return window.confirm(mensagem);
  };

  const registrarPagamentoEmLote = async () => {
    if (contasParaPagamentoLote.length === 0) {
      toast.error("Selecione pelo menos uma conta com saldo aberto para pagar");
      return;
    }
    if (!confirmarSaldoNegativoPagamentoEmLote()) {
      return;
    }

    try {
      const response = await api.post("/contas-pagar/pagar-lote", {
        conta_ids: contasParaPagamentoLote.map((conta) => conta.id),
        data_pagamento: dadosPagamentoLote.data_pagamento || formatarDataISO(new Date()),
        forma_pagamento_id: dadosPagamentoLote.forma_pagamento_id || null,
        conta_bancaria_id: dadosPagamentoLote.conta_bancaria_id || null,
        observacoes: dadosPagamentoLote.observacoes,
      });

      toast.success(
        `${response.data?.pagamentos_registrados || contasParaPagamentoLote.length} pagamento(s) registrado(s)`,
      );
      setMostrarModalPagamentoLote(false);
      limparSelecaoContas();
      carregarDados();
    } catch (error) {
      console.error("Erro ao registrar pagamentos em lote:", error);
      toast.error(extrairMensagemErroPagamento(error));
    }
  };

  const excluirContaPagar = async (conta) => {
    if (conta.eh_recorrente || conta.conta_recorrencia_origem_id) {
      await carregarRecorrenciaExclusao(conta);
      return;
    }

    const confirmado = window.confirm(
      `Excluir a conta "${conta.descricao}"? Apenas contas sem pagamento registrado podem ser excluidas.`,
    );
    if (!confirmado) return;

    try {
      await api.delete(`/contas-pagar/${conta.id}`);
      toast.success("Conta excluida com sucesso");
      carregarDados();
    } catch (error) {
      console.error("Erro ao excluir conta:", error);
      toast.error(error.response?.data?.detail || "Erro ao excluir conta a pagar");
    }
  };

  const precisaClassificacao = (conta) => {
    return !conta.categoria_id || !conta.dre_subcategoria_id;
  };

  const abrirModalClassificacao = (conta) => {
    setContaSelecionada(conta);
    setDadosClassificacao({
      categoria_id: conta.categoria_id || null,
      dre_subcategoria_id: conta.dre_subcategoria_id || null,
      tipo_despesa_id: conta.tipo_despesa_id || null,
      canal: conta.canal || "loja_fisica",
    });
    setMostrarModalClassificacao(true);
  };

  const salvarClassificacao = async () => {
    if (!contaSelecionada) return;
    try {
      const response = await api.patch(
        `/contas-pagar/${contaSelecionada.id}/classificacao?aplicar_fornecedor=true`,
        dadosClassificacao,
      );
      setMostrarModalClassificacao(false);
      await carregarDados();

      const outrasAtualizadas = Number(response?.data?.fornecedor_atualizadas || 0);
      if (outrasAtualizadas > 0) {
        toast.success(
          `Classificação aplicada automaticamente em ${outrasAtualizadas + 1} lançamentos do fornecedor`,
        );
      } else {
        toast.success("Classificação salva com sucesso");
      }
    } catch (error) {
      console.error("Erro ao classificar conta:", error);
      toast.error(error.response?.data?.detail || "Erro ao classificar conta");
    }
  };

  const handleFormaChange = (formaId) => {
    const forma = formasPagamento.find((f) => f.id === parseInt(formaId));
    setDadosPagamento({
      ...dadosPagamento,
      forma_pagamento_id: parseInt(formaId) || "",
      conta_bancaria_id: forma?.conta_bancaria_destino_id || dadosPagamento.conta_bancaria_id || "",
    });
  };
  const salvarNovaForma = async () => {
    try {
      await api.post(`/financeiro/formas-pagamento`, {
        ...novaFormaData,
        taxa_percentual: 0,
        taxa_fixa: 0,
        prazo_dias: 0,
        ativo: true,
        permite_parcelamento: false,
        parcelas_maximas: 1,
      });
      toast.success("Forma de pagamento criada!");
      setMostrarModalNovaForma(false);
      setNovaFormaData({ nome: "", tipo: "dinheiro", conta_bancaria_destino_id: null });
      carregarDados(); // Recarregar formas
    } catch (error) {
      console.error("Erro:", error);
      toast.error("Erro ao criar forma de pagamento");
    }
  };

  const calcularValorFinalPagamento = (dados = dadosPagamento) =>
    (Number(dados.valor_pago) || 0) +
    (Number(dados.valor_juros) || 0) +
    (Number(dados.valor_multa) || 0) -
    (Number(dados.valor_desconto) || 0);

  const confirmarSaldoNegativoPagamento = () => {
    const contaBancaria = safeArray(contasBancarias).find(
      (conta) => Number(conta.id) === Number(dadosPagamento.conta_bancaria_id),
    );

    if (!contaBancaria) {
      return true;
    }

    const saldoAtual = Number(contaBancaria.saldo_atual || 0);
    const valorFinal = calcularValorFinalPagamento();

    if (valorFinal <= saldoAtual) {
      return true;
    }

    const saldoDepois = saldoAtual - valorFinal;
    const mensagem = [
      `Saldo insuficiente na conta bancaria "${contaBancaria.nome}".`,
      "",
      `Saldo atual: ${formatarMoeda(saldoAtual)}`,
      `Pagamento: ${formatarMoeda(valorFinal)}`,
      `A conta ficara negativo em ${formatarMoeda(Math.abs(saldoDepois))}.`,
      "",
      "Deseja baixar mesmo assim?",
    ].join("\n");

    return window.confirm(mensagem);
  };

  const registrarPagamento = async () => {
    if (!confirmarSaldoNegativoPagamento()) {
      return;
    }

    const payloadPagamento = {
      ...dadosPagamento,
      data_pagamento: dadosPagamento.data_pagamento || formatarDataISO(new Date()),
    };

    try {
      await api.post(`/contas-pagar/${contaSelecionada.id}/pagar`, payloadPagamento);

      toast.success("Pagamento registrado com sucesso!");
      setMostrarModalPagamento(false);
      carregarDados();
    } catch (error) {
      console.error("Erro ao registrar pagamento:", error);
      toast.error(extrairMensagemErroPagamento(error));
    }
  };

  const formatarData = (data) => {
    if (!data) return "-";
    // Evita problemas de timezone ao criar data diretamente dos componentes
    const partes = data.split("T")[0].split("-");
    const dataLocal = new Date(parseInt(partes[0]), parseInt(partes[1]) - 1, parseInt(partes[2]));
    return dataLocal.toLocaleDateString("pt-BR");
  };

  const formatarMoeda = (valor) => {
    return formatMoneyCellValue(valor);
  };

  const getStatusBadge = (conta) => {
    const hoje = new Date();
    const vencimento = new Date(conta.data_vencimento);
    if (conta.status === "cancelado") return <StatusBadge status="cancelado" />;
    if (conta.status === "pago") return <StatusBadge status="pago" />;
    if (vencimento < hoje) return <StatusBadge status="vencida" />;
    if (conta.status === "parcial") return <StatusBadge status="parcial" />;
    return <StatusBadge status="pendente" />;
  };

  const getOrigemLabel = (conta) => {
    const origem = conta.origem_lancamento || "manual";

    if (origem === "caixa_pdv") {
      return conta.caixa_referencia ? `Caixa/PDV (${conta.caixa_referencia})` : "Caixa/PDV";
    }

    if (origem === "nota_entrada") {
      return "Nota entrada";
    }

    return "Manual";
  };

  const getDescricaoPrincipal = (conta) => {
    const descricao = String(conta.descricao || "-").trim();
    const nfMatch = descricao.match(/\bNF-e?\s+\d+/i);
    if (nfMatch) return nfMatch[0].replace(/\s+/g, " ");
    return descricao;
  };

  const getContaTooltip = (conta) => {
    const linhas = [
      `Descricao: ${conta.descricao || "-"}`,
      conta.documento ? `Documento/NF: ${conta.documento}` : null,
      `Origem: ${getOrigemLabel(conta)}`,
      conta.tipo_despesa_nome ? `Tipo de despesa: ${conta.tipo_despesa_nome}` : null,
      conta.eh_parcelado ? `Parcela: ${conta.numero_parcela}/${conta.total_parcelas}` : null,
      conta.e_custo_fixo === true ? "Tipo de custo: Fixo" : null,
      conta.e_custo_fixo === false ? "Tipo de custo: Variavel" : null,
    ].filter(Boolean);

    return linhas.join("\n");
  };

  const tiposDespesaOrdenados = [...safeArray(tiposDespesa)].sort((a, b) =>
    String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR", { sensitivity: "base" }),
  );

  const fornecedorFiltroSelecionado = safeArray(fornecedores).find(
    (fornecedor) => String(fornecedor.id) === String(filtros.fornecedor_id),
  );

  const handleFiltrosSubmit = (event) => {
    event.preventDefault();
  };

  return (
    <ContasPagarView
      loading={loading}
      setContaEdicao={setContaEdicao}
      setMostrarModalNovaConta={setMostrarModalNovaConta}
      filtros={filtros}
      setFiltros={setFiltros}
      fornecedores={fornecedores}
      fornecedorFiltroSelecionado={fornecedorFiltroSelecionado}
      tiposDespesaOrdenados={tiposDespesaOrdenados}
      aplicarPeriodoRapido={aplicarPeriodoRapido}
      filtrarDespesasCaixa={filtrarDespesasCaixa}
      filtrarTaxasCartao={filtrarTaxasCartao}
      alternarOcultarTaxasCartao={alternarOcultarTaxasCartao}
      limparFiltros={limparFiltros}
      aplicarFiltros={aplicarFiltros}
      handleFiltrosSubmit={handleFiltrosSubmit}
      contasVisiveis={contasVisiveis}
      contasSelecionadas={contasSelecionadas}
      contasSelecionadasObjetos={contasParaPagamentoLote}
      todasVisiveisSelecionadas={todasVisiveisSelecionadas}
      algumasVisiveisSelecionadas={algumasVisiveisSelecionadas}
      selecionarTodasContasVisiveis={selecionarTodasContasVisiveis}
      alternarSelecaoConta={alternarSelecaoConta}
      getContaTooltip={getContaTooltip}
      getDescricaoPrincipal={getDescricaoPrincipal}
      getStatusBadge={getStatusBadge}
      formatarData={formatarData}
      abrirModalEdicao={abrirModalEdicao}
      abrirModalPagamento={abrirModalPagamento}
      precisaClassificacao={precisaClassificacao}
      abrirModalClassificacao={abrirModalClassificacao}
      excluirContaPagar={excluirContaPagar}
      contaTemPagamento={contaTemPagamento}
      totalSelecionadas={totalSelecionadas}
      abrirPagamentoEmLote={abrirPagamentoEmLote}
      editarContaSelecionada={editarContaSelecionada}
      estornarContasSelecionadas={estornarContasSelecionadas}
      cancelarContasSelecionadas={cancelarContasSelecionadas}
      excluirContasSelecionadas={excluirContasSelecionadas}
      limparSelecaoContas={limparSelecaoContas}
      haContaPagavelSelecionada={haContaPagavelSelecionada}
      haContaPagaSelecionada={haContaPagaSelecionada}
      haContaCancelavelSelecionada={haContaCancelavelSelecionada}
      haContaExcluivelSelecionada={haContaExcluivelSelecionada}
      mostrarModalPagamento={mostrarModalPagamento}
      contaSelecionada={contaSelecionada}
      setMostrarModalPagamento={setMostrarModalPagamento}
      formatarMoeda={formatarMoeda}
      dadosPagamento={dadosPagamento}
      setDadosPagamento={setDadosPagamento}
      mostrarModalPagamentoLote={mostrarModalPagamentoLote}
      setMostrarModalPagamentoLote={setMostrarModalPagamentoLote}
      dadosPagamentoLote={dadosPagamentoLote}
      setDadosPagamentoLote={setDadosPagamentoLote}
      handleFormaPagamentoLoteChange={handleFormaPagamentoLoteChange}
      registrarPagamentoEmLote={registrarPagamentoEmLote}
      saldoTotalPagamentoLote={saldoTotalPagamentoLote}
      handleFormaChange={handleFormaChange}
      formasPagamento={formasPagamento}
      setMostrarModalNovaForma={setMostrarModalNovaForma}
      contasBancarias={contasBancarias}
      registrarPagamento={registrarPagamento}
      mostrarModalNovaForma={mostrarModalNovaForma}
      novaFormaData={novaFormaData}
      setNovaFormaData={setNovaFormaData}
      salvarNovaForma={salvarNovaForma}
      mostrarModalClassificacao={mostrarModalClassificacao}
      setMostrarModalClassificacao={setMostrarModalClassificacao}
      dadosClassificacao={dadosClassificacao}
      setDadosClassificacao={setDadosClassificacao}
      categoriasFinanceiras={categoriasFinanceiras}
      subcategoriasDre={subcategoriasDre}
      tiposDespesaOrdenados={tiposDespesaOrdenados}
      salvarClassificacao={salvarClassificacao}
      modalExclusaoRecorrencia={modalExclusaoRecorrencia}
      setModalExclusaoRecorrencia={setModalExclusaoRecorrencia}
      recorrenciasSelecionadasExclusao={recorrenciasSelecionadasExclusao}
      setRecorrenciasSelecionadasExclusao={setRecorrenciasSelecionadasExclusao}
      alternarRecorrenciaExclusao={alternarRecorrenciaExclusao}
      confirmarExclusaoRecorrencia={confirmarExclusaoRecorrencia}
      mostrarModalNovaConta={mostrarModalNovaConta}
      contaEdicao={contaEdicao}
      carregarDados={carregarDados}
    />
  );
};

export default ContasPagar;
