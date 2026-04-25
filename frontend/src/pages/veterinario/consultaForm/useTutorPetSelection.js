import { useEffect, useMemo, useState } from "react";

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

  const tutoresIndex = useMemo(() => {
    const mapa = new Map();
    for (const pet of pets) {
      const tutorId = pet.cliente_id;
      if (!tutorId) continue;
      if (!mapa.has(tutorId)) {
        mapa.set(tutorId, {
          id: tutorId,
          nome: pet.cliente_nome ?? `Tutor #${tutorId}`,
          telefone: pet.cliente_telefone ?? "",
          celular: pet.cliente_celular ?? "",
        });
      }
    }
    return Array.from(mapa.values()).sort((a, b) => a.nome.localeCompare(b.nome));
  }, [pets]);

  const petsDoTutor = useMemo(() => {
    if (!tutorSelecionado) return [];

    const petsTutor = pets.filter(
      (pet) => String(pet.cliente_id) === String(tutorSelecionado.id) && pet.ativo !== false
    );

    const porId = new Map();
    for (const pet of petsTutor) {
      porId.set(String(pet.id), pet);
    }
    return Array.from(porId.values());
  }, [pets, tutorSelecionado]);

  const petSelecionado = useMemo(
    () => pets.find((pet) => String(pet.id) === String(formPetId)) ?? null,
    [pets, formPetId]
  );

  const petSelecionadoLabel = useMemo(() => {
    if (!petSelecionado) return "Selecione o pet";
    const especie = petSelecionado.especie;
    const especieValida = especie && !/\?/.test(especie);
    return especieValida ? `${petSelecionado.nome} (${especie})` : petSelecionado.nome;
  }, [petSelecionado]);

  const sugestoesEspecies = useMemo(
    () =>
      Array.from(new Set(pets.map((pet) => pet?.especie).filter((especie) => especie && !/\?/.test(especie)))),
    [pets]
  );

  useEffect(() => {
    if (isEdicao) return;
    const petIdAlvo = novoPetIdQuery || petIdQuery;
    if (!petIdAlvo || !pets.length) return;

    const petEncontrado = pets.find((pet) => String(pet.id) === String(petIdAlvo));
    if (!petEncontrado) return;

    setCampo("pet_id", String(petEncontrado.id));
    setTutorSelecionado({
      id: petEncontrado.cliente_id,
      nome: petEncontrado.cliente_nome ?? `Tutor #${petEncontrado.cliente_id}`,
      telefone: petEncontrado.cliente_telefone ?? "",
      celular: petEncontrado.cliente_celular ?? "",
    });
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
    const termo = buscaTutor.trim();
    if (!termo) {
      setTutoresSugeridos([]);
      return;
    }

    const termoLower = termo.toLowerCase();
    const termoDigitos = termo.replaceAll(/\D/g, "");

    const sugestoes = tutoresIndex
      .filter((tutor) => {
        const nome = (tutor.nome ?? "").toLowerCase();
        const telefone = (tutor.telefone ?? "").toLowerCase();
        const celular = (tutor.celular ?? "").toLowerCase();
        const telefoneDigitos = telefone.replaceAll(/\D/g, "");
        const celularDigitos = celular.replaceAll(/\D/g, "");

        return (
          nome.includes(termoLower) ||
          telefone.includes(termoLower) ||
          celular.includes(termoLower) ||
          (termoDigitos && (telefoneDigitos.includes(termoDigitos) || celularDigitos.includes(termoDigitos)))
        );
      })
      .slice(0, 20);

    setTutoresSugeridos(sugestoes);
  }, [buscaTutor, tutoresIndex]);

  useEffect(() => {
    if (!formPetId || !pets.length) return;
    const petAtual = pets.find((pet) => String(pet.id) === String(formPetId));
    if (!petAtual) return;

    setTutorSelecionado((prev) => {
      if (prev && String(prev.id) === String(petAtual.cliente_id)) return prev;
      return {
        id: petAtual.cliente_id,
        nome: petAtual.cliente_nome ?? `Tutor #${petAtual.cliente_id}`,
        telefone: petAtual.cliente_telefone ?? "",
        celular: petAtual.cliente_celular ?? "",
      };
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
    setPets((prev) => {
      const semDuplicado = prev.filter((pet) => String(pet.id) !== String(petCriado.id));
      return [petCriado, ...semDuplicado];
    });

    setTutorSelecionado((prev) => ({
      id: petCriado.cliente_id,
      nome: petCriado.cliente_nome ?? prev?.nome ?? tutorSelecionado?.nome ?? `Tutor #${petCriado.cliente_id}`,
      telefone: petCriado.cliente_telefone ?? prev?.telefone ?? "",
      celular: petCriado.cliente_celular ?? prev?.celular ?? "",
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
