import CampanhasRetencaoForm from "./CampanhasRetencaoForm";

export default function CampanhasRetencaoTab({
  retencaoEditando,
  salvandoRetencao,
  loadingRetencao,
  retencaoRegras,
  deletandoRetencao,
  onSalvarRetencao,
  onCancelarEdicao,
  onNovaRegra,
  onEditarRegra,
  onDeletarRegra,
}) {
  return (
    <div className="space-y-4">
      <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 flex items-start gap-3">
        <span className="text-2xl">♻️</span>
        <div>
          <p className="font-semibold text-orange-800">Retencao Dinamica</p>
          <p className="text-sm text-orange-700 mt-0.5">
            Cada regra detecta clientes que nao compraram ha X dias e envia
            automaticamente um cupom de incentivo. Voce pode ter multiplas
            reguas: 30 dias, 60 dias, 90 dias, cada uma com desconto e
            mensagem diferentes.
          </p>
        </div>
      </div>

      {retencaoEditando !== null && (
        <CampanhasRetencaoForm
          inicial={retencaoEditando}
          salvando={salvandoRetencao}
          onSalvar={onSalvarRetencao}
          onCancelar={onCancelarEdicao}
        />
      )}

      {retencaoEditando === null && (
        <button
          onClick={onNovaRegra}
          className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 text-sm font-medium"
        >
          <span>+</span> Nova Regra de Retencao
        </button>
      )}

      {loadingRetencao ? (
        <p className="text-gray-500 text-sm">Carregando...</p>
      ) : retencaoRegras.length === 0 ? (
        <div className="bg-white border rounded-xl p-8 text-center text-gray-500">
          <p className="text-3xl mb-2">🧭</p>
          <p className="font-medium">
            Nenhuma regra de retencao cadastrada ainda.
          </p>
          <p className="text-sm mt-1">
            Crie sua primeira regra para comecar a recuperar clientes inativos.
          </p>
        </div>
      ) : (
        <div className="grid gap-3">
          {retencaoRegras.map((regra) => (
            <div
              key={regra.id}
              className="bg-white border border-orange-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center gap-3"
            >
              <div className="flex-1">
                <p className="font-semibold text-gray-800">
                  {regra.name || "(sem nome)"}
                </p>
                <div className="flex flex-wrap gap-3 mt-1 text-sm text-gray-600">
                  <span>
                    🕒{" "}
                    <strong>{regra.params?.inactivity_days ?? "?"} dias</strong>{" "}
                    sem compra
                  </span>
                  <span>
                    🎟️ Cupom:{" "}
                    <strong>
                      {regra.params?.coupon_type === "percent"
                        ? `${regra.params.coupon_value}%`
                        : `R$ ${regra.params?.coupon_value}`}
                    </strong>
                  </span>
                  <span>
                    📅 Validade:{" "}
                    <strong>{regra.params?.coupon_valid_days ?? "?"} dias</strong>
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      regra.status === "active"
                        ? "bg-green-100 text-green-700"
                        : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {regra.status === "active" ? "Ativa" : "Pausada"}
                  </span>
                </div>
                {regra.params?.notification_message && (
                  <p className="text-xs text-gray-400 mt-1 italic">
                    "{regra.params.notification_message}"
                  </p>
                )}
              </div>

              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={() =>
                    onEditarRegra({
                      id: regra.id,
                      name: regra.name,
                      priority: regra.priority,
                      ...regra.params,
                    })
                  }
                  className="px-3 py-1.5 text-sm border border-orange-300 text-orange-700 rounded-lg hover:bg-orange-50"
                >
                  Editar
                </button>
                <button
                  onClick={() => onDeletarRegra(regra.id)}
                  disabled={deletandoRetencao === regra.id}
                  className="px-3 py-1.5 text-sm border border-red-200 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50"
                >
                  {deletandoRetencao === regra.id ? "..." : "Excluir"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
