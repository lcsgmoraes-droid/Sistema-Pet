import CustomerIdentity from "../../components/ui/CustomerIdentity";
import { formatarDataCurta } from "./lembretesFormatters";

export default function LembretesCampanhasAlertas({ alertasCampanhas }) {
  if (!alertasCampanhas) return null;

  const cards = montarCardsCampanha(alertasCampanhas);

  return (
    <div
      style={{
        marginBottom: "20px",
        borderRadius: "12px",
        border: "1px solid #e5e7eb",
        overflow: "hidden",
        background: "#fff",
      }}
    >
      <div
        style={{
          background: "#fef3c7",
          padding: "12px 20px",
          borderBottom: "1px solid #fde68a",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <span style={{ fontSize: "16px" }}>!</span>
        <span style={{ fontWeight: "600", color: "#92400e", fontSize: "14px" }}>
          Alertas de Campanhas
        </span>
      </div>
      <div style={{ padding: "12px 20px", display: "flex", flexWrap: "wrap", gap: "12px" }}>
        {cards.map((card) => (
          <CampanhaAlertaCard key={card.id} card={card} />
        ))}
      </div>
    </div>
  );
}

function montarCardsCampanha(alertas) {
  const cards = [];
  const proximos = alertas.proximos_eventos || {};
  const alertasInternos = alertas.alertas || {};

  if (proximos.total_aniversarios_amanha > 0) {
    cards.push({
      id: "aniversarios-amanha",
      background: "#fdf2f8",
      border: "#f9a8d4",
      color: "#9d174d",
      count: proximos.total_aniversarios_amanha,
      title: "Aniversario(s) amanha",
      items: (proximos.aniversarios_amanha || []).slice(0, 3).map((a) => a.nome),
      more: proximos.total_aniversarios_amanha > 3 ? proximos.total_aniversarios_amanha - 3 : 0,
    });
  }

  if (alertas.total_aniversarios > 0) {
    cards.push({
      id: "aniversarios-hoje",
      background: "#fff7ed",
      border: "#fed7aa",
      color: "#c2410c",
      count: alertas.total_aniversarios,
      title: "Aniversario(s) hoje",
      items: (alertas.aniversarios_hoje || []).slice(0, 3).map((a) => a.nome),
    });
  }

  if (alertasInternos.inativos_30d > 0) {
    cards.push({
      id: "inativos-30d",
      background: "#fff7ed",
      border: "#fdba74",
      color: "#c2410c",
      count: alertasInternos.inativos_30d,
      title: "Inativos ha +30 dias",
    });
  }

  if (alertasInternos.novos_inativos_hoje > 0) {
    cards.push({
      id: "novos-inativos",
      background: "#fef2f2",
      border: "#fca5a5",
      color: "#b91c1c",
      count: alertasInternos.novos_inativos_hoje,
      title: "Atingiram 30 dias de inatividade hoje",
    });
  }

  if (alertasInternos.total_sorteios_pendentes > 0) {
    cards.push({
      id: "sorteios-pendentes",
      background: "#fefce8",
      border: "#fde047",
      color: "#a16207",
      count: alertasInternos.total_sorteios_pendentes,
      title: "Sorteio(s) pendente(s)",
    });
  }

  if (proximos.sorteios_esta_semana?.length > 0) {
    cards.push({
      id: "sorteios-semana",
      background: "#fffbeb",
      border: "#fcd34d",
      color: "#92400e",
      count: proximos.sorteios_esta_semana.length,
      title: "Sorteio(s) esta semana",
      items: proximos.sorteios_esta_semana
        .slice(0, 3)
        .map((s) => `${s.name}${s.draw_date ? ` - ${formatarDataCurta(s.draw_date)}` : ""}`),
    });
  }

  if (alertasInternos.total_brindes_pendentes > 0) {
    cards.push({
      id: "brindes-pendentes",
      background: "#fff7ed",
      border: "#fdba74",
      color: "#c2410c",
      count: alertasInternos.total_brindes_pendentes,
      title: "Brinde(s) pendente(s) de retirada",
      brindeItems: (alertasInternos.brindes_pendentes || []).slice(0, 2),
      more:
        alertasInternos.total_brindes_pendentes > 2
          ? alertasInternos.total_brindes_pendentes - 2
          : 0,
    });
  }

  if (proximos.dias_ate_fim_mes != null) {
    const urgente = proximos.dias_ate_fim_mes <= 3;
    cards.push({
      id: "fim-mes",
      background: urgente ? "#fefce8" : "#f0fdf4",
      border: urgente ? "#fde047" : "#86efac",
      color: urgente ? "#a16207" : "#15803d",
      count: proximos.dias_ate_fim_mes,
      title:
        proximos.dias_ate_fim_mes === 0
          ? "Ultimo dia - calcule o destaque!"
          : "dia(s) p/ Destaque Mensal",
    });
  }

  return cards;
}

function CampanhaAlertaCard({ card }) {
  return (
    <div
      style={{
        background: card.background,
        border: `1px solid ${card.border}`,
        borderRadius: "8px",
        padding: "10px 14px",
        minWidth: "160px",
      }}
    >
      <p style={{ fontWeight: "700", color: card.color, fontSize: "22px", margin: 0 }}>
        {card.count}
      </p>
      <p style={{ color: "#6b7280", fontSize: "12px", margin: "2px 0 6px" }}>{card.title}</p>
      {card.items?.map((item, index) => (
        <p
          key={`${card.id}-${index}`}
          style={{ fontSize: "12px", color: "#374151", margin: "1px 0" }}
        >
          {item}
        </p>
      ))}
      {card.brindeItems?.map((brinde, index) => (
        <p
          key={`${card.id}-brinde-${index}`}
          style={{ fontSize: "12px", color: "#374151", margin: "1px 0" }}
        >
          <CustomerIdentity
            code={brinde.customer_id}
            fallback="Cliente nao informado"
            layout="inline"
            name={brinde.nome_cliente}
            nameClassName="font-medium text-slate-700"
            record={brinde}
          />
          {brinde.retirar_ate ? ` - ate ${formatarDataCurta(brinde.retirar_ate)}` : ""}
        </p>
      ))}
      {card.more > 0 && (
        <p style={{ fontSize: "11px", color: "#9ca3af", margin: "2px 0 0" }}>+{card.more} mais</p>
      )}
    </div>
  );
}
