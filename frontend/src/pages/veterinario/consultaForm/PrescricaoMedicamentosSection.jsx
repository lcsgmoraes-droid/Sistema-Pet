import { Calculator, X } from "lucide-react";
import { css } from "./consultaFormUtils";

export default function PrescricaoMedicamentosSection({
  modoSomenteLeitura,
  form,
  medicamentosCatalogo,
  adicionarItem,
  removerItem,
  setItem,
  selecionarMedicamentoNoItem,
  recalcularDoseItem,
}) {
  return (
    <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3 disabled:opacity-100">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-gray-700">Prescrição (opcional)</h2>
        <button
          onClick={adicionarItem}
          className="text-xs text-blue-600 hover:text-blue-800 underline"
        >
          + Adicionar medicamento
        </button>
      </div>
      {form.prescricao_itens.length === 0 && (
        <p className="text-xs text-gray-400">Nenhum medicamento adicionado ainda.</p>
      )}
      {form.prescricao_itens.map((item, idx) => (
        <div key={idx} className="border border-gray-100 rounded-lg p-3 space-y-2 relative">
          <button
            onClick={() => removerItem(idx)}
            className="absolute top-2 right-2 text-gray-300 hover:text-red-400"
          >
            <X size={14} />
          </button>
          <div className="grid grid-cols-2 gap-2">
            <select
              value={item.medicamento_id || ""}
              onChange={(e) => selecionarMedicamentoNoItem(idx, e.target.value)}
              className={css.select}
            >
              <option value="">Selecionar do catálogo...</option>
              {medicamentosCatalogo.map((m) => (
                <option key={m.id} value={m.id}>{m.nome}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => recalcularDoseItem(idx)}
              className="inline-flex items-center justify-center gap-2 px-3 py-2 text-xs border border-blue-200 text-blue-700 rounded-lg hover:bg-blue-50"
            >
              <Calculator size={14} />
              Calcular dose pelo peso
            </button>
          </div>
          {(item.dose_minima_mg_kg || item.dose_maxima_mg_kg) && (
            <p className="text-[11px] text-gray-500">
              Referência do catálogo: {item.dose_minima_mg_kg || "-"}
              {item.dose_maxima_mg_kg ? ` a ${item.dose_maxima_mg_kg}` : ""} mg/kg
            </p>
          )}
          <div className="grid grid-cols-2 gap-2">
            <input type="text" placeholder="Nome do medicamento" value={item.nome} onChange={(e) => setItem(idx, "nome", e.target.value)} className={css.input} />
            <input type="text" placeholder="Princípio ativo" value={item.principio_ativo} onChange={(e) => setItem(idx, "principio_ativo", e.target.value)} className={css.input} />
            <input type="text" placeholder="Dose (ex: 10 mg/kg)" value={item.dose_mg} onChange={(e) => setItem(idx, "dose_mg", e.target.value)} className={css.input} />
            <select value={item.via} onChange={(e) => setItem(idx, "via", e.target.value)} className={css.select}>
              <option value="oral">Oral</option>
              <option value="iv">IV</option><option value="im">IM</option>
              <option value="sc">SC</option><option value="topico">Tópico</option>
              <option value="oftalmico">Oftálmico</option>
            </select>
            <input type="text" placeholder="Frequência (ex: a cada 12h)" value={item.frequencia} onChange={(e) => setItem(idx, "frequencia", e.target.value)} className={css.input} />
            <input type="number" placeholder="Duração (dias)" value={item.duracao_dias} onChange={(e) => setItem(idx, "duracao_dias", e.target.value)} className={css.input} />
          </div>
          <input type="text" placeholder="Instruções ao tutor" value={item.instrucoes} onChange={(e) => setItem(idx, "instrucoes", e.target.value)} className={css.input} />
        </div>
      ))}
    </fieldset>
  );
}
