const CHANNEL_LABELS = {
  app: "App",
  ecommerce: "E-commerce",
  "e-commerce": "E-commerce",
  pdv: "PDV",
};

const CHANNEL_CLASSES = {
  app: "border-emerald-200 bg-emerald-50 text-emerald-700",
  ecommerce: "border-emerald-200 bg-emerald-50 text-emerald-700",
  "e-commerce": "border-emerald-200 bg-emerald-50 text-emerald-700",
  pdv: "border-blue-200 bg-blue-50 text-blue-700",
  default: "border-slate-200 bg-slate-50 text-slate-700",
};

function normalizeChannel(channel) {
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
        <span
          key={channel.key}
          className={[
            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
            CHANNEL_CLASSES[channel.key] || CHANNEL_CLASSES.default,
          ].join(" ")}
          title={`Ativo no ${channel.label}`}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
          {channel.label}
        </span>
      ))}
    </div>
  );
}
