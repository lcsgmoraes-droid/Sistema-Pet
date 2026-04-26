import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";

import { api } from "../../../services/api";
import { buildReturnTo } from "../../../utils/petReturnFlow";
import { vetApi } from "../vetApi";
import { calcularDose, obterDoseMedia } from "./calculadoraDosesUtils";

export function useVetCalculadoraDoses() {
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
    setForm((prev) => ({
      ...prev,
      dose_mg_kg: prev.dose_mg_kg || String(obterDoseMedia(medicamentoSelecionado) || ""),
    }));
  }, [medicamentoSelecionado]);

  const calculo = useMemo(() => calcularDose(form), [form]);

  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search),
    [location.pathname, location.search]
  );

  const setCampo = (campo, valor) => setForm((prev) => ({ ...prev, [campo]: valor }));

  const selecionarTutor = (cliente) => {
    setTutorSelecionado(cliente);
    setForm((prev) => ({
      ...prev,
      pessoa_id: cliente?.id ? String(cliente.id) : "",
      pet_id: "",
      peso_kg: "",
    }));
  };

  const selecionarPet = (petId) => {
    const pet = petsDaPessoa.find((item) => String(item.id) === String(petId));
    setForm((prev) => ({
      ...prev,
      pet_id: petId,
      peso_kg: pet?.peso ? String(pet.peso) : "",
    }));
  };

  const selecionarMedicamento = (medicamentoId) => {
    setCampo("medicamento_id", medicamentoId);
    setCampo("dose_mg_kg", "");
  };

  return {
    calculo,
    form,
    medicamentoSelecionado,
    medicamentos,
    petSelecionado,
    petsDaPessoa,
    retornoNovoPet,
    selecionarMedicamento,
    selecionarPet,
    selecionarTutor,
    setCampo,
    tutorSelecionado,
  };
}
