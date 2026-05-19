import CurvaEvolucaoInternacao from "./CurvaEvolucaoInternacao";
import EvolucoesResumoInternacao from "./EvolucoesResumoInternacao";
import ProcedimentosResumoInternacao from "./ProcedimentosResumoInternacao";
import OrcamentoMvpPanel from "../orcamentos/OrcamentoMvpPanel";

export default function InternacaoDetalhe({ internacao, evolucoes, procedimentos, procedimentosCatalogo }) {
  return (
    <div className="border-t border-gray-100 bg-gray-50 px-5 py-4">
      <CurvaEvolucaoInternacao evolucoes={evolucoes} />

      {(internacao.observacoes_alta || internacao.observacoes) && (
        <div className="mb-3 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
          <p className="text-xs font-semibold text-green-700 mb-1">Observação da alta</p>
          <p className="text-xs text-green-800">{internacao.observacoes_alta || internacao.observacoes}</p>
        </div>
      )}

      <EvolucoesResumoInternacao evolucoes={evolucoes} />
      <ProcedimentosResumoInternacao procedimentos={procedimentos} />
      <div className="mt-4">
        <OrcamentoMvpPanel
          contexto={{
            internacaoId: internacao.id,
            consultaId: internacao.consulta_id ?? null,
            petId: internacao.pet_id ?? null,
            clienteId: internacao.tutor_id ?? null,
            veterinarioId: internacao.veterinario_id ?? null,
            previsaoDias: 1,
          }}
          procedimentosCatalogo={procedimentosCatalogo}
          titulo="Orçamento da internação"
        />
      </div>
    </div>
  );
}
