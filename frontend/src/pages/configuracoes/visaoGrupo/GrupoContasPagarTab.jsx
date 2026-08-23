import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiAlertTriangle, FiCheckCircle, FiDollarSign, FiTrendingDown } from "react-icons/fi";
import ActionButton from "../../../components/ui/ActionButton";
import EmptyState from "../../../components/ui/EmptyState";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import StatusBadge from "../../../components/ui/StatusBadge";
import { obterContasPagarGrupo } from "../../../services/gruposEmpresas";
import { formatMoneyBRL } from "../../../utils/formatters";
import GrupoAnaliseFiltros from "./GrupoAnaliseFiltros";

const SITUACOES = [
  ["abertas", "Em aberto"],
  ["vencidas", "Vencidas"],
  ["pagas", "Pagas"],
  ["todas", "Todas"],
];

function formatarData(valor) {
  if (!valor) return "-";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(`${valor}T12:00:00`));
}

export default function GrupoContasPagarTab({ empresas, grupoId, periodoDias }) {
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [empresaId, setEmpresaId] = useState("");
  const [situacao, setSituacao] = useState("abertas");
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(
        await obterContasPagarGrupo(grupoId, {
          periodo_dias: periodoDias,
          situacao,
          busca: buscaAplicada || undefined,
          empresa_id: empresaId || undefined,
        }),
      );
    } catch (error) {
      toast.error(
        error?.response?.data?.detail || "Não foi possível carregar o contas a pagar do grupo.",
      );
    } finally {
      setCarregando(false);
    }
  }, [buscaAplicada, empresaId, grupoId, periodoDias, situacao]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const resumo = dados?.resumo || {};
  const itens = dados?.itens || [];

  return (
    <div className="space-y-4">
      <Panel
        title="Situação dos títulos"
        subtitle="A consulta é somente leitura; pagamentos continuam sendo feitos dentro de cada empresa."
      >
        <div className="flex flex-wrap gap-2">
          {SITUACOES.map(([valor, label]) => (
            <ActionButton
              key={valor}
              intent={situacao === valor ? "info" : "neutral"}
              tone={situacao === valor ? "solid" : "soft"}
              disabled={carregando}
              onClick={() => setSituacao(valor)}
            >
              {label}
            </ActionButton>
          ))}
        </div>
      </Panel>

      <GrupoAnaliseFiltros
        busca={busca}
        carregando={carregando}
        empresaId={empresaId}
        empresas={empresas}
        onBuscaChange={setBusca}
        onEmpresaChange={setEmpresaId}
        onSubmit={(event) => {
          event.preventDefault();
          setBuscaAplicada(busca.trim());
        }}
        placeholder="Buscar descrição, fornecedor, documento ou NF"
      />

      <MetricGrid>
        <MetricCard
          icon={<FiTrendingDown />}
          intent="blue"
          size="compact"
          label="Títulos encontrados"
          value={resumo.contas || 0}
        />
        <MetricCard
          icon={<FiDollarSign />}
          intent="red"
          size="compact"
          label="Saldo em aberto"
          value={formatMoneyBRL(resumo.saldo_aberto || 0)}
        />
        <MetricCard
          icon={<FiAlertTriangle />}
          intent="amber"
          size="compact"
          label="Saldo vencido"
          value={formatMoneyBRL(resumo.saldo_vencido || 0)}
        />
        <MetricCard
          icon={<FiCheckCircle />}
          intent="emerald"
          size="compact"
          label="Valor já pago"
          value={formatMoneyBRL(resumo.valor_pago || 0)}
        />
      </MetricGrid>

      {itens.length === 0 && !carregando ? (
        <EmptyState
          icon={FiTrendingDown}
          title="Nenhuma conta encontrada"
          description="Altere a situação, a empresa ou os termos da pesquisa."
        />
      ) : (
        <Panel
          title="Contas a pagar mescladas"
          subtitle="Cada título mantém a identificação da empresa responsável."
          padding="none"
        >
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                <tr>
                  <th className="px-4 py-3">Vencimento</th>
                  <th className="px-4 py-3">Empresa</th>
                  <th className="px-4 py-3">Descrição / fornecedor</th>
                  <th className="px-4 py-3">Documento</th>
                  <th className="px-4 py-3">Situação</th>
                  <th className="px-4 py-3 text-right">Valor</th>
                  <th className="px-4 py-3 text-right">Saldo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {itens.map((item) => (
                  <tr key={`${item.empresa_id}-${item.conta_id}`}>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span
                        className={item.vencida ? "font-semibold text-red-700" : "text-slate-700"}
                      >
                        {formatarData(item.data_vencimento)}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                      {item.empresa_nome}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800 dark:text-slate-100">
                        {item.descricao}
                      </div>
                      <div className="text-xs text-slate-500">{item.fornecedor_nome}</div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">
                      {item.documento || "-"}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.vencida ? "vencida" : item.status} />
                    </td>
                    <td className="px-4 py-3 text-right">{formatMoneyBRL(item.valor_final)}</td>
                    <td className="px-4 py-3 text-right font-semibold text-red-700 dark:text-red-300">
                      {formatMoneyBRL(item.saldo_aberto)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}
