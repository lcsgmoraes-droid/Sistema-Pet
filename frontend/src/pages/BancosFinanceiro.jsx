import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowLeft,
  ArrowRightLeft,
  ArrowUpRight,
  Landmark,
  RefreshCw,
  Save,
  X,
} from "lucide-react";
import api from "../api";
import CurrencyInput from "../components/CurrencyInput";
import ActionButton from "../components/ui/ActionButton";
import DataTable from "../components/ui/DataTable";
import LoadingState from "../components/ui/LoadingState";
import MetricCard from "../components/ui/MetricCard";
import MetricGrid from "../components/ui/MetricGrid";
import MoneyCell, { formatMoneyCellValue } from "../components/ui/MoneyCell";
import PageHeader from "../components/ui/PageHeader";
import StatusBadge from "../components/ui/StatusBadge";
import { safeArray } from "../utils/safeArray";

const MOTIVO_PADRAO = "Ajuste de saldo bancario";
const CONFIRMACAO_VIRADA_HISTORICA = "VIRADA_BANCARIA_HISTORICA";

const ORIGEM_LABELS = {
  abertura_conta: "Abertura",
  ajuste_manual: "Ajuste manual",
  conta_pagar: "Conta paga",
  conta_receber: "Conta recebida",
  venda: "Venda",
  caixa: "Caixa",
};

function arredondarMoeda(valor) {
  return Math.round(Number(valor || 0) * 100) / 100;
}

function dataHojeInput() {
  const hoje = new Date();
  const ano = hoje.getFullYear();
  const mes = String(hoje.getMonth() + 1).padStart(2, "0");
  const dia = String(hoje.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

function saldoDaConta(conta) {
  return Number(conta?.saldo_atual || 0);
}

function mensagemErro(error, fallback) {
  return error?.response?.data?.detail || error?.message || fallback;
}

function movimentoEhEntrada(tipo) {
  return ["entrada", "credito", "crédito"].includes(String(tipo || "").toLowerCase());
}

function formatarData(data) {
  if (!data) return "-";

  try {
    return new Date(data).toLocaleDateString("pt-BR");
  } catch {
    return "-";
  }
}

function origemLabel(origemTipo) {
  return ORIGEM_LABELS[origemTipo] || origemTipo || "-";
}

export default function BancosFinanceiro() {
  const navigate = useNavigate();
  const [contasBancarias, setContasBancarias] = useState([]);
  const [contaSelecionadaId, setContaSelecionadaId] = useState(null);
  const [movimentacoes, setMovimentacoes] = useState([]);
  const [loadingContas, setLoadingContas] = useState(true);
  const [loadingMovimentacoes, setLoadingMovimentacoes] = useState(false);
  const [processando, setProcessando] = useState(false);
  const [loadingVirada, setLoadingVirada] = useState(false);
  const [modalAjuste, setModalAjuste] = useState({
    aberto: false,
    conta: null,
    novoSaldo: 0,
    descricao: MOTIVO_PADRAO,
  });
  const [modalVirada, setModalVirada] = useState({
    aberto: false,
    conta: null,
    dataCorte: dataHojeInput(),
    saldoReal: 0,
    previa: null,
    confirmacao: "",
    aplicado: false,
  });

  const contaSelecionada = useMemo(
    () => contasBancarias.find((conta) => String(conta.id) === String(contaSelecionadaId)) || null,
    [contaSelecionadaId, contasBancarias],
  );

  const carregarContasBancarias = useCallback(async () => {
    setLoadingContas(true);

    try {
      const response = await api.get("/contas-bancarias?apenas_ativas=true");
      const contas = safeArray(response.data);

      setContasBancarias(contas);
      setContaSelecionadaId((atual) => {
        if (atual && contas.some((conta) => String(conta.id) === String(atual))) {
          return atual;
        }

        return contas[0]?.id ?? null;
      });
    } catch (error) {
      console.error("Erro ao carregar contas bancarias:", error);
      toast.error(mensagemErro(error, "Nao foi possivel carregar as contas bancarias."));
    } finally {
      setLoadingContas(false);
    }
  }, []);

  const carregarMovimentacoes = useCallback(async (contaId) => {
    if (!contaId) {
      setMovimentacoes([]);
      return;
    }

    setLoadingMovimentacoes(true);

    try {
      const response = await api.get(`/contas-bancarias/${contaId}/movimentacoes?limit=200`);
      setMovimentacoes(safeArray(response.data));
    } catch (error) {
      console.error("Erro ao carregar extrato bancario:", error);
      toast.error(mensagemErro(error, "Nao foi possivel carregar o extrato bancario."));
      setMovimentacoes([]);
    } finally {
      setLoadingMovimentacoes(false);
    }
  }, []);

  useEffect(() => {
    carregarContasBancarias();
  }, [carregarContasBancarias]);

  useEffect(() => {
    carregarMovimentacoes(contaSelecionadaId);
  }, [carregarMovimentacoes, contaSelecionadaId]);

  const resumo = useMemo(() => {
    const saldoTotal = contasBancarias.reduce((total, conta) => total + saldoDaConta(conta), 0);
    const entradas = movimentacoes
      .filter((movimento) => movimentoEhEntrada(movimento.tipo))
      .reduce((total, movimento) => total + Number(movimento.valor || 0), 0);
    const saidas = movimentacoes
      .filter((movimento) => !movimentoEhEntrada(movimento.tipo))
      .reduce((total, movimento) => total + Number(movimento.valor || 0), 0);

    return {
      saldoTotal: arredondarMoeda(saldoTotal),
      saldoConta: arredondarMoeda(saldoDaConta(contaSelecionada)),
      entradas: arredondarMoeda(entradas),
      saidas: arredondarMoeda(saidas),
    };
  }, [contaSelecionada, contasBancarias, movimentacoes]);

  const abrirModalAjuste = (conta) => {
    if (!conta) return;

    setModalAjuste({
      aberto: true,
      conta,
      novoSaldo: saldoDaConta(conta),
      descricao: MOTIVO_PADRAO,
    });
  };

  const abrirModalVirada = (conta) => {
    if (!conta) return;

    setModalVirada({
      aberto: true,
      conta,
      dataCorte: dataHojeInput(),
      saldoReal: saldoDaConta(conta),
      previa: null,
      confirmacao: "",
      aplicado: false,
    });
  };

  const resetarModalAjuste = () => {
    setModalAjuste({
      aberto: false,
      conta: null,
      novoSaldo: 0,
      descricao: MOTIVO_PADRAO,
    });
  };

  const resetarModalVirada = () => {
    setModalVirada({
      aberto: false,
      conta: null,
      dataCorte: dataHojeInput(),
      saldoReal: 0,
      previa: null,
      confirmacao: "",
      aplicado: false,
    });
  };

  const fecharModalAjuste = () => {
    if (processando) return;

    resetarModalAjuste();
  };

  const fecharModalVirada = () => {
    if (loadingVirada) return;

    resetarModalVirada();
  };

  const confirmarAjuste = async () => {
    const conta = modalAjuste.conta;
    if (!conta) return;

    if (!modalAjuste.descricao.trim()) {
      toast.error("Informe o motivo do ajuste.");
      return;
    }

    const saldoAtualSistema = saldoDaConta(conta);
    const diferenca = arredondarMoeda(modalAjuste.novoSaldo - saldoAtualSistema);

    if (Math.abs(diferenca) < 0.005) {
      toast.error("O saldo informado e igual ao saldo atual.");
      return;
    }

    setProcessando(true);

    try {
      await api.post(`/contas-bancarias/${conta.id}/ajustar-saldo`, {
        novo_saldo: modalAjuste.novoSaldo,
        descricao: modalAjuste.descricao.trim(),
      });

      toast.success(`${conta.nome} ajustada em ${formatMoneyCellValue(diferenca)}.`);
      resetarModalAjuste();
      await carregarContasBancarias();
      await carregarMovimentacoes(conta.id);
    } catch (error) {
      console.error("Erro ao ajustar saldo bancario:", error);
      toast.error(mensagemErro(error, "Nao foi possivel ajustar o saldo."));
    } finally {
      setProcessando(false);
    }
  };

  const atualizarModalAjuste = (campo, valor) => {
    setModalAjuste((atual) => ({ ...atual, [campo]: valor }));
  };

  const atualizarModalVirada = (campo, valor) => {
    setModalVirada((atual) => ({
      ...atual,
      [campo]: valor,
      ...(campo === "dataCorte" || campo === "saldoReal"
        ? { previa: null, confirmacao: "", aplicado: false }
        : {}),
    }));
  };

  const preverViradaHistorica = async () => {
    const conta = modalVirada.conta;
    if (!conta) return;

    if (!modalVirada.dataCorte) {
      toast.error("Informe a data de corte.");
      return;
    }

    setLoadingVirada(true);

    try {
      const params = new URLSearchParams({
        data_corte: modalVirada.dataCorte,
        conta_bancaria_id: String(conta.id),
        saldo_real: String(modalVirada.saldoReal || 0),
      });
      const response = await api.get(`/contas-bancarias/virada-historica/previa?${params}`);
      setModalVirada((atual) => ({
        ...atual,
        previa: response.data,
        confirmacao: "",
        aplicado: false,
      }));
      toast.success("Previa calculada.");
    } catch (error) {
      console.error("Erro ao prever virada historica:", error);
      toast.error(mensagemErro(error, "Nao foi possivel calcular a previa."));
    } finally {
      setLoadingVirada(false);
    }
  };

  const aplicarViradaHistorica = async () => {
    const conta = modalVirada.conta;
    const previa = modalVirada.previa;
    const expectedSaldoAtual = previa?.saldo_bancario?.saldo_atual_antes;
    if (!conta || !previa) return;

    if (modalVirada.confirmacao.trim() !== CONFIRMACAO_VIRADA_HISTORICA) {
      toast.error(`Digite ${CONFIRMACAO_VIRADA_HISTORICA} para aplicar.`);
      return;
    }

    if (expectedSaldoAtual === null || expectedSaldoAtual === undefined) {
      toast.error("Refaca a previa antes de aplicar a virada.");
      return;
    }

    setLoadingVirada(true);

    try {
      const response = await api.post("/contas-bancarias/virada-historica/aplicar", {
        data_corte: modalVirada.dataCorte,
        conta_bancaria_id: conta.id,
        saldo_real: String(modalVirada.saldoReal || 0),
        expected_saldo_atual: String(expectedSaldoAtual),
        baixar_historico: true,
        ajustar_saldo: true,
        confirmacao: modalVirada.confirmacao.trim(),
      });

      setModalVirada((atual) => ({
        ...atual,
        previa: response.data,
        aplicado: true,
      }));
      toast.success("Virada historica aplicada.");
      await carregarContasBancarias();
      await carregarMovimentacoes(conta.id);
    } catch (error) {
      console.error("Erro ao aplicar virada historica:", error);
      toast.error(mensagemErro(error, "Nao foi possivel aplicar a virada."));
    } finally {
      setLoadingVirada(false);
    }
  };

  const extratoColumns = [
    {
      key: "data",
      header: "Data",
      render: (movimento) => formatarData(movimento.data_movimento || movimento.created_at),
    },
    {
      key: "descricao",
      header: "Movimentacao",
      render: (movimento) => (
        <div className="min-w-0">
          <div className="truncate font-semibold text-slate-900 dark:text-slate-100">
            {movimento.descricao || origemLabel(movimento.origem_tipo)}
          </div>
          <div className="truncate text-xs text-slate-500 dark:text-slate-400">
            {movimento.documento || movimento.origem_venda || origemLabel(movimento.origem_tipo)}
          </div>
        </div>
      ),
    },
    {
      key: "origem",
      header: "Origem",
      render: (movimento) => (
        <StatusBadge
          intent={movimento.origem_tipo === "ajuste_manual" ? "warning" : "neutral"}
          size="xs"
        >
          {origemLabel(movimento.origem_tipo)}
        </StatusBadge>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (movimento) => <StatusBadge status={movimento.status} size="xs" />,
    },
    {
      key: "valor",
      header: "Valor",
      align: "right",
      render: (movimento) => {
        const entrada = movimentoEhEntrada(movimento.tipo);

        return (
          <span
            className={
              entrada
                ? "font-semibold text-emerald-700 dark:text-emerald-300"
                : "font-semibold text-red-700 dark:text-red-300"
            }
          >
            <MoneyCell value={movimento.valor} sign={entrada ? "+" : "-"} absolute />
          </span>
        );
      },
    },
  ];

  const saldoAtualSistema = saldoDaConta(modalAjuste.conta);
  const diferenca = arredondarMoeda(modalAjuste.novoSaldo - saldoAtualSistema);
  const viradaProntaParaAplicar = Boolean(
    modalVirada.previa && modalVirada.confirmacao.trim() === CONFIRMACAO_VIRADA_HISTORICA,
  );

  if (loadingContas && contasBancarias.length === 0) {
    return <LoadingState className="min-h-screen" label="Carregando bancos..." />;
  }

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        actions={
          <>
            <ActionButton
              icon={ArrowLeft}
              intent="neutral"
              tone="soft"
              onClick={() => navigate("/financeiro/fluxo-caixa")}
            >
              Fluxo de Caixa
            </ActionButton>
            <ActionButton
              icon={RefreshCw}
              intent="neutral"
              tone="soft"
              loading={loadingContas || loadingMovimentacoes}
              onClick={() => {
                carregarContasBancarias();
                carregarMovimentacoes(contaSelecionadaId);
              }}
            >
              Atualizar
            </ActionButton>
            <ActionButton
              icon={Save}
              intent="edit"
              disabled={!contaSelecionada}
              onClick={() => abrirModalAjuste(contaSelecionada)}
            >
              Ajustar saldo
            </ActionButton>
            <ActionButton
              icon={AlertTriangle}
              intent="warning"
              tone="soft"
              disabled={!contaSelecionada}
              onClick={() => abrirModalVirada(contaSelecionada)}
            >
              Prever virada
            </ActionButton>
          </>
        }
        icon={Landmark}
        subtitle="Saldos por conta, extrato bancario e ajustes auditaveis."
        title="Bancos"
      />

      <MetricGrid>
        <MetricCard
          intent="blue"
          icon={<Landmark className="h-5 w-5" />}
          label="Saldo em bancos"
          value={<MoneyCell value={resumo.saldoTotal} />}
        />
        <MetricCard
          intent={resumo.saldoConta >= 0 ? "cyan" : "red"}
          icon={<ArrowRightLeft className="h-5 w-5" />}
          label="Saldo da conta"
          value={<MoneyCell value={resumo.saldoConta} />}
          subtitle={contaSelecionada?.nome || "Nenhuma conta selecionada"}
        />
        <MetricCard
          intent="emerald"
          icon={<ArrowDownLeft className="h-5 w-5" />}
          label="Entradas no extrato"
          value={<MoneyCell value={resumo.entradas} zeroAsDash />}
        />
        <MetricCard
          intent="red"
          icon={<ArrowUpRight className="h-5 w-5" />}
          label="Saidas no extrato"
          value={<MoneyCell value={resumo.saidas} zeroAsDash />}
        />
      </MetricGrid>

      <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
        <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <div className="border-b border-slate-200 p-4 dark:border-slate-800">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Contas bancarias
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Selecione uma conta para ver o extrato.
            </p>
          </div>

          <div className="max-h-[560px] space-y-2 overflow-y-auto p-3">
            {contasBancarias.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                Nenhuma conta bancaria ativa encontrada.
              </div>
            ) : (
              contasBancarias.map((conta) => {
                const selecionada = String(conta.id) === String(contaSelecionadaId);

                return (
                  <button
                    key={conta.id}
                    type="button"
                    className={[
                      "w-full rounded-lg border p-3 text-left transition",
                      selecionada
                        ? "border-blue-300 bg-blue-50 shadow-sm dark:border-blue-400/40 dark:bg-blue-500/10"
                        : "border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-950 dark:hover:bg-slate-900",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    onClick={() => setContaSelecionadaId(conta.id)}
                  >
                    <div className="flex min-w-0 items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                          {conta.nome}
                        </div>
                        <div className="truncate text-xs text-slate-500 dark:text-slate-400">
                          {conta.banco || conta.tipo || "Conta bancaria"}
                        </div>
                      </div>
                      <StatusBadge status={conta.ativa ? "ativa" : "inativo"} size="xs" />
                    </div>
                    <div className="mt-3 text-lg font-bold text-slate-950 dark:text-slate-100">
                      <MoneyCell value={saldoDaConta(conta)} />
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <div className="flex flex-col gap-3 border-b border-slate-200 p-4 dark:border-slate-800 md:flex-row md:items-center md:justify-between">
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Extrato</h2>
              <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                {contaSelecionada
                  ? `${contaSelecionada.nome} - ultimas movimentacoes`
                  : "Selecione uma conta para acompanhar as movimentacoes."}
              </p>
            </div>

            <ActionButton
              icon={Save}
              intent="edit"
              tone="soft"
              disabled={!contaSelecionada}
              onClick={() => abrirModalAjuste(contaSelecionada)}
            >
              Ajustar saldo
            </ActionButton>
            <ActionButton
              icon={AlertTriangle}
              intent="warning"
              tone="soft"
              disabled={!contaSelecionada}
              onClick={() => abrirModalVirada(contaSelecionada)}
            >
              Prever virada
            </ActionButton>
          </div>

          <DataTable
            columns={extratoColumns}
            data={movimentacoes}
            emptyMessage="Nenhuma movimentacao encontrada para esta conta."
            getRowKey={(movimento) => movimento.id}
            loading={loadingMovimentacoes}
            loadingMessage="Carregando extrato..."
            tableClassName="min-w-[880px]"
            tbodyClassName="divide-y divide-slate-100 dark:divide-slate-800"
            theadClassName="bg-slate-50 dark:bg-slate-900"
          />
        </section>
      </div>

      {modalAjuste.aberto ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4">
          <div className="w-full max-w-lg rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-950">
            <div className="flex items-start justify-between gap-3 border-b border-slate-200 p-4 dark:border-slate-800">
              <div>
                <h2 className="text-base font-semibold text-slate-950 dark:text-slate-100">
                  Ajustar saldo
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {modalAjuste.conta?.nome}
                </p>
              </div>
              <ActionButton
                icon={X}
                intent="neutral"
                tone="ghost"
                size="xs"
                disabled={processando}
                onClick={fecharModalAjuste}
              >
                Fechar
              </ActionButton>
            </div>

            <div className="space-y-4 p-4">
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-400/30 dark:bg-amber-500/10 dark:text-amber-100">
                <div className="flex gap-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p>
                    O ajuste cria uma movimentacao realizada de origem ajuste_manual no extrato. Ele
                    corrige o banco, mas nao cria receita, despesa ou DRE.
                  </p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                  <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                    Saldo no sistema
                  </p>
                  <p className="mt-1 text-lg font-bold text-slate-950 dark:text-slate-100">
                    <MoneyCell value={saldoAtualSistema} />
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                  <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                    Diferenca
                  </p>
                  <p
                    className={
                      diferenca >= 0
                        ? "mt-1 text-lg font-bold text-emerald-700 dark:text-emerald-300"
                        : "mt-1 text-lg font-bold text-red-700 dark:text-red-300"
                    }
                  >
                    <MoneyCell value={diferenca} />
                  </p>
                </div>
              </div>

              <div>
                <label
                  htmlFor="saldo-real-banco"
                  className="mb-1 block text-sm font-semibold text-slate-700 dark:text-slate-200"
                >
                  Saldo real do banco
                </label>
                <CurrencyInput
                  allowNegative
                  id="saldo-real-banco"
                  className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-right text-sm font-semibold text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-blue-500/20"
                  title="Use a tecla - para alternar saldo negativo."
                  value={modalAjuste.novoSaldo}
                  onChange={(valor) => atualizarModalAjuste("novoSaldo", valor)}
                />
              </div>

              <div>
                <label
                  htmlFor="motivo-ajuste-banco"
                  className="mb-1 block text-sm font-semibold text-slate-700 dark:text-slate-200"
                >
                  Motivo do ajuste
                </label>
                <textarea
                  id="motivo-ajuste-banco"
                  className="min-h-[86px] w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-blue-500/20"
                  maxLength={500}
                  value={modalAjuste.descricao}
                  onChange={(event) => atualizarModalAjuste("descricao", event.target.value)}
                />
              </div>
            </div>

            <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 p-4 dark:border-slate-800">
              <ActionButton
                intent="neutral"
                tone="soft"
                disabled={processando}
                onClick={fecharModalAjuste}
              >
                Cancelar
              </ActionButton>
              <ActionButton
                icon={Save}
                intent="edit"
                loading={processando}
                disabled={Math.abs(diferenca) < 0.005}
                onClick={confirmarAjuste}
              >
                Confirmar ajuste
              </ActionButton>
            </div>
          </div>
        </div>
      ) : null}

      {modalVirada.aberto ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4">
          <div className="w-full max-w-3xl rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-950">
            <div className="flex items-start justify-between gap-3 border-b border-slate-200 p-4 dark:border-slate-800">
              <div>
                <h2 className="text-base font-semibold text-slate-950 dark:text-slate-100">
                  Virada historica
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {modalVirada.conta?.nome}
                </p>
              </div>
              <ActionButton
                icon={X}
                intent="neutral"
                tone="ghost"
                size="xs"
                disabled={loadingVirada}
                onClick={fecharModalVirada}
              >
                Fechar
              </ActionButton>
            </div>

            <div className="space-y-4 p-4">
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-400/30 dark:bg-amber-500/10 dark:text-amber-100">
                <div className="flex gap-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p>
                    Esta previa nao baixa contas e nao altera saldo. Ela mostra o impacto de marcar
                    contas antigas como pagas/recebidas sem movimentar banco e de informar o saldo
                    real para iniciar o uso do extrato.
                  </p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label
                    htmlFor="data-corte-virada"
                    className="mb-1 block text-sm font-semibold text-slate-700 dark:text-slate-200"
                  >
                    Data de corte
                  </label>
                  <input
                    id="data-corte-virada"
                    type="date"
                    className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-blue-500/20"
                    value={modalVirada.dataCorte}
                    onChange={(event) => atualizarModalVirada("dataCorte", event.target.value)}
                  />
                </div>
                <div>
                  <label
                    htmlFor="saldo-real-virada"
                    className="mb-1 block text-sm font-semibold text-slate-700 dark:text-slate-200"
                  >
                    Saldo real do banco
                  </label>
                  <CurrencyInput
                    allowNegative
                    id="saldo-real-virada"
                    className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-right text-sm font-semibold text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-blue-500/20"
                    title="Use a tecla - para alternar saldo negativo."
                    value={modalVirada.saldoReal}
                    onChange={(valor) => atualizarModalVirada("saldoReal", valor)}
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <ActionButton
                  icon={RefreshCw}
                  intent="warning"
                  loading={loadingVirada}
                  onClick={preverViradaHistorica}
                >
                  Prever virada
                </ActionButton>
              </div>

              {modalVirada.previa ? (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    Baixas historicas
                  </h3>
                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                      <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                        Contas a receber
                      </p>
                      <p className="mt-1 text-lg font-bold text-slate-950 dark:text-slate-100">
                        {modalVirada.previa.resumo?.contas_receber_baixadas || 0}
                      </p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        <MoneyCell value={modalVirada.previa.resumo?.valor_receber_baixado} />
                      </p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                      <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                        Contas a pagar
                      </p>
                      <p className="mt-1 text-lg font-bold text-slate-950 dark:text-slate-100">
                        {modalVirada.previa.resumo?.contas_pagar_baixadas || 0}
                      </p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        <MoneyCell value={modalVirada.previa.resumo?.valor_pagar_baixado} />
                      </p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                      <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                        Saldo bancario
                      </p>
                      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                        Sistema:{" "}
                        <MoneyCell value={modalVirada.previa.saldo_bancario?.saldo_atual_antes} />
                      </p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        Real:{" "}
                        <MoneyCell value={modalVirada.previa.saldo_bancario?.saldo_atual_depois} />
                      </p>
                      <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                        Diferenca:{" "}
                        <MoneyCell value={modalVirada.previa.saldo_bancario?.diferenca} />
                      </p>
                    </div>
                  </div>

                  {modalVirada.aplicado ? (
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/10 dark:text-emerald-100">
                      Virada aplicada. O extrato e os saldos foram atualizados.
                    </div>
                  ) : (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900 dark:border-red-400/30 dark:bg-red-500/10 dark:text-red-100">
                      <div className="flex gap-2">
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                        <div className="min-w-0 flex-1 space-y-3">
                          <p>
                            A aplicacao baixa os historicos ate a data de corte e define o saldo
                            real desta conta. Se o saldo do sistema mudar depois da previa, o
                            backend bloqueia a operacao.
                          </p>
                          <div>
                            <label
                              htmlFor="confirmacao-virada"
                              className="mb-1 block text-xs font-semibold uppercase text-red-800 dark:text-red-100"
                            >
                              Confirmacao
                            </label>
                            <input
                              id="confirmacao-virada"
                              type="text"
                              className="h-10 w-full rounded-md border border-red-300 bg-white px-3 text-sm font-semibold text-red-950 shadow-sm focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-100 dark:border-red-500/40 dark:bg-slate-950 dark:text-red-50 dark:focus:ring-red-500/20"
                              placeholder={CONFIRMACAO_VIRADA_HISTORICA}
                              value={modalVirada.confirmacao}
                              onChange={(event) =>
                                atualizarModalVirada("confirmacao", event.target.value)
                              }
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 p-4 dark:border-slate-800">
              <ActionButton
                intent="neutral"
                tone="soft"
                disabled={loadingVirada}
                onClick={fecharModalVirada}
              >
                Fechar
              </ActionButton>
              <ActionButton
                icon={AlertTriangle}
                intent="warning"
                loading={loadingVirada}
                disabled={!viradaProntaParaAplicar || modalVirada.aplicado}
                onClick={aplicarViradaHistorica}
              >
                Aplicar virada
              </ActionButton>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
