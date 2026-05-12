const CHANNEL_LABELS = {
  amazon: "Amazon",
  app: "App",
  ecommerce: "E-commerce",
  "e-commerce": "E-commerce",
  full: "FULL (geral)",
  mercado_livre: "Mercado Livre",
  pdv: "PDV",
  shopee: "Shopee",
};

const CHANNEL_CLASSES = {
  amazon: "border-emerald-200 bg-emerald-50 text-emerald-700",
  app: "border-emerald-200 bg-emerald-50 text-emerald-700",
  ecommerce: "border-emerald-200 bg-emerald-50 text-emerald-700",
  "e-commerce": "border-emerald-200 bg-emerald-50 text-emerald-700",
  full: "border-slate-200 bg-slate-50 text-slate-700",
  mercado_livre: "border-yellow-200 bg-yellow-50 text-yellow-800",
  pdv: "border-blue-200 bg-blue-50 text-blue-700",
  shopee: "border-orange-200 bg-orange-50 text-orange-700",
  default: "border-slate-200 bg-slate-50 text-slate-700",
};

export function normalizeChannel(channel) {
  if (!channel) return null;
  if (typeof channel === "string") {
    return { key: channel.toLowerCase(), label: CHANNEL_LABELS[channel.toLowerCase()] || channel };
  }

  const key = String(channel.key || channel.value || channel.id || "").toLowerCase();
  return {
    key,
    label: channel.label || CHANNEL_LABELS[key] || channel.nome || key,
  };
}

export function getChannelConfig(channel, fallbackLabel) {
  const normalized = normalizeChannel(channel);
  const key = normalized?.key || "";
  return {
    key,
    label: fallbackLabel || normalized?.label || "Canal nao informado",
    className: CHANNEL_CLASSES[key] || CHANNEL_CLASSES.default,
  };
}

export function ChannelBadge({ channel, className = "", label, title }) {
  const config = getChannelConfig(channel, label);

  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        config.className,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      title={title || `Canal: ${config.label}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {config.label}
    </span>
  );
}

export default function ChannelBadges({
  channels = [],
  className = "",
  empty = "-",
  layout = "column",
}) {
  const normalized = channels.map(normalizeChannel).filter((channel) => channel?.key);

  if (normalized.length === 0) {
    return empty ? <span className="text-xs text-gray-400">{empty}</span> : null;
  }

  return (
    <div
      className={[
        "flex gap-1.5",
        layout === "row" ? "flex-row flex-wrap" : "flex-col items-center",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {normalized.map((channel) => (
        <ChannelBadge key={channel.key} channel={channel} title={`Ativo no ${channel.label}`} />
      ))}
    </div>
  );
}
