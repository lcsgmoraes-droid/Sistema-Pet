import InputDataHora from "../v2/InputDataHora/InputDataHora";

export default function PromocaoFields({
  title = "Promocao",
  description,
  priceControl,
  startLabel = "Inicio",
  endLabel = "Fim",
  startId,
  endId,
  startValue,
  endValue,
  onStartChange,
  onEndChange,
}) {
  return (
    <div className="rounded-lg border border-amber-100 bg-amber-50/40 p-4 dark:border-amber-900 dark:bg-amber-950/20">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-amber-900 dark:text-amber-200">{title}</h3>
        {description && (
          <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">{description}</p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {priceControl}

        <InputDataHora
          id={startId}
          label={startLabel}
          value={startValue || ""}
          onChange={onStartChange}
        />
        <InputDataHora id={endId} label={endLabel} value={endValue || ""} onChange={onEndChange} />
      </div>
    </div>
  );
}
