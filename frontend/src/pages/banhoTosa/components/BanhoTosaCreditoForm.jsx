import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import TutorAutocomplete from "../../../components/TutorAutocomplete";
import { api } from "../../../services/api";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage } from "../banhoTosaUtils";

const todayIso = () => new Date().toISOString().slice(0, 10);
const initialForm = {
  pacote_id: "",
  pet_id: "",
  data_inicio: todayIso(),
  data_validade: "",
  observacoes: "",
};

export default function BanhoTosaCreditoForm({ pacotes = [], onChanged }) {
  const [form, setForm] = useState(initialForm);
  const [tutor, setTutor] = useState(null);
  const [pets, setPets] = useState([]);
  const [loadingPets, setLoadingPets] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!tutor?.id) {
      setPets([]);
      setForm((prev) => ({ ...prev, pet_id: "" }));
      return;
    }

    let active = true;
    setLoadingPets(true);
    api.get("/vet/pets", { params: { cliente_id: tutor.id, limit: 100 } })
      .then((response) => {
        if (!active) return;
        const lista = response.data?.items ?? response.data ?? [];
        setPets(Array.isArray(lista) ? lista : []);
      })
      .catch(() => active && setPets([]))
      .finally(() => active && setLoadingPets(false));

    return () => {
      active = false;
    };
  }, [tutor?.id]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function liberarCredito(event) {
    event.preventDefault();
    if (!form.pacote_id || !tutor?.id) {
      toast.error("Selecione pacote e tutor.");
      return;
    }

    setSaving(true);
    try {
      await banhoTosaApi.criarCreditoPacote({
        pacote_id: Number(form.pacote_id),
        cliente_id: Number(tutor.id),
        pet_id: form.pet_id ? Number(form.pet_id) : null,
        data_inicio: form.data_inicio || null,
        data_validade: form.data_validade || null,
        observacoes: form.observacoes || null,
      });
      toast.success("Credito liberado para o tutor.");
      setForm(initialForm);
      setTutor(null);
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel liberar o credito."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={liberarCredito} className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
        Creditos
      </p>
      <h2 className="mt-2 text-xl font-black text-slate-900">Liberar pacote para cliente</h2>

      <div className="mt-5 space-y-4">
        <SelectField label="Pacote" value={form.pacote_id} onChange={(value) => updateField("pacote_id", value)}>
          <option value="">Selecione</option>
          {pacotes.filter((item) => item.ativo).map((pacote) => (
            <option key={pacote.id} value={pacote.id}>
              {pacote.nome} - {pacote.quantidade_creditos} creditos
            </option>
          ))}
        </SelectField>

        <TutorAutocomplete
          label="Tutor"
          inputId="bt-pacote-tutor"
          selectedTutor={tutor}
          onSelect={setTutor}
        />

        <SelectField
          label="Pet vinculado"
          value={form.pet_id}
          disabled={!tutor?.id || loadingPets}
          onChange={(value) => updateField("pet_id", value)}
        >
          <option value="">
            {!tutor?.id ? "Selecione o tutor primeiro" : "Todos os pets do tutor"}
          </option>
          {pets.map((pet) => (
            <option key={pet.id} value={pet.id}>
              {pet.nome} {pet.especie ? `(${pet.especie})` : ""}
            </option>
          ))}
        </SelectField>

        <div className="grid gap-3 sm:grid-cols-2">
          <TextField label="Inicio" type="date" value={form.data_inicio} onChange={(value) => updateField("data_inicio", value)} />
          <TextField label="Validade manual" type="date" value={form.data_validade} onChange={(value) => updateField("data_validade", value)} />
        </div>
        <TextField label="Observacoes" value={form.observacoes} onChange={(value) => updateField("observacoes", value)} />
      </div>

      <button
        type="submit"
        disabled={saving}
        className="mt-6 w-full rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-emerald-700 disabled:opacity-60"
      >
        {saving ? "Liberando..." : "Liberar credito"}
      </button>
    </form>
  );
}

function SelectField({ label, value, onChange, children, disabled = false }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100 disabled:text-slate-400"
      >
        {children}
      </select>
    </label>
  );
}

function TextField({ label, value, onChange, type = "text" }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}
