export function buildReturnTo(pathname, search = "", extraParams = {}) {
  const base = typeof window !== "undefined" ? window.location.origin : "http://localhost";
  const url = new URL(`${pathname}${search || ""}`, base);

  Object.entries(extraParams || {}).forEach(([key, value]) => {
    if (value == null || value === "" || value === false) {
      url.searchParams.delete(key);
      return;
    }
    url.searchParams.set(key, String(value));
  });

  return `${url.pathname}${url.search}${url.hash}`;
}

export function buildNovoPetPath({ tutorId, tutorNome, returnTo }) {
  const params = new URLSearchParams();

  if (tutorId) {
    params.set("cliente_id", String(tutorId));
  }
  if (tutorNome) {
    params.set("tutor_nome", tutorNome);
  }
  if (returnTo) {
    params.set("return_to", returnTo);
  }

  const search = params.toString();
  return search ? `/pets/novo?${search}` : "/pets/novo";
}

export function buildReturnWithNovoPet(returnTo, pet) {
  const base = typeof window !== "undefined" ? window.location.origin : "http://localhost";
  const url = new URL(returnTo || "/pets", base);

  if (pet?.id) {
    url.searchParams.set("novo_pet_id", String(pet.id));
  }
  if (pet?.cliente_id) {
    url.searchParams.set("tutor_id", String(pet.cliente_id));
  }
  if (pet?.cliente_nome) {
    url.searchParams.set("tutor_nome", pet.cliente_nome);
  }
  if (pet?.nome) {
    url.searchParams.set("novo_pet_nome", pet.nome);
  }

  return `${url.pathname}${url.search}${url.hash}`;
}
