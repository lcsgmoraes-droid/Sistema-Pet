import { FiBell } from "react-icons/fi";
import CustomerIdentity from "../../components/ui/CustomerIdentity";
import { formatarDataCurta } from "./lembretesFormatters";

export default function LembretesCampanhasAlertas({ alertasCampanhas }) {
  if (!alertasCampanhas) return null;

  const cards = montarCardsCampanha(alertasCampanhas);

  return (
    <section className="mb-5 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <header className="flex items-center gap-3 border-b border-amber-200 bg-amber-50 px-5 py-4 dark:border-amber-500/30 dark:bg-amber-500/10">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white text-amber-700 shadow-sm ring-1 ring-amber-200 dark:bg-slate-900 dark:text-amber-300 dark:ring-amber-500/30">
          <FiBell aria-hidden="true" />
        </span>
        <div>
          <h2 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
            Alertas de Campanhas
          </h2>
          <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-400">
            Datas e oportunidades que precisam de atencao.
          </p>
        </div>
      </header>
      <div className="flex flex-wrap gap-3 p-4 sm:p-5">
        {cards.map((card) => (
          <CampanhaAlertaCard key={card.id} card={card} />
        ))}
      </div>
    </section>
  );
}

function montarCardsCampanha(alertas) {
  const cards = [];
  const proximos = alertas.proximos_eventos || {};
  const alertasInternos = alertas.alertas || {};

  if (proximos.total_aniversarios_amanha > 0) {
    cards.push({
      id: "aniversarios-amanha",
      count: proximos.total_aniversarios_amanha,
      title: "Aniversario(s) amanha",
      items: (proximos.aniversarios_amanha || []).slice(0, 3).map((a) => a.nome),
      more: proximos.total_aniversarios_amanha > 3 ? proximos.total_aniversarios_amanha - 3 : 0,
      tone: "pink",
    });
  }
  if (alertas.total_aniversarios > 0) {
    cards.push({
      id: "aniversarios-hoje",
      count: alertas.total_aniversarios,
      title: "Aniversario(s) hoje",
      items: (alertas.aniversarios_hoje || []).slice(0, 3).map((a) => a.nome),
      tone: "amber",
    });
  }
  if (alertasInternos.inativos_30d > 0) {
    cards.push({
      id: "inativos-30d",
      count: alertasInternos.inativos_30d,
      title: "Inativos ha +30 dias",
      tone: "amber",
    });
  }
  if (alertasInternos.novos_inativos_hoje > 0) {
    cards.push({
      id: "novos-inativos",
      count: alertasInternos.novos_inativos_hoje,
      title: "Atingiram 30 dias de inatividade hoje",
      tone: "red",
    });
  }
  if (alertasInternos.total_sorteios_pendentes > 0) {
    cards.push({
      id: "sorteios-pendentes",
      count: alertasInternos.total_sorteios_pendentes,
      title: "Sorteio(s) pendente(s)",
      tone: "yellow",
    });
  }
  if (proximos.sorteios_esta_semana?.length > 0) {
    cards.push({
      id: "sorteios-semana",
      count: proximos.sorteios_esta_semana.length,
      title: "Sorteio(s) esta semana",
      items: proximos.sorteios_esta_semana
        .slice(0, 3)
        .map((s) => `${s.name}${s.draw_date ? ` - ${formatarDataCurta(s.draw_date)}` : ""}`),
      tone: "amber",
    });
  }
  if (alertasInternos.total_brindes_pendentes > 0) {
    cards.push({
      id: "brindes-pendentes",
      count: alertasInternos.total_brindes_pendentes,
      title: "Brinde(s) pendente(s) de retirada",
      brindeItems: (alertasInternos.brindes_pendentes || []).slice(0, 2),
      more:
        alertasInternos.total_brindes_pendentes > 2
          ? alertasInternos.total_brindes_pendentes - 2
          : 0,
      tone: "amber",
    });
  }
  if (proximos.dias_ate_fim_mes != null) {
    const urgente = proximos.dias_ate_fim_mes <= 3;
    cards.push({
      id: "fim-mes",
      count: proximos.dias_ate_fim_mes,
      title:
        proximos.dias_ate_fim_mes === 0
          ? "Ultimo dia - calcule o destaque!"
          : "dia(s) p/ Destaque Mensal",
      tone: urgente ? "yellow" : "green",
    });
  }
  return cards;
}

const TONES = {
  amber:
    "border-orange-200 bg-orange-50 text-orange-800 dark:border-orange-500/30 dark:bg-orange-500/10 dark:text-orange-200",
  green:
    "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200",
  pink: "border-pink-200 bg-pink-50 text-pink-800 dark:border-pink-500/30 dark:bg-pink-500/10 dark:text-pink-200",
  red: "border-red-200 bg-red-50 text-red-800 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200",
  yellow:
    "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200",
};

function CampanhaAlertaCard({ card }) {
  return (
    <article
      className={`min-w-40 flex-1 rounded-xl border px-4 py-3 sm:max-w-xs ${TONES[card.tone] || TONES.amber}`}
    >
      <p className="m-0 text-2xl font-bold">{card.count}</p>
      <p className="mt-0.5 text-xs font-medium opacity-80">{card.title}</p>
      {card.items?.map((item, index) => (
        <p key={`${card.id}-${index}`} className="mt-1 text-xs text-slate-700 dark:text-slate-300">
          {item}
        </p>
      ))}
      {card.brindeItems?.map((brinde, index) => (
        <p
          key={`${card.id}-brinde-${index}`}
          className="mt-1 text-xs text-slate-700 dark:text-slate-300"
        >
          <CustomerIdentity
            code={brinde.customer_id}
            fallback="Cliente nao informado"
            layout="inline"
            name={brinde.nome_cliente}
            nameClassName="font-medium"
            record={brinde}
          />
          {brinde.retirar_ate ? ` - ate ${formatarDataCurta(brinde.retirar_ate)}` : ""}
        </p>
      ))}
      {card.more > 0 && <p className="mt-1 text-xs opacity-70">+{card.more} mais</p>}
    </article>
  );
}
