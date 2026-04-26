import AgendaProcedimentoCard from "./AgendaProcedimentoCard";

export default function AgendaProcedimentosLista({
  agendaCarregando,
  agendaOrdenada,
  internacaoPorId,
  salvando,
  onReabrirProcedimento,
  onAbrirModalFeito,
  onRemoverProcedimentoAgenda,
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <p className="text-sm font-semibold text-gray-700 mb-3">Horarios de hoje e proximos</p>
      {agendaCarregando ? (
        <p className="text-xs text-gray-400">Carregando agenda de procedimentos...</p>
      ) : agendaOrdenada.length === 0 ? (
        <p className="text-xs text-gray-400">Nenhum procedimento agendado ainda.</p>
      ) : (
        <div className="space-y-2">
          {agendaOrdenada.map((item) => (
            <AgendaProcedimentoCard
              key={item.id}
              item={item}
              baiaExibicao={obterBaiaExibicao(item, internacaoPorId)}
              salvando={salvando}
              onReabrirProcedimento={onReabrirProcedimento}
              onAbrirModalFeito={onAbrirModalFeito}
              onRemoverProcedimentoAgenda={onRemoverProcedimentoAgenda}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function obterBaiaExibicao(item, internacaoPorId) {
  const internacaoAtual = internacaoPorId.get(String(item.internacao_id));
  return (internacaoAtual?.box || item.baia || "").trim() || "Sem baia";
}
