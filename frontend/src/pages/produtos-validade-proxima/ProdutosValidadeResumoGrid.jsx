import { formatarMoeda } from "../../api/produtos";
import { formatarQuantidade } from "./produtosValidadeProximaFormatters";

export default function ProdutosValidadeResumoGrid({ controller }) {
  const { dados, loteMaisUrgente, prazoMaisCurto } = controller;
  const totais = dados.totais || {};

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-4 xl:grid-cols-6">
      <ResumoCard
        titulo="Lotes no filtro"
        valor={totais.total_lotes}
        descricao={`${totais.total_produtos || 0} produto(s) com risco comercial no recorte atual.`}
        destaque="blue"
      />
      <ResumoCard
        titulo="Vencidos"
        valor={totais.lotes_vencidos}
        descricao="Itens que ja precisam de tratativa imediata."
        destaque="rose"
      />
      <ResumoCard
        titulo="Na campanha"
        valor={totais.lotes_em_campanha || 0}
        descricao={`Excluidos manualmente: ${totais.lotes_excluidos_campanha || 0}.`}
        destaque="emerald"
      />
      <ResumoCard
        titulo="Custo em risco"
        valor={formatarMoeda(totais.valor_custo_em_risco)}
        descricao={`Quantidade total: ${formatarQuantidade(totais.total_quantidade)}`}
        destaque="violet"
      />
      <ResumoCard
        titulo="Prazo mais curto"
        valor={prazoMaisCurto ? prazoMaisCurto.destaque : "--"}
        descricao={
          prazoMaisCurto && loteMaisUrgente
            ? `${prazoMaisCurto.apoio} - ${loteMaisUrgente.nome}`
            : "Sem lotes no recorte atual."
        }
        destaque={
          loteMaisUrgente?.dias_para_vencer < 0
            ? "rose"
            : loteMaisUrgente?.dias_para_vencer <= 30
              ? "amber"
              : "blue"
        }
        valorClassName="text-3xl"
        descricaoClassName="line-clamp-2"
      />
      <ResumoCard
        titulo="Potencial de venda"
        valor={formatarMoeda(totais.valor_venda_em_risco)}
        descricao={`Ate 60 dias: ${totais.lotes_ate_60_dias || 0} lote(s) no radar.`}
        destaque="emerald"
      />
    </div>
  );
}

function ResumoCard({
  titulo,
  valor,
  descricao,
  destaque = "blue",
  valorClassName = "",
  descricaoClassName = "",
}) {
  const estilos = {
    blue: "border-blue-100 bg-blue-50 text-blue-900",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-900",
    amber: "border-amber-100 bg-amber-50 text-amber-900",
    rose: "border-rose-100 bg-rose-50 text-rose-900",
    violet: "border-violet-100 bg-violet-50 text-violet-900",
  };

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${estilos[destaque] || estilos.blue}`}>
      <p className="text-sm font-medium opacity-80">{titulo}</p>
      <p className={`mt-2 text-2xl font-bold ${valorClassName}`}>{valor}</p>
      <p className={`mt-2 text-xs opacity-75 ${descricaoClassName}`}>{descricao}</p>
    </div>
  );
}
