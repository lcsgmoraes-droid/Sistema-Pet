import { useEffect, useMemo, useState } from "react";
import {
  criarTutorAPartirDoPet,
  criarTutoresIndex,
  filtrarTutoresPorTermo,
  inserirPetSemDuplicar,
  listarPetsAtivosDoTutor,
  listarSugestoesEspecies,
  obterPetSelecionadoLabel,
} from "./tutorPetSelectionUtils";

export default function useTutorPetSelection({
  pets,
  setPets,
  formPetId,
  setCampo,
  isEdicao,
  petIdQuery,
  novoPetIdQuery,
  tutorIdQuery,
  tutorNomeQuery,
}) {
  const [buscaTutor, setBuscaTutor] = useState("");
  const [tutorSelecionado, setTutorSelecionado] = useState(null);
  const [tutoresSugeridos, setTutoresSugeridos] = useState([]);
  const [listaPetsExpandida, setListaPetsExpandida] = useState(false);

  const tutoresIndex = useMemo(() => criarTutoresIndex(pets), [pets]);

  const petsDoTutor = useMemo(
    () => listarPetsAtivosDoTutor(pets, tutorSelecionado),
    [pets, tutorSelecionado]
  );

  const petSelecionado = useMemo(
    () => pets.find((pet) => String(pet.id) === String(formPetId)) ?? null,
    [pets, formPetId]
  );

  const petSelecionadoLabel = useMemo(
    () => obterPetSelecionadoLabel(petSelecionado),
    [petSelecionado]
  );

  const sugestoesEspecies = useMemo(
    () => listarSugestoesEspecies(pets),
    [pets]
  );

  useEffect(() => {
    if (isEdicao) return;
    const petIdAlvo = novoPetIdQuery || petIdQuery;
    if (!petIdAlvo || !pets.length) return;

    const petEncontrado = pets.find((pet) => String(pet.id) === String(petIdAlvo));
    if (!petEncontrado) return;

    setCampo("pet_id", String(petEncontrado.id));
    setTutorSelecionado(criarTutorAPartirDoPet(petEncontrado));
    setBuscaTutor(petEncontrado.cliente_nome ?? "");
    setListaPetsExpandida(false);
  }, [isEdicao, petIdQuery, novoPetIdQuery, pets, setCampo]);

  useEffect(() => {
    if (isEdicao || !tutorIdQuery) return;
    setTutorSelecionado((prev) => {
      if (prev?.id && String(prev.id) === String(tutorIdQuery)) return prev;
      return {
        id: String(tutorIdQuery),
        nome: tutorNomeQuery || `Tutor #${tutorIdQuery}`,
        telefone: "",
        celular: "",
      };
    });
    setBuscaTutor((prev) => prev || tutorNomeQuery || "");
  }, [isEdicao, tutorIdQuery, tutorNomeQuery]);

  useEffect(() => {
    setTutoresSugeridos(filtrarTutoresPorTermo(tutoresIndex, buscaTutor));
  }, [buscaTutor, tutoresIndex]);

  useEffect(() => {
    if (!formPetId || !pets.length) return;
    const petAtual = pets.find((pet) => String(pet.id) === String(formPetId));
    if (!petAtual) return;

    setTutorSelecionado((prev) => {
      if (prev && String(prev.id) === String(petAtual.cliente_id)) return prev;
      return criarTutorAPartirDoPet(petAtual);
    });
    setBuscaTutor((prev) => prev || petAtual.cliente_nome || "");
  }, [formPetId, pets]);

  function selecionarTutor(tutor) {
    setTutorSelecionado(tutor);
    setBuscaTutor(tutor.nome);
    setTutoresSugeridos([]);
    setListaPetsExpandida(true);
    setCampo("pet_id", "");
  }

  function limparTutor() {
    setTutorSelecionado(null);
    setBuscaTutor("");
    setTutoresSugeridos([]);
    setListaPetsExpandida(false);
    setCampo("pet_id", "");
  }

  function selecionarPetCriado(petCriado) {
    setPets((prev) => inserirPetSemDuplicar(prev, petCriado));

    setTutorSelecionado((prev) => criarTutorAPartirDoPet(petCriado, {
      nome: prev?.nome ?? tutorSelecionado?.nome,
      telefone: prev?.telefone,
      celular: prev?.celular,
    }));
    setBuscaTutor(petCriado.cliente_nome ?? tutorSelecionado?.nome ?? buscaTutor);
    setCampo("pet_id", String(petCriado.id));
    setListaPetsExpandida(false);
    return `Pet ${petCriado.nome} cadastrado e selecionado na consulta.`;
  }

  return {
    buscaTutor,
    setBuscaTutor,
    tutorSelecionado,
    setTutorSelecionado,
    tutoresSugeridos,
    listaPetsExpandida,
    setListaPetsExpandida,
    petsDoTutor,
    petSelecionado,
    petSelecionadoLabel,
    sugestoesEspecies,
    selecionarTutor,
    limparTutor,
    selecionarPetCriado,
  };
}
