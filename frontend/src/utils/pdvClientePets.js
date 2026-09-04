function idsIguais(valorA, valorB) {
  if (valorA === null || valorA === undefined || valorB === null || valorB === undefined) {
    return false;
  }

  return String(valorA) === String(valorB);
}

export function incluirPetNoClienteSelecionado(cliente, pet) {
  if (!cliente?.id || !pet?.id) return cliente;

  const tutorIdPet = pet.cliente_id ?? pet.tutor_id;
  if (tutorIdPet != null && !idsIguais(tutorIdPet, cliente.id)) {
    return cliente;
  }

  const petsAtuais = Array.isArray(cliente.pets) ? cliente.pets : [];
  const petExistenteIndex = petsAtuais.findIndex((item) => idsIguais(item?.id, pet.id));

  if (petExistenteIndex < 0) {
    return {
      ...cliente,
      pets: [pet, ...petsAtuais],
    };
  }

  return {
    ...cliente,
    pets: petsAtuais.map((item, index) =>
      index === petExistenteIndex ? { ...item, ...pet } : item,
    ),
  };
}
