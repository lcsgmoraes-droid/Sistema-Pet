import { SelectField, TextField } from "../../../components/ui/FormField";

export default function BanhoTosaTaxiDogForm({
  agendamentos,
  dataRef,
  form,
  funcionarios,
  saving,
  onChangeData,
  onChangeField,
  onSubmit,
}) {
  return (
    <form onSubmit={onSubmit} className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">Taxi dog</p>
      <h2 className="mt-2 text-xl font-black text-slate-900">Transporte vinculado a agenda</h2>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <TextField label="Data" type="date" value={dataRef} onChange={onChangeData} tone="warm" />
        <SelectField label="Tipo" value={form.tipo} onChange={(value) => onChangeField("tipo", value)} tone="warm">
          <option value="ida">Somente ida</option>
          <option value="volta">Somente volta</option>
          <option value="ida_volta">Ida e volta</option>
        </SelectField>
        <SelectField label="Agendamento" value={form.agendamento_id} onChange={(value) => onChangeField("agendamento_id", value)} tone="warm">
          <option value="">Selecione</option>
          {agendamentos.map((item) => (
            <option key={item.id} value={item.id}>
              {hora(item.data_hora_inicio)} - {item.pet_nome} / {item.cliente_nome}
            </option>
          ))}
        </SelectField>
        <SelectField label="Motorista" value={form.motorista_id} onChange={(value) => onChangeField("motorista_id", value)} tone="warm">
          <option value="">Nao definido</option>
          {funcionarios.map((pessoa) => (
            <option key={pessoa.id} value={pessoa.id}>{pessoa.nome}</option>
          ))}
        </SelectField>
        <TextField label="Janela inicio" type="datetime-local" value={form.janela_inicio} onChange={(value) => onChangeField("janela_inicio", value)} tone="warm" />
        <TextField label="Janela fim" type="datetime-local" value={form.janela_fim} onChange={(value) => onChangeField("janela_fim", value)} tone="warm" />
        <TextField label="Km estimado" type="number" value={form.km_estimado} onChange={(value) => onChangeField("km_estimado", value)} tone="warm" />
        <TextField label="Valor cobrado" type="number" value={form.valor_cobrado} onChange={(value) => onChangeField("valor_cobrado", value)} tone="warm" />
        <TextField label="Custo estimado" type="number" value={form.custo_estimado} onChange={(value) => onChangeField("custo_estimado", value)} tone="warm" />
        <TextField label="Custo real" type="number" value={form.custo_real} onChange={(value) => onChangeField("custo_real", value)} tone="warm" />
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <TextField label="Origem" value={form.endereco_origem} onChange={(value) => onChangeField("endereco_origem", value)} tone="warm" />
        <TextField label="Destino" value={form.endereco_destino} onChange={(value) => onChangeField("endereco_destino", value)} tone="warm" />
      </div>
      <button type="submit" disabled={saving} className="mt-6 w-full rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60">
        {saving ? "Salvando..." : "Criar taxi dog"}
      </button>
    </form>
  );
}

function hora(value) {
  return value ? String(value).slice(11, 16) : "--:--";
}
