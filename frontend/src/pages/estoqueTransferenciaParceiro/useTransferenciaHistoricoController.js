import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import { buscarClientes } from "../../api/clientes";
import {
  COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  baixarArquivoBlob,
  criarFiltrosHistoricoTransferencia,
  criarFormBaixaTransferencia,
  criarHistoricoEntradasParceiroVazio,
  criarHistoricoTransferenciasVazio,
  distribuirCompensacaoAutomatica,
  fimDoMesBaseIso,
  hojeIso,
  inicioDoMesIso,
  montarCompensacoesBaixaPayload,
  montarCupomTransferencia,
  montarFiltrosHistoricoTransferenciaParams,
  montarParametrosDocumentoTransferencia,
  normalizarColunasDocumentoTransferencia,
  normalizarNumero,
} from "./transferenciaParceiroUtils";
import useTransferenciaBaixaLoteController from "./useTransferenciaBaixaLoteController";
export default function useTransferenciaHistoricoController({
  parceiroSelecionado,
  transferenciaEditando,
  limparLancamentoAtual,
  setAbaAtiva,
} = {}) {
  const [contaGerandoPdf, setContaGerandoPdf] = useState(null);
  const [gerandoPdfConsolidado, setGerandoPdfConsolidado] = useState(false);
  const [cupomTransferencia, setCupomTransferencia] = useState("");
  const [modalDocumentoTransferencia, setModalDocumentoTransferencia] = useState({
    aberto: false,
    tipo: null,
    registro: null,
  });
  const [colunasDocumentoTransferencia, setColunasDocumentoTransferencia] = useState(
    COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  );
  const [contaEnviandoEmail, setContaEnviandoEmail] = useState(null);
  const [contaRecebendo, setContaRecebendo] = useState(null);
  const [contaExcluindo, setContaExcluindo] = useState(null);
  const [selecionadosHistorico, setSelecionadosHistorico] = useState([]);
  const [historicoExpandidoIds, setHistoricoExpandidoIds] = useState([]);
  const [baixaAbertaId, setBaixaAbertaId] = useState(null);
  const [formBaixa, setFormBaixa] = useState(() => criarFormBaixaTransferencia());
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [loadingFormasPagamento, setLoadingFormasPagamento] = useState(false);
  const [contasPagarCompensacao, setContasPagarCompensacao] = useState([]);
  const [loadingContasPagarCompensacao, setLoadingContasPagarCompensacao] = useState(false);
  const [paginaHistorico, setPaginaHistorico] = useState(1);
  const [paginaEntradasParceiro, setPaginaEntradasParceiro] = useState(1);
  const [loadingHistorico, setLoadingHistorico] = useState(false);
  const [loadingEntradasParceiro, setLoadingEntradasParceiro] = useState(false);
  const [filtrosHistoricoForm, setFiltrosHistoricoForm] = useState(() =>
    criarFiltrosHistoricoTransferencia(),
  );
  const [filtrosHistoricoAplicados, setFiltrosHistoricoAplicados] = useState(() =>
    criarFiltrosHistoricoTransferencia(),
  );
  const [pessoaHistoricoSelecionada, setPessoaHistoricoSelecionada] = useState(null);
  const [sugestoesPessoasHistorico, setSugestoesPessoasHistorico] = useState([]);
  const [loadingPessoasHistorico, setLoadingPessoasHistorico] = useState(false);
  const [historico, setHistorico] = useState(() => criarHistoricoTransferenciasVazio());
  const [entradasParceiro, setEntradasParceiro] = useState(() =>
    criarHistoricoEntradasParceiroVazio(),
  );
  async function carregarFormasPagamento() {
    try {
      setLoadingFormasPagamento(true);
      const response = await api.get("/financeiro/formas-pagamento", {
        params: { apenas_ativas: true },
      });
      setFormasPagamento(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error("Erro ao carregar formas de pagamento:", error);
      setFormasPagamento([]);
    } finally {
      setLoadingFormasPagamento(false);
    }
  }

  async function carregarHistoricoTransferencias(filtros, pagina) {
    try {
      setLoadingHistorico(true);
      const params = {
        page: pagina,
        page_size: 20,
        ...montarFiltrosHistoricoTransferenciaParams(filtros),
      };

      const response = await api.get("/estoque/transferencia-parceiro/historico", { params });
      setHistorico(response.data);
    } catch (error) {
      console.error("Erro ao carregar historico de transferencias:", error);
      toast.error("Nao foi possivel carregar o historico de transferencias.");
      setHistorico(criarHistoricoTransferenciasVazio());
    } finally {
      setLoadingHistorico(false);
    }
  }

  async function carregarEntradasParceiro(filtros, pagina = 1) {
    try {
      setLoadingEntradasParceiro(true);
      const params = {
        page: pagina,
        page_size: 8,
        ...montarFiltrosHistoricoTransferenciaParams(filtros),
      };

      const response = await api.get("/estoque/transferencia-parceiro/entrada-parceiro/historico", {
        params,
      });
      setEntradasParceiro(response.data);
    } catch (error) {
      console.error("Erro ao carregar entradas de parceiro:", error);
      setEntradasParceiro(criarHistoricoEntradasParceiroVazio());
    } finally {
      setLoadingEntradasParceiro(false);
    }
  }

  useEffect(() => {
    void carregarFormasPagamento();
  }, []);

  useEffect(() => {
    void carregarHistoricoTransferencias(filtrosHistoricoAplicados, paginaHistorico);
  }, [filtrosHistoricoAplicados, paginaHistorico]);

  useEffect(() => {
    void carregarEntradasParceiro(filtrosHistoricoAplicados, paginaEntradasParceiro);
  }, [filtrosHistoricoAplicados, paginaEntradasParceiro]);

  useEffect(() => {
    const termo = filtrosHistoricoForm.busca.trim();
    if (filtrosHistoricoForm.parceiro_id || termo.length < 2) {
      setSugestoesPessoasHistorico([]);
      setLoadingPessoasHistorico(false);
      return undefined;
    }

    const timer = setTimeout(async () => {
      try {
        setLoadingPessoasHistorico(true);
        const termoDigitos = termo.replace(/\D/g, "");
        const termoBusca = termoDigitos.length >= 8 ? termoDigitos : termo;
        const clientes = await buscarClientes({
          search: termoBusca,
          limit: 10,
          incluir_inativos: true,
        });
        setSugestoesPessoasHistorico(clientes);
      } catch (error) {
        console.error("Erro ao buscar pessoas para o historico:", error);
        setSugestoesPessoasHistorico([]);
      } finally {
        setLoadingPessoasHistorico(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [filtrosHistoricoForm.busca, filtrosHistoricoForm.parceiro_id]);

  useEffect(() => {
    const limparCupom = () => setCupomTransferencia("");
    window.addEventListener("afterprint", limparCupom);
    return () => window.removeEventListener("afterprint", limparCupom);
  }, []);

  const totalCompensadoBaixa = useMemo(
    () =>
      Object.values(formBaixa.compensacoes || {}).reduce(
        (acumulado, valor) =>
          acumulado + (Number.isFinite(normalizarNumero(valor)) ? normalizarNumero(valor) : 0),
        0,
      ),
    [formBaixa.compensacoes],
  );

  const idsHistoricoPagina = useMemo(
    () => historico.items.map((item) => item.conta_receber_id),
    [historico.items],
  );

  const todosPaginaSelecionados = useMemo(
    () =>
      idsHistoricoPagina.length > 0 &&
      idsHistoricoPagina.every((id) => selecionadosHistorico.includes(id)),
    [idsHistoricoPagina, selecionadosHistorico],
  );

  const totalPaginasHistorico = historico.pages || 0;
  const loadingDocumentoTransferencia =
    modalDocumentoTransferencia.tipo === "pdf_consolidado"
      ? gerandoPdfConsolidado
      : modalDocumentoTransferencia.tipo === "email" && modalDocumentoTransferencia.registro
        ? contaEnviandoEmail === modalDocumentoTransferencia.registro.conta_receber_id
        : modalDocumentoTransferencia.tipo === "pdf" && modalDocumentoTransferencia.registro
          ? contaGerandoPdf === modalDocumentoTransferencia.registro.conta_receber_id
          : false;

  const carregarContasPagarCompensacao = async (contaReceberId) => {
    if (!contaReceberId) {
      setContasPagarCompensacao([]);
      return;
    }

    try {
      setLoadingContasPagarCompensacao(true);
      const response = await api.get(
        `/estoque/transferencia-parceiro/${contaReceberId}/contas-pagar-compensacao`,
      );
      const items = Array.isArray(response?.data?.items) ? response.data.items : [];
      setContasPagarCompensacao(items);
    } catch (error) {
      console.error("Erro ao carregar contas para compensacao:", error);
      setContasPagarCompensacao([]);
      toast.error("Nao foi possivel carregar as contas a pagar para compensacao.");
    } finally {
      setLoadingContasPagarCompensacao(false);
    }
  };

  const rotuloPessoaHistorico = (pessoa) =>
    pessoa?.nome || pessoa?.razao_social || pessoa?.nome_fantasia || `Pessoa #${pessoa?.id || ""}`;

  const baixaLote = useTransferenciaBaixaLoteController({
    historico,
    filtrosHistoricoAplicados,
    pessoaHistoricoSelecionada,
    parceiroSelecionado,
    contasPagarCompensacao,
    setContasPagarCompensacao,
    carregarContasPagarCompensacao,
    carregarHistoricoTransferencias,
    paginaHistorico,
    rotuloPessoa: rotuloPessoaHistorico,
  });

  const atualizarFiltroHistorico = (campo, valor) => {
    setFiltrosHistoricoForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const atualizarBuscaPessoaHistorico = (valor) => {
    setPessoaHistoricoSelecionada(null);
    setSugestoesPessoasHistorico([]);
    setFiltrosHistoricoForm((prev) => ({ ...prev, busca: valor, parceiro_id: "" }));
  };

  const selecionarPessoaHistorico = (pessoa) => {
    if (!pessoa?.id) return;
    setPessoaHistoricoSelecionada(pessoa);
    setSugestoesPessoasHistorico([]);
    setFiltrosHistoricoForm((prev) => ({
      ...prev,
      busca: rotuloPessoaHistorico(pessoa),
      parceiro_id: String(pessoa.id),
    }));
  };

  const aplicarPeriodoRapidoHistorico = (tipo) => {
    const hoje = new Date();
    let dataInicio = "";
    let dataFim = "";

    if (tipo === "mes_atual") {
      dataInicio = inicioDoMesIso(hoje);
      dataFim = fimDoMesBaseIso(hoje);
    } else if (tipo === "mes_anterior") {
      const anterior = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
      dataInicio = inicioDoMesIso(anterior);
      dataFim = fimDoMesBaseIso(anterior);
    }

    setPaginaHistorico(1);
    setPaginaEntradasParceiro(1);
    setSelecionadosHistorico([]);
    setFiltrosHistoricoForm((prev) => ({ ...prev, data_inicio: dataInicio, data_fim: dataFim }));
    setFiltrosHistoricoAplicados((prev) => ({
      ...prev,
      data_inicio: dataInicio,
      data_fim: dataFim,
    }));
  };

  const aplicarFiltrosHistorico = (event) => {
    event.preventDefault();
    setPaginaHistorico(1);
    setPaginaEntradasParceiro(1);
    setSelecionadosHistorico([]);
    setFiltrosHistoricoAplicados({ ...filtrosHistoricoForm });
  };

  const limparFiltrosHistorico = () => {
    setPaginaHistorico(1);
    setPaginaEntradasParceiro(1);
    setSelecionadosHistorico([]);
    setPessoaHistoricoSelecionada(null);
    setSugestoesPessoasHistorico([]);
    setFiltrosHistoricoForm(criarFiltrosHistoricoTransferencia());
    setFiltrosHistoricoAplicados(criarFiltrosHistoricoTransferencia());
  };

  const usarParceiroAtualNoHistorico = () => {
    if (!parceiroSelecionado?.id) return;
    const rotulo = rotuloPessoaHistorico(parceiroSelecionado);
    setPaginaHistorico(1);
    setPaginaEntradasParceiro(1);
    setSelecionadosHistorico([]);
    setPessoaHistoricoSelecionada(parceiroSelecionado);
    setFiltrosHistoricoForm((prev) => ({
      ...prev,
      busca: rotulo,
      parceiro_id: String(parceiroSelecionado.id),
    }));
    setFiltrosHistoricoAplicados((prev) => ({
      ...prev,
      busca: rotulo,
      parceiro_id: String(parceiroSelecionado.id),
    }));
  };

  const alternarSelecaoHistorico = (contaReceberId) => {
    setSelecionadosHistorico((prev) =>
      prev.includes(contaReceberId)
        ? prev.filter((id) => id !== contaReceberId)
        : [...prev, contaReceberId],
    );
  };

  const alternarSelecaoPaginaHistorico = () => {
    setSelecionadosHistorico((prev) => {
      if (todosPaginaSelecionados) {
        return prev.filter((id) => !idsHistoricoPagina.includes(id));
      }
      const proximo = new Set(prev);
      idsHistoricoPagina.forEach((id) => proximo.add(id));
      return Array.from(proximo);
    });
  };

  const alternarExpansaoHistorico = (contaReceberId) => {
    setHistoricoExpandidoIds((prev) =>
      prev.includes(contaReceberId)
        ? prev.filter((id) => id !== contaReceberId)
        : [...prev, contaReceberId],
    );
  };

  const abrirModalDocumentoTransferencia = (registro, tipo) => {
    setModalDocumentoTransferencia({ aberto: true, tipo, registro: registro || null });
  };

  const fecharModalDocumentoTransferencia = () => {
    setModalDocumentoTransferencia({ aberto: false, tipo: null, registro: null });
  };

  const gerarPdfTransferencia = async (
    registro,
    colunasDocumento = COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  ) => {
    try {
      setContaGerandoPdf(registro.conta_receber_id);
      const response = await api.get(
        `/estoque/transferencia-parceiro/${registro.conta_receber_id}/pdf`,
        {
          params: montarParametrosDocumentoTransferencia(colunasDocumento),
          responseType: "blob",
        },
      );
      baixarArquivoBlob(
        response.data,
        `transferencia_${registro.documento || registro.conta_receber_id}.pdf`,
      );
      return true;
    } catch (error) {
      console.error("Erro ao gerar PDF da transferencia:", error);
      toast.error(
        error?.response?.data?.detail || "Nao foi possivel gerar o PDF da transferencia.",
      );
      return false;
    } finally {
      setContaGerandoPdf(null);
    }
  };

  const imprimirCupomTransferencia = (
    registro,
    colunasDocumento = COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  ) => {
    setCupomTransferencia(montarCupomTransferencia(registro, colunasDocumento));
    window.setTimeout(() => globalThis.print(), 0);
  };

  const gerarPdfConsolidadoHistorico = async (
    colunasDocumento = COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  ) => {
    if ((historico.totais.total_registros || 0) <= 0) {
      toast.error("Nao ha transferencias no filtro atual para consolidar.");
      return false;
    }

    const filtrosConsolidados =
      montarFiltrosHistoricoTransferenciaParams(filtrosHistoricoAplicados);
    if (filtrosConsolidados.parceiro_id) {
      filtrosConsolidados.parceiro_id = Number(filtrosConsolidados.parceiro_id);
    }

    const payload = {
      conta_receber_ids: selecionadosHistorico,
      ...filtrosConsolidados,
      ...montarParametrosDocumentoTransferencia(colunasDocumento),
    };

    try {
      setGerandoPdfConsolidado(true);
      const response = await api.post("/estoque/transferencia-parceiro/pdf-consolidado", payload, {
        responseType: "blob",
      });
      baixarArquivoBlob(response.data, "transferencias_consolidadas.pdf");
      return true;
    } catch (error) {
      console.error("Erro ao gerar PDF consolidado das transferencias:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Nao foi possivel gerar o PDF consolidado das transferencias.",
      );
      return false;
    } finally {
      setGerandoPdfConsolidado(false);
    }
  };

  const enviarEmailTransferencia = async (
    registro,
    colunasDocumento = COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  ) => {
    if (!registro?.parceiro_email) {
      toast.error("Essa pessoa nao possui e-mail cadastrado.");
      return false;
    }

    try {
      setContaEnviandoEmail(registro.conta_receber_id);
      await api.post(`/estoque/transferencia-parceiro/${registro.conta_receber_id}/enviar-email`, {
        email: registro.parceiro_email,
        ...montarParametrosDocumentoTransferencia(colunasDocumento),
      });
      toast.success(`E-mail enviado para ${registro.parceiro_email}.`);
      return true;
    } catch (error) {
      console.error("Erro ao enviar e-mail da transferencia:", error);
      toast.error(
        error?.response?.data?.detail || "Nao foi possivel enviar o e-mail da transferencia.",
      );
      return false;
    } finally {
      setContaEnviandoEmail(null);
    }
  };

  const confirmarDocumentoTransferencia = async () => {
    const colunas = normalizarColunasDocumentoTransferencia(colunasDocumentoTransferencia);
    if (colunas.length === 0) {
      toast.error("Selecione ao menos uma informacao para o documento.");
      return;
    }

    const { tipo, registro } = modalDocumentoTransferencia;
    if (tipo === "cupom" && registro) {
      fecharModalDocumentoTransferencia();
      imprimirCupomTransferencia(registro, colunas);
      return;
    }
    if (tipo === "pdf" && registro) {
      const gerado = await gerarPdfTransferencia(registro, colunas);
      if (gerado) fecharModalDocumentoTransferencia();
      return;
    }
    if (tipo === "email" && registro) {
      const enviado = await enviarEmailTransferencia(registro, colunas);
      if (enviado) fecharModalDocumentoTransferencia();
      return;
    }
    if (tipo === "pdf_consolidado") {
      const gerado = await gerarPdfConsolidadoHistorico(colunas);
      if (gerado) fecharModalDocumentoTransferencia();
    }
  };

  const abrirBaixaTransferencia = async (registro) => {
    setBaixaAbertaId(registro.conta_receber_id);
    setHistoricoExpandidoIds((prev) =>
      prev.includes(registro.conta_receber_id) ? prev : [...prev, registro.conta_receber_id],
    );
    setFormBaixa(
      criarFormBaixaTransferencia({
        valor_recebido: Number(registro.saldo_aberto || 0).toFixed(2),
      }),
    );
    await carregarContasPagarCompensacao(registro.conta_receber_id);
  };

  const fecharBaixaTransferencia = () => {
    setBaixaAbertaId(null);
    setContasPagarCompensacao([]);
    setFormBaixa(criarFormBaixaTransferencia());
  };

  const registrarBaixaTransferencia = async (registro) => {
    const valorRecebido = normalizarNumero(formBaixa.valor_recebido);
    if (!Number.isFinite(valorRecebido) || valorRecebido <= 0) {
      toast.error("Informe um valor recebido maior que zero.");
      return;
    }

    const compensacoesPayload = montarCompensacoesBaixaPayload(formBaixa.compensacoes);
    const totalCompensado = compensacoesPayload.reduce(
      (acumulado, item) => acumulado + Number(item.valor_compensado || 0),
      0,
    );
    if (
      formBaixa.modo_baixa === "acerto" &&
      compensacoesPayload.length > 0 &&
      Math.abs(totalCompensado - valorRecebido) > 0.01
    ) {
      toast.error(
        "No acerto com contas selecionadas, o total compensado precisa bater com o valor da baixa.",
      );
      return;
    }

    try {
      setContaRecebendo(registro.conta_receber_id);
      await api.post(`/estoque/transferencia-parceiro/${registro.conta_receber_id}/receber`, {
        valor_recebido: valorRecebido,
        data_recebimento: formBaixa.data_recebimento || hojeIso(),
        modo_baixa: formBaixa.modo_baixa || "recebimento",
        forma_pagamento_id:
          formBaixa.modo_baixa === "recebimento" && formBaixa.forma_pagamento_id
            ? Number(formBaixa.forma_pagamento_id)
            : undefined,
        compensacoes: formBaixa.modo_baixa === "acerto" ? compensacoesPayload : undefined,
        observacao: formBaixa.observacao.trim() || undefined,
      });
      toast.success("Baixa registrada com sucesso.");
      fecharBaixaTransferencia();
      void Promise.all([
        carregarHistoricoTransferencias(filtrosHistoricoAplicados, paginaHistorico),
        carregarEntradasParceiro(filtrosHistoricoAplicados, paginaEntradasParceiro),
      ]);
      setAbaAtiva?.("historico");
    } catch (error) {
      console.error("Erro ao registrar baixa da transferencia:", error);
      toast.error(
        error?.response?.data?.detail || "Nao foi possivel registrar a baixa da transferencia.",
      );
    } finally {
      setContaRecebendo(null);
    }
  };

  const excluirTransferencia = async (registro) => {
    const confirmar = window.confirm(
      `Excluir a transferencia ${registro.documento || registro.conta_receber_id}? O estoque sera estornado.`,
    );
    if (!confirmar) return;

    try {
      setContaExcluindo(registro.conta_receber_id);
      await api.delete(`/estoque/transferencia-parceiro/${registro.conta_receber_id}`);
      toast.success("Transferencia excluida com sucesso.");
      setSelecionadosHistorico((prev) => prev.filter((id) => id !== registro.conta_receber_id));
      if (baixaAbertaId === registro.conta_receber_id) fecharBaixaTransferencia();
      if (transferenciaEditando?.conta_receber_id === registro.conta_receber_id) {
        limparLancamentoAtual?.();
      }
      void Promise.all([
        carregarHistoricoTransferencias(filtrosHistoricoAplicados, paginaHistorico),
        carregarEntradasParceiro(filtrosHistoricoAplicados, paginaEntradasParceiro),
      ]);
    } catch (error) {
      console.error("Erro ao excluir transferencia:", error);
      toast.error(error?.response?.data?.detail || "Nao foi possivel excluir a transferencia.");
    } finally {
      setContaExcluindo(null);
    }
  };

  const recarregarPrimeiraPagina = async () => {
    setPaginaHistorico(1);
    setPaginaEntradasParceiro(1);
    setSelecionadosHistorico([]);
    await Promise.all([
      carregarHistoricoTransferencias(filtrosHistoricoAplicados, 1),
      carregarEntradasParceiro(filtrosHistoricoAplicados, 1),
    ]);
  };

  const recarregarPaginaAtual = () =>
    Promise.all([
      carregarHistoricoTransferencias(filtrosHistoricoAplicados, paginaHistorico),
      carregarEntradasParceiro(filtrosHistoricoAplicados, paginaEntradasParceiro),
    ]);

  return {
    contaGerandoPdf,
    gerandoPdfConsolidado,
    cupomTransferencia,
    modalDocumentoTransferencia,
    colunasDocumentoTransferencia,
    setColunasDocumentoTransferencia: (colunas) =>
      setColunasDocumentoTransferencia(normalizarColunasDocumentoTransferencia(colunas)),
    contaEnviandoEmail,
    contaRecebendo,
    salvandoBaixaLote: baixaLote.salvandoBaixaLote,
    loadingPreviewBaixaLote: baixaLote.loadingPreviewBaixaLote,
    contaExcluindo,
    baixaLoteAberta: baixaLote.baixaLoteAberta,
    selecionadosHistorico,
    historicoExpandidoIds,
    baixaAbertaId,
    formBaixa,
    setFormBaixa,
    formBaixaLote: baixaLote.formBaixaLote,
    setFormBaixaLote: baixaLote.setFormBaixaLote,
    previewBaixaLote: baixaLote.previewBaixaLote,
    aplicacoesBaixaLote: baixaLote.aplicacoesBaixaLote,
    totalAplicadoBaixaLote: baixaLote.totalAplicadoBaixaLote,
    totalCompensadoBaixaLote: baixaLote.totalCompensadoBaixaLote,
    diferencaAplicacaoBaixaLote: baixaLote.diferencaAplicacaoBaixaLote,
    formasPagamento,
    loadingFormasPagamento,
    contasPagarCompensacao,
    loadingContasPagarCompensacao,
    paginaHistorico,
    setPaginaHistorico,
    paginaEntradasParceiro,
    setPaginaEntradasParceiro,
    loadingHistorico,
    loadingEntradasParceiro,
    filtrosHistoricoForm,
    filtrosHistoricoAplicados,
    pessoaHistoricoSelecionada,
    pessoaBaixaLoteNome: baixaLote.pessoaBaixaLoteNome,
    sugestoesPessoasHistorico,
    loadingPessoasHistorico,
    historico,
    entradasParceiro,
    totalCompensadoBaixa,
    todosPaginaSelecionados,
    totalPaginasHistorico,
    loadingDocumentoTransferencia,
    atualizarFiltroHistorico,
    atualizarBuscaPessoaHistorico,
    selecionarPessoaHistorico,
    aplicarPeriodoRapidoHistorico,
    aplicarFiltrosHistorico,
    limparFiltrosHistorico,
    usarParceiroAtualNoHistorico,
    alternarSelecaoHistorico,
    alternarSelecaoPaginaHistorico,
    limparSelecaoHistorico: () => setSelecionadosHistorico([]),
    alternarExpansaoHistorico,
    abrirModalDocumentoTransferencia,
    fecharModalDocumentoTransferencia,
    confirmarDocumentoTransferencia,
    abrirBaixaTransferencia,
    fecharBaixaTransferencia,
    registrarBaixaTransferencia,
    abrirBaixaLoteTransferencia: baixaLote.abrirBaixaLoteTransferencia,
    fecharBaixaLoteTransferencia: baixaLote.fecharBaixaLoteTransferencia,
    carregarPreviewBaixaLoteTransferencia: baixaLote.carregarPreviewBaixaLoteTransferencia,
    registrarBaixaLoteTransferencia: baixaLote.registrarBaixaLoteTransferencia,
    atualizarValorAplicacaoBaixaLote: baixaLote.atualizarValorAplicacaoBaixaLote,
    alternarAplicacaoBaixaLote: baixaLote.alternarAplicacaoBaixaLote,
    atualizarValorCompensacaoBaixaLote: baixaLote.atualizarValorCompensacaoBaixaLote,
    atualizarValorCompensacao: (contaPagarId, valor) =>
      setFormBaixa((prev) => ({
        ...prev,
        compensacoes: { ...(prev.compensacoes || {}), [contaPagarId]: valor },
      })),
    preencherCompensacaoAutomatica: () => {
      const valorBase = normalizarNumero(formBaixa.valor_recebido);
      if (!Number.isFinite(valorBase) || valorBase <= 0) {
        toast.error("Informe primeiro o valor da baixa para preencher a compensacao.");
        return;
      }
      setFormBaixa((prev) => ({
        ...prev,
        compensacoes: distribuirCompensacaoAutomatica(valorBase, contasPagarCompensacao),
      }));
    },
    limparCompensacoesBaixa: () => setFormBaixa((prev) => ({ ...prev, compensacoes: {} })),
    preencherCompensacaoAutomaticaBaixaLote: baixaLote.preencherCompensacaoAutomaticaBaixaLote,
    limparCompensacoesBaixaLote: baixaLote.limparCompensacoesBaixaLote,
    excluirTransferencia,
    recarregarPrimeiraPagina,
    recarregarPaginaAtual,
  };
}
