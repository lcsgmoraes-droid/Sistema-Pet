import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { buscarClientes } from "../api/clientes";
import { getProdutos } from "../api/produtos";
import {
  COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  baixarArquivoBlob,
  criarFiltrosHistoricoTransferencia,
  criarFormBaixaTransferencia,
  criarFormTransferencia,
  criarHistoricoTransferenciasVazio,
  criarItemTransferencia,
  criarItensEdicaoTransferencia,
  extrairListaProdutos,
  extrairObservacaoManualTransferencia,
  fimDoMesBaseIso,
  distribuirCompensacaoAutomatica,
  hojeIso,
  incrementarItemTransferencia,
  inicioDoMesIso,
  montarCompensacoesBaixaPayload,
  montarCupomTransferencia,
  montarFiltrosHistoricoTransferenciaParams,
  montarParametrosDocumentoTransferencia,
  montarPayloadTransferencia,
  normalizarColunasDocumentoTransferencia,
  normalizarNumero,
  produtoConfereCodigo,
} from "./estoqueTransferenciaParceiro/transferenciaParceiroUtils";
import ModalDocumentoTransferenciaParceiro from "./estoqueTransferenciaParceiro/ModalDocumentoTransferenciaParceiro";
import CupomTransferenciaPrintArea from "./estoqueTransferenciaParceiro/CupomTransferenciaPrintArea";
import TransferenciaParceiroHeader from "./estoqueTransferenciaParceiro/TransferenciaParceiroHeader";
import LancamentoTransferenciaParceiro from "./estoqueTransferenciaParceiro/LancamentoTransferenciaParceiro";
import HistoricoTransferenciaFilters from "./estoqueTransferenciaParceiro/HistoricoTransferenciaFilters";
import HistoricoTransferenciaResults from "./estoqueTransferenciaParceiro/HistoricoTransferenciaResults";

export default function EstoqueTransferenciaParceiro() {
  const parceiroRef = useRef(null);
  const produtoRef = useRef(null);
  const produtoInputRef = useRef(null);
  const itensRef = useRef(null);

  const [form, setForm] = useState(() => criarFormTransferencia());
  const [parceiroSelecionado, setParceiroSelecionado] = useState(null);
  const [buscaParceiro, setBuscaParceiro] = useState("");
  const [sugestoesParceiros, setSugestoesParceiros] = useState([]);
  const [dropdownParceiroAberto, setDropdownParceiroAberto] = useState(false);
  const [loadingParceiros, setLoadingParceiros] = useState(false);

  const [buscaProduto, setBuscaProduto] = useState("");
  const [sugestoesProdutos, setSugestoesProdutos] = useState([]);
  const [dropdownProdutoAberto, setDropdownProdutoAberto] = useState(false);
  const [loadingProdutos, setLoadingProdutos] = useState(false);

  const [itens, setItens] = useState([]);
  const [salvando, setSalvando] = useState(false);
  const [transferenciaEditando, setTransferenciaEditando] = useState(null);
  const [abaAtiva, setAbaAtiva] = useState("lancamento");
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
  const [loadingHistorico, setLoadingHistorico] = useState(false);
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

  useEffect(() => {
    const termo = buscaParceiro.trim();
    if (parceiroSelecionado || termo.length < 2) {
      setSugestoesParceiros([]);
      setLoadingParceiros(false);
      return undefined;
    }

    const timer = setTimeout(async () => {
      try {
        setLoadingParceiros(true);
        const clientes = await buscarClientes({
          search: termo,
          limit: 8,
          ativo: true,
        });
        setSugestoesParceiros(clientes);
      } catch (error) {
        console.error("Erro ao buscar pessoas:", error);
        setSugestoesParceiros([]);
      } finally {
        setLoadingParceiros(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [buscaParceiro, parceiroSelecionado]);

  useEffect(() => {
    const termo = buscaProduto.trim();
    if (termo.length < 2) {
      setSugestoesProdutos([]);
      setLoadingProdutos(false);
      return undefined;
    }

    const timer = setTimeout(async () => {
      try {
        setLoadingProdutos(true);
        const response = await getProdutos({
          busca: termo,
          page: 1,
          page_size: 8,
          include_variations: true,
          busca_completa: false,
          incluir_imagens: false,
          incluir_lotes: false,
          incluir_detalhes_composto: false,
        });
        setSugestoesProdutos(
          extrairListaProdutos(response?.data).filter(
            (produto) => !produto?.is_parent && produto?.tipo_produto !== "PAI",
          ),
        );
      } catch (error) {
        console.error("Erro ao buscar produtos:", error);
        setSugestoesProdutos([]);
      } finally {
        setLoadingProdutos(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [buscaProduto]);

  useEffect(() => {
    const handleClickFora = (event) => {
      if (!parceiroRef.current?.contains(event.target)) {
        setDropdownParceiroAberto(false);
      }
      if (!produtoRef.current?.contains(event.target)) {
        setDropdownProdutoAberto(false);
      }
    };

    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  useEffect(() => {
    void carregarFormasPagamento();
  }, []);

  useEffect(() => {
    void carregarHistoricoTransferencias(filtrosHistoricoAplicados, paginaHistorico);
  }, [filtrosHistoricoAplicados, paginaHistorico]);

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

  const totalQuantidade = useMemo(
    () => itens.reduce((acumulado, item) => acumulado + Number(item.quantidade || 0), 0),
    [itens],
  );

  const totalRessarcimento = useMemo(
    () => itens.reduce((acumulado, item) => acumulado + Number(item.total_item || 0), 0),
    [itens],
  );

  const itensSemValor = useMemo(
    () => itens.filter((item) => Number(item.total_item || 0) <= 0).length,
    [itens],
  );

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

  const carregarFormasPagamento = async () => {
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
  };

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

  const atualizarValorCompensacao = (contaPagarId, valor) => {
    setFormBaixa((prev) => ({
      ...prev,
      compensacoes: {
        ...(prev.compensacoes || {}),
        [contaPagarId]: valor,
      },
    }));
  };

  const preencherCompensacaoAutomatica = () => {
    const valorBase = normalizarNumero(formBaixa.valor_recebido);
    if (!Number.isFinite(valorBase) || valorBase <= 0) {
      toast.error("Informe primeiro o valor da baixa para preencher a compensacao.");
      return;
    }

    setFormBaixa((prev) => ({
      ...prev,
      compensacoes: distribuirCompensacaoAutomatica(valorBase, contasPagarCompensacao),
    }));
  };

  const limparCompensacoesBaixa = () => {
    setFormBaixa((prev) => ({
      ...prev,
      compensacoes: {},
    }));
  };

  const carregarHistoricoTransferencias = async (filtros, pagina) => {
    try {
      setLoadingHistorico(true);
      const params = {
        page: pagina,
        page_size: 20,
        ...montarFiltrosHistoricoTransferenciaParams(filtros),
      };

      const response = await api.get("/estoque/transferencia-parceiro/historico", {
        params,
      });
      setHistorico(response.data);
    } catch (error) {
      console.error("Erro ao carregar historico de transferencias:", error);
      toast.error("Nao foi possivel carregar o historico de transferencias.");
      setHistorico(criarHistoricoTransferenciasVazio());
    } finally {
      setLoadingHistorico(false);
    }
  };

  const atualizarFiltroHistorico = (campo, valor) => {
    setFiltrosHistoricoForm((prev) => ({
      ...prev,
      [campo]: valor,
    }));
  };

  const rotuloPessoaHistorico = (pessoa) =>
    pessoa?.nome || pessoa?.razao_social || pessoa?.nome_fantasia || `Pessoa #${pessoa?.id || ""}`;

  const atualizarBuscaPessoaHistorico = (valor) => {
    setPessoaHistoricoSelecionada(null);
    setSugestoesPessoasHistorico([]);
    setFiltrosHistoricoForm((prev) => ({
      ...prev,
      busca: valor,
      parceiro_id: "",
    }));
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
    setSelecionadosHistorico([]);
    setFiltrosHistoricoForm((prev) => ({
      ...prev,
      data_inicio: dataInicio,
      data_fim: dataFim,
    }));
    setFiltrosHistoricoAplicados((prev) => ({
      ...prev,
      data_inicio: dataInicio,
      data_fim: dataFim,
    }));
  };

  const aplicarFiltrosHistorico = (event) => {
    event.preventDefault();
    setPaginaHistorico(1);
    setSelecionadosHistorico([]);
    setFiltrosHistoricoAplicados({
      ...filtrosHistoricoForm,
    });
  };

  const limparFiltrosHistorico = () => {
    setPaginaHistorico(1);
    setSelecionadosHistorico([]);
    setPessoaHistoricoSelecionada(null);
    setSugestoesPessoasHistorico([]);
    setFiltrosHistoricoForm(criarFiltrosHistoricoTransferencia());
    setFiltrosHistoricoAplicados(criarFiltrosHistoricoTransferencia());
  };

  const usarParceiroAtualNoHistorico = () => {
    if (!parceiroSelecionado?.id) return;
    setPaginaHistorico(1);
    setSelecionadosHistorico([]);
    setPessoaHistoricoSelecionada(parceiroSelecionado);
    setFiltrosHistoricoForm((prev) => ({
      ...prev,
      busca: rotuloPessoaHistorico(parceiroSelecionado),
      parceiro_id: String(parceiroSelecionado.id),
    }));
    setFiltrosHistoricoAplicados((prev) => ({
      ...prev,
      busca: rotuloPessoaHistorico(parceiroSelecionado),
      parceiro_id: String(parceiroSelecionado.id),
    }));
  };

  const selecionarParceiro = (parceiro) => {
    setParceiroSelecionado(parceiro);
    setForm((prev) => ({
      ...prev,
      parceiro_id: String(parceiro.id),
    }));
    setBuscaParceiro("");
    setSugestoesParceiros([]);
    setDropdownParceiroAberto(false);
  };

  const limparParceiro = () => {
    setParceiroSelecionado(null);
    setBuscaParceiro("");
    setSugestoesParceiros([]);
    setDropdownParceiroAberto(false);
    setForm((prev) => ({
      ...prev,
      parceiro_id: "",
    }));
  };

  const adicionarProduto = (produto, options = {}) => {
    setItens((prev) => {
      const indiceExistente = prev.findIndex((item) => item.produto_id === produto.id);
      if (indiceExistente >= 0) {
        return prev.map((item, index) => {
          if (index !== indiceExistente) return item;
          return incrementarItemTransferencia(item, produto);
        });
      }

      return [...prev, criarItemTransferencia(produto)];
    });

    setBuscaProduto("");
    setSugestoesProdutos([]);
    setDropdownProdutoAberto(false);
    setAbaAtiva("lancamento");
    window.setTimeout(() => {
      if (options.scroll !== false) {
        itensRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      produtoInputRef.current?.focus();
    }, 80);
  };

  const adicionarProdutoPorBuscaAtual = async () => {
    const termo = buscaProduto.trim();
    if (termo.length < 2) return;

    const local = sugestoesProdutos.find((produto) => produtoConfereCodigo(produto, termo));
    if (local) {
      adicionarProduto(local, { scroll: false });
      return;
    }

    try {
      setLoadingProdutos(true);
      const response = await getProdutos({
        busca: termo,
        page: 1,
        page_size: 12,
        include_variations: true,
        busca_completa: false,
        incluir_imagens: false,
        incluir_lotes: false,
        incluir_detalhes_composto: false,
      });
      const produtos = extrairListaProdutos(response?.data).filter(
        (produto) => !produto?.is_parent && produto?.tipo_produto !== "PAI",
      );
      const encontrado =
        produtos.find((produto) => produtoConfereCodigo(produto, termo)) ||
        (produtos.length === 1 ? produtos[0] : null);
      if (encontrado) {
        adicionarProduto(encontrado, { scroll: false });
      } else {
        setSugestoesProdutos(produtos);
        setDropdownProdutoAberto(true);
      }
    } catch (error) {
      console.error("Erro ao buscar produto pelo leitor:", error);
      toast.error("Nao foi possivel localizar o produto.");
    } finally {
      setLoadingProdutos(false);
    }
  };

  const atualizarQuantidade = (uid, valor) => {
    if (valor === "") {
      setItens((prev) =>
        prev.map((item) => (item.uid === uid ? { ...item, quantidade: "", total_item: 0 } : item)),
      );
      return;
    }

    const quantidade = normalizarNumero(valor);
    if (!Number.isFinite(quantidade) || quantidade < 0) {
      return;
    }

    setItens((prev) =>
      prev.map((item) =>
        item.uid === uid
          ? {
              ...item,
              quantidade,
              total_item: quantidade * Number(item.custo_unitario || 0),
            }
          : item,
      ),
    );
  };

  const atualizarCustoUnitario = (uid, valor) => {
    if (valor === "") {
      setItens((prev) =>
        prev.map((item) =>
          item.uid === uid ? { ...item, custo_unitario: "", total_item: 0 } : item,
        ),
      );
      return;
    }

    const custoUnitario = normalizarNumero(valor);
    if (!Number.isFinite(custoUnitario) || custoUnitario < 0) {
      return;
    }

    setItens((prev) =>
      prev.map((item) =>
        item.uid === uid
          ? {
              ...item,
              custo_unitario: custoUnitario,
              total_item: Number(item.quantidade || 0) * custoUnitario,
            }
          : item,
      ),
    );
  };

  const atualizarTotalItem = (uid, valor) => {
    if (valor === "") {
      setItens((prev) =>
        prev.map((item) => (item.uid === uid ? { ...item, total_item: "" } : item)),
      );
      return;
    }

    const totalItem = normalizarNumero(valor);
    if (!Number.isFinite(totalItem) || totalItem < 0) {
      return;
    }

    setItens((prev) =>
      prev.map((item) => {
        if (item.uid !== uid) return item;
        const quantidade = Number(item.quantidade || 0);
        return {
          ...item,
          total_item: totalItem,
          custo_unitario:
            quantidade > 0 ? totalItem / quantidade : Number(item.custo_unitario || 0),
        };
      }),
    );
  };

  const removerItem = (uid) => {
    setItens((prev) => prev.filter((item) => item.uid !== uid));
  };

  const atualizarCampo = (campo, valor) => {
    setForm((prev) => ({
      ...prev,
      [campo]: valor,
    }));
  };

  const limparLancamentoAtual = () => {
    setTransferenciaEditando(null);
    setItens([]);
    setBuscaProduto("");
    setSugestoesProdutos([]);
    setDropdownProdutoAberto(false);
    setForm((prev) => ({
      ...prev,
      documento: "",
      observacao: "",
    }));
  };

  const iniciarEdicaoTransferencia = (registro) => {
    if (!registro?.conta_receber_id) return;
    if (Number(registro.valor_recebido || 0) > 0 || registro.status === "recebido") {
      toast.error("Transferencia com baixa registrada nao pode ser editada.");
      return;
    }
    if (registro.status === "cancelado") {
      toast.error("Transferencia cancelada nao pode ser editada.");
      return;
    }

    const parceiro = {
      id: registro.parceiro_id,
      nome: registro.parceiro_nome,
      codigo: registro.parceiro_codigo,
      email: registro.parceiro_email,
      tipo_cadastro: "pessoa",
    };

    setTransferenciaEditando(registro);
    setParceiroSelecionado(parceiro);
    setBuscaParceiro("");
    setSugestoesParceiros([]);
    setDropdownParceiroAberto(false);
    setForm(
      criarFormTransferencia({
        parceiro_id: registro.parceiro_id ? String(registro.parceiro_id) : "",
        data_vencimento: registro.data_vencimento || criarFormTransferencia().data_vencimento,
        documento: registro.documento || "",
        observacao: extrairObservacaoManualTransferencia(registro.observacoes),
      }),
    );
    setItens(criarItensEdicaoTransferencia(registro));
    setBuscaProduto("");
    setSugestoesProdutos([]);
    setDropdownProdutoAberto(false);
    window.setTimeout(() => {
      window.scrollTo({ top: 0, behavior: "smooth" });
      produtoInputRef.current?.focus();
    }, 80);
  };

  const cancelarEdicaoTransferencia = () => {
    limparLancamentoAtual();
    toast("Edicao cancelada. O lancamento original continua sem alteracoes.");
  };

  const registrarTransferencia = async () => {
    if (!parceiroSelecionado?.id) {
      toast.error("Selecione uma pessoa para registrar a transferencia.");
      return;
    }

    if (itens.length === 0) {
      toast.error("Adicione ao menos um produto na transferencia.");
      return;
    }

    if (itens.some((item) => Number(item.quantidade || 0) <= 0)) {
      toast.error("Informe uma quantidade maior que zero para todos os itens.");
      return;
    }

    if (itensSemValor > 0) {
      toast.error("Existem itens com valor total zerado. Ajuste os valores antes de transferir.");
      return;
    }

    try {
      setSalvando(true);
      const payload = montarPayloadTransferencia(parceiroSelecionado.id, form, itens);

      const response = transferenciaEditando?.conta_receber_id
        ? await api.put(
            `/estoque/transferencia-parceiro/${transferenciaEditando.conta_receber_id}`,
            payload,
          )
        : await api.post("/estoque/transferencia-parceiro", payload);
      const documentoGerado = response?.data?.documento || "registrada";
      toast.success(
        transferenciaEditando?.conta_receber_id
          ? `Transferencia ${documentoGerado} atualizada com sucesso.`
          : `Transferencia ${documentoGerado} registrada com sucesso.`,
      );

      limparLancamentoAtual();
      setPaginaHistorico(1);
      void carregarHistoricoTransferencias(filtrosHistoricoAplicados, 1);
    } catch (error) {
      console.error("Erro ao registrar transferencia:", error);
      toast.error(error?.response?.data?.detail || "Nao foi possivel registrar a transferencia.");
    } finally {
      setSalvando(false);
    }
  };

  const abrirModalDocumentoTransferencia = (registro, tipo) => {
    setModalDocumentoTransferencia({
      aberto: true,
      tipo,
      registro: registro || null,
    });
  };

  const fecharModalDocumentoTransferencia = () => {
    setModalDocumentoTransferencia({
      aberto: false,
      tipo: null,
      registro: null,
    });
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

  const limparSelecaoHistorico = () => {
    setSelecionadosHistorico([]);
  };

  const alternarExpansaoHistorico = (contaReceberId) => {
    setHistoricoExpandidoIds((prev) =>
      prev.includes(contaReceberId)
        ? prev.filter((id) => id !== contaReceberId)
        : [...prev, contaReceberId],
    );
  };

  const gerarPdfConsolidadoHistorico = async (
    colunasDocumento = COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
  ) => {
    if ((historico.totais.total_registros || 0) <= 0) {
      toast.error("Nao ha transferencias no filtro atual para consolidar.");
      return false;
    }

    const filtrosConsolidados = montarFiltrosHistoricoTransferenciaParams(filtrosHistoricoAplicados);
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
      void carregarHistoricoTransferencias(filtrosHistoricoAplicados, paginaHistorico);
      setAbaAtiva("historico");
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
      if (baixaAbertaId === registro.conta_receber_id) {
        fecharBaixaTransferencia();
      }
      if (transferenciaEditando?.conta_receber_id === registro.conta_receber_id) {
        limparLancamentoAtual();
      }
      void carregarHistoricoTransferencias(filtrosHistoricoAplicados, paginaHistorico);
    } catch (error) {
      console.error("Erro ao excluir transferencia:", error);
      toast.error(error?.response?.data?.detail || "Nao foi possivel excluir a transferencia.");
    } finally {
      setContaExcluindo(null);
    }
  };

  const totalPaginasHistorico = historico.pages || 0;
  const modoEdicao = Boolean(transferenciaEditando?.conta_receber_id);
  const loadingDocumentoTransferencia =
    modalDocumentoTransferencia.tipo === "pdf_consolidado"
      ? gerandoPdfConsolidado
      : modalDocumentoTransferencia.tipo === "email" && modalDocumentoTransferencia.registro
        ? contaEnviandoEmail === modalDocumentoTransferencia.registro.conta_receber_id
        : modalDocumentoTransferencia.tipo === "pdf" && modalDocumentoTransferencia.registro
          ? contaGerandoPdf === modalDocumentoTransferencia.registro.conta_receber_id
          : false;

  return (
    <div className="space-y-6 p-6">
      <CupomTransferenciaPrintArea cupomTransferencia={cupomTransferencia} />
      <ModalDocumentoTransferenciaParceiro
        modal={modalDocumentoTransferencia}
        colunasSelecionadas={colunasDocumentoTransferencia}
        onChangeColunas={(colunas) =>
          setColunasDocumentoTransferencia(normalizarColunasDocumentoTransferencia(colunas))
        }
        onClose={fecharModalDocumentoTransferencia}
        onConfirmar={() => void confirmarDocumentoTransferencia()}
        loading={loadingDocumentoTransferencia}
      />
      <TransferenciaParceiroHeader
        modoEdicao={modoEdicao}
        transferenciaEditando={transferenciaEditando}
        onCancelarEdicao={cancelarEdicaoTransferencia}
        abaAtiva={abaAtiva}
        onChangeAba={setAbaAtiva}
        totalRegistrosHistorico={historico.totais.total_registros}
      />

      {abaAtiva === "lancamento" ? (
        <LancamentoTransferenciaParceiro
          parceiroRef={parceiroRef}
          parceiroSelecionado={parceiroSelecionado}
          limparParceiro={limparParceiro}
          buscaParceiro={buscaParceiro}
          setBuscaParceiro={setBuscaParceiro}
          setDropdownParceiroAberto={setDropdownParceiroAberto}
          dropdownParceiroAberto={dropdownParceiroAberto}
          loadingParceiros={loadingParceiros}
          sugestoesParceiros={sugestoesParceiros}
          selecionarParceiro={selecionarParceiro}
          form={form}
          atualizarCampo={atualizarCampo}
          produtoRef={produtoRef}
          produtoInputRef={produtoInputRef}
          buscaProduto={buscaProduto}
          setBuscaProduto={setBuscaProduto}
          setDropdownProdutoAberto={setDropdownProdutoAberto}
          dropdownProdutoAberto={dropdownProdutoAberto}
          adicionarProdutoPorBuscaAtual={adicionarProdutoPorBuscaAtual}
          loadingProdutos={loadingProdutos}
          sugestoesProdutos={sugestoesProdutos}
          adicionarProduto={adicionarProduto}
          itensRef={itensRef}
          itens={itens}
          totalQuantidade={totalQuantidade}
          totalRessarcimento={totalRessarcimento}
          registrarTransferencia={registrarTransferencia}
          salvando={salvando}
          modoEdicao={modoEdicao}
          itensSemValor={itensSemValor}
          atualizarCustoUnitario={atualizarCustoUnitario}
          atualizarQuantidade={atualizarQuantidade}
          atualizarTotalItem={atualizarTotalItem}
          removerItem={removerItem}
        />
      ) : (
        <section className="rounded-3xl border border-gray-200 bg-white shadow-sm">
          <HistoricoTransferenciaFilters
            parceiroSelecionado={parceiroSelecionado}
            onUsarParceiroAtual={usarParceiroAtualNoHistorico}
            onAtualizarHistorico={() =>
              void carregarHistoricoTransferencias(filtrosHistoricoAplicados, paginaHistorico)
            }
            totais={historico.totais}
            filtros={filtrosHistoricoForm}
            atualizarFiltro={atualizarFiltroHistorico}
            pessoaSelecionada={pessoaHistoricoSelecionada}
            sugestoesPessoas={sugestoesPessoasHistorico}
            loadingPessoas={loadingPessoasHistorico}
            onAtualizarBuscaPessoa={atualizarBuscaPessoaHistorico}
            onSelecionarPessoa={selecionarPessoaHistorico}
            aplicarPeriodoRapido={aplicarPeriodoRapidoHistorico}
            limparFiltros={limparFiltrosHistorico}
            onSubmit={aplicarFiltrosHistorico}
          />

          <HistoricoTransferenciaResults
            loadingHistorico={loadingHistorico}
            historico={historico}
            selecionadosHistorico={selecionadosHistorico}
            todosPaginaSelecionados={todosPaginaSelecionados}
            gerandoPdfConsolidado={gerandoPdfConsolidado}
            historicoExpandidoIds={historicoExpandidoIds}
            baixaAbertaId={baixaAbertaId}
            formBaixa={formBaixa}
            setFormBaixa={setFormBaixa}
            loadingFormasPagamento={loadingFormasPagamento}
            formasPagamento={formasPagamento}
            totalCompensadoBaixa={totalCompensadoBaixa}
            loadingContasPagarCompensacao={loadingContasPagarCompensacao}
            contasPagarCompensacao={contasPagarCompensacao}
            contaRecebendo={contaRecebendo}
            contaGerandoPdf={contaGerandoPdf}
            contaEnviandoEmail={contaEnviandoEmail}
            contaExcluindo={contaExcluindo}
            totalPaginasHistorico={totalPaginasHistorico}
            paginaHistorico={paginaHistorico}
            onAlternarSelecaoPaginaHistorico={alternarSelecaoPaginaHistorico}
            onLimparSelecaoHistorico={limparSelecaoHistorico}
            onAbrirModalDocumentoTransferencia={abrirModalDocumentoTransferencia}
            onAlternarSelecaoHistorico={alternarSelecaoHistorico}
            onAlternarExpansaoHistorico={alternarExpansaoHistorico}
            onAbrirBaixaTransferencia={abrirBaixaTransferencia}
            onIniciarEdicaoTransferencia={iniciarEdicaoTransferencia}
            onExcluirTransferencia={excluirTransferencia}
            onPreencherCompensacaoAutomatica={preencherCompensacaoAutomatica}
            onLimparCompensacoesBaixa={limparCompensacoesBaixa}
            onAtualizarValorCompensacao={atualizarValorCompensacao}
            onFecharBaixaTransferencia={fecharBaixaTransferencia}
            onRegistrarBaixaTransferencia={registrarBaixaTransferencia}
            onSetPaginaHistorico={setPaginaHistorico}
          />
        </section>
      )}
    </div>
  );
}
