export default function CalculadoraDoseResultado({ resultado }) {
  return (
    <div className="mt-5 rounded-xl border border-cyan-100 bg-cyan-50 p-4">
      {!resultado ? (
        <p className="text-sm text-cyan-700">
          Informe peso e dose para calcular. Se quiser, você ainda pode abrir a calculadora completa depois.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-cyan-600">mg por dose</p>
            <p className="text-lg font-semibold text-cyan-900">{resultado.mgPorDose.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-cyan-600">doses / dia</p>
            <p className="text-lg font-semibold text-cyan-900">
              {resultado.dosesPorDia ? resultado.dosesPorDia.toFixed(2) : "-"}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-cyan-600">mg / dia</p>
            <p className="text-lg font-semibold text-cyan-900">
              {resultado.mgDia ? resultado.mgDia.toFixed(2) : "-"}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-cyan-600">mg tratamento</p>
            <p className="text-lg font-semibold text-cyan-900">
              {resultado.mgTratamento ? resultado.mgTratamento.toFixed(2) : "-"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
