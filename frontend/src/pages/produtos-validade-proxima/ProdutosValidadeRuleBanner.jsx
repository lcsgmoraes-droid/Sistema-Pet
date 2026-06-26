export default function ProdutosValidadeRuleBanner({ controller, embedded }) {
  return (
    <div className="rounded-lg border border-emerald-100 bg-gradient-to-r from-emerald-50 via-white to-amber-50 p-4 shadow-sm md:p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Regra automatica por validade</h2>
          <p className="mt-1 text-sm text-gray-600">
            60 dias para planejar giro, 30 dias para acelerar oferta e 7 dias para acao forte.
            Quando a campanha estiver ativa, o lote entra sozinho com limite de quantidade do
            proprio lote.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {embedded && (
            <button
              type="button"
              onClick={controller.exportarCsv}
              disabled={controller.exportando}
              className="rounded-full bg-white px-3 py-1.5 text-sm font-medium text-blue-700 ring-1 ring-blue-200 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {controller.exportando ? "Exportando..." : "Exportar CSV"}
            </button>
          )}
          {embedded && (
            <button
              type="button"
              onClick={controller.irParaCampanhas}
              className="rounded-full bg-white px-3 py-1.5 text-sm font-medium text-emerald-700 ring-1 ring-emerald-200 transition-colors hover:bg-emerald-50"
            >
              Abrir campanhas
            </button>
          )}
          {controller.quickDays.map((dia) => (
            <button
              key={dia}
              type="button"
              onClick={() => controller.atualizarFiltro("dias", dia)}
              className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                Number(controller.filtrosForm.dias) === dia
                  ? "bg-emerald-600 text-white"
                  : "bg-white text-emerald-700 ring-1 ring-emerald-200 hover:bg-emerald-50"
              }`}
            >
              Ate {dia} dias
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
