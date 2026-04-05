import CampanhasSorteioCard from "./CampanhasSorteioCard";
import CampanhasSorteioResultadoBanner from "./CampanhasSorteioResultadoBanner";

export default function CampanhasSorteiosTab({
  loadingSorteios,
  sorteios,
  sorteioResultado,
  setSorteioResultado,
  setErroCriarSorteio,
  setModalSorteio,
  inscrevendo,
  inscreverSorteio,
  executandoSorteio,
  executarSorteio,
  cancelarSorteio,
  abrirCodigosOffline,
  rankLabels,
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Sorteios</h2>
          <p className="text-sm text-gray-500">
            Crie sorteios exclusivos por nivel de ranking. O resultado e
            auditavel via seed UUID.
          </p>
        </div>
        <button
          onClick={() => {
            setErroCriarSorteio("");
            setModalSorteio(true);
          }}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
        >
          + Novo Sorteio
        </button>
      </div>

      <CampanhasSorteioResultadoBanner
        sorteioResultado={sorteioResultado}
        onFechar={() => setSorteioResultado(null)}
      />

      {loadingSorteios ? (
        <div className="p-8 text-center text-gray-400">
          Carregando sorteios...
        </div>
      ) : sorteios.length === 0 ? (
        <div className="bg-white rounded-xl border shadow-sm p-8 text-center text-gray-400">
          <p className="text-3xl mb-2">S</p>
          <p>Nenhum sorteio criado ainda.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sorteios.map((sorteio) => (
            <CampanhasSorteioCard
              key={sorteio.id}
              sorteio={sorteio}
              rankLabels={rankLabels}
              inscrevendo={inscrevendo}
              onInscrever={inscreverSorteio}
              executandoSorteio={executandoSorteio}
              onExecutar={executarSorteio}
              onCancelar={cancelarSorteio}
              onAbrirCodigosOffline={abrirCodigosOffline}
            />
          ))}
        </div>
      )}
    </div>
  );
}
