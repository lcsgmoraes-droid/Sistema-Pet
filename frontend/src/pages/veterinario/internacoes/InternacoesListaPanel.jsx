import InternacaoCard from "./InternacaoCard";

export default function InternacoesListaPanel({
  aba,
  internacoesOrdenadas,
  expandida,
  evolucoes,
  procedimentosInternacao,
  onAbrirDetalhe,
  onAbrirInsumoRapido,
  onAbrirEvolucao,
  onAbrirAlta,
  onAbrirFichaPet,
  onAbrirHistoricoPet,
}) {
  return (
    <div className="space-y-3">
      {aba === "ativas" && (
        <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
          <p className="text-sm font-semibold text-gray-700">Ficha de internados</p>
          <p className="text-xs text-gray-500">
            Evoluções + procedimentos concluídos ficam centralizados por internação.
          </p>
        </div>
      )}

      {internacoesOrdenadas.map((internacao) => (
        <InternacaoCard
          key={internacao.id}
          internacao={internacao}
          aberta={expandida === internacao.id}
          evolucoes={evolucoes[internacao.id] ?? []}
          procedimentos={procedimentosInternacao[internacao.id] ?? []}
          onAbrirDetalhe={onAbrirDetalhe}
          onAbrirInsumoRapido={onAbrirInsumoRapido}
          onAbrirEvolucao={onAbrirEvolucao}
          onAbrirAlta={onAbrirAlta}
          onAbrirFichaPet={onAbrirFichaPet}
          onAbrirHistoricoPet={onAbrirHistoricoPet}
        />
      ))}
    </div>
  );
}
