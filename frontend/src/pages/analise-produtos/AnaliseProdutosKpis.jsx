import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { formatMoneyBRL, formatPercent } from "../../utils/formatters";

const quantidade = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });

function Variacao({ valor }) {
  if (valor == null) {
    return <span className="text-xs font-medium text-slate-500">Sem base anterior</span>;
  }
  const positiva = valor > 0;
  const negativa = valor < 0;
  const Icone = positiva ? ArrowUpRight : negativa ? ArrowDownRight : Minus;
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-semibold ${
        positiva ? "text-emerald-700" : negativa ? "text-rose-700" : "text-slate-500"
      }`}
    >
      <Icone className="h-3.5 w-3.5" aria-hidden="true" />
      {formatPercent(Math.abs(valor))} vs. período anterior
    </span>
  );
}

function Kpi({ titulo, valor, variacao, detalhe }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-600">{titulo}</p>
      <p className="mt-2 text-2xl font-bold tracking-tight text-slate-950">{valor}</p>
      {variacao !== undefined && (
        <div className="mt-2">
          <Variacao valor={variacao} />
        </div>
      )}
      {detalhe && <p className="mt-2 text-xs text-slate-500">{detalhe}</p>}
    </div>
  );
}

export default function AnaliseProdutosKpis({ resumo }) {
  const variacoes = resumo.variacoes || {};
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <Kpi
        titulo="Faturamento em produtos"
        valor={formatMoneyBRL(resumo.faturamento)}
        variacao={variacoes.faturamento}
      />
      <Kpi
        titulo="Quantidade vendida"
        valor={quantidade.format(Number(resumo.quantidade || 0))}
        variacao={variacoes.quantidade}
      />
      <Kpi
        titulo="Produtos com venda"
        valor={quantidade.format(Number(resumo.produtos_vendidos || 0))}
        variacao={variacoes.produtos_vendidos}
      />
      <Kpi
        titulo="Lucro estimado"
        valor={formatMoneyBRL(resumo.lucro_estimado)}
        variacao={variacoes.lucro_estimado}
        detalhe="Receita menos o custo atual cadastrado."
      />
      <Kpi
        titulo="Margem estimada"
        valor={formatPercent(resumo.margem_estimada_pct)}
        detalhe={`${quantidade.format(Number(resumo.vendas || 0))} vendas no período`}
      />
    </div>
  );
}
