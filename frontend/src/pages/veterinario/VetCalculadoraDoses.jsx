import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Calculator, Pill, Scale } from "lucide-react";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";
import TutorAutocomplete from "../../components/TutorAutocomplete";
import NovoPetButton from "../../components/veterinario/NovoPetButton";
import { buildReturnTo } from "../../utils/petReturnFlow";

function numero(valor) {
  const parsed = Number.parseFloat(String(valor).replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

export default function VetCalculadoraDoses() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const petIdQuery = searchParams.get("pet_id") || "";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";
  const [pets, setPets] = useState([]);
  const [medicamentos, setMedicamentos] = useState([]);
  const [tutorSelecionado, setTutorSelecionado] = useState(null);
  const [form, setForm] = useState({
    pessoa_id: "",
    pet_id: novoPetIdQuery || petIdQuery,
    peso_kg: "",
    medicamento_id: "",
    dose_mg_kg: "",
    frequencia_horas: "12",
    dias: "7",
  });

  useEffect(() => {
    api.get("/pets", { params: { limit: 500 } })
      .then((res) => setPets(res.data?.items ?? res.data ?? []))
      .catch(() => setPets([]));

    vetApi.listarMedicamentos()
      .then((res) => setMedicamentos(Array.isArray(res.data) ? res.data : (res.data?.items ?? [])))
      .catch(() => setMedicamentos([]));
  }, []);

  useEffect(() => {
    const petIdAlvo = novoPetIdQuery || petIdQuery;
    if (!petIdAlvo || !pets.length) return;
    const pet = pets.find((item) => String(item.id) === String(petIdAlvo));
    if (!pet) return;
    setForm((prev) => ({
      ...prev,
      pessoa_id: pet?.cliente_id ? String(pet.cliente_id) : prev.pessoa_id,
      pet_id: String(pet.id),
      peso_kg: prev.peso_kg || String(pet.peso || ""),
    }));
    setTutorSelecionado(
      pet?.cliente_id
        ? { id: String(pet.cliente_id), nome: pet.cliente_nome ?? `Pessoa #${pet.cliente_id}` }
        : null
    );
  }, [petIdQuery, novoPetIdQuery, pets]);

  useEffect(() => {
    if (!tutorIdQuery || tutorSelecionado?.id) return;
    setTutorSelecionado({
      id: String(tutorIdQuery),
      nome: tutorNomeQuery || `Pessoa #${tutorIdQuery}`,
    });
    setForm((prev) => ({
      ...prev,
      pessoa_id: String(tutorIdQuery),
    }));
  }, [tutorIdQuery, tutorNomeQuery, tutorSelecionado]);

  const petsDaPessoa = useMemo(() => {
    if (!form.pessoa_id) return [];
    return pets.filter(
      (pet) => String(pet.cliente_id) === String(form.pessoa_id) && pet.ativo !== false
    );
  }, [pets, form.pessoa_id]);

  const petSelecionado = useMemo(
    () => pets.find((item) => String(item.id) === String(form.pet_id)) ?? null,
    [pets, form.pet_id]
  );

  const medicamentoSelecionado = useMemo(
    () => medicamentos.find((item) => String(item.id) === String(form.medicamento_id)) ?? null,
    [medicamentos, form.medicamento_id]
  );

  useEffect(() => {
    if (!medicamentoSelecionado) return;
    const doseMin = numero(medicamentoSelecionado.dose_min_mgkg);
    const doseMax = numero(medicamentoSelecionado.dose_max_mgkg);
    const doseMedia = doseMin && doseMax ? ((doseMin + doseMax) / 2).toFixed(2) : (doseMin || doseMax || "");
    setForm((prev) => ({
      ...prev,
      dose_mg_kg: prev.dose_mg_kg || String(doseMedia || ""),
    }));
  }, [medicamentoSelecionado]);

  const calculo = useMemo(() => {
    const peso = numero(form.peso_kg);
    const dose = numero(form.dose_mg_kg);
    const frequencia = numero(form.frequencia_horas);
    const dias = numero(form.dias);
    if (!peso || !dose) return null;

    const mgPorDose = peso * dose;
    const dosesPorDia = frequencia ? 24 / frequencia : null;
    const mgDia = dosesPorDia ? mgPorDose * dosesPorDia : null;
    const mgTratamento = mgDia && dias ? mgDia * dias : null;

    return {
      mgPorDose,
      dosesPorDia,
      mgDia,
      mgTratamento,
    };
  }, [form]);

  const setCampo = (campo, valor) => setForm((prev) => ({ ...prev, [campo]: valor }));
  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search),
    [location.pathname, location.search]
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="rounded-2xl bg-cyan-100 p-3 text-cyan-700">
          <Calculator size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Calculadora de doses</h1>
          <p className="text-sm text-gray-500">Ferramenta livre para checagem rápida por mg/kg.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-gray-200 bg-white p-5 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <TutorAutocomplete
                label="Tutor"
                inputId="calc-dose-tutor"
                selectedTutor={tutorSelecionado}
                onSelect={(cliente) => {
                  setTutorSelecionado(cliente);
                  setForm((prev) => ({
                    ...prev,
                    pessoa_id: cliente?.id ? String(cliente.id) : "",
                    pet_id: "",
                    peso_kg: "",
                  }));
                }}
              />
            </div>

            <div>
              <div className="mb-1 flex items-center justify-between gap-2">
                <label htmlFor="calc-dose-pet" className="block text-sm font-medium text-gray-700">Pet</label>
                <NovoPetButton
                  tutorId={tutorSelecionado?.id || form.pessoa_id}
                  tutorNome={tutorSelecionado?.nome}
                  returnTo={retornoNovoPet}
                />
              </div>
              <select
                id="calc-dose-pet"
                value={form.pet_id}
                disabled={!form.pessoa_id}
                onChange={(e) => {
                  const petId = e.target.value;
                  const pet = petsDaPessoa.find((item) => String(item.id) === String(petId));
                  setForm((prev) => ({
                    ...prev,
                    pet_id: petId,
                    peso_kg: pet?.peso ? String(pet.peso) : "",
                  }));
                }}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm disabled:bg-gray-100"
              >
                <option value="">{form.pessoa_id ? "Selecione o pet..." : "Selecione o tutor primeiro..."}</option>
                {petsDaPessoa.map((pet) => (
                  <option key={pet.id} value={pet.id}>{pet.nome} {pet.especie ? `• ${pet.especie}` : ""}</option>
                ))}
              </select>
              {form.pessoa_id && petsDaPessoa.length === 0 && (
                <p className="mt-2 text-xs text-amber-600">Nenhum pet ativo encontrado para esta pessoa.</p>
              )}
            </div>

            <div>
              <label htmlFor="calc-dose-peso" className="block text-sm font-medium text-gray-700 mb-1">Peso atual (kg)</label>
              <input
                id="calc-dose-peso"
                type="number"
                step="0.01"
                value={form.peso_kg}
                onChange={(e) => setCampo("peso_kg", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label htmlFor="calc-dose-medicamento" className="block text-sm font-medium text-gray-700 mb-1">Medicamento</label>
              <select
                id="calc-dose-medicamento"
                value={form.medicamento_id}
                onChange={(e) => {
                  setCampo("medicamento_id", e.target.value);
                  setCampo("dose_mg_kg", "");
                }}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              >
                <option value="">Selecione...</option>
                {medicamentos.map((med) => (
                  <option key={med.id} value={med.id}>{med.nome}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="calc-dose-mgkg" className="block text-sm font-medium text-gray-700 mb-1">Dose desejada (mg/kg)</label>
              <input
                id="calc-dose-mgkg"
                type="number"
                step="0.01"
                value={form.dose_mg_kg}
                onChange={(e) => setCampo("dose_mg_kg", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label htmlFor="calc-dose-frequencia" className="block text-sm font-medium text-gray-700 mb-1">Frequência (horas)</label>
              <input
                id="calc-dose-frequencia"
                type="number"
                min="1"
                value={form.frequencia_horas}
                onChange={(e) => setCampo("frequencia_horas", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label htmlFor="calc-dose-dias" className="block text-sm font-medium text-gray-700 mb-1">Dias de tratamento</label>
              <input
                id="calc-dose-dias"
                type="number"
                min="1"
                value={form.dias}
                onChange={(e) => setCampo("dias", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
          </div>

          {medicamentoSelecionado && (
            <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-900">
              <p className="font-semibold">Faixa cadastrada no catálogo</p>
              <p className="mt-1">
                {medicamentoSelecionado.dose_min_mgkg ?? "-"} a {medicamentoSelecionado.dose_max_mgkg ?? "-"} mg/kg
              </p>
              {medicamentoSelecionado.posologia_referencia && (
                <p className="mt-2 text-cyan-800">{medicamentoSelecionado.posologia_referencia}</p>
              )}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-gray-200 bg-slate-900 text-white p-5 space-y-4">
          <div className="flex items-center gap-2 text-slate-200">
            <Scale size={18} />
            <span className="text-sm">Resultado rápido</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-white/10 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-300">Mg por dose</p>
              <p className="mt-2 text-2xl font-bold">{calculo ? calculo.mgPorDose.toFixed(2) : "--"}</p>
            </div>
            <div className="rounded-xl bg-white/10 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-300">Doses por dia</p>
              <p className="mt-2 text-2xl font-bold">{calculo?.dosesPorDia ? calculo.dosesPorDia.toFixed(2) : "--"}</p>
            </div>
            <div className="rounded-xl bg-white/10 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-300">Mg por dia</p>
              <p className="mt-2 text-2xl font-bold">{calculo?.mgDia ? calculo.mgDia.toFixed(2) : "--"}</p>
            </div>
            <div className="rounded-xl bg-white/10 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-300">Mg no tratamento</p>
              <p className="mt-2 text-2xl font-bold">{calculo?.mgTratamento ? calculo.mgTratamento.toFixed(2) : "--"}</p>
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
            <div className="flex items-center gap-2 mb-2">
              <Pill size={16} />
              <span className="font-medium">Resumo</span>
            </div>
            <p>Tutor: {tutorSelecionado?.nome || petSelecionado?.cliente_nome || "não selecionado"}</p>
            <p>Pet: {petSelecionado?.nome || "não selecionado"}</p>
            <p>Medicamento: {medicamentoSelecionado?.nome || "não selecionado"}</p>
            <p>Peso considerado: {form.peso_kg || "--"} kg</p>
            <p>Dose usada: {form.dose_mg_kg || "--"} mg/kg</p>
          </div>
        </div>
      </div>
    </div>
  );
}
