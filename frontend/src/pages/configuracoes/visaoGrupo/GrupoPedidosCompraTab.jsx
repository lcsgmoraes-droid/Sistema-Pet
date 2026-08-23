import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiClock, FiCpu, FiDollarSign, FiShoppingCart } from "react-icons/fi";
import EmptyState from "../../../components/ui/EmptyState";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import StatusBadge from "../../../components/ui/StatusBadge";
import { obterPedidosCompraGrupo } from "../../../services/gruposEmpresas";
import { formatMoneyBRL } from "../../../utils/formatters";
import GrupoAnaliseFiltros from "./GrupoAnaliseFiltros";

const STATUS_INTENT = {
  rascunho: "neutral",
  enviado: "info",
  confirmado: "info",
  recebido_parcial: "warning",
  recebido_total: "success",
  cancelado: "danger",
};

function formatarData(valor) {
  if (!valor) return "-";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(valor));
}

function rotuloStatus(status) {
  return String(status || "-")
    .replaceAll("_", " ")
    .replace(/^./, (letra) => letra.toUpperCase());
}

export default function GrupoPedidosCompraTab({ empresas, grupoId, periodoDias }) {
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [empresaId, setEmpresaId] = useState("");
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(
        await obterPedidosCompraGrupo(grupoId, {
          periodo_dias: periodoDias,
          busca: buscaAplicada || undefined,
          empresa_id: empresaId || undefined,
        }),
      );
    } catch (error) {
      toast.error(
        error?.response?.data?.detail || "Não foi possível carregar os pedidos de compra.",
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
        placeholder="Buscar número, fornecedor ou observação"
      />

      <MetricGrid>
        <MetricCard
          icon={<FiShoppingCart />}
          intent="blue"
          size="compact"
          label="Pedidos de compra"
          value={resumo.pedidos || 0}
        />
        <MetricCard
          icon={<FiClock />}
          intent="amber"
          size="compact"
          label="Em andamento"
          value={resumo.em_andamento || 0}
        />
        <MetricCard
          icon={<FiCpu />}
          intent="violet"
          size="compact"
          label="Sugeridos pela IA"
          value={resumo.sugeridos_ia || 0}
        />
        <MetricCard
          icon={<FiDollarSign />}
          intent="emerald"
          size="compact"
          label="Valor dos pedidos"
          value={formatMoneyBRL(resumo.valor_total || 0)}
        />
      </MetricGrid>

      {itens.length === 0 && !carregando ? (
        <EmptyState
          icon={FiShoppingCart}
          title="Nenhum pedido de compra encontrado"
          description="Altere o período, a empresa ou a pesquisa para ampliar a consulta."
        />
      ) : (
        <Panel
          title="Pedidos de compra do grupo"
          subtitle="A tela reúne pedidos manuais e inteligentes, preservando a empresa e o fornecedor de origem."
          padding="none"
        >
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                <tr>
                  <th className="px-4 py-3">Data</th>
                  <th className="px-4 py-3">Empresa</th>
                  <th className="px-4 py-3">Pedido / fornecedor</th>
                  <th className="px-4 py-3">Situação</th>
                  <th className="px-4 py-3 text-right">Itens</th>
                  <th className="px-4 py-3 text-right">Recebimento</th>
                  <th className="px-4 py-3 text-right">Valor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {itens.map((item) => (
                  <tr key={`${item.empresa_id}-${item.pedido_id}`}>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-600 dark:text-slate-300">
                      {formatarData(item.data_pedido)}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                      {item.empresa_nome}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-mono text-xs font-semibold text-slate-800 dark:text-slate-100">
                        {item.numero_pedido}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">{item.fornecedor_nome}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <StatusBadge intent={STATUS_INTENT[item.status] || "neutral"}>
                          {rotuloStatus(item.status)}
                        </StatusBadge>
                        {item.sugestao_ia ? <StatusBadge intent="purple">IA</StatusBadge> : null}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">{item.quantidade_itens}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="font-medium">{item.quantidade_recebida}</div>
                      <div className="text-xs text-slate-500">
                        de {item.quantidade_pedida} unidades
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-900 dark:text-slate-100">
                      {formatMoneyBRL(item.valor_final)}
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
