import { DollarSign, ShoppingCart, Target, TrendingUp } from "lucide-react";
import { formatMoneyBRL, formatPercent } from "../../utils/formatters";
import DetalhamentoMargemPanel from "./DetalhamentoMargemPanel";
import PontoEquilibrioMetricCard from "./PontoEquilibrioMetricCard";

export default function PontoEquilibrioResumoTab({
  dados,
  margemPeriodoPercentual,
  margemUsadaPercentual,
  onAbrirDetalhes,
}) {
  return (
    <>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <PontoEquilibrioMetricCard
          icon={Target}
          title="Ponto minimo"
          value={
            dados.ponto_equilibrio == null ? "Indefinido" : formatMoneyBRL(dados.ponto_equilibrio)
          }
          subtitle="Faturamento necessario para empatar"
          tone={dados.status === "atingido" ? "green" : "amber"}
        />
        <PontoEquilibrioMetricCard
          icon={DollarSign}
          title="Faturamento"
          value={formatMoneyBRL(dados.faturamento)}
          subtitle={`${dados.quantidade_vendas || 0} venda(s) no periodo`}
          tone="blue"
        />
        <PontoEquilibrioMetricCard
          icon={TrendingUp}
          title="Margem usada"
          value={formatPercent(margemUsadaPercentual)}
          subtitle={`${dados.margem_usada_label || "Fonte atual"} | Periodo: ${formatPercent(margemPeriodoPercentual)}`}
          tone={margemUsadaPercentual > 0 ? "green" : "red"}
        />
        <PontoEquilibrioMetricCard
          icon={ShoppingCart}
          title="Vendas necessarias"
          value={dados.vendas_necessarias == null ? "-" : String(dados.vendas_necessarias)}
          subtitle={`Ticket medio ${formatMoneyBRL(dados.ticket_medio_usado ?? dados.ticket_medio)}`}
          tone="slate"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold text-slate-900">Composicao da margem</h2>
          <div className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between gap-4">
              <span className="text-slate-600">Receita produtos/servicos</span>
              <span className="font-semibold text-emerald-700">
                {formatMoneyBRL(dados.receita_produtos_servicos ?? dados.faturamento)}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-600">Receita entrega</span>
              <span className="font-semibold text-emerald-700">
                {formatMoneyBRL(dados.receita_entrega || 0)}
              </span>
            </div>
            <div className="flex justify-between gap-4 border-t border-slate-100 pt-3">
              <span className="text-slate-600">Faturamento total</span>
              <span className="font-semibold text-slate-900">
                {formatMoneyBRL(dados.faturamento)}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-600">CMV estimado</span>
              <span className="font-semibold text-red-700">
                - {formatMoneyBRL(dados.cmv_estimado)}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-600">Custos de venda</span>
              <span className="font-semibold text-red-700">
                - {formatMoneyBRL(dados.despesas_variaveis)}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 rounded-md bg-slate-50 p-3 text-xs text-slate-600">
              <span>Descontos: {formatMoneyBRL(dados.descontos || 0)}</span>
              <span>Campanhas: {formatMoneyBRL(dados.beneficios_campanhas || 0)}</span>
              <span>Cartao: {formatMoneyBRL(dados.taxas_cartao || 0)}</span>
              <span>
                Entrega:{" "}
                {formatMoneyBRL(
                  (dados.repasse_entrega || 0) + (dados.custo_operacional_entrega || 0),
                )}
              </span>
              <span>Comissoes: {formatMoneyBRL(dados.comissoes || 0)}</span>
              <span>Custo gerencial: {formatMoneyBRL(dados.custo_fiscal || 0)}</span>
              <span>Outros variaveis: {formatMoneyBRL(dados.outros_variaveis || 0)}</span>
            </div>
            <div className="border-t border-slate-100 pt-3">
              <div className="flex justify-between gap-4">
                <span className="font-semibold text-slate-700">
                  Margem de contribuicao do periodo
                </span>
                <span className="font-bold text-emerald-700">
                  {formatMoneyBRL(dados.margem_contribuicao)}
                </span>
              </div>
              <div className="mt-2 flex justify-between gap-4 text-xs text-slate-500">
                <span>Margem usada no calculo</span>
                <span>
                  {formatPercent(margemUsadaPercentual)} (
                  {dados.margem_usada_label || "Fonte atual"})
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold text-slate-900">Base de custos fixos</h2>
          <div className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between gap-4">
              <span className="text-slate-600">Custos fixos classificados</span>
              <span className="font-semibold text-slate-900">
                {formatMoneyBRL(dados.despesas_fixas)}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-600">Custos variaveis totais</span>
              <span className="font-semibold text-slate-900">
                {formatMoneyBRL(dados.custos_variaveis)}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-600">Sem classificacao para PE</span>
              <span className="font-semibold text-amber-700">
                {formatMoneyBRL(dados.despesas_sem_classificacao)}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-600">Fora do PE: compras de estoque</span>
              <span className="font-semibold text-slate-700">
                {formatMoneyBRL(dados.despesas_estoque_excluidas || 0)}
              </span>
            </div>
            <p className="rounded-md bg-slate-50 p-3 text-xs text-slate-600">
              A base usa contas a pagar para os valores reais, DRE para a classificacao gerencial e
              provisoes, e complementa a folha pelos funcionarios ativos quando ainda nao houver
              lancamento suficiente. Compras de produto para revenda ficam separadas porque o custo
              entra pelo CMV quando o produto e vendido.
            </p>
          </div>
        </div>
      </div>

      <DetalhamentoMargemPanel dados={dados} onAbrirDetalhes={onAbrirDetalhes} />
    </>
  );
}
