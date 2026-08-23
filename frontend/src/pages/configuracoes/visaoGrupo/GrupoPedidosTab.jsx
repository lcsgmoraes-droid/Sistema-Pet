import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiDollarSign, FiPackage, FiShoppingBag } from "react-icons/fi";
import EmptyState from "../../../components/ui/EmptyState";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import StatusBadge from "../../../components/ui/StatusBadge";
import { obterPedidosGrupo } from "../../../services/gruposEmpresas";
import { formatMoneyBRL } from "../../../utils/formatters";
import GrupoAnaliseFiltros from "./GrupoAnaliseFiltros";

function formatarDataHora(valor) {
  if (!valor) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(valor));
}

export default function GrupoPedidosTab({ empresas, grupoId, periodoDias }) {
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [empresaId, setEmpresaId] = useState("");
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(
        await obterPedidosGrupo(grupoId, {
          periodo_dias: periodoDias,
          busca: buscaAplicada || undefined,
          empresa_id: empresaId || undefined,
        }),
      );
    } catch (error) {
      toast.error(
        error?.response?.data?.detail || "Não foi possível carregar os pedidos do grupo.",
      );
    } finally {
      setCarregando(false);
    }
  }, [buscaAplicada, empresaId, grupoId, periodoDias]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const resumo = dados?.resumo || {};
  const itens = dados?.itens || [];

  return (
    <div className="space-y-4">
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
        placeholder="Buscar por número do pedido, cliente ou canal"
      />

      <MetricGrid>
        <MetricCard
          icon={<FiShoppingBag />}
          intent="blue"
          size="compact"
          label="Pedidos / vendas"
          value={resumo.pedidos || 0}
        />
        <MetricCard
          icon={<FiPackage />}
          intent="violet"
          size="compact"
          label="Unidades vendidas"
          value={Number(resumo.unidades || 0).toLocaleString("pt-BR")}
        />
        <MetricCard
          icon={<FiDollarSign />}
          intent="emerald"
          size="compact"
          label="Valor vendido"
          value={formatMoneyBRL(resumo.valor_total || 0)}
          subtitle={`Ticket médio ${formatMoneyBRL(resumo.ticket_medio || 0)}`}
        />
      </MetricGrid>

      {itens.length === 0 && !carregando ? (
        <EmptyState
          icon={FiShoppingBag}
          title="Nenhum pedido encontrado"
          description="Altere o período, a empresa ou a pesquisa para ampliar a consulta."
        />
      ) : (
        <Panel
          title="Pedidos das empresas"
          subtitle="As vendas aparecem juntas, identificadas pela empresa de origem."
          padding="none"
        >
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                <tr>
                  <th className="px-4 py-3">Data</th>
                  <th className="px-4 py-3">Empresa</th>
                  <th className="px-4 py-3">Pedido</th>
                  <th className="px-4 py-3">Cliente</th>
                  <th className="px-4 py-3">Canal / status</th>
                  <th className="px-4 py-3 text-right">Itens</th>
                  <th className="px-4 py-3 text-right">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {itens.map((item) => (
                  <tr key={`${item.empresa_id}-${item.venda_id}`}>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-600 dark:text-slate-300">
                      {formatarDataHora(item.data_venda)}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                      {item.empresa_nome}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-200">
                      {item.numero_venda}
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                      {item.cliente_nome}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <StatusBadge intent="info">{item.canal.replaceAll("_", " ")}</StatusBadge>
                        <StatusBadge status={item.status} />
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="font-medium">{item.quantidade_itens}</div>
                      <div className="text-xs text-slate-500">{item.unidades} un.</div>
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-900 dark:text-slate-100">
                      {formatMoneyBRL(item.valor_total)}
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
