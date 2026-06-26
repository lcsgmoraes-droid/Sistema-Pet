import { formatMoneyBRL, formatPercent } from "../../utils/formatters";

export function TooltipMoeda({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-md border border-slate-200 bg-white p-2 text-xs shadow-sm">
      <p className="font-semibold text-slate-900">{label}</p>
      {payload.map((item) => (
        <p key={item.name} className="text-slate-600">
          {item.name}: {formatMoneyBRL(item.value)}
        </p>
      ))}
    </div>
  );
}

export function TooltipPercentual({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-md border border-slate-200 bg-white p-2 text-xs shadow-sm">
      <p className="font-semibold text-slate-900">{label}</p>
      {payload.map((item) => (
        <p key={item.name} className="text-slate-600">
          {item.name}: {formatPercent(item.value)}
        </p>
      ))}
    </div>
  );
}
