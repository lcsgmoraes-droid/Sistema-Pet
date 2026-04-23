import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { buscarClientes } from "../api/clientes";
import { formatarMoeda, getProdutos } from "../api/produtos";

const formatarQuantidade = (valor) =>
  new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor || 0));

function fimDoMesIso() {
  const data = new Date();
  data.setMonth(data.getMonth() + 1, 0);
  return data.toISOString().split("T")[0];
}

function inicioDoMesIso(dataBase = new Date()) {
  const data = new Date(dataBase);
  data.setDate(1);
  return data.toISOString().split("T")[0];
}

function fimDoMesBaseIso(dataBase = new Date()) {
  const data = new Date(dataBase.getFullYear(), dataBase.getMonth() + 1, 0);
  return data.toISOString().split("T")[0];
}

function hojeIso() {
  return new Date().toISOString().split("T")[0];
}

function extrairListaProdutos(payload) {
  if (!payload) return [];
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload.itens)) return payload.itens;
  if (Array.isArray(payload.produtos)) return payload.produtos;
  if (Array.isArray(payload.data)) return payload.data;
  if (Array.isArray(payload)) return payload;
  return [];
}

function normalizarNumero(valor) {
  return Number(String(valor || "").replace(",", "."));
}

function formatarData(valor) {
  if (!valor) return "-";
  const data = new Date(`${valor}T00:00:00`);
  if (Number.isNaN(data.getTime())) return valor;
  return data.toLocaleDateString("pt-BR");
}

function baixarArquivoBlob(blob, nomeArquivo) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function StatusTransferenciaBadge({ status, label }) {
  const estilos = {
    pendente: "bg-amber-100 text-amber-800",
    parcial: "bg-sky-100 text-sky-800",
    recebido: "bg-emerald-100 text-emerald-800",
    vencido: "bg-rose-100 text-rose-800",
    cancelado: "bg-slate-200 text-slate-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${estilos[status] || estilos.pendente}`}
    >
      {label || status}
    </span>
  );
}

function ResumoTransferenciaCard({ titulo, valor, descricao, destaque = "slate" }) {
  const estilos = {
    slate: "border-slate-200 bg-slate-50 text-slate-900",
    blue: "border-blue-100 bg-blue-50 text-blue-900",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-900",
    amber: "border-amber-100 bg-amber-50 text-amber-900",
  };

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${estilos[destaque] || estilos.slate}`}>
      <p className="text-sm font-medium opacity-80">{titulo}</p>
      <p className="mt-2 text-2xl font-bold">{valor}</p>
      <p className="mt-2 text-xs opacity-75">{descricao}</p>
    </div>
  );
}

export default function EstoqueTransferenciaParceiro() {
  const parceiroRef = useRef(null);
  const produtoRef = useRef(null);

  const [form, setForm] = useState({
    parceiro_id: "",
    data_vencimento: fimDoMesIso(),
    documento: "",
    observacao: "",
  });
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
  const [contaGerandoPdf, setContaGerandoPdf] = useState(null);
  const [gerandoPdfConsolidado, setGerandoPdfConsolidado] = useState(false);
  const [contaEnviandoEmail, setContaEnviandoEmail] = useState(null);
  const [contaRecebendo, setContaRecebendo] = useState(null);
  const [contaExcluindo, setContaExcluindo] = useState(null);
  const [selecionadosHistorico, setSelecionadosHistorico] = useState([]);
  const [baixaAbertaId, setBaixaAbertaId] = useState(null);
  const [formBaixa, setFormBaixa] = useState({
    valor_recebido: "",
    data_recebimento: hojeIso(),
    modo_baixa: "recebimento",
    forma_pagamento_id: "",
    compensacoes: {},
    observacao: "",
  });
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [loadingFormasPagamento, setLoadingFormasPagamento] = useState(false);
  const [contasPagarCompensacao, setContasPagarCompensacao] = useState([]);
  const [loadingContasPagarCompensacao, setLoadingContasPagarCompensacao] = useState(false);
  const [paginaHistorico, setPaginaHistorico] = useState(1);
  const [loadingHistorico, setLoadingHistorico] = useState(false);
  const [filtrosHistoricoForm, setFiltrosHistoricoForm] = useState({
    busca: "",
    status_filtro: "",
    data_inicio: "",
    data_fim: "",
    parceiro_id: "",
  });
  const [filtrosHistoricoAplicados, setFiltrosHistoricoAplicados] = useState({
    busca: "",
    status_filtro: "",
    data_inicio: "",
    data_fim: "",
    parceiro_id: "",
  });
  const [historico, setHistorico] = useState({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    pages: 0,
    totais: {
      total_registros: 0,
      valor_total: 0,
      valor_recebido: 0,
      saldo_aberto: 0,
      pendentes: 0,
      recebidas: 0,
      vencidas: 0,
    },
  });

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

  const totalQuantidade = useMemo(
    () => itens.reduce((acumulado, item) => acumulado + Number(item.quantidade || 0), 0),
    [itens],
  );

  const totalRessarcimento = useMemo(
    () =>
      itens.reduce(
        (acumulado, item) => acumulado + Number(item.total_item || 0),
        0,
      ),
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

    let restante = valorBase;
    const proximaCompensacao = {};

    contasPagarCompensacao.forEach((conta) => {
      if (restante <= 0) {
        proximaCompensacao[conta.conta_pagar_id] = "";
        return;
      }
      const saldo = Number(conta.saldo_aberto || 0);
      const valorAplicado = Math.min(restante, saldo);
      proximaCompensacao[conta.conta_pagar_id] =
        valorAplicado > 0 ? valorAplicado.toFixed(2) : "";
      restante = Number((restante - valorAplicado).toFixed(2));
    });

    setFormBaixa((prev) => ({
      ...prev,
      compensacoes: proximaCompensacao,
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
      };

      if (filtros.busca?.trim()) params.busca = filtros.busca.trim();
      if (filtros.status_filtro) params.status_filtro = filtros.status_filtro;
      if (filtros.data_inicio) params.data_inicio = filtros.data_inicio;
      if (filtros.data_fim) params.data_fim = filtros.data_fim;
      if (filtros.parceiro_id) params.parceiro_id = filtros.parceiro_id;

      const response = await api.get("/estoque/transferencia-parceiro/historico", {
        params,
      });
      setHistorico(response.data);
    } catch (error) {
      console.error("Erro ao carregar historico de transferencias:", error);
      toast.error("Nao foi possivel carregar o historico de transferencias.");
      setHistorico({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        pages: 0,
        totais: {
          total_registros: 0,
          valor_total: 0,
          valor_recebido: 0,
          saldo_aberto: 0,
          pendentes: 0,
          recebidas: 0,
          vencidas: 0,
        },
      });
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
    setFiltrosHistoricoForm({
      busca: "",
      status_filtro: "",
      data_inicio: "",
      data_fim: "",
      parceiro_id: "",
    });
    setFiltrosHistoricoAplicados({
      busca: "",
      status_filtro: "",
      data_inicio: "",
      data_fim: "",
      parceiro_id: "",
    });
  };

  const usarParceiroAtualNoHistorico = () => {
    if (!parceiroSelecionado?.id) return;
    setPaginaHistorico(1);
    setSelecionadosHistorico([]);
    setFiltrosHistoricoForm((prev) => ({
      ...prev,
      parceiro_id: String(parceiroSelecionado.id),
    }));
    setFiltrosHistoricoAplicados((prev) => ({
      ...prev,
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

  const adicionarProduto = (produto) => {
    const custoUnitario = Number(produto?.preco_custo || 0);
    setItens((prev) => {
      const indiceExistente = prev.findIndex((item) => item.produto_id === produto.id);
      if (indiceExistente >= 0) {
        return prev.map((item, index) => {
          if (index !== indiceExistente) return item;
          const novaQuantidade = Number(item.quantidade || 0) + 1;
          return {
            ...item,
            quantidade: novaQuantidade,
            total_item: novaQuantidade * Number(item.custo_unitario || 0),
            estoque_atual: Number(produto?.estoque_atual || item.estoque_atual || 0),
          };
        });
      }

      return [
        ...prev,
        {
          uid: `${produto.id}-${Date.now()}`,
          produto_id: produto.id,
          produto_nome: produto.nome,
          codigo: produto.codigo,
          codigo_barras: produto.codigo_barras,
          estoque_atual: Number(produto?.estoque_atual || 0),
          custo_unitario: custoUnitario,
          quantidade: 1,
          total_item: custoUnitario,
        },
      ];
    });

    setBuscaProduto("");
    setSugestoesProdutos([]);
    setDropdownProdutoAberto(false);
  };

  const atualizarQuantidade = (uid, valor) => {
    const quantidade = normalizarNumero(valor);
    if (!Number.isFinite(quantidade) || quantidade <= 0) {
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
          custo_unitario: quantidade > 0 ? totalItem / quantidade : Number(item.custo_unitario || 0),
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

  const registrarTransferencia = async () => {
    if (!parceiroSelecionado?.id) {
      toast.error("Selecione uma pessoa para registrar a transferencia.");
      return;
    }

    if (itens.length === 0) {
      toast.error("Adicione ao menos um produto na transferencia.");
      return;
    }

    if (itensSemValor > 0) {
      toast.error("Existem itens com valor total zerado. Ajuste os valores antes de transferir.");
      return;
    }

    try {
      setSalvando(true);
      const payload = {
        parceiro_id: Number(parceiroSelecionado.id),
        data_vencimento: form.data_vencimento || undefined,
        documento: form.documento.trim() || undefined,
        observacao: form.observacao.trim() || undefined,
        itens: itens.map((item) => ({
          produto_id: Number(item.produto_id),
          quantidade: Number(item.quantidade),
          custo_unitario: Number(item.custo_unitario || 0),
          valor_total: Number(item.total_item || 0),
        })),
      };

      const response = await api.post("/estoque/transferencia-parceiro", payload);
      const documentoGerado = response?.data?.documento || "registrada";
      toast.success(`Transferencia ${documentoGerado} registrada com sucesso.`);

      setItens([]);
      setBuscaProduto("");
      setSugestoesProdutos([]);
      setDropdownProdutoAberto(false);
      setForm((prev) => ({
        ...prev,
        documento: "",
        observacao: "",
      }));
      setPaginaHistorico(1);
      void carregarHistoricoTransferencias(filtrosHistoricoAplicados, 1);
    } catch (error) {
      console.error("Erro ao registrar transferencia:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Nao foi possivel registrar a transferencia.",
      );
    } finally {
      setSalvando(false);
    }
  };

  const gerarPdfTransferencia = async (registro) => {
    try {
      setContaGerandoPdf(registro.conta_receber_id);
      const response = await api.get(
        `/estoque/transferencia-parceiro/${registro.conta_receber_id}/pdf`,
        { responseType: "blob" },
      );
      baixarArquivoBlob(
        response.data,
        `transferencia_${registro.documento || registro.conta_receber_id}.pdf`,
      );
    } catch (error) {
      console.error("Erro ao gerar PDF da transferencia:", error);
      toast.error(
        error?.response?.data?.detail || "Nao foi possivel gerar o PDF da transferencia.",
      );
    } finally {
      setContaGerandoPdf(null);
    }
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

  const gerarPdfConsolidadoHistorico = async () => {
    if ((historico.totais.total_registros || 0) <= 0) {
      toast.error("Nao ha transferencias no filtro atual para consolidar.");
      return;
    }

    const payload = {
      conta_receber_ids: selecionadosHistorico,
      parceiro_id: filtrosHistoricoAplicados.parceiro_id
        ? Number(filtrosHistoricoAplicados.parceiro_id)
        : undefined,
      status_filtro: filtrosHistoricoAplicados.status_filtro || undefined,
      busca: filtrosHistoricoAplicados.busca?.trim() || undefined,
      data_inicio: filtrosHistoricoAplicados.data_inicio || undefined,
      data_fim: filtrosHistoricoAplicados.data_fim || undefined,
    };

    try {
      setGerandoPdfConsolidado(true);
      const response = await api.post(
        "/estoque/transferencia-parceiro/pdf-consolidado",
        payload,
        { responseType: "blob" },
      );
      baixarArquivoBlob(response.data, "transferencias_consolidadas.pdf");
    } catch (error) {
      console.error("Erro ao gerar PDF consolidado das transferencias:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Nao foi possivel gerar o PDF consolidado das transferencias.",
      );
    } finally {
      setGerandoPdfConsolidado(false);
    }
  };

  const enviarEmailTransferencia = async (registro) => {
    if (!registro?.parceiro_email) {
      toast.error("Essa pessoa nao possui e-mail cadastrado.");
      return;
    }

    try {
      setContaEnviandoEmail(registro.conta_receber_id);
      await api.post(
        `/estoque/transferencia-parceiro/${registro.conta_receber_id}/enviar-email`,
        { email: registro.parceiro_email },
      );
      toast.success(`E-mail enviado para ${registro.parceiro_email}.`);
    } catch (error) {
      console.error("Erro ao enviar e-mail da transferencia:", error);
      toast.error(
        error?.response?.data?.detail || "Nao foi possivel enviar o e-mail da transferencia.",
      );
    } finally {
      setContaEnviandoEmail(null);
    }
  };

  const abrirBaixaTransferencia = async (registro) => {
    setBaixaAbertaId(registro.conta_receber_id);
    setFormBaixa({
      valor_recebido: Number(registro.saldo_aberto || 0).toFixed(2),
      data_recebimento: hojeIso(),
      modo_baixa: "recebimento",
      forma_pagamento_id: "",
      compensacoes: {},
      observacao: "",
    });
    await carregarContasPagarCompensacao(registro.conta_receber_id);
  };

  const fecharBaixaTransferencia = () => {
    setBaixaAbertaId(null);
    setContasPagarCompensacao([]);
    setFormBaixa({
      valor_recebido: "",
      data_recebimento: hojeIso(),
      modo_baixa: "recebimento",
      forma_pagamento_id: "",
      compensacoes: {},
      observacao: "",
    });
  };

  const registrarBaixaTransferencia = async (registro) => {
    const valorRecebido = normalizarNumero(formBaixa.valor_recebido);
    if (!Number.isFinite(valorRecebido) || valorRecebido <= 0) {
      toast.error("Informe um valor recebido maior que zero.");
      return;
    }

    const compensacoesPayload = Object.entries(formBaixa.compensacoes || {})
      .map(([contaPagarId, valor]) => ({
        conta_pagar_id: Number(contaPagarId),
        valor_compensado: normalizarNumero(valor),
      }))
      .filter(
        (item) =>
          Number.isFinite(item.valor_compensado) &&
          item.valor_compensado > 0 &&
          item.conta_pagar_id > 0,
      );

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
      await api.post(
        `/estoque/transferencia-parceiro/${registro.conta_receber_id}/receber`,
        {
          valor_recebido: valorRecebido,
          data_recebimento: formBaixa.data_recebimento || hojeIso(),
          modo_baixa: formBaixa.modo_baixa || "recebimento",
          forma_pagamento_id:
            formBaixa.modo_baixa === "recebimento" && formBaixa.forma_pagamento_id
              ? Number(formBaixa.forma_pagamento_id)
              : undefined,
          compensacoes:
            formBaixa.modo_baixa === "acerto" ? compensacoesPayload : undefined,
          observacao: formBaixa.observacao.trim() || undefined,
        },
      );
      toast.success("Baixa registrada com sucesso.");
      fecharBaixaTransferencia();
      void carregarHistoricoTransferencias(filtrosHistoricoAplicados, paginaHistorico);
    } catch (error) {
      console.error("Erro ao registrar baixa da transferencia:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Nao foi possivel registrar a baixa da transferencia.",
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
      setSelecionadosHistorico((prev) =>
        prev.filter((id) => id !== registro.conta_receber_id),
      );
      if (baixaAbertaId === registro.conta_receber_id) {
        fecharBaixaTransferencia();
      }
      void carregarHistoricoTransferencias(filtrosHistoricoAplicados, paginaHistorico);
    } catch (error) {
      console.error("Erro ao excluir transferencia:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Nao foi possivel excluir a transferencia.",
      );
    } finally {
      setContaExcluindo(null);
    }
  };

  const totalPaginasHistorico = historico.pages || 0;

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Transferencia com Ressarcimento
          </h1>
          <p className="mt-2 max-w-4xl text-sm text-gray-600">
            Use esta tela para baixar estoque pelo custo quando qualquer pessoa
            ou parceiro levar produtos. O sistema nao cria venda no PDV e gera
            um contas a receber separado para o ressarcimento, com baixa por
            recebimento normal ou acerto.
          </p>
        </div>

        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Nao entra em faturamento de vendas. Sai do estoque e fica pendente no
          financeiro da pessoa responsavel pelo ressarcimento ate voce baixar.
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ResumoTransferenciaCard
          titulo="Itens na transferencia"
          valor={String(itens.length)}
          descricao="Linhas de produto montadas para a saida com ressarcimento."
          destaque="slate"
        />
        <ResumoTransferenciaCard
          titulo="Quantidade total"
          valor={formatarQuantidade(totalQuantidade)}
          descricao="Unidades que sairao do estoque neste lancamento."
          destaque="blue"
        />
        <ResumoTransferenciaCard
          titulo="Ressarcimento"
          valor={formatarMoeda(totalRessarcimento)}
          descricao="Total configurado para o acerto desta transferencia."
          destaque="emerald"
        />
        <ResumoTransferenciaCard
          titulo="Itens sem valor"
          valor={String(itensSemValor)}
          descricao="Itens com total zerado travam o registro para evitar distorcao."
          destaque="amber"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Pessoa responsavel e dados da transferencia
              </h2>
              <p className="mt-1 text-sm text-gray-600">
                Primeiro selecione quem vai ressarcir o custo desta saida.
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-4">
            <div ref={parceiroRef} className="relative">
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Pessoa / parceiro
              </label>
              {parceiroSelecionado ? (
                <div className="flex items-start justify-between gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4">
                  <div>
                    <p className="text-sm font-semibold text-blue-900">
                      {parceiroSelecionado.nome}
                    </p>
                    <p className="mt-1 text-xs text-blue-800">
                      Codigo: {parceiroSelecionado.codigo || "-"}
                      {parceiroSelecionado.celular ? ` | Celular: ${parceiroSelecionado.celular}` : ""}
                    </p>
                    <p className="mt-1 text-xs text-blue-800">
                      Tipo: {parceiroSelecionado.tipo_cadastro || "pessoa"}
                      {parceiroSelecionado.parceiro_ativo ? " | Parceiro ativo" : ""}
                    </p>
                    {parceiroSelecionado.email ? (
                      <p className="mt-1 text-xs text-blue-800">
                        {parceiroSelecionado.email}
                      </p>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    onClick={limparParceiro}
                    className="rounded-xl border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
                  >
                    Trocar
                  </button>
                </div>
              ) : (
                <>
                  <input
                    type="text"
                    value={buscaParceiro}
                    onChange={(event) => setBuscaParceiro(event.target.value)}
                    onFocus={() => setDropdownParceiroAberto(true)}
                    placeholder="Buscar pessoa por nome, codigo, telefone ou email"
                    className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                  />

                  {dropdownParceiroAberto && (
                    <div className="absolute z-20 mt-2 w-full rounded-2xl border border-gray-200 bg-white p-2 shadow-xl">
                      {loadingParceiros ? (
                        <p className="px-3 py-3 text-sm text-gray-500">
                          Buscando pessoas...
                        </p>
                      ) : sugestoesParceiros.length > 0 ? (
                        sugestoesParceiros.map((parceiro) => (
                          <button
                            key={parceiro.id}
                            type="button"
                            onClick={() => selecionarParceiro(parceiro)}
                            className="flex w-full flex-col rounded-xl px-3 py-3 text-left transition-colors hover:bg-slate-50"
                          >
                            <span className="text-sm font-semibold text-gray-900">
                              {parceiro.nome}
                            </span>
                            <span className="mt-1 text-xs text-gray-500">
                              Codigo: {parceiro.codigo || "-"}
                              {parceiro.celular ? ` | ${parceiro.celular}` : ""}
                            </span>
                            <span className="mt-1 text-xs text-gray-500">
                              {parceiro.tipo_cadastro || "pessoa"}
                              {parceiro.parceiro_ativo ? " | Parceiro ativo" : ""}
                            </span>
                          </button>
                        ))
                      ) : (
                        <p className="px-3 py-3 text-sm text-gray-500">
                          Nenhuma pessoa ativa encontrada para esta busca.
                        </p>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Vencimento do ressarcimento
                </label>
                <input
                  type="date"
                  value={form.data_vencimento}
                  onChange={(event) => atualizarCampo("data_vencimento", event.target.value)}
                  className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Documento interno
                </label>
                <input
                  type="text"
                  value={form.documento}
                  onChange={(event) => atualizarCampo("documento", event.target.value)}
                  placeholder="Opcional. Se vazio, o sistema gera um codigo."
                  className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Observacao
              </label>
              <textarea
                value={form.observacao}
                onChange={(event) => atualizarCampo("observacao", event.target.value)}
                rows={4}
                placeholder="Ex.: itens enviados para reposicao da loja parceira, acerto no fim do mes."
                className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              />
            </div>
          </div>
        </section>

        <section className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Adicionar produtos
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              Pesquise por nome, SKU, codigo ou codigo de barras e monte a
              transferencia.
            </p>
          </div>

          <div ref={produtoRef} className="relative mt-5">
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Buscar produto
            </label>
            <input
              type="text"
              value={buscaProduto}
              onChange={(event) => setBuscaProduto(event.target.value)}
              onFocus={() => setDropdownProdutoAberto(true)}
              placeholder="Digite nome, SKU ou codigo de barras"
              className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />

            {dropdownProdutoAberto && (
              <div className="absolute z-20 mt-2 w-full rounded-2xl border border-gray-200 bg-white p-2 shadow-xl">
                {loadingProdutos ? (
                  <p className="px-3 py-3 text-sm text-gray-500">
                    Buscando produtos...
                  </p>
                ) : sugestoesProdutos.length > 0 ? (
                  sugestoesProdutos.map((produto) => (
                    <button
                      key={produto.id}
                      type="button"
                      onClick={() => adicionarProduto(produto)}
                      className="flex w-full flex-col rounded-xl px-3 py-3 text-left transition-colors hover:bg-slate-50"
                    >
                      <span className="text-sm font-semibold text-gray-900">
                        {produto.nome}
                      </span>
                      <span className="mt-1 text-xs text-gray-500">
                        Codigo: {produto.codigo || "-"}
                        {produto.codigo_barras ? ` | CB: ${produto.codigo_barras}` : ""}
                      </span>
                      <span className="mt-1 text-xs text-gray-500">
                        Estoque: {formatarQuantidade(produto.estoque_atual)} | Custo: {formatarMoeda(produto.preco_custo || 0)}
                      </span>
                    </button>
                  ))
                ) : (
                  <p className="px-3 py-3 text-sm text-gray-500">
                    Nenhum produto encontrado para esta busca.
                  </p>
                )}
              </div>
            )}
          </div>

          <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
            Se o mesmo produto for selecionado novamente, o sistema soma mais
            uma unidade na transferencia para acelerar o lancamento.
          </div>

          <button
            type="button"
            onClick={registrarTransferencia}
            disabled={salvando}
            className="mt-5 inline-flex w-full items-center justify-center rounded-2xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
          >
            {salvando ? "Registrando transferencia..." : "Registrar transferencia"}
          </button>
        </section>
      </div>

      <section className="rounded-3xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-gray-100 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Itens da transferencia
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              Ajuste as quantidades e confira o total de ressarcimento antes de salvar.
            </p>
          </div>

          <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700">
            {itens.length} item(ns) | {formatarQuantidade(totalQuantidade)} un | {formatarMoeda(totalRessarcimento)}
          </div>
        </div>

        {itens.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="text-base font-semibold text-gray-900">
              Nenhum item adicionado ainda
            </p>
            <p className="mt-2 text-sm text-gray-500">
              Use a busca acima para incluir os produtos que sairao para a pessoa responsavel.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-slate-50">
                <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                  <th className="px-6 py-4">Produto</th>
                  <th className="px-6 py-4">Estoque atual</th>
                  <th className="px-6 py-4">Custo unit.</th>
                  <th className="px-6 py-4">Quantidade</th>
                  <th className="px-6 py-4">Total</th>
                  <th className="px-6 py-4 text-right">Acoes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {itens.map((item) => {
                  const semValor = Number(item.total_item || 0) <= 0;
                  return (
                    <tr key={item.uid} className="align-top">
                      <td className="px-6 py-4">
                        <p className="text-sm font-semibold text-gray-900">
                          {item.produto_nome}
                        </p>
                        <p className="mt-1 text-xs text-gray-500">
                          Codigo: {item.codigo || "-"}
                          {item.codigo_barras ? ` | CB: ${item.codigo_barras}` : ""}
                        </p>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700">
                        {formatarQuantidade(item.estoque_atual)}
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={Number(item.custo_unitario || 0).toFixed(2)}
                          onChange={(event) =>
                            atualizarCustoUnitario(item.uid, event.target.value)
                          }
                          className={`w-28 rounded-xl border px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100 ${
                            semValor ? "border-amber-300 bg-amber-50" : "border-gray-300"
                          }`}
                        />
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="number"
                          min="0.001"
                          step="0.001"
                          value={item.quantidade}
                          onChange={(event) => atualizarQuantidade(item.uid, event.target.value)}
                          className="w-28 rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={Number(item.total_item || 0).toFixed(2)}
                          onChange={(event) =>
                            atualizarTotalItem(item.uid, event.target.value)
                          }
                          className={`w-32 rounded-xl border px-3 py-2 text-sm font-semibold text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100 ${
                            semValor ? "border-amber-300 bg-amber-50" : "border-gray-300"
                          }`}
                        />
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          type="button"
                          onClick={() => removerItem(item.uid)}
                          className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700 transition-colors hover:bg-rose-100"
                        >
                          Remover
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-3xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-col gap-4 border-b border-gray-100 px-6 py-5 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Historico de transferencias
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              Acompanhe o que saiu do estoque, quanto a pessoa ja ressarciu e o que segue em aberto.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {parceiroSelecionado ? (
              <button
                type="button"
                onClick={usarParceiroAtualNoHistorico}
                className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
              >
                Filtrar pessoa atual
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => void carregarHistoricoTransferencias(filtrosHistoricoAplicados, paginaHistorico)}
              className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Atualizar historico
            </button>
          </div>
        </div>

        <div className="grid gap-4 border-b border-gray-100 px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
          <ResumoTransferenciaCard
            titulo="Transferencias filtradas"
            valor={String(historico.totais.total_registros || 0)}
            descricao="Documentos localizados no historico atual."
            destaque="slate"
          />
        <ResumoTransferenciaCard
          titulo="Valor transferido"
          valor={formatarMoeda(historico.totais.valor_total || 0)}
          descricao="Total em custo enviado para pessoas com ressarcimento."
          destaque="blue"
        />
          <ResumoTransferenciaCard
            titulo="Saldo em aberto"
            valor={formatarMoeda(historico.totais.saldo_aberto || 0)}
            descricao={`${historico.totais.pendentes || 0} pendente(s) e ${historico.totais.vencidas || 0} vencida(s).`}
            destaque="amber"
          />
          <ResumoTransferenciaCard
            titulo="Valor recebido"
            valor={formatarMoeda(historico.totais.valor_recebido || 0)}
            descricao={`${historico.totais.recebidas || 0} transferencia(s) ja recebida(s).`}
            destaque="emerald"
          />
        </div>

        <form
          onSubmit={aplicarFiltrosHistorico}
          className="grid gap-4 border-b border-gray-100 px-6 py-5 md:grid-cols-2 xl:grid-cols-5"
        >
          <div className="xl:col-span-2">
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Buscar documento ou pessoa
            </label>
            <input
              type="text"
              value={filtrosHistoricoForm.busca}
              onChange={(event) => atualizarFiltroHistorico("busca", event.target.value)}
              placeholder="Ex.: TRP-2026, nome da pessoa ou observacao"
              className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Status
            </label>
            <select
              value={filtrosHistoricoForm.status_filtro}
              onChange={(event) => atualizarFiltroHistorico("status_filtro", event.target.value)}
              className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            >
              <option value="">Todos</option>
              <option value="pendente">Pendente</option>
              <option value="parcial">Parcial</option>
              <option value="vencido">Vencida</option>
              <option value="recebido">Recebida</option>
              <option value="cancelado">Cancelada</option>
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Data inicial
            </label>
            <input
              type="date"
              value={filtrosHistoricoForm.data_inicio}
              onChange={(event) => atualizarFiltroHistorico("data_inicio", event.target.value)}
              className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Data final
            </label>
            <input
              type="date"
              value={filtrosHistoricoForm.data_fim}
              onChange={(event) => atualizarFiltroHistorico("data_fim", event.target.value)}
              className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </div>

          <div className="md:col-span-2 xl:col-span-5 flex flex-wrap justify-end gap-2">
            <button
              type="button"
              onClick={() => aplicarPeriodoRapidoHistorico("mes_atual")}
              className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
            >
              Mes atual
            </button>
            <button
              type="button"
              onClick={() => aplicarPeriodoRapidoHistorico("mes_anterior")}
              className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
            >
              Mes anterior
            </button>
            <button
              type="button"
              onClick={limparFiltrosHistorico}
              className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Limpar filtros
            </button>
            <button
              type="submit"
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              Aplicar filtros
            </button>
          </div>
        </form>

        {loadingHistorico ? (
          <div className="px-6 py-12 text-center text-sm text-gray-500">
            Carregando historico de transferencias...
          </div>
        ) : historico.items.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="text-base font-semibold text-gray-900">
              Nenhuma transferencia encontrada
            </p>
            <p className="mt-2 text-sm text-gray-500">
              Ajuste os filtros acima ou registre uma nova transferencia para comecar o historico.
            </p>
          </div>
        ) : (
          <div className="space-y-4 px-6 py-5">
            <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  PDF consolidado do acerto
                </p>
                <p className="mt-1 text-xs text-slate-600">
                  Marque lancamentos especificos ou gere um PDF unico com todo o filtro atual.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={alternarSelecaoPaginaHistorico}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100"
                >
                  {todosPaginaSelecionados ? "Desmarcar pagina" : "Selecionar pagina"}
                </button>
                <button
                  type="button"
                  onClick={limparSelecaoHistorico}
                  disabled={selecionadosHistorico.length === 0}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Limpar selecao
                </button>
                <button
                  type="button"
                  onClick={() => void gerarPdfConsolidadoHistorico()}
                  disabled={gerandoPdfConsolidado}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                >
                  {gerandoPdfConsolidado
                    ? "Gerando PDF consolidado..."
                    : selecionadosHistorico.length > 0
                      ? `Gerar PDF (${selecionadosHistorico.length} selecionado(s))`
                      : "Gerar PDF do filtro atual"}
                </button>
              </div>
            </div>

            {historico.items.map((registro) => (
              <article
                key={registro.conta_receber_id}
                className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
              >
                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <label className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                        <input
                          type="checkbox"
                          checked={selecionadosHistorico.includes(registro.conta_receber_id)}
                          onChange={() => alternarSelecaoHistorico(registro.conta_receber_id)}
                          className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
                        />
                        Selecionar
                      </label>
                      <h3 className="text-base font-semibold text-gray-900">
                        {registro.documento || `Transferencia #${registro.conta_receber_id}`}
                      </h3>
                      <StatusTransferenciaBadge
                        status={registro.status}
                        label={registro.status_label}
                      />
                    </div>
                    <p className="text-sm text-gray-700">
                      {registro.parceiro_nome}
                      {registro.parceiro_codigo ? ` | Codigo ${registro.parceiro_codigo}` : ""}
                    </p>
                    {registro.parceiro_email ? (
                      <p className="text-xs text-gray-500">{registro.parceiro_email}</p>
                    ) : null}
                    <p className="text-xs text-gray-500">
                      Emissao: {formatarData(registro.data_emissao)} | Vencimento: {formatarData(registro.data_vencimento)} | Recebimento: {formatarData(registro.data_recebimento)}
                    </p>
                    {registro.modo_baixa_label || registro.forma_pagamento_nome ? (
                      <div className="flex flex-wrap gap-2">
                        {registro.modo_baixa_label ? (
                          <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                            {registro.modo_baixa_label}
                          </span>
                        ) : null}
                        {registro.forma_pagamento_nome ? (
                          <span className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                            Forma: {registro.forma_pagamento_nome}
                          </span>
                        ) : null}
                      </div>
                    ) : null}
                    {registro.observacoes ? (
                      <p className="text-xs text-gray-500">{registro.observacoes}</p>
                    ) : null}
                  </div>

                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-2xl bg-white px-4 py-3 text-right shadow-sm">
                      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                        Valor
                      </p>
                      <p className="mt-1 text-base font-semibold text-gray-900">
                        {formatarMoeda(registro.valor_original)}
                      </p>
                    </div>
                    <div className="rounded-2xl bg-white px-4 py-3 text-right shadow-sm">
                      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                        Recebido
                      </p>
                      <p className="mt-1 text-base font-semibold text-emerald-700">
                        {formatarMoeda(registro.valor_recebido)}
                      </p>
                    </div>
                    <div className="rounded-2xl bg-white px-4 py-3 text-right shadow-sm">
                      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                        Saldo
                      </p>
                      <p className="mt-1 text-base font-semibold text-amber-700">
                        {formatarMoeda(registro.saldo_aberto)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap justify-end gap-2">
                  {registro.status !== "recebido" && registro.status !== "cancelado" ? (
                    <button
                      type="button"
                      onClick={() => void abrirBaixaTransferencia(registro)}
                      className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-100"
                    >
                      Dar baixa
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => void gerarPdfTransferencia(registro)}
                    disabled={contaGerandoPdf === registro.conta_receber_id}
                    className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {contaGerandoPdf === registro.conta_receber_id ? "Gerando PDF..." : "Gerar PDF"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void enviarEmailTransferencia(registro)}
                    disabled={
                      contaEnviandoEmail === registro.conta_receber_id ||
                      !registro.parceiro_email
                    }
                    className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {contaEnviandoEmail === registro.conta_receber_id
                      ? "Enviando e-mail..."
                      : registro.parceiro_email
                        ? "Enviar por e-mail"
                        : "Sem e-mail cadastrado"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void excluirTransferencia(registro)}
                    disabled={
                      contaExcluindo === registro.conta_receber_id ||
                      Number(registro.valor_recebido || 0) > 0
                    }
                    className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700 transition-colors hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {contaExcluindo === registro.conta_receber_id
                      ? "Excluindo..."
                      : "Excluir lancamento"}
                  </button>
                </div>

                {baixaAbertaId === registro.conta_receber_id ? (
                  <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                    <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
                      <div className="space-y-4">
                        <div>
                          <label className="mb-2 block text-sm font-medium text-emerald-900">
                            Tipo de baixa
                          </label>
                          <div className="grid gap-3 md:grid-cols-2">
                            <button
                              type="button"
                              onClick={() =>
                                setFormBaixa((prev) => ({
                                  ...prev,
                                  modo_baixa: "recebimento",
                                  compensacoes: {},
                                }))
                              }
                              className={`rounded-2xl border px-4 py-3 text-left transition ${
                                formBaixa.modo_baixa === "recebimento"
                                  ? "border-emerald-500 bg-white shadow-sm"
                                  : "border-emerald-200 bg-emerald-50 hover:bg-white"
                              }`}
                            >
                              <p className="text-sm font-semibold text-emerald-900">
                                Recebimento normal
                              </p>
                              <p className="mt-1 text-xs text-emerald-800">
                                Usa o contas a receber e pode vincular uma forma de pagamento.
                              </p>
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                setFormBaixa((prev) => ({
                                  ...prev,
                                  modo_baixa: "acerto",
                                  forma_pagamento_id: "",
                                  compensacoes: prev.compensacoes || {},
                                }))
                              }
                              className={`rounded-2xl border px-4 py-3 text-left transition ${
                                formBaixa.modo_baixa === "acerto"
                                  ? "border-amber-500 bg-white shadow-sm"
                                  : "border-amber-200 bg-amber-50 hover:bg-white"
                              }`}
                            >
                              <p className="text-sm font-semibold text-amber-900">
                                Acerto / compensacao
                              </p>
                              <p className="mt-1 text-xs text-amber-800">
                                Ideal para o mata quando a pessoa tambem tem contas com voce.
                              </p>
                            </button>
                          </div>
                        </div>

                        {formBaixa.modo_baixa === "recebimento" ? (
                          <div>
                            <label className="mb-2 block text-sm font-medium text-emerald-900">
                              Forma de pagamento
                            </label>
                            <select
                              value={formBaixa.forma_pagamento_id}
                              onChange={(event) =>
                                setFormBaixa((prev) => ({
                                  ...prev,
                                  forma_pagamento_id: event.target.value,
                                }))
                              }
                              className="w-full rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                            >
                              <option value="">
                                {loadingFormasPagamento
                                  ? "Carregando formas..."
                                  : "Sem forma especifica"}
                              </option>
                              {formasPagamento.map((forma) => (
                                <option key={forma.id} value={forma.id}>
                                  {forma.nome}
                                </option>
                              ))}
                            </select>
                            <p className="mt-2 text-xs text-emerald-800">
                              Opcional. Se nao informar, a baixa fica sem forma vinculada.
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                              O sistema vai registrar esta baixa usando a forma de pagamento{" "}
                              <span className="font-semibold">Acerto</span>.
                            </div>

                            <div className="rounded-2xl border border-amber-200 bg-white p-4">
                              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                                <div>
                                  <p className="text-sm font-semibold text-amber-900">
                                    Contas a pagar em aberto da mesma pessoa
                                  </p>
                                  <p className="mt-1 text-xs text-amber-800">
                                    Se preencher valores aqui, o sistema baixa a transferencia e
                                    tambem compensa esses titulos no contas a pagar.
                                  </p>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  <button
                                    type="button"
                                    onClick={preencherCompensacaoAutomatica}
                                    className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700 transition hover:bg-amber-100"
                                  >
                                    Preencher automatico
                                  </button>
                                  <button
                                    type="button"
                                    onClick={limparCompensacoesBaixa}
                                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                                  >
                                    Limpar compensacoes
                                  </button>
                                </div>
                              </div>

                              <div className="mt-3 grid gap-3 md:grid-cols-3">
                                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                                    Total compensado
                                  </p>
                                  <p className="mt-1 text-lg font-bold text-slate-900">
                                    {formatarMoeda(totalCompensadoBaixa)}
                                  </p>
                                </div>
                                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                                    Valor da baixa
                                  </p>
                                  <p className="mt-1 text-lg font-bold text-slate-900">
                                    {formatarMoeda(normalizarNumero(formBaixa.valor_recebido) || 0)}
                                  </p>
                                </div>
                                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                                    Diferenca
                                  </p>
                                  <p className="mt-1 text-lg font-bold text-amber-700">
                                    {formatarMoeda(
                                      Math.max(
                                        (normalizarNumero(formBaixa.valor_recebido) || 0) -
                                          totalCompensadoBaixa,
                                        0,
                                      ),
                                    )}
                                  </p>
                                </div>
                              </div>

                              {loadingContasPagarCompensacao ? (
                                <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
                                  Carregando contas a pagar para compensacao...
                                </div>
                              ) : contasPagarCompensacao.length === 0 ? (
                                <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
                                  Essa pessoa nao possui contas a pagar em aberto para compensar no momento.
                                </div>
                              ) : (
                                <div className="mt-4 space-y-3">
                                  {contasPagarCompensacao.map((contaPagar) => (
                                    <div
                                      key={contaPagar.conta_pagar_id}
                                      className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
                                    >
                                      <div className="grid gap-3 xl:grid-cols-[1.6fr_0.8fr_0.8fr_0.9fr] xl:items-center">
                                        <div>
                                          <p className="text-sm font-semibold text-slate-900">
                                            {contaPagar.documento || `Conta #${contaPagar.conta_pagar_id}`}
                                          </p>
                                          <p className="mt-1 text-sm text-slate-700">
                                            {contaPagar.descricao}
                                          </p>
                                          <p className="mt-1 text-xs text-slate-500">
                                            Vencimento: {formatarData(contaPagar.data_vencimento)} |{" "}
                                            {contaPagar.status_label}
                                          </p>
                                        </div>
                                        <div className="text-sm text-slate-700">
                                          <p className="text-xs uppercase tracking-wide text-slate-500">
                                            Saldo
                                          </p>
                                          <p className="mt-1 font-semibold text-slate-900">
                                            {formatarMoeda(contaPagar.saldo_aberto)}
                                          </p>
                                        </div>
                                        <div className="text-sm text-slate-700">
                                          <p className="text-xs uppercase tracking-wide text-slate-500">
                                            Ja pago
                                          </p>
                                          <p className="mt-1 font-semibold text-slate-900">
                                            {formatarMoeda(contaPagar.valor_pago)}
                                          </p>
                                        </div>
                                        <div>
                                          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
                                            Valor a compensar
                                          </label>
                                          <input
                                            type="number"
                                            min="0"
                                            step="0.01"
                                            value={formBaixa.compensacoes?.[contaPagar.conta_pagar_id] || ""}
                                            onChange={(event) =>
                                              atualizarValorCompensacao(
                                                contaPagar.conta_pagar_id,
                                                event.target.value,
                                              )
                                            }
                                            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
                                          />
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm text-emerald-900">
                        <p className="font-semibold">Saldo atual</p>
                        <p className="mt-1 text-lg font-bold">
                          {formatarMoeda(registro.saldo_aberto)}
                        </p>
                        <p className="mt-2 text-xs text-emerald-700">
                          Pode ser baixa total ou parcial, conforme o valor informado.
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <div>
                        <label className="mb-2 block text-sm font-medium text-emerald-900">
                          Valor recebido
                        </label>
                        <input
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={formBaixa.valor_recebido}
                          onChange={(event) =>
                            setFormBaixa((prev) => ({
                              ...prev,
                              valor_recebido: event.target.value,
                            }))
                          }
                          className="w-full rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                        />
                      </div>
                      <div>
                        <label className="mb-2 block text-sm font-medium text-emerald-900">
                          Data do recebimento
                        </label>
                        <input
                          type="date"
                          value={formBaixa.data_recebimento}
                          onChange={(event) =>
                            setFormBaixa((prev) => ({
                              ...prev,
                              data_recebimento: event.target.value,
                            }))
                          }
                          className="w-full rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                        />
                      </div>
                    </div>

                    <div className="mt-4">
                      <label className="mb-2 block text-sm font-medium text-emerald-900">
                        Observacao da baixa
                      </label>
                      <textarea
                        rows={3}
                        value={formBaixa.observacao}
                        onChange={(event) =>
                          setFormBaixa((prev) => ({
                            ...prev,
                            observacao: event.target.value,
                          }))
                        }
                        placeholder="Opcional. Ex.: pix recebido hoje, acerto parcial da remessa."
                        className="w-full rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                      />
                    </div>

                    <div className="mt-4 flex flex-wrap justify-end gap-2">
                      <button
                        type="button"
                        onClick={fecharBaixaTransferencia}
                        className="rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
                      >
                        Cancelar
                      </button>
                      <button
                        type="button"
                        onClick={() => registrarBaixaTransferencia(registro)}
                        disabled={contaRecebendo === registro.conta_receber_id}
                        className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
                      >
                        {contaRecebendo === registro.conta_receber_id
                          ? "Registrando baixa..."
                          : "Confirmar baixa"}
                      </button>
                    </div>
                  </div>
                ) : null}

                <div className="mt-4 overflow-x-auto rounded-2xl bg-white">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-slate-100">
                      <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                        <th className="px-4 py-3">Item</th>
                        <th className="px-4 py-3 text-right">Qtd</th>
                        <th className="px-4 py-3 text-right">Custo</th>
                        <th className="px-4 py-3 text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 bg-white">
                      {registro.itens.map((item, index) => (
                        <tr key={`${registro.conta_receber_id}-${item.produto_id}-${index}`}>
                          <td className="px-4 py-3">
                            <p className="text-sm font-medium text-gray-900">
                              {item.produto_nome}
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              Codigo: {item.codigo || "-"}
                            </p>
                          </td>
                          <td className="px-4 py-3 text-right text-sm text-gray-700">
                            {formatarQuantidade(item.quantidade)}
                          </td>
                          <td className="px-4 py-3 text-right text-sm text-gray-700">
                            {formatarMoeda(item.custo_unitario)}
                          </td>
                          <td className="px-4 py-3 text-right text-sm font-semibold text-gray-900">
                            {formatarMoeda(item.valor_total)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>
            ))}

            {totalPaginasHistorico > 1 ? (
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setPaginaHistorico((prev) => Math.max(prev - 1, 1))}
                  disabled={paginaHistorico <= 1 || loadingHistorico}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Anterior
                </button>
                <span className="text-sm text-gray-600">
                  Pagina {historico.page || 1} de {totalPaginasHistorico}
                </span>
                <button
                  type="button"
                  onClick={() =>
                    setPaginaHistorico((prev) => Math.min(prev + 1, totalPaginasHistorico))
                  }
                  disabled={paginaHistorico >= totalPaginasHistorico || loadingHistorico}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Proxima
                </button>
              </div>
            ) : null}
          </div>
        )}
      </section>
    </div>
  );
}
