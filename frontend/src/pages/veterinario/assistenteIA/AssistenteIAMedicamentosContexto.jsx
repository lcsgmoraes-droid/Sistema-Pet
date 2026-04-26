import { Calculator, Pill } from "lucide-react";
import { assistenteIaCss } from "./assistenteIAUtils";

function CampoMedicamento({ id, label, value, onChange, placeholder }) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium text-gray-600 mb-1">
        {label}
      </label>
      <div className="relative">
        <Pill size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={`${assistenteIaCss.input} pl-9`}
          placeholder={placeholder}
        />
      </div>
    </div>
  );
}

export default function AssistenteIAMedicamentosContexto({
  med1,
  med2,
  pesoKg,
  setMed1,
  setMed2,
  setPesoKg,
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div>
        <label htmlFor="vet-ia-peso" className="block text-xs font-medium text-gray-600 mb-1">
          Peso (kg) para cálculo de dose
        </label>
        <div className="relative">
          <Calculator size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            id="vet-ia-peso"
            value={pesoKg}
            onChange={(event) => setPesoKg(event.target.value)}
            className={`${assistenteIaCss.input} pl-9`}
            placeholder="Ex: 12,5"
          />
        </div>
      </div>

      <CampoMedicamento
        id="vet-ia-med1"
        label="Medicamento 1 (opcional)"
        value={med1}
        onChange={setMed1}
        placeholder="Ex: amoxicilina"
      />
      <CampoMedicamento
        id="vet-ia-med2"
        label="Medicamento 2 (opcional)"
        value={med2}
        onChange={setMed2}
        placeholder="Ex: prednisolona"
      />
    </div>
  );
}
