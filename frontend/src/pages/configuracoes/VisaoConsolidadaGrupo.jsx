import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import {
  FiAlertTriangle,
  FiBarChart2,
  FiBox,
  FiChevronLeft,
  FiDollarSign,
  FiShoppingBag,
  FiTrendingDown,
  FiTrendingUp,
} from "react-icons/fi";
import ActionButton from "../../components/ui/ActionButton";
import LoadingState from "../../components/ui/LoadingState";
import MetricCard from "../../components/ui/MetricCard";
import MetricGrid from "../../components/ui/MetricGrid";
import ModuleTabs from "../../components/ui/ModuleTabs";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import StatusBadge from "../../components/ui/StatusBadge";
import { obterVisaoConsolidadaGrupo } from "../../services/gruposEmpresas";
import { formatMoneyBRL } from "../../utils/formatters";
import GrupoContasPagarTab from "./visaoGrupo/GrupoContasPagarTab";
import GrupoPedidosTab from "./visaoGrupo/GrupoPedidosTab";
import GrupoPedidosCompraTab from "./visaoGrupo/GrupoPedidosCompraTab";
import GrupoProdutosVendidosTab from "./visaoGrupo/GrupoProdutosVendidosTab";
import GrupoVinculosProdutosTab from "./visaoGrupo/GrupoVinculosProdutosTab";

const PERIODOS = [7, 30, 90, 180, 365];
const ABAS = [
  { id: "resumo", label: "Resumo" },
  { id: "pedidos", label: "Pedidos / vendas" },
  { id: "produtos", label: "Produtos vendidos" },
  { id: "pedidos-compra", label: "Pedidos de compra" },
  { id: "contas-pagar", label: "Contas a pagar" },
  { id: "vinculos", label: "Vínculos de produtos" },
];

function formatarQuantidade(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}

function formatarData(valor) {
  if (!valor) return "-";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(`${valor}T12:00:00`));
}

function mensagemErro(error) {
  return error?.response?.data?.detail || "Não foi possível carregar a visão consolidada.";
}

export default function VisaoConsolidadaGrupo() {
  const { grupoId } = useParams();
  const [aba, setAba] = useState("resumo");
  const [periodoDias, setPeriodoDias] = useState(30);
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      setDados(await obterVisaoConsolidadaGrupo(grupoId, periodoDias));
    } catch (error) {
      const detalhe = mensagemErro(error);
      setErro(detalhe);
      toast.error(detalhe);
    } finally {
      setCarregando(false);
    }
  }, [grupoId, periodoDias]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  if (carregando && !dados) {
    return <LoadingState label="Consolidando os resultados do grupo..." />;
  }

  const totais = dados?.totais;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <Link
        to="/configuracoes/grupos-empresas"
        className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
      >
        <FiChevronLeft aria-hidden="true" />
        Voltar para Grupos de empresas
      </Link>

      <PageHeader
        icon={FiBarChart2}
        title="Visão consolidada do grupo"
        subtitle={
          dados?.grupo?.nome
            ? `${dados.grupo.nome}: resultados, pedidos, produtos e financeiro em conjunto.`
            : "Analise as empresas participantes em conjunto."
        }
      />

      <ModuleTabs
        active={aba}
        ariaLabel="Análises consolidadas do grupo"
        onChange={setAba}
        tabs={ABAS}
      />

      {["resumo", "pedidos", "produtos", "pedidos-compra", "contas-pagar"].includes(aba) ? (
        <Panel
          title="Período das vendas"
          subtitle="O filtro atualiza vendas, pedidos, produtos e títulos pagos/todos. Estoque e saldos em aberto mostram a posição atual."
        >
          <div className="flex flex-wrap gap-2">
            {PERIODOS.map((dias) => (
              <ActionButton
                key={dias}
                intent={periodoDias === dias ? "info" : "neutral"}
                tone={periodoDias === dias ? "solid" : "soft"}
                disabled={carregando}
                onClick={() => setPeriodoDias(dias)}
              >
                {dias} dias
              </ActionButton>
            ))}
          </div>
          {dados?.periodo ? (
            <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
              Vendas de {formatarData(dados.periodo.data_inicio)} a{" "}
              {formatarData(dados.periodo.data_fim)}.
            </p>
          ) : null}
        </Panel>
      ) : null}

      {erro ? (
        <Panel className="border-red-200 bg-red-50 dark:border-red-500/30 dark:bg-red-500/10">
          <div className="flex items-start gap-3 text-red-800 dark:text-red-200">
            <FiAlertTriangle className="mt-0.5 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-semibold">Não foi possível atualizar os números.</p>
              <p className="mt-1 text-sm">{erro}</p>
              <ActionButton className="mt-3" intent="info" tone="soft" onClick={carregar}>
                Tentar novamente
              </ActionButton>
            </div>
          </div>
        </Panel>
      ) : null}

      {aba === "resumo" && totais ? (
        <>
          <MetricGrid>
            <MetricCard
              icon={<FiShoppingBag />}
              intent="blue"
              label="Vendas do grupo"
              value={formatMoneyBRL(totais.vendas.valor_total)}
              subtitle={`${totais.vendas.quantidade} vendas · ${totais.vendas.finalizadas} finalizadas`}
            />
            <MetricCard
              icon={<FiDollarSign />}
              intent="cyan"
              label="Ticket médio"
              value={formatMoneyBRL(totais.vendas.ticket_medio)}
              subtitle="Média das vendas não canceladas no período"
            />
            <MetricCard
              icon={<FiBox />}
              intent="violet"
              label="Estoque a custo"
              value={formatMoneyBRL(totais.estoque.valor_custo)}
              subtitle={`${totais.estoque.produtos_ativos} produtos ativos`}
            />
            <MetricCard
              icon={<FiBox />}
              intent="slate"
              label="Quantidade em estoque"
              value={formatarQuantidade(totais.estoque.quantidade)}
              subtitle="Somente saldos positivos controlados"
            />
          </MetricGrid>

          <Panel
            title="Posição financeira atual"
            subtitle="Saldos em aberto de todas as empresas do grupo, independentemente do período das vendas."
          >
            <MetricGrid>
              <MetricCard
                icon={<FiTrendingUp />}
                intent="emerald"
                size="compact"
                label="A receber"
                value={formatMoneyBRL(totais.financeiro.receber_aberto)}
              />
              <MetricCard
                icon={<FiAlertTriangle />}
                intent="amber"
                size="compact"
                label="A receber vencido"
                value={formatMoneyBRL(totais.financeiro.receber_vencido)}
              />
              <MetricCard
                icon={<FiTrendingDown />}
                intent="red"
                size="compact"
                label="A pagar"
                value={formatMoneyBRL(totais.financeiro.pagar_aberto)}
              />
              <MetricCard
                icon={<FiAlertTriangle />}
                intent="red"
                size="compact"
                label="A pagar vencido"
                value={formatMoneyBRL(totais.financeiro.pagar_vencido)}
              />
            </MetricGrid>
          </Panel>

          <Panel
            title="Espelho por empresa"
            subtitle="Cada linha resume uma empresa ativa do grupo, sem mostrar clientes ou lançamentos individuais."
            padding="none"
          >
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
                <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                  <tr>
                    <th className="px-4 py-3">Empresa</th>
                    <th className="px-4 py-3 text-right">Vendas</th>
                    <th className="px-4 py-3 text-right">Ticket médio</th>
                    <th className="px-4 py-3 text-right">Estoque a custo</th>
                    <th className="px-4 py-3 text-right">A receber</th>
                    <th className="px-4 py-3 text-right">A pagar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {dados.empresas.map((empresa) => (
                    <tr key={empresa.empresa_id} className="text-slate-700 dark:text-slate-200">
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold text-slate-900 dark:text-slate-100">
                            {empresa.empresa_nome}
                          </span>
                          {empresa.papel === "responsavel" ? (
                            <StatusBadge intent="purple">Responsável</StatusBadge>
                          ) : null}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="font-semibold">
                          {formatMoneyBRL(empresa.vendas.valor_total)}
                        </div>
                        <div className="text-xs text-slate-500">
                          {empresa.vendas.quantidade} vendas
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right font-medium">
                        {formatMoneyBRL(empresa.vendas.ticket_medio)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="font-medium">
                          {formatMoneyBRL(empresa.estoque.valor_custo)}
                        </div>
                        <div className="text-xs text-slate-500">
                          {formatarQuantidade(empresa.estoque.quantidade)} em estoque
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="font-medium text-emerald-700 dark:text-emerald-300">
                          {formatMoneyBRL(empresa.financeiro.receber_aberto)}
                        </div>
                        <div className="text-xs text-amber-700 dark:text-amber-300">
                          {formatMoneyBRL(empresa.financeiro.receber_vencido)} vencido
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="font-medium text-red-700 dark:text-red-300">
                          {formatMoneyBRL(empresa.financeiro.pagar_aberto)}
                        </div>
                        <div className="text-xs text-red-600 dark:text-red-300">
                          {formatMoneyBRL(empresa.financeiro.pagar_vencido)} vencido
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      ) : null}

      {aba === "pedidos" ? (
        <GrupoPedidosTab
          empresas={dados?.empresas || []}
          grupoId={grupoId}
          periodoDias={periodoDias}
        />
      ) : null}
      {aba === "produtos" ? (
        <GrupoProdutosVendidosTab grupoId={grupoId} periodoDias={periodoDias} />
      ) : null}
      {aba === "pedidos-compra" ? (
        <GrupoPedidosCompraTab
          empresas={dados?.empresas || []}
          grupoId={grupoId}
          periodoDias={periodoDias}
        />
      ) : null}
      {aba === "contas-pagar" ? (
        <GrupoContasPagarTab
          empresas={dados?.empresas || []}
          grupoId={grupoId}
          periodoDias={periodoDias}
        />
      ) : null}
      {aba === "vinculos" ? (
        <GrupoVinculosProdutosTab empresas={dados?.empresas || []} grupoId={grupoId} />
      ) : null}
    </div>
  );
}
