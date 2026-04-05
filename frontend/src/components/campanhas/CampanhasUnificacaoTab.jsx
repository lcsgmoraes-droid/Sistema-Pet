import CampanhasUnificacaoResultadoBanner from "./CampanhasUnificacaoResultadoBanner";
import CampanhasUnificacaoSugestoesTable from "./CampanhasUnificacaoSugestoesTable";

export default function CampanhasUnificacaoTab({
  carregarSugestoes,
  loadingSugestoes,
  resultadoMerge,
  desfazerMerge,
  sugestoes,
  confirmarMerge,
  confirmandoMerge,
}) {
  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border shadow-sm p-5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="font-semibold text-gray-800">
              Unificacao cross-canal por CPF/Telefone
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Clientes que parecem ser a mesma pessoa aparecem aqui para
              unificacao manual.
            </p>
          </div>
          <button
            onClick={carregarSugestoes}
            disabled={loadingSugestoes}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loadingSugestoes ? "Buscando..." : "Buscar duplicatas"}
          </button>
        </div>

        <CampanhasUnificacaoResultadoBanner
          resultadoMerge={resultadoMerge}
          onDesfazer={desfazerMerge}
        />

        {loadingSugestoes && (
          <div className="p-8 text-center text-gray-400">
            Buscando duplicatas...
          </div>
        )}

        {!loadingSugestoes && sugestoes.length === 0 && (
          <div className="p-8 text-center text-gray-400">
            <p className="text-3xl mb-2">OK</p>
            <p>
              Nenhuma duplicata encontrada. Clique em "Buscar Duplicatas" para
              verificar.
            </p>
          </div>
        )}

        <CampanhasUnificacaoSugestoesTable
          sugestoes={sugestoes}
          confirmandoMerge={confirmandoMerge}
          onConfirmarMerge={confirmarMerge}
        />
      </div>
    </div>
  );
}
