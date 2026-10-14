import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";

export default function PetFormSaudeTab({ formData, setField }) {
  return (
    <div className="space-y-4">
      <InputTextoLongo
        id="pet-alergias"
        label="Alergias"
        help="Uma linha por item."
        value={formData.alergias}
        onChange={setField("alergias")}
        linhas={3}
        placeholder="Descreva alergias conhecidas (alimentares, medicamentos, etc)"
      />

      <InputTextoLongo
        id="pet-doencas-cronicas"
        label="Doenças Crônicas"
        help="Uma linha por condição registrada."
        value={formData.doencas_cronicas}
        onChange={setField("doencas_cronicas")}
        linhas={3}
        placeholder="Descreva doenças crônicas diagnosticadas"
      />

      <InputTextoLongo
        id="pet-medicamentos"
        label="Medicamentos Contínuos"
        help="Uma linha por medicamento, de preferência com dose."
        value={formData.medicamentos_continuos}
        onChange={setField("medicamentos_continuos")}
        linhas={3}
        placeholder="Liste medicamentos de uso contínuo com dosagem"
      />

      <InputTextoLongo
        id="pet-restricoes"
        label="Restrições alimentares"
        help="Uma linha por restrição, intolerância ou dieta especial."
        value={formData.restricoes_alimentares}
        onChange={setField("restricoes_alimentares")}
        linhas={3}
        placeholder="Ex: sem frango, dieta renal, alimento úmido controlado"
      />

      <InputTextoLongo
        id="pet-historico-clinico"
        label="Histórico Clínico"
        value={formData.historico_clinico}
        onChange={setField("historico_clinico")}
        linhas={4}
        placeholder="Descreva o histórico clínico do pet (cirurgias, tratamentos anteriores, etc)"
      />
    </div>
  );
}
