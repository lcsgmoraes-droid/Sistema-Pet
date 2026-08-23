import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  FiAlertTriangle,
  FiCalendar,
  FiDollarSign,
  FiTrendingDown,
  FiTrendingUp,
} from "react-icons/fi";
import EmptyState from "../../../components/ui/EmptyState";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import StatusBadge from "../../../components/ui/StatusBadge";
import { obterAnaliseFinanceiraGrupo } from "../../../services/gruposEmpresas";
import { formatMoneyBRL } from "../../../utils/formatters";

function classeSaldo(valor) {
  return Number(valor || 0) >= 0
    ? "text-emerald-700 dark:text-emerald-300"
    : "text-red-700 dark:text-red-300";
}

export default function GrupoAnaliseFinanceiraTab({ grupoId }) {
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(await obterAnaliseFinanceiraGrupo(grupoId));
    } catch (error) {
      toast.error(
        error?.response?.data?.detail || "Não foi possível analisar o financeiro do grupo.",
      );
    } finally {
      setCarregando(false);
    }
  }, [grupoId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const resumo = dados?.resumo || {};
  const faixas = dados?.faixas || [];
  const empresas = dados?.empresas || [];

  if (!carregando && !dados) {
    return (
      <EmptyState
        icon={FiDollarSign}
        title="Análise financeira indisponível"
        description="Tente atualizar a tela novamente."
      />
    );
  }

  return (
    <div className="space-y-4">
      <MetricGrid>
        <MetricCard
          icon={<FiTrendingUp />}
          intent="emerald"
          size="compact"
          label="A receber"
          value={formatMoneyBRL(resumo.receber_aberto || 0)}
          subtitle={`${resumo.inadimplencia_receber_percentual || 0}% vencido`}
        />
        <MetricCard
          icon={<FiTrendingDown />}
          intent="red"
          size="compact"
          label="A pagar"
          value={formatMoneyBRL(resumo.pagar_aberto || 0)}
          subtitle={`${resumo.atraso_pagar_percentual || 0}% vencido`}
        />
        <MetricCard
          icon={<FiDollarSign />}
          intent={Number(resumo.saldo_liquido || 0) >= 0 ? "cyan" : "amber"}
          size="compact"
          label="Saldo líquido em aberto"
          value={formatMoneyBRL(resumo.saldo_liquido || 0)}
          subtitle="Recebíveis menos compromissos"
        />
        <MetricCard
          icon={<FiCalendar />}
          intent={Number(resumo.saldo_30_dias || 0) >= 0 ? "blue" : "red"}
          size="compact"
          label="Saldo projetado em 30 dias"
          value={formatMoneyBRL(resumo.saldo_30_dias || 0)}
          subtitle="Sem incluir títulos já vencidos"
        />
      </MetricGrid>

      <Panel
        title="Pressão financeira por vencimento"
        subtitle="Entradas e saídas são agrupadas pela data de vencimento. O saldo positivo indica mais valores a receber que a pagar na faixa."
        padding="none"
      >
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-300">
              <tr>
                <th className="px-4 py-3">Vencimento</th>
                <th className="px-4 py-3 text-right">A receber</th>
                <th className="px-4 py-3 text-right">A pagar</th>
                <th className="px-4 py-3 text-right">Saldo</th>
                <th className="px-4 py-3 text-right">Títulos</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {faixas.map((faixa) => (
                <tr key={faixa.chave}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-900 dark:text-slate-100">
                        {faixa.label}
                      </span>
                      {faixa.chave === "vencido" ? (
                        <StatusBadge intent="danger">Atrasado</StatusBadge>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-emerald-700 dark:text-emerald-300">
                    {formatMoneyBRL(faixa.receber)}
                  </td>
                  <td className="px-4 py-3 text-right text-red-700 dark:text-red-300">
                    {formatMoneyBRL(faixa.pagar)}
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold ${classeSaldo(faixa.saldo)}`}>
                    {formatMoneyBRL(faixa.saldo)}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-500">
                    {faixa.titulos_receber} entradas · {faixa.titulos_pagar} saídas
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel
        title="Espelho financeiro por empresa"
        subtitle="Cada empresa continua responsável pelas próprias baixas e negociações."
        padding="none"
      >
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-300">
              <tr>
                <th className="px-4 py-3">Empresa</th>
                <th className="px-4 py-3 text-right">A receber</th>
                <th className="px-4 py-3 text-right">Receber vencido</th>
                <th className="px-4 py-3 text-right">A pagar</th>
                <th className="px-4 py-3 text-right">Pagar vencido</th>
                <th className="px-4 py-3 text-right">Saldo líquido</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {empresas.map((empresa) => (
                <tr key={empresa.empresa_id}>
                  <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                    <div className="flex items-center gap-2">
                      {empresa.empresa_nome}
                      {empresa.papel === "responsavel" ? (
                        <StatusBadge intent="purple">Responsável</StatusBadge>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-emerald-700 dark:text-emerald-300">
                    {formatMoneyBRL(empresa.receber_aberto)}
                  </td>
                  <td className="px-4 py-3 text-right text-amber-700 dark:text-amber-300">
                    {formatMoneyBRL(empresa.receber_vencido)}
                  </td>
                  <td className="px-4 py-3 text-right text-red-700 dark:text-red-300">
                    {formatMoneyBRL(empresa.pagar_aberto)}
                  </td>
                  <td className="px-4 py-3 text-right text-red-700 dark:text-red-300">
                    {formatMoneyBRL(empresa.pagar_vencido)}
                  </td>
                  <td
                    className={`px-4 py-3 text-right font-semibold ${classeSaldo(empresa.saldo_liquido)}`}
                  >
                    {formatMoneyBRL(empresa.saldo_liquido)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {(resumo.receber_vencido > 0 || resumo.pagar_vencido > 0) && !carregando ? (
        <Panel className="border-amber-200 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/10">
          <div className="flex items-start gap-3 text-amber-900 dark:text-amber-100">
            <FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />
            <p className="text-sm">
              Existem {formatMoneyBRL(resumo.receber_vencido)} a receber e{" "}
              {formatMoneyBRL(resumo.pagar_vencido)} a pagar já vencidos no grupo.
            </p>
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
