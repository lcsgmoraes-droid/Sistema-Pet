import ProcedimentoInsumoRow from "./ProcedimentoInsumoRow";
import ProcedimentoResumoMargem from "./ProcedimentoResumoMargem";

export default function ProcedimentoInsumosSection({
  adicionarInsumo,
  atualizarInsumo,
  form,
  produtos,
  removerInsumo,
  resumoMargem,
}) {
  return (
    <div className="space-y-3 rounded-xl border border-gray-200 bg-gray-50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-800">Insumos com baixa automatica</p>
          <p className="text-xs text-gray-500">
            Escolha os itens do estoque que saem automaticamente quando o procedimento for usado.
          </p>
        </div>
        <button
          type="button"
          onClick={adicionarInsumo}
          className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium hover:bg-gray-100"
        >
          + Adicionar insumo
        </button>
      </div>

      {form.insumos.length === 0 ? (
        <p className="text-xs text-gray-500">Nenhum insumo vinculado.</p>
      ) : (
        form.insumos.map((item, index) => (
          <ProcedimentoInsumoRow
            key={`insumo_${index}`}
            index={index}
            item={item}
            produtos={produtos}
            removerInsumo={removerInsumo}
            atualizarInsumo={atualizarInsumo}
          />
        ))
      )}

      <ProcedimentoResumoMargem resumoMargem={resumoMargem} />
    </div>
  );
}
