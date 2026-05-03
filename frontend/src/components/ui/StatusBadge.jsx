const INTENTS = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  info: "border-blue-200 bg-blue-50 text-blue-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-red-200 bg-red-50 text-red-700",
  neutral: "border-slate-200 bg-slate-50 text-slate-700",
  purple: "border-violet-200 bg-violet-50 text-violet-700",
};

const STATUS_MAP = {
  ativa: ["Ativa", "success"],
  ativo: ["Ativo", "success"],
  aberto: ["Aberto", "warning"],
  aberta: ["Aberta", "warning"],
  baixa_parcial: ["Parcial", "info"],
  cancelada: ["Cancelada", "danger"],
  cancelado: ["Cancelado", "danger"],
  entregue: ["Entregue", "success"],
  finalizada: ["Pago", "success"],
  inativo: ["Inativo", "neutral"],
  parcial: ["Parcial", "info"],
  pago: ["Pago", "success"],
  pago_nf: ["Pago NF", "success"],
  pendente: ["Pendente", "warning"],
  recebida: ["Recebida", "success"],
  recebido: ["Recebido", "success"],
  vencida: ["Vencida", "danger"],
  vencido: ["Vencido", "danger"],
};

const SIZES = {
  xs: "px-1.5 py-0.5 text-[10px]",
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
};

export default function StatusBadge({
  children,
  className = "",
  intent,
  size = "sm",
  status,
  title,
}) {
  const mapped = status ? STATUS_MAP[String(status).toLowerCase()] : null;
  const label = children || mapped?.[0] || status || "-";
  const resolvedIntent = intent || mapped?.[1] || "neutral";

  return (
    <span
      className={[
        "inline-flex items-center rounded-full border font-medium leading-none",
        SIZES[size] || SIZES.sm,
        INTENTS[resolvedIntent] || INTENTS.neutral,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      title={title}
    >
      {label}
    </span>
  );
}
