export function criarTutorAPartirDoPet(pet, fallback = {}) {
  return {
    id: pet.cliente_id,
    nome: pet.cliente_nome ?? fallback.nome ?? `Tutor #${pet.cliente_id}`,
    telefone: pet.cliente_telefone ?? fallback.telefone ?? "",
    celular: pet.cliente_celular ?? fallback.celular ?? "",
  };
}

export function criarTutoresIndex(pets) {
  const mapa = new Map();
  for (const pet of pets) {
    const tutorId = pet.cliente_id;
    if (!tutorId) continue;
    if (!mapa.has(tutorId)) {
      mapa.set(tutorId, criarTutorAPartirDoPet(pet));
    }
  }
  return Array.from(mapa.values()).sort((a, b) => a.nome.localeCompare(b.nome));
}

export function listarPetsAtivosDoTutor(pets, tutorSelecionado) {
  if (!tutorSelecionado) return [];

  const petsTutor = pets.filter(
    (pet) => String(pet.cliente_id) === String(tutorSelecionado.id) && pet.ativo !== false
  );

  const porId = new Map();
  for (const pet of petsTutor) {
    porId.set(String(pet.id), pet);
  }
  return Array.from(porId.values());
}

export function obterPetSelecionadoLabel(petSelecionado) {
  if (!petSelecionado) return "Selecione o pet";
  const especie = petSelecionado.especie;
  const especieValida = especie && !/\?/.test(especie);
  return especieValida ? `${petSelecionado.nome} (${especie})` : petSelecionado.nome;
}

export function listarSugestoesEspecies(pets) {
  return Array.from(
    new Set(pets.map((pet) => pet?.especie).filter((especie) => especie && !/\?/.test(especie)))
  );
}

export function filtrarTutoresPorTermo(tutoresIndex, termoBusca) {
  const termo = termoBusca.trim();
  if (!termo) return [];

  const termoLower = termo.toLowerCase();
  const termoDigitos = termo.replaceAll(/\D/g, "");

  return tutoresIndex
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
}

export function inserirPetSemDuplicar(pets, petCriado) {
  const semDuplicado = pets.filter((pet) => String(pet.id) !== String(petCriado.id));
  return [petCriado, ...semDuplicado];
}
