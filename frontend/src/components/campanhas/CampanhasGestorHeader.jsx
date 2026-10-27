import BuscaPessoa from "../v2/BuscaPessoa/BuscaPessoa";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import InputCombobox from "../v2/InputCombobox/InputCombobox";

export default function CampanhasGestorHeader({
  gestorModo,
  setGestorModo,
  gestorSearch,
  setGestorSearch,
  buscarClientesGestor,
  setGestorSugestoes,
  gestorBuscando,
  gestorSugestoes,
  selecionarClienteGestor,
  gestorCampanhaTipo,
  setGestorCampanhaTipo,
  carregarClientesPorCampanha,
  gestorCampanhaCarregando,
}) {
  return (
    <div className="bg-white rounded-xl border shadow-sm p-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div>
          <h2 className="font-semibold text-gray-800">Gestor de Beneficios</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {gestorModo === "cliente"
              ? "Busque um cliente para gerenciar seus beneficios."
              : "Selecione um tipo e veja todos os clientes participantes."}
          </p>
        </div>

        <div className="flex gap-2 shrink-0">
          <BotaoInteracao
            onClick={() => setGestorModo("cliente")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              gestorModo === "cliente"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            Por Cliente
          </BotaoInteracao>
          <BotaoInteracao
            onClick={() => setGestorModo("campanha")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              gestorModo === "campanha"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            Por Campanha
          </BotaoInteracao>
        </div>
      </div>

      {gestorModo === "cliente" && (
        <div className="relative max-w-md">
          <BuscaPessoa
            value={gestorSearch}
            onChange={(valor) => {
              setGestorSearch(valor);
              buscarClientesGestor(valor);
            }}
            onKeyDown={(evento) => {
              if (evento.key === "Escape") setGestorSugestoes([]);
            }}
            onSelect={selecionarClienteGestor}
            suggestions={gestorSugestoes}
            showSuggestions={gestorSugestoes.length > 0}
            loading={gestorBuscando}
            placeholder="Codigo, nome, CPF ou telefone..."
          />
        </div>
      )}

      {gestorModo === "campanha" && (
        <div className="flex gap-3 flex-wrap items-center">
          <InputCombobox
            value={gestorCampanhaTipo}
            onChange={setGestorCampanhaTipo}
            label="Tipo de campanha"
            permitirLimpar={false}
            opcoes={[
              { value: "carimbos", label: "Cartao Fidelidade" },
              { value: "cashback", label: "Cashback (saldo positivo)" },
              { value: "cupons", label: "Cupons Ativos" },
              { value: "ranking", label: "Ranking (mes atual)" },
            ]}
          />
          <BotaoInteracao
            onClick={() => carregarClientesPorCampanha(gestorCampanhaTipo)}
            disabled={gestorCampanhaCarregando}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {gestorCampanhaCarregando ? "Carregando..." : "Buscar Clientes"}
          </BotaoInteracao>
        </div>
      )}
    </div>
  );
}
