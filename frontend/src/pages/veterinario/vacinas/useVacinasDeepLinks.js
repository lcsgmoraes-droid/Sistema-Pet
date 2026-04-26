import { useEffect } from "react";

export function useVacinasDeepLinks({
  acaoQuery,
  novoPetIdQuery,
  petIdQuery,
  pets,
  setForm,
  setNovaAberta,
  setPessoaFiltro,
  setPetSelecionado,
  setTutorFiltroSelecionado,
  setTutorFormSelecionado,
  tutorFormSelecionado,
  tutorIdQuery,
  tutorNomeQuery,
}) {
  useEffect(() => {
    const petIdAlvo = novoPetIdQuery || petIdQuery;
    if (!petIdAlvo || !pets.length) return;

    const petEncontrado = pets.find((pet) => String(pet.id) === String(petIdAlvo));
    if (!petEncontrado) return;

    const pessoaId = petEncontrado?.cliente_id ? String(petEncontrado.cliente_id) : "";
    if (pessoaId) {
      const tutorSelecionado = {
        id: pessoaId,
        nome: petEncontrado.cliente_nome ?? `Pessoa #${pessoaId}`,
      };

      setPessoaFiltro(pessoaId);
      setTutorFiltroSelecionado(tutorSelecionado);
      setTutorFormSelecionado(tutorSelecionado);
      setForm((prev) => ({ ...prev, pessoa_id: pessoaId }));
    }

    setPetSelecionado(String(petEncontrado.id));
    setForm((prev) => ({ ...prev, pet_id: String(petEncontrado.id) }));

    if (acaoQuery === "novo" || novoPetIdQuery) {
      setNovaAberta(true);
    }
  }, [
    acaoQuery,
    novoPetIdQuery,
    petIdQuery,
    pets,
    setForm,
    setNovaAberta,
    setPessoaFiltro,
    setPetSelecionado,
    setTutorFiltroSelecionado,
    setTutorFormSelecionado,
  ]);

  useEffect(() => {
    if (!tutorIdQuery || tutorFormSelecionado?.id) return;

    setTutorFormSelecionado({
      id: String(tutorIdQuery),
      nome: tutorNomeQuery || `Pessoa #${tutorIdQuery}`,
    });
    setForm((prev) => ({ ...prev, pessoa_id: String(tutorIdQuery) }));
  }, [setForm, setTutorFormSelecionado, tutorFormSelecionado, tutorIdQuery, tutorNomeQuery]);
}
