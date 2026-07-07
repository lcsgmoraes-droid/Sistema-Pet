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
  calcularValorFinalPagamentoContasPagar,
  criarFiltrosPadraoContasPagar,
  criarFiltrosDespesasCaixaContasPagar,
  criarFiltrosTaxasCartaoContasPagar,
  encontrarFornecedorFiltroContasPagar,
  extrairMensagemErroPagamento,
  formatarDataContasPagar,
  formatarDataISO,
  getContaTooltipContasPagar,
  getDescricaoPrincipalContasPagar,
  montarParamsFiltrosContasPagar,
  ordenarTiposDespesaContasPagar,
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
        api.get(`/contas-pagar/?${montarParamsFiltrosContasPagar(filtros)}`),
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
      const response = await api.get(
        `/contas-pagar/?${montarParamsFiltrosContasPagar(filtrosParaAplicar)}`,
      );

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
    const filtrosCaixa = criarFiltrosDespesasCaixaContasPagar(filtrosPadrao, filtros);
    setFiltros(filtrosCaixa);
    aplicarFiltros(filtrosCaixa);
  };

  const filtrarTaxasCartao = () => {
    const filtrosTaxas = criarFiltrosTaxasCartaoContasPagar(filtrosPadrao, filtros);
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
    calcularValorFinalPagamentoContasPagar(dados);

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

  const tiposDespesaOrdenados = ordenarTiposDespesaContasPagar(tiposDespesa, safeArray);

  const fornecedorFiltroSelecionado = encontrarFornecedorFiltroContasPagar(
    fornecedores,
    filtros.fornecedor_id,
    safeArray,
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
      getContaTooltip={getContaTooltipContasPagar}
      getDescricaoPrincipal={getDescricaoPrincipalContasPagar}
      getStatusBadge={getStatusBadge}
      formatarData={formatarDataContasPagar}
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
