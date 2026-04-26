import { Pill, Scale } from "lucide-react";

export default function CalculadoraDosesResultado({
  calculo,
  form,
  medicamentoSelecionado,
  petSelecionado,
  tutorSelecionado,
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-slate-900 text-white p-5 space-y-4">
      <div className="flex items-center gap-2 text-slate-200">
        <Scale size={18} />
        <span className="text-sm">Resultado rapido</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <ResultadoCard label="Mg por dose" valor={calculo ? calculo.mgPorDose.toFixed(2) : "--"} />
        <ResultadoCard label="Doses por dia" valor={calculo?.dosesPorDia ? calculo.dosesPorDia.toFixed(2) : "--"} />
        <ResultadoCard label="Mg por dia" valor={calculo?.mgDia ? calculo.mgDia.toFixed(2) : "--"} />
        <ResultadoCard label="Mg no tratamento" valor={calculo?.mgTratamento ? calculo.mgTratamento.toFixed(2) : "--"} />
      </div>

      <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
        <div className="flex items-center gap-2 mb-2">
          <Pill size={16} />
          <span className="font-medium">Resumo</span>
        </div>
        <p>Tutor: {tutorSelecionado?.nome || petSelecionado?.cliente_nome || "nao selecionado"}</p>
        <p>Pet: {petSelecionado?.nome || "nao selecionado"}</p>
        <p>Medicamento: {medicamentoSelecionado?.nome || "nao selecionado"}</p>
        <p>Peso considerado: {form.peso_kg || "--"} kg</p>
        <p>Dose usada: {form.dose_mg_kg || "--"} mg/kg</p>
      </div>
    </div>
  );
}

function ResultadoCard({ label, valor }) {
  return (
    <div className="rounded-xl bg-white/10 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-300">{label}</p>
      <p className="mt-2 text-2xl font-bold">{valor}</p>
    </div>
  );
}
