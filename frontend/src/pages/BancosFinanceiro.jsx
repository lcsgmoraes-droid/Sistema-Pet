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
  const [modalAjuste, setModalAjuste] = useState({
    aberto: false,
    conta: null,
    novoSaldo: 0,
    descricao: MOTIVO_PADRAO,
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

  const resetarModalAjuste = () => {
    setModalAjuste({
      aberto: false,
      conta: null,
      novoSaldo: 0,
      descricao: MOTIVO_PADRAO,
    });
  };

  const fecharModalAjuste = () => {
    if (processando) return;

    resetarModalAjuste();
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
    </div>
  );
}
