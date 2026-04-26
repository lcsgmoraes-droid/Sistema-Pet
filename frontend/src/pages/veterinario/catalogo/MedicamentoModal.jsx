import { Modal } from "./shared";

const CAMPOS_TEXTO = [
  { campo: "nome_comercial", label: "Nome comercial" },
  { campo: "principio_ativo", label: "Principio ativo" },
  { campo: "fabricante", label: "Fabricante" },
  { campo: "forma_farmaceutica", label: "Forma farmaceutica", placeholder: "Comprimido, solucao, pomada..." },
  { campo: "concentracao", label: "Concentracao", placeholder: "250 mg, 5%, 10 mg/ml..." },
  { campo: "especies_indicadas", label: "Especies indicadas", placeholder: "cao, gato, aves..." },
  {
    campo: "posologia_referencia",
    label: "Posologia de referencia",
    placeholder: "1 comp a cada 12h por 7 dias",
  },
];

const CAMPOS_TEXTAREA = [
  { campo: "indicacoes", label: "Indicacoes", className: "md:col-span-2" },
  { campo: "contraindicacoes", label: "Contraindicacoes" },
  { campo: "interacoes", label: "Interacoes" },
  { campo: "observacoes", label: "Observacoes", className: "md:col-span-2" },
];

export default function MedicamentoModal({ editando, form, onClose, onSave, salvando, setCampo }) {
  return (
    <Modal
      titulo={editando ? "Editar medicamento" : "Novo medicamento"}
      subtitulo="Cadastre ou ajuste a referencia para prescricao, dose e apoio clinico."
      onClose={onClose}
      onSave={onSave}
      salvando={salvando}
    >
      <div className="grid gap-3 md:grid-cols-2">
        <div className="md:col-span-2">
          <label className="mb-1 block text-xs font-medium text-gray-600">Nome *</label>
          <input
            type="text"
            value={form.nome}
            onChange={(event) => setCampo("nome", event.target.value)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          />
        </div>

        {CAMPOS_TEXTO.map((campo) => (
          <CampoTexto key={campo.campo} config={campo} form={form} setCampo={setCampo} />
        ))}

        <CampoDose
          campo="dose_min_mgkg"
          label="Dose minima (mg/kg)"
          value={form.dose_min_mgkg}
          setCampo={setCampo}
        />
        <CampoDose
          campo="dose_max_mgkg"
          label="Dose maxima (mg/kg)"
          value={form.dose_max_mgkg}
          setCampo={setCampo}
        />

        {CAMPOS_TEXTAREA.map((campo) => (
          <CampoTextarea key={campo.campo} config={campo} form={form} setCampo={setCampo} />
        ))}

        <CampoBoolean
          checked={form.eh_antibiotico}
          label="Antibiotico"
          onChange={(valor) => setCampo("eh_antibiotico", valor)}
        />
        <CampoBoolean
          checked={form.eh_controlado}
          label="Controlado"
          onChange={(valor) => setCampo("eh_controlado", valor)}
        />
      </div>
    </Modal>
  );
}

function CampoTexto({ config, form, setCampo }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-600">{config.label}</label>
      <input
        type="text"
        value={form[config.campo]}
        onChange={(event) => setCampo(config.campo, event.target.value)}
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        placeholder={config.placeholder}
      />
    </div>
  );
}

function CampoDose({ campo, label, setCampo, value }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-600">{label}</label>
      <input
        type="number"
        step="0.01"
        value={value}
        onChange={(event) => setCampo(campo, event.target.value)}
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
      />
    </div>
  );
}

function CampoTextarea({ config, form, setCampo }) {
  return (
    <div className={config.className}>
      <label className="mb-1 block text-xs font-medium text-gray-600">{config.label}</label>
      <textarea
        value={form[config.campo]}
        onChange={(event) => setCampo(config.campo, event.target.value)}
        className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
      />
    </div>
  );
}

function CampoBoolean({ checked, label, onChange }) {
  return (
    <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}
