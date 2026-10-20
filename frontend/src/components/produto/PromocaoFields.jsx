export default function PromocaoFields({
  title = "Promocao",
  description,
  priceControl,
  startLabel = "Inicio",
  endLabel = "Fim",
  startValue,
  endValue,
  onStartChange,
  onEndChange,
}) {
  const normalizarDateTimeLocal = (value) => (value ? String(value).slice(0, 16) : "");

  return (
    <div className="rounded-lg border border-amber-100 bg-amber-50/40 p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-amber-900">{title}</h3>
        {description && <p className="mt-1 text-xs text-amber-700">{description}</p>}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {priceControl}

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">{startLabel}</label>
          <input
            type="datetime-local"
            value={normalizarDateTimeLocal(startValue)}
            onChange={(e) => onStartChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-amber-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">{endLabel}</label>
          <input
            type="datetime-local"
            value={normalizarDateTimeLocal(endValue)}
            onChange={(e) => onEndChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-amber-500"
          />
        </div>
      </div>
    </div>
  );
}
