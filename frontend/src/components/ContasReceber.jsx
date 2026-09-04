import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowDownUp, CheckSquare, Plus, Receipt } from "lucide-react";
import api from "../api";
import { getAccessToken } from "../auth/tokenStorage";
import { toast } from "react-hot-toast";
import {
  calcularSaldoAtualizadoFinanceiro,
  ehContaDeRepasseCartao,
  ehLancamentoFinanceiroCancelado,
} from "../utils/financeiroStatus";
import { safeArray } from "../utils/safeArray";
import ActionButton from "./ui/ActionButton";
import CustomerIdentity from "./ui/CustomerIdentity";
import DataTable from "./ui/DataTable";
import LoadingState from "./ui/LoadingState";
import MoneyCell, { formatMoneyCellValue } from "./ui/MoneyCell";
import PageHeader from "./ui/PageHeader";
import StatusBadge from "./ui/StatusBadge";
import ComprovanteRecebimentoModal from "./contasReceber/ComprovanteRecebimentoModal";
import {
  ContasReceberDetalhesModal,
  ContasReceberFilters,
  ContasReceberRecebimentoLoteModal,
  ContasReceberRecebimentoModal,
} from "./contasReceber/ContasReceberPanels";
import ContasReceberAnalise from "./contasReceber/ContasReceberAnalise";
import {
  aplicarPeriodoRapidoContasReceber,
  criarFiltrosContasReceberDaUrl,
  montarParamsFiltrosContasReceber,
  normalizarListaClientes,
} from "./contasReceber/contasReceberFilterHelpers";
import { montarDadosComprovanteRecebimento } from "../utils/comprovanteRecebimento";

const formatarDataISO = (data) => {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
};

const adicionarMeses = (data, meses) => {
  const resultado = new Date(data);
  resultado.setMonth(resultado.getMonth() + meses);
  return resultado;
};

const calcularIntervaloAnaliseReceber = (periodo) => {
  const hoje = new Date();
  const amanha = new Date(hoje);
  amanha.setDate(hoje.getDate() + 1);
  const inicioMes = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
  const fimMes = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
  const fim12Meses = new Date(adicionarMeses(inicioMes, 12));
  fim12Meses.setDate(0);

  if (periodo === "hoje") {
    return { data_inicio: formatarDataISO(hoje), data_fim: formatarDataISO(hoje) };
  }
  if (periodo === "amanha") {
    return { data_inicio: formatarDataISO(amanha), data_fim: formatarDataISO(amanha) };
  }
  if (periodo === "mes") {
    return { data_inicio: formatarDataISO(inicioMes), data_fim: formatarDataISO(fimMes) };
  }
  if (periodo === "proximos_12_meses") {
    return { data_inicio: formatarDataISO(hoje), data_fim: formatarDataISO(fim12Meses) };
  }
  return { data_inicio: "", data_fim: "" };
};

const ContasReceber = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [contas, setContas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [abaAtivaContasReceber, setAbaAtivaContasReceber] = useState("lancamentos");
  const [filtros, setFiltros] = useState(() => criarFiltrosContasReceberDaUrl(searchParams));

  const [busca, setBusca] = useState("");
  const [ordenacao, setOrdenacao] = useState("desc"); // 'asc' = mais antiga primeiro, 'desc' = mais nova primeiro

  const [clientes, setClientes] = useState([]);
  const [contaSelecionada, setContaSelecionada] = useState(null);
  const [detalhesCompletos, setDetalhesCompletos] = useState(null);
  const [mostrarModalRecebimento, setMostrarModalRecebimento] = useState(false);
  const [mostrarModalRecebimentoLote, setMostrarModalRecebimentoLote] = useState(false);
  const [mostrarDetalhes, setMostrarDetalhes] = useState(false);
  const [contasSelecionadas, setContasSelecionadas] = useState(() => new Set());
  const [calculoEncargos, setCalculoEncargos] = useState(null);
  const [comprovanteRecebimento, setComprovanteRecebimento] = useState(null);
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [contasBancarias, setContasBancarias] = useState([]);

  const [dadosRecebimento, setDadosRecebimento] = useState({
    valor_recebido: 0,
    data_recebimento: new Date().toISOString().split("T")[0],
    forma_pagamento_id: null,
    conta_bancaria_id: null,
    valor_juros: 0,
    valor_multa: 0,
    valor_desconto: 0,
    observacoes: "",
    aplicar_encargos_automaticos: false,
    quitar: true,
  });
  const [dadosRecebimentoLote, setDadosRecebimentoLote] = useState({
    data_recebimento: new Date().toISOString().split("T")[0],
    forma_pagamento_id: null,
    observacoes: "",
    aplicar_encargos_automaticos: true,
  });

  useEffect(() => {
    carregarDados();
    carregarDadosAuxiliares();
  }, []);

  const carregarFormasPagamento = async (headers) => {
    const response = await api.get("/financeiro/formas-pagamento?apenas_ativas=true", { headers });
    return safeArray(response.data).map((forma) => ({
      id: forma.id,
      nome: forma.nome,
      tipo: forma.tipo || forma.nome?.toLowerCase()?.replace(/\s+/g, "_") || "outro",
      icone: forma.icone || "",
      conta_bancaria_destino_id: forma.conta_bancaria_destino_id || null,
    }));
  };

  const carregarDadosAuxiliares = async () => {
    const token = getAccessToken();
    const headers = { Authorization: `Bearer ${token}` };
    const [clientesRes, formasRes, bancariasRes] = await Promise.allSettled([
      api.get(`/clientes/`, { headers }),
      carregarFormasPagamento(headers),
      api.get(`/contas-bancarias?apenas_ativas=true`, { headers }),
    ]);

    if (clientesRes.status === "fulfilled") {
      setClientes(normalizarListaClientes(clientesRes.value.data));
    } else {
      console.warn("Nao foi possivel carregar a lista de clientes.", clientesRes.reason);
    }

    if (formasRes.status === "fulfilled") {
      setFormasPagamento(safeArray(formasRes.value));
    } else {
      setFormasPagamento([]);
      console.warn("Nao foi possivel carregar formas de pagamento.", formasRes.reason);
    }

    if (bancariasRes.status === "fulfilled") {
      setContasBancarias(safeArray(bancariasRes.value.data));
    } else {
      console.warn("Nao foi possivel carregar contas bancarias.", bancariasRes.reason);
    }
  };

  // Aplicar a busca automaticamente depois que o usuario parar de digitar.
  useEffect(() => {
    if (busca.trim().length > 0) {
      const timer = setTimeout(() => {
        aplicarFiltros();
      }, 500); // Debounce de 500ms
      return () => clearTimeout(timer);
    } else if (busca === "") {
      // Se limpar o campo, recarregar tudo
      carregarDados();
    }
  }, [busca]);

  const carregarDados = async () => {
    try {
      setLoading(true);
      const token = getAccessToken();
      const headers = { Authorization: `Bearer ${token}` };
      const contasRes = await api.get(
        `/contas-receber/?${montarParamsFiltrosContasReceber(filtros)}`,
        { headers },
      );

      // Ordenar por ID (mais recentes primeiro por padrao)
      const contasOrdenadas = [...safeArray(contasRes.data)].sort((a, b) => b.id - a.id);
      setContas(contasOrdenadas);
      setContasSelecionadas(new Set());
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      toast.error("Erro ao carregar contas a receber");
    } finally {
      setLoading(false);
    }
  };

  const carregarContasComFiltros = async (
    filtrosParaAplicar = filtros,
    buscaParaAplicar = busca,
  ) => {
    try {
      setLoading(true);
      const params = montarParamsFiltrosContasReceber(filtrosParaAplicar, buscaParaAplicar);

      const response = await api.get(`/contas-receber/?${params}`);

      setContas(response.data);
      setContasSelecionadas(new Set());
    } catch (error) {
      console.error("Erro ao filtrar:", error);
      toast.error("Erro ao aplicar filtros");
    } finally {
      setLoading(false);
    }
  };

  const aplicarFiltros = async () => carregarContasComFiltros(filtros, busca);

  const aplicarPeriodoRapido = (periodo) => {
    const novosFiltros = aplicarPeriodoRapidoContasReceber(filtros, periodo);
    setFiltros(novosFiltros);
    void carregarContasComFiltros(novosFiltros, busca);
  };

  const abrirListaComFiltrosAnalise = (filtrosAnalise = {}) => {
    const novosFiltros = {
      ...filtros,
      status: "todos",
      cliente_id: null,
      data_inicio: "",
      data_fim: "",
      apenas_vencidas: false,
      apenas_vencer: false,
    };

    if (filtrosAnalise.periodo_analise === "vencido") {
      novosFiltros.apenas_vencidas = true;
    } else {
      Object.assign(novosFiltros, calcularIntervaloAnaliseReceber(filtrosAnalise.periodo_analise));
    }

    if (
      filtrosAnalise.cliente_modo === "incluir" &&
      safeArray(filtrosAnalise.cliente_ids).length === 1
    ) {
      novosFiltros.cliente_id = filtrosAnalise.cliente_ids[0];
    }

    setFiltros(novosFiltros);
    setAbaAtivaContasReceber("lancamentos");
    void carregarContasComFiltros(novosFiltros, busca);
  };

  const abrirVendaNoPDV = (vendaId) => {
    // Armazena ID da venda para abrir automaticamente no PDV
    sessionStorage.setItem("abrirVenda", vendaId);
    sessionStorage.setItem("abrirModalPagamento", "true");
    toast.success("Redirecionando para o PDV...");
    navigate("/pdv");
  };

  const abrirFluxoDeCaixa = (conta) => {
    // Redireciona para o fluxo de caixa com filtros da conta
    const params = new URLSearchParams();
    if (conta.cliente_nome) {
      params.append("busca", conta.cliente_nome);
    }
    if (conta.documento) {
      params.append("documento", conta.documento);
    }
    navigate(`/financeiro/fluxo-caixa?${params.toString()}`);
    toast.success("Redirecionando para o Fluxo de Caixa...");
  };

  const alternarOrdenacao = () => {
    const novaOrdenacao = ordenacao === "desc" ? "asc" : "desc";
    setOrdenacao(novaOrdenacao);

    const contasOrdenadas = [...contas].sort((a, b) => {
      if (novaOrdenacao === "desc") {
        return b.id - a.id; // Mais nova primeiro
      } else {
        return a.id - b.id; // Mais antiga primeiro
      }
    });

    setContas(contasOrdenadas);
    toast.success(
      novaOrdenacao === "desc"
        ? "Ordenado: mais recentes primeiro"
        : "Ordenado: mais antigas primeiro",
    );
  };

  const carregarCalculoEncargos = async (conta, dataCalculo) => {
    try {
      const response = await api.get(`/contas-receber/${conta.id}/encargos`, {
        params: { data_calculo: dataCalculo },
      });
      const calculo = response.data || null;
      setCalculoEncargos(calculo);
      setDadosRecebimento((prev) => ({
        ...prev,
        valor_recebido: prev.quitar
          ? Number(
              calculo?.encargos_automaticos_ativos && prev.aplicar_encargos_automaticos
                ? calculo.saldo_atualizado
                : calculo?.saldo_atual,
            )
          : prev.valor_recebido,
      }));
    } catch (error) {
      console.error("Erro ao calcular encargos:", error);
      setCalculoEncargos(null);
    }
  };

  const abrirModalRecebimento = (conta) => {
    const dataHoje = new Date().toISOString().split("T")[0];
    const aplicarAutomaticos = Boolean(conta.encargos_automaticos_ativos && conta.eh_crediario);
    setContaSelecionada(conta);
    setDadosRecebimento({
      valor_recebido: Number(
        aplicarAutomaticos
          ? conta.saldo_atualizado
          : (conta.valor_final - conta.valor_recebido).toFixed(2),
      ),
      data_recebimento: dataHoje,
      forma_pagamento_id: conta.forma_pagamento_id || null,
      conta_bancaria_id: null,
      valor_juros: 0,
      valor_multa: 0,
      valor_desconto: 0,
      observacoes: "",
      aplicar_encargos_automaticos: aplicarAutomaticos,
      quitar: true,
    });
    setCalculoEncargos({
      eh_crediario: conta.eh_crediario,
      encargos_automaticos_ativos: conta.encargos_automaticos_ativos,
      dias_atraso: conta.dias_atraso,
      valor_juros_calculado: conta.valor_juros_calculado,
      valor_multa_calculada: conta.valor_multa_calculada,
      saldo_atual: conta.valor_final - conta.valor_recebido,
      saldo_atualizado: conta.saldo_atualizado,
    });
    setMostrarModalRecebimento(true);
  };

  const atualizarDataRecebimento = (data_recebimento) => {
    setDadosRecebimento((prev) => ({ ...prev, data_recebimento }));
    if (contaSelecionada) void carregarCalculoEncargos(contaSelecionada, data_recebimento);
  };

  const abrirDetalhes = async (conta) => {
    try {
      const response = await api.get(`/contas-receber/${conta.id}`);

      setContaSelecionada(conta);
      setDetalhesCompletos(response.data);
      setMostrarDetalhes(true);
    } catch (error) {
      console.error("Erro ao carregar detalhes:", error);
      toast.error("Erro ao carregar detalhes da conta");
    }
  };

  const abrirVenda = (vendaId) => {
    // Navegar para o PDV com a venda
    navigate(`/pdv?venda=${vendaId}`);
  };

  const registrarRecebimento = async () => {
    try {
      const response = await api.post(
        `/contas-receber/${contaSelecionada.id}/receber`,
        dadosRecebimento,
      );

      setComprovanteRecebimento(
        montarDadosComprovanteRecebimento({
          conta: contaSelecionada,
          formasPagamento,
          recebimento: {
            ...(response.data?.recebimento || {}),
            data: response.data?.recebimento?.data || dadosRecebimento.data_recebimento,
            valor: response.data?.recebimento?.valor ?? dadosRecebimento.valor_recebido,
            forma_pagamento_id:
              response.data?.recebimento?.forma_pagamento_id || dadosRecebimento.forma_pagamento_id,
            observacoes: response.data?.recebimento?.observacoes || dadosRecebimento.observacoes,
            conta_bancaria_nome: contasBancarias.find(
              (conta) => Number(conta.id) === Number(dadosRecebimento.conta_bancaria_id),
            )?.nome,
          },
          saldoRestante: response.data?.saldo_restante,
        }),
      );

      toast.success("Recebimento registrado com sucesso!");
      setMostrarModalRecebimento(false);
      carregarDados();
    } catch (error) {
      console.error("Erro ao registrar recebimento:", error);
      toast.error(error.response?.data?.detail || "Erro ao registrar recebimento");
    }
  };

  const contasReceberExibidas = safeArray(contas);

  const contasAbertasExibidas = contasReceberExibidas.filter(
    (conta) => conta.status !== "recebido" && !ehLancamentoFinanceiroCancelado(conta),
  );

  const contasSelecionadasDetalhes = contasAbertasExibidas.filter((conta) =>
    contasSelecionadas.has(conta.id),
  );

  const alternarContaSelecionada = (contaId) => {
    setContasSelecionadas((anteriores) => {
      const proximas = new Set(anteriores);
      if (proximas.has(contaId)) proximas.delete(contaId);
      else proximas.add(contaId);
      return proximas;
    });
  };

  const alternarTodasContas = () => {
    setContasSelecionadas((anteriores) => {
      const todasSelecionadas =
        contasAbertasExibidas.length > 0 &&
        contasAbertasExibidas.every((conta) => anteriores.has(conta.id));
      return todasSelecionadas
        ? new Set()
        : new Set(contasAbertasExibidas.map((conta) => conta.id));
    });
  };

  const registrarRecebimentosLote = async () => {
    try {
      const response = await api.post("/contas-receber/receber-lote", {
        ...dadosRecebimentoLote,
        conta_ids: contasSelecionadasDetalhes.map((conta) => conta.id),
      });
      toast.success(response.data?.message || "Parcelas recebidas com sucesso!");
      setMostrarModalRecebimentoLote(false);
      setContasSelecionadas(new Set());
      await carregarDados();
    } catch (error) {
      console.error("Erro ao receber parcelas em lote:", error);
      toast.error(error.response?.data?.detail || "Erro ao receber parcelas selecionadas");
    }
  };

  const emitirComprovanteHistorico = (recebimento) => {
    setComprovanteRecebimento(
      montarDadosComprovanteRecebimento({
        conta: contaSelecionada,
        detalhes: detalhesCompletos,
        formasPagamento,
        recebimento,
      }),
    );
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
    if (ehLancamentoFinanceiroCancelado(conta)) return <StatusBadge status="cancelado" />;
    if (conta.status === "recebido") return <StatusBadge status="recebido" />;
    if (ehContaDeRepasseCartao(conta)) {
      if (conta.status === "parcial") {
        return (
          <StatusBadge intent="info" title="Cliente pagou; a operadora repassou parte do valor">
            Pago · repasse parcial
          </StatusBadge>
        );
      }
      if (vencimento < hoje) {
        return (
          <StatusBadge intent="danger" title="Cliente pagou; o repasse da operadora está atrasado">
            Pago · repasse atrasado
          </StatusBadge>
        );
      }
      return (
        <StatusBadge intent="warning" title="Cliente pagou; aguardando repasse da operadora">
          Pago · repasse pendente
        </StatusBadge>
      );
    }
    if (vencimento < hoje) return <StatusBadge status="vencida" />;
    if (conta.status === "parcial") return <StatusBadge status="parcial" />;
    return <StatusBadge status="pendente" />;
  };

  const contasReceberColumns = [
    {
      key: "selecao",
      header: (
        <input
          type="checkbox"
          aria-label="Selecionar todas as contas em aberto"
          checked={
            contasAbertasExibidas.length > 0 &&
            contasAbertasExibidas.every((conta) => contasSelecionadas.has(conta.id))
          }
          onChange={alternarTodasContas}
        />
      ),
      render: (conta) =>
        conta.status !== "recebido" && !ehLancamentoFinanceiroCancelado(conta) ? (
          <input
            type="checkbox"
            aria-label={`Selecionar conta ${conta.id}`}
            checked={contasSelecionadas.has(conta.id)}
            onChange={() => alternarContaSelecionada(conta.id)}
          />
        ) : null,
    },
    {
      key: "id",
      header: "ID",
      render: (conta) => conta.id,
    },
    {
      key: "descricao",
      header: "Descricao",
      className: "min-w-[220px]",
      render: (conta) => (
        <div>
          {conta.descricao}
          {conta.eh_parcelado && (
            <span className="ml-2 px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">
              {conta.numero_parcela}/{conta.total_parcelas}
            </span>
          )}
        </div>
      ),
    },
    {
      key: "cliente",
      header: "Cliente",
      className: "min-w-[160px]",
      render: (conta) => (
        <CustomerIdentity fallback="" nameClassName="font-medium text-slate-800" record={conta} />
      ),
    },
    {
      key: "vencimento",
      header: "Vencimento",
      render: (conta) => formatarData(conta.data_vencimento),
    },
    {
      key: "valor_original",
      header: "Valor Original",
      align: "right",
      render: (conta) => <MoneyCell value={conta.valor_original} />,
    },
    {
      key: "valor_recebido",
      header: "Valor Recebido",
      align: "right",
      render: (conta) => <MoneyCell value={conta.valor_recebido} zeroAsDash />,
    },
    {
      key: "saldo",
      header: "Saldo",
      align: "right",
      className: "font-bold",
      render: (conta) => (
        <MoneyCell value={calcularSaldoAtualizadoFinanceiro(conta, "valor_recebido")} zeroAsDash />
      ),
    },
    {
      key: "status",
      header: "Status",
      render: getStatusBadge,
    },
    {
      key: "acoes",
      header: "Acoes",
      className: "min-w-[230px]",
      render: (conta) => (
        <div className="flex flex-wrap items-center gap-2">
          {conta.status !== "recebido" && !ehLancamentoFinanceiroCancelado(conta) && (
            <>
              {conta.nsu && !conta.conciliado ? (
                <>
                  <ActionButton
                    intent="warning"
                    size="xs"
                    onClick={() => navigate(`/conciliacao-cartao?nsu=${conta.nsu}`)}
                    title={`Conciliar NSU ${conta.nsu} com extrato da operadora`}
                  >
                    Conciliar
                  </ActionButton>
                  <ActionButton
                    intent="create"
                    size="xs"
                    onClick={() => abrirModalRecebimento(conta)}
                    title="Receber manual (caso nao consiga conciliar)"
                  >
                    Manual
                  </ActionButton>
                </>
              ) : conta.venda_id && !conta.nsu ? (
                <>
                  <ActionButton
                    intent="neutral"
                    size="xs"
                    onClick={() => {
                      if (conta.venda_id) {
                        abrirVendaNoPDV(conta.venda_id);
                      } else {
                        abrirModalRecebimento(conta);
                      }
                    }}
                    title="Receber no PDV (movimenta caixa)"
                  >
                    PDV
                  </ActionButton>
                  <ActionButton
                    intent="create"
                    size="xs"
                    onClick={() => abrirModalRecebimento(conta)}
                    title="Receber manual (sem PDV)"
                  >
                    Manual
                  </ActionButton>
                </>
              ) : (
                <ActionButton
                  intent="create"
                  size="xs"
                  onClick={() => abrirModalRecebimento(conta)}
                  title="Registrar recebimento manual"
                >
                  Receber Manual
                </ActionButton>
              )}
            </>
          )}
          {conta.conciliado && (
            <span
              className="text-xs text-green-600 font-semibold"
              title={`Conciliado em ${conta.data_conciliacao}`}
            >
              Conciliado
            </span>
          )}
          <ActionButton
            intent="neutral"
            tone="soft"
            size="xs"
            title="Ver Detalhes"
            onClick={() => abrirDetalhes(conta)}
          >
            Ver
          </ActionButton>
        </div>
      ),
    },
  ];

  const handleFiltrosSubmit = (event) => {
    event.preventDefault();
  };

  if (loading) {
    return <LoadingState label="Carregando contas a receber..." />;
  }

  return (
    <div className="p-6">
      <PageHeader
        actions={
          <>
            <ActionButton
              onClick={alternarOrdenacao}
              intent="neutral"
              tone="soft"
              size="md"
              icon={ArrowDownUp}
              title={
                ordenacao === "desc"
                  ? "Clique para ver mais antigas primeiro"
                  : "Clique para ver mais recentes primeiro"
              }
            >
              {ordenacao === "desc" ? "Mais recentes" : "Mais antigas"}
            </ActionButton>
            {contasSelecionadasDetalhes.length > 0 && (
              <ActionButton
                onClick={() => setMostrarModalRecebimentoLote(true)}
                intent="create"
                size="md"
                icon={CheckSquare}
              >
                Baixar selecionadas ({contasSelecionadasDetalhes.length})
              </ActionButton>
            )}
            <ActionButton intent="create" size="md" icon={Plus}>
              Nova Conta
            </ActionButton>
          </>
        }
        className="mb-6"
        icon={Receipt}
        subtitle="Acompanhe recebimentos, vencimentos e saldos"
        title="Contas a Receber"
      />

      <div className="mb-5 flex flex-wrap gap-2 border-b border-slate-200">
        {[
          { id: "lancamentos", label: "Lancamentos" },
          { id: "analise", label: "Analise" },
        ].map((aba) => {
          const ativa = abaAtivaContasReceber === aba.id;
          return (
            <button
              key={aba.id}
              type="button"
              onClick={() => setAbaAtivaContasReceber(aba.id)}
              className={[
                "border-b-2 px-4 py-2 text-sm font-semibold transition",
                ativa
                  ? "border-blue-600 text-blue-700"
                  : "border-transparent text-slate-500 hover:text-slate-800",
              ].join(" ")}
            >
              {aba.label}
            </button>
          );
        })}
      </div>

      {abaAtivaContasReceber === "analise" ? (
        <ContasReceberAnalise
          clientes={clientes}
          formasPagamento={formasPagamento}
          formatarMoeda={formatarMoeda}
          onAbrirListaComFiltros={abrirListaComFiltrosAnalise}
        />
      ) : (
        <>
          <ContasReceberFilters
            aplicarFiltros={aplicarFiltros}
            aplicarPeriodoRapido={aplicarPeriodoRapido}
            busca={busca}
            clientes={clientes}
            filtros={filtros}
            handleFiltrosSubmit={handleFiltrosSubmit}
            setBusca={setBusca}
            setFiltros={setFiltros}
          />
          {/* Tabela de Contas */}
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <DataTable
              columns={contasReceberColumns}
              data={contasReceberExibidas}
              emptyMessage="Nenhuma conta encontrada"
              getRowKey={(conta) => conta.id}
              tableClassName="min-w-[960px]"
              theadClassName="bg-gray-50"
              tbodyClassName="divide-y divide-gray-200"
            />

            {contasReceberExibidas.length > 0 && (
              <div className="bg-green-50 border-t border-green-200 px-4 py-3">
                <strong>Total:</strong> {contasReceberExibidas.length} conta(s) |
                <strong className="ml-3">Saldo a Receber:</strong>{" "}
                <MoneyCell
                  value={contasReceberExibidas.reduce(
                    (sum, c) => sum + calcularSaldoAtualizadoFinanceiro(c, "valor_recebido"),
                    0,
                  )}
                  zeroAsDash
                />
              </div>
            )}
          </div>
        </>
      )}

      <ContasReceberRecebimentoModal
        calculoEncargos={calculoEncargos}
        contaSelecionada={contaSelecionada}
        contasBancarias={contasBancarias}
        dadosRecebimento={dadosRecebimento}
        formasPagamento={formasPagamento}
        formatarMoeda={formatarMoeda}
        mostrarModalRecebimento={mostrarModalRecebimento}
        registrarRecebimento={registrarRecebimento}
        onDataRecebimentoChange={atualizarDataRecebimento}
        setDadosRecebimento={setDadosRecebimento}
        setMostrarModalRecebimento={setMostrarModalRecebimento}
      />

      <ContasReceberRecebimentoLoteModal
        contasSelecionadas={contasSelecionadasDetalhes}
        dadosRecebimento={dadosRecebimentoLote}
        formasPagamento={formasPagamento}
        formatarMoeda={formatarMoeda}
        mostrar={mostrarModalRecebimentoLote}
        onConfirmar={registrarRecebimentosLote}
        onFechar={() => setMostrarModalRecebimentoLote(false)}
        setDadosRecebimento={setDadosRecebimentoLote}
      />
      <ContasReceberDetalhesModal
        abrirFluxoDeCaixa={abrirFluxoDeCaixa}
        abrirVenda={abrirVenda}
        contaSelecionada={contaSelecionada}
        detalhesCompletos={detalhesCompletos}
        formatarData={formatarData}
        formatarMoeda={formatarMoeda}
        mostrarDetalhes={mostrarDetalhes}
        onEmitirComprovante={emitirComprovanteHistorico}
        setMostrarDetalhes={setMostrarDetalhes}
      />
      <ComprovanteRecebimentoModal
        comprovante={comprovanteRecebimento}
        onClose={() => setComprovanteRecebimento(null)}
      />
    </div>
  );
};

export default ContasReceber;
