import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { AlertTriangle, ArrowRightLeft, Landmark, RefreshCw, RotateCcw, Save } from "lucide-react";
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

function arredondarMoeda(valor) {
  return Math.round(Number(valor || 0) * 100) / 100;
}

function saldoDaConta(conta) {
  return Number(conta?.saldo_atual || 0);
}

function mensagemErro(error, fallback) {
  return error?.response?.data?.detail || error?.message || fallback;
}

export default function AjusteSaldosBancarios() {
  const navigate = useNavigate();
  const [contasBancarias, setContasBancarias] = useState([]);
  const [saldosInformados, setSaldosInformados] = useState({});
  const [descricao, setDescricao] = useState(MOTIVO_PADRAO);
  const [loading, setLoading] = useState(true);
  const [processando, setProcessando] = useState(null);

  const carregarContasBancarias = useCallback(async (opcoes = {}) => {
    const preservarDigitados = opcoes.preservarDigitados !== false;
    setLoading(true);

    try {
      const response = await api.get("/contas-bancarias?apenas_ativas=true");
      const contas = safeArray(response.data);

      setContasBancarias(contas);
      setSaldosInformados((atuais) => {
        const proximos = {};

        contas.forEach((conta) => {
          proximos[conta.id] =
            preservarDigitados && atuais[conta.id] !== undefined
              ? atuais[conta.id]
              : saldoDaConta(conta);
        });

        return proximos;
      });
    } catch (error) {
      console.error("Erro ao carregar contas bancarias:", error);
      toast.error(mensagemErro(error, "Nao foi possivel carregar as contas bancarias."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregarContasBancarias();
  }, [carregarContasBancarias]);

  const montarAjuste = useCallback(
    (conta) => {
      const saldoAtualSistema = saldoDaConta(conta);
      const novoSaldo = Number(saldosInformados[conta.id] ?? saldoAtualSistema);
      const diferenca = arredondarMoeda(novoSaldo - saldoAtualSistema);

      return {
        conta,
        saldoAtualSistema,
        novoSaldo,
        diferenca,
        temDiferenca: Math.abs(diferenca) >= 0.005,
      };
    },
    [saldosInformados],
  );

  const ajustes = useMemo(
    () => contasBancarias.map((conta) => montarAjuste(conta)),
    [contasBancarias, montarAjuste],
  );

  const ajustesPendentes = useMemo(
    () => ajustes.filter((ajuste) => ajuste.temDiferenca),
    [ajustes],
  );

  const resumo = useMemo(() => {
    const totalSistema = contasBancarias.reduce((total, conta) => total + saldoDaConta(conta), 0);
    const totalInformado = ajustes.reduce((total, ajuste) => total + ajuste.novoSaldo, 0);
    const ajusteLiquido = arredondarMoeda(totalInformado - totalSistema);

    return {
      totalSistema: arredondarMoeda(totalSistema),
      totalInformado: arredondarMoeda(totalInformado),
      ajusteLiquido,
      contasComAjuste: ajustesPendentes.length,
    };
  }, [ajustes, ajustesPendentes.length, contasBancarias]);

  const atualizarSaldoInformado = (contaId, valor) => {
    setSaldosInformados((atuais) => ({ ...atuais, [contaId]: valor }));
  };

  const limparLinha = (conta) => {
    atualizarSaldoInformado(conta.id, saldoDaConta(conta));
  };

  const payloadAjuste = (ajuste) => ({
    novo_saldo: ajuste.novoSaldo,
    descricao: descricao.trim(),
  });

  const validarAntesDeAjustar = (ajustesParaValidar) => {
    if (!descricao.trim()) {
      toast.error("Informe o motivo do ajuste.");
      return false;
    }

    if (ajustesParaValidar.length === 0) {
      toast.error("Nenhuma conta tem diferenca para ajustar.");
      return false;
    }

    return true;
  };

  const ajustarConta = async (ajuste) => {
    if (!validarAntesDeAjustar([ajuste]) || !ajuste.temDiferenca) {
      return;
    }

    setProcessando(ajuste.conta.id);

    try {
      await api.post(`/contas-bancarias/${ajuste.conta.id}/ajustar-saldo`, payloadAjuste(ajuste));
      toast.success(`${ajuste.conta.nome} ajustada em ${formatMoneyCellValue(ajuste.diferenca)}.`);
      await carregarContasBancarias({ preservarDigitados: false });
    } catch (error) {
      console.error("Erro ao ajustar saldo bancario:", error);
      toast.error(mensagemErro(error, "Nao foi possivel ajustar o saldo."));
    } finally {
      setProcessando(null);
    }
  };

  const ajustarTodos = async () => {
    if (!validarAntesDeAjustar(ajustesPendentes)) {
      return;
    }

    setProcessando("todos");
    let totalSucesso = 0;
    const falhas = [];

    for (const ajuste of ajustesPendentes) {
      try {
        await api.post(`/contas-bancarias/${ajuste.conta.id}/ajustar-saldo`, payloadAjuste(ajuste));
        totalSucesso += 1;
      } catch (error) {
        falhas.push(`${ajuste.conta.nome}: ${mensagemErro(error, "erro no ajuste")}`);
      }
    }

    if (totalSucesso > 0) {
      toast.success(`${totalSucesso} saldo(s) bancario(s) ajustado(s).`);
    }

    if (falhas.length > 0) {
      toast.error(`Alguns ajustes falharam. Primeiro erro: ${falhas[0]}`);
    }

    await carregarContasBancarias({ preservarDigitados: false });
    setProcessando(null);
  };

  const columns = [
    {
      key: "conta",
      header: "Conta",
      render: (conta) => (
        <div className="min-w-0">
          <div className="truncate font-semibold text-slate-900 dark:text-slate-100">
            {conta.nome}
          </div>
          <div className="truncate text-xs text-slate-500 dark:text-slate-400">
            {conta.banco || conta.tipo || "Conta bancaria"}
          </div>
        </div>
      ),
    },
    {
      key: "saldoAtual",
      header: "Saldo no sistema",
      align: "right",
      render: (conta) => <MoneyCell value={saldoDaConta(conta)} />,
    },
    {
      key: "saldoReal",
      header: "Saldo real informado",
      align: "right",
      render: (conta) => (
        <CurrencyInput
          allowNegative
          aria-label={`Saldo real informado para ${conta.nome}`}
          className="h-9 w-36 rounded-md border border-slate-300 bg-white px-3 text-right text-sm font-semibold text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-blue-500/20"
          title="Use a tecla - para alternar saldo negativo."
          value={saldosInformados[conta.id] ?? saldoDaConta(conta)}
          onChange={(valor) => atualizarSaldoInformado(conta.id, valor)}
        />
      ),
    },
    {
      key: "diferenca",
      header: "Diferenca",
      align: "right",
      render: (conta) => {
        const ajuste = montarAjuste(conta);

        if (!ajuste.temDiferenca) {
          return <StatusBadge intent="neutral">Sem ajuste</StatusBadge>;
        }

        return (
          <span
            className={
              ajuste.diferenca > 0
                ? "font-semibold text-emerald-700 dark:text-emerald-300"
                : "font-semibold text-red-700 dark:text-red-300"
            }
          >
            <MoneyCell
              value={ajuste.diferenca}
              sign={ajuste.diferenca > 0 ? "+" : ""}
              absolute={ajuste.diferenca > 0}
            />
          </span>
        );
      },
    },
    {
      key: "acoes",
      header: "Acoes",
      align: "right",
      render: (conta) => {
        const ajuste = montarAjuste(conta);
        const isProcessando = processando === conta.id || processando === "todos";

        return (
          <div className="flex justify-end gap-2">
            <ActionButton
              icon={RotateCcw}
              intent="neutral"
              tone="ghost"
              size="xs"
              disabled={isProcessando}
              onClick={() => limparLinha(conta)}
            >
              Limpar
            </ActionButton>
            <ActionButton
              icon={Save}
              intent="edit"
              size="xs"
              loading={processando === conta.id}
              disabled={!ajuste.temDiferenca || processando === "todos"}
              onClick={() => ajustarConta(ajuste)}
            >
              Ajustar saldo
            </ActionButton>
          </div>
        );
      },
    },
  ];

  if (loading && contasBancarias.length === 0) {
    return <LoadingState className="min-h-screen" label="Carregando contas bancarias..." />;
  }

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        actions={
          <>
            <ActionButton
              icon={ArrowRightLeft}
              intent="neutral"
              tone="soft"
              onClick={() => navigate("/financeiro/fluxo-caixa")}
            >
              Ver fluxo
            </ActionButton>
            <ActionButton
              icon={RefreshCw}
              intent="neutral"
              tone="soft"
              loading={loading}
              onClick={() => carregarContasBancarias({ preservarDigitados: false })}
            >
              Atualizar
            </ActionButton>
          </>
        }
        icon={Landmark}
        subtitle="Alinhe o saldo real de cada banco com o saldo usado no financeiro."
        title="Ajuste de saldos bancarios"
      />

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-400/30 dark:bg-amber-500/10 dark:text-amber-100">
        <div className="flex gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
          <div className="space-y-1">
            <p className="font-semibold">
              Use esta tela para iniciar o financeiro com saldos reais.
            </p>
            <p>
              Cada ajuste cria uma movimentacao realizada de origem ajuste_manual. Ele corrige o
              caixa e o extrato da conta, mas nao cria receita, despesa ou classificacao de DRE.
            </p>
          </div>
        </div>
      </div>

      <MetricGrid>
        <MetricCard
          intent="blue"
          icon={<Landmark className="h-5 w-5" />}
          label="Saldo no sistema"
          value={<MoneyCell value={resumo.totalSistema} />}
        />
        <MetricCard
          intent="emerald"
          icon={<Save className="h-5 w-5" />}
          label="Saldo informado"
          value={<MoneyCell value={resumo.totalInformado} />}
        />
        <MetricCard
          intent={resumo.ajusteLiquido >= 0 ? "cyan" : "red"}
          icon={<ArrowRightLeft className="h-5 w-5" />}
          label="Ajuste liquido"
          value={<MoneyCell value={resumo.ajusteLiquido} />}
        />
        <MetricCard
          intent={resumo.contasComAjuste > 0 ? "amber" : "slate"}
          icon={<AlertTriangle className="h-5 w-5" />}
          label="Contas com ajuste"
          value={resumo.contasComAjuste}
        />
      </MetricGrid>

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 dark:border-slate-800 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0 flex-1">
            <label
              htmlFor="motivo-ajuste-saldo"
              className="mb-1 block text-sm font-semibold text-slate-700 dark:text-slate-200"
            >
              Motivo aplicado aos ajustes
            </label>
            <input
              id="motivo-ajuste-saldo"
              className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-blue-500/20"
              maxLength={500}
              value={descricao}
              onChange={(event) => setDescricao(event.target.value)}
            />
          </div>

          <ActionButton
            icon={Save}
            intent="create"
            size="md"
            loading={processando === "todos"}
            disabled={ajustesPendentes.length === 0 || processando !== null}
            onClick={ajustarTodos}
          >
            Ajustar todos
          </ActionButton>
        </div>

        <DataTable
          columns={columns}
          data={contasBancarias}
          emptyMessage="Nenhuma conta bancaria ativa encontrada."
          getRowKey={(conta) => conta.id}
          loading={loading}
          loadingMessage="Atualizando contas bancarias..."
          tableClassName="min-w-[980px]"
          tbodyClassName="divide-y divide-slate-100 dark:divide-slate-800"
          theadClassName="bg-slate-50 dark:bg-slate-900"
        />
      </section>
    </div>
  );
}
