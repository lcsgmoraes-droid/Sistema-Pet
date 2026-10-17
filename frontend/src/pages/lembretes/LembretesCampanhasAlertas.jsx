import { Bell } from "lucide-react";
import CustomerIdentity from "../../components/ui/CustomerIdentity";
import CartaoIndicador from "../../components/v2/CartaoIndicador/CartaoIndicador";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import { formatarDataCurta } from "./lembretesFormatters";

export default function LembretesCampanhasAlertas({ alertasCampanhas }) {
  const cards = alertasCampanhas ? montarCardsCampanha(alertasCampanhas) : [];
  if (cards.length === 0) {
    return (
      <EstadoVazio icone={Bell} titulo="Nenhum alerta de campanha disponível neste momento." />
    );
  }

  return (
    <section className="grid gap-3">
      <div>
        <h3 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
          Alertas de campanhas
        </h3>
        <p className="v2-texto-ajuda mt-0.5">Datas e oportunidades que precisam de atenção.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
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

  if (alertasInternos.inativos_30d > 0) {
    cards.push({
      id: "inativos-30d",
      count: alertasInternos.inativos_30d,
      title: "Inativos há +30 dias",
      tom: "atencao",
    });
  }
  if (alertasInternos.novos_inativos_hoje > 0) {
    cards.push({
      id: "novos-inativos",
      count: alertasInternos.novos_inativos_hoje,
      title: "Atingiram 30 dias de inatividade hoje",
      tom: "perigo",
    });
  }
  if (alertasInternos.total_sorteios_pendentes > 0) {
    cards.push({
      id: "sorteios-pendentes",
      count: alertasInternos.total_sorteios_pendentes,
      title: "Sorteio(s) pendente(s)",
      tom: "atencao",
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
      tom: "atencao",
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
      tom: "atencao",
    });
  }
  if (proximos.dias_ate_fim_mes != null) {
    const urgente = proximos.dias_ate_fim_mes <= 3;
    cards.push({
      id: "fim-mes",
      count: proximos.dias_ate_fim_mes,
      title:
        proximos.dias_ate_fim_mes === 0
          ? "Último dia - calcule o destaque!"
          : "dia(s) p/ Destaque Mensal",
      tom: urgente ? "atencao" : "sucesso",
    });
  }
  return cards;
}

function CampanhaAlertaCard({ card }) {
  return (
    <CartaoIndicador icone={Bell} titulo={card.title} tom={card.tom}>
      <p className="text-2xl font-bold text-slate-950 dark:text-white">{card.count}</p>
      {card.items?.map((item, index) => (
        <p key={`${card.id}-${index}`} className="v2-texto-ajuda mt-1">
          {item}
        </p>
      ))}
      {card.brindeItems?.map((brinde, index) => (
        <p key={`${card.id}-brinde-${index}`} className="v2-texto-ajuda mt-1">
          <CustomerIdentity
            code={brinde.customer_id}
            fallback="Cliente não informado"
            layout="inline"
            name={brinde.nome_cliente}
            nameClassName="font-medium"
            record={brinde}
          />
          {brinde.retirar_ate ? ` - até ${formatarDataCurta(brinde.retirar_ate)}` : ""}
        </p>
      ))}
      {card.more > 0 && <p className="v2-texto-ajuda mt-1">+{card.more} mais</p>}
    </CartaoIndicador>
  );
}
