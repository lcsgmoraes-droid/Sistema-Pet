import { Modal } from "./shared";

export default function ProtocoloVacinaModal({
  editando,
  form,
  salvando,
  onClose,
  onSave,
  onSetCampo,
}) {
  return (
    <Modal
      titulo={editando ? "Editar protocolo de vacina" : "Novo protocolo de vacina"}
      subtitulo="Defina especie, serie, inicio e reforcos do protocolo."
      onClose={onClose}
      onSave={onSave}
      salvando={salvando}
    >
      <div className="grid gap-3 md:grid-cols-2">
        <CampoTexto label="Nome *" value={form.nome} onChange={(value) => onSetCampo("nome", value)} />
        <CampoTexto
          label="Especie *"
          placeholder="Cao, gato..."
          value={form.especie}
          onChange={(value) => onSetCampo("especie", value)}
        />
        <CampoNumero
          label="Inicio (semanas de vida)"
          value={form.dose_inicial_semanas}
          onChange={(value) => onSetCampo("dose_inicial_semanas", value)}
        />
        <CampoNumero
          label="Numero de doses"
          min="1"
          value={form.numero_doses_serie}
          onChange={(value) => onSetCampo("numero_doses_serie", value)}
        />
        <CampoNumero
          label="Intervalo entre doses (dias)"
          min="1"
          value={form.intervalo_doses_dias}
          onChange={(value) => onSetCampo("intervalo_doses_dias", value)}
        />
        <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm">
          <input
            type="checkbox"
            checked={form.reforco_anual}
            onChange={(event) => onSetCampo("reforco_anual", event.target.checked)}
          />
          Tem reforco anual
        </label>
        <div className="md:col-span-2">
          <label className="mb-1 block text-xs font-medium text-gray-600">Observacoes</label>
          <textarea
            value={form.observacoes}
            onChange={(event) => onSetCampo("observacoes", event.target.value)}
            className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          />
        </div>
      </div>
    </Modal>
  );
}

function CampoTexto({ label, onChange, placeholder, value }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-600">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        placeholder={placeholder}
      />
    </div>
  );
}

function CampoNumero({ label, min, onChange, value }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-600">{label}</label>
      <input
        type="number"
        min={min}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
      />
    </div>
  );
}
