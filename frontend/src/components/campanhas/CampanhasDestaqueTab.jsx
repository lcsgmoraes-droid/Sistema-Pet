import CampanhasDestaqueDesempateInfo from "./CampanhasDestaqueDesempateInfo";
import CampanhasDestaqueIntroCard from "./CampanhasDestaqueIntroCard";
import CampanhasDestaqueResultadoBanner from "./CampanhasDestaqueResultadoBanner";
import CampanhasDestaqueTop5Section from "./CampanhasDestaqueTop5Section";
import CampanhasDestaqueVencedorCard from "./CampanhasDestaqueVencedorCard";

export default function CampanhasDestaqueTab({
  loadingDestaque,
  destaque,
  carregarDestaque,
  premiosPorVencedor,
  setPremiosPorVencedor,
  vencedoresSelecionados,
  setVencedoresSelecionados,
  createDefaultPremio,
  destaqueResultado,
  setDestaqueResultado,
  enviarDestaque,
  enviandoDestaque,
}) {
  if (loadingDestaque) {
    return (
      <div className="space-y-4">
        <CampanhasDestaqueIntroCard />
        <div className="p-8 text-center text-gray-400">Carregando destaque...</div>
      </div>
    );
  }

  if (!destaque) {
    return (
      <div className="space-y-4">
        <CampanhasDestaqueIntroCard />
        <div className="p-8 text-center">
          <button
            onClick={carregarDestaque}
            className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600"
          >
            Calcular Vencedores
          </button>
        </div>
      </div>
    );
  }

  const possuiVencedores = Object.keys(destaque.vencedores).length > 0;

  return (
    <div className="space-y-4">
      <CampanhasDestaqueIntroCard />

      <div className="bg-white rounded-xl border shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold text-gray-900">
              Vencedores - {destaque.periodo}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {destaque.total_clientes_ativos} clientes ativos no periodo
            </p>
          </div>
          <button
            onClick={carregarDestaque}
            className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-200"
          >
            Recalcular
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
          {Object.entries(destaque.vencedores).map(([categoria, info]) => {
            const premio =
              premiosPorVencedor[categoria] || createDefaultPremio();
            const setPremio = (update) =>
              setPremiosPorVencedor((prev) => ({
                ...prev,
                [categoria]: {
                  ...(prev[categoria] || createDefaultPremio()),
                  ...update,
                },
              }));
            const selecionado = vencedoresSelecionados[categoria] !== false;

            return (
              <CampanhasDestaqueVencedorCard
                key={categoria}
                categoria={categoria}
                info={info}
                premio={premio}
                selecionado={selecionado}
                onToggleSelecionado={(checked) =>
                  setVencedoresSelecionados((prev) => ({
                    ...prev,
                    [categoria]: checked,
                  }))
                }
                onPremioChange={setPremio}
              />
            );
          })}

          {!possuiVencedores && (
            <div className="col-span-2 p-6 text-center text-gray-400">
              Nenhum vencedor identificado para o periodo.
            </div>
          )}
        </div>

        <CampanhasDestaqueDesempateInfo desempateInfo={destaque.desempate_info} />

        {destaqueResultado ? (
          <CampanhasDestaqueResultadoBanner
            destaqueResultado={destaqueResultado}
            onReset={() => setDestaqueResultado(null)}
          />
        ) : (
          possuiVencedores && (
            <button
              onClick={enviarDestaque}
              disabled={
                enviandoDestaque ||
                Object.values(vencedoresSelecionados).every((valor) => !valor)
              }
              className="w-full py-3 bg-amber-500 text-white rounded-xl font-semibold hover:bg-amber-600 disabled:opacity-50 transition-colors"
            >
              {enviandoDestaque
                ? "Enviando premios..."
                : "Enviar Premios aos Vencedores"}
            </button>
          )
        )}
      </div>

      <CampanhasDestaqueTop5Section destaque={destaque} />
    </div>
  );
}
