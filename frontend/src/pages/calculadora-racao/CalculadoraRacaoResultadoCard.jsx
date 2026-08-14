import { CalendarDays, Gauge, Package, Scale, ShoppingBag, WalletCards } from "lucide-react";
import { formatMoneyBRL } from "../../utils/formatters";

const classificacoes = {
  super_premium: "Super Premium",
  premium: "Premium",
  especial: "Especial",
  standard: "Standard",
};

const formatarNumero = (valor, casas = 1) =>
  Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: casas,
  });

export default function CalculadoraRacaoResultadoCard({ resultado }) {
  if (!resultado) return null;

  const metricas = [
    {
      icon: CalendarDays,
      label: "Duração estimada",
      value: `${formatarNumero(resultado.duracao_dias)} dias`,
      hint: `aprox. ${formatarNumero(resultado.duracao_meses)} meses`,
      tone: "teal",
    },
    {
      icon: Scale,
      label: "Consumo diário",
      value: `${formatarNumero(resultado.quantidade_diaria_g)} g`,
      hint: "por dia para este pet",
      tone: "blue",
    },
    {
      icon: Package,
      label: "Custo por quilo",
      value: formatMoneyBRL(resultado.custo_por_kg),
      hint: "valor proporcional",
      tone: "orange",
    },
    {
      icon: Gauge,
      label: "Custo por dia",
      value: formatMoneyBRL(resultado.custo_por_dia),
      hint: "investimento diário",
      tone: "violet",
    },
    {
      icon: WalletCards,
      label: "Custo mensal estimado",
      value: formatMoneyBRL(resultado.custo_mensal),
      hint: "projeção para 30 dias",
      tone: "green",
      featured: true,
    },
  ];

  return (
    <article className="result-card">
      <header className="result-card__heading">
        <div className="result-card__eyebrow">
          <ShoppingBag size={16} aria-hidden="true" />
          Planejamento alimentar
        </div>
        <h2>Resultado do cálculo</h2>
        <p>Veja quanto a embalagem rende e qual é o investimento para este pet.</p>
      </header>

      <div className="result-product">
        <div>
          <span className="result-product__label">Ração selecionada</span>
          <h3>{resultado.produto_nome}</h3>
        </div>
        {resultado.classificacao && (
          <span className={`badge badge-${resultado.classificacao}`}>
            {classificacoes[resultado.classificacao] || resultado.classificacao.replace("_", " ")}
          </span>
        )}
      </div>

      <div className="result-overview">
        <div className="result-overview__item">
          <span className="result-overview__icon result-overview__icon--teal">
            <Package size={22} aria-hidden="true" />
          </span>
          <div>
            <span className="result-overview__label">Peso da embalagem</span>
            <strong>{formatarNumero(resultado.peso_embalagem_kg, 3)} kg</strong>
          </div>
        </div>
        <div className="result-overview__item">
          <span className="result-overview__icon result-overview__icon--orange">
            <WalletCards size={22} aria-hidden="true" />
          </span>
          <div>
            <span className="result-overview__label">Preço da embalagem</span>
            <strong>{formatMoneyBRL(resultado.preco)}</strong>
          </div>
        </div>
      </div>

      <div className="result-details">
        {metricas.map(({ featured, hint, icon: Icon, label, tone, value }) => (
          <div
            className={`result-metric result-metric--${tone}${featured ? " result-metric--featured" : ""}`}
            key={label}
          >
            <span className="result-metric__icon">
              <Icon size={21} aria-hidden="true" />
            </span>
            <div>
              <span className="result-metric__label">{label}</span>
              <strong>{value}</strong>
              <small>{hint}</small>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}
