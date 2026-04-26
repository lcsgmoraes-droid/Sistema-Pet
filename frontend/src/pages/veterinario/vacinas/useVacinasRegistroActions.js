import { useCallback } from "react";

import { vetApi } from "../vetApi";
import { criarFormVacinaInicial } from "./vacinaUtils";

export function useVacinasRegistroActions({
  acaoQuery,
  agendamentoIdQuery,
  carregarVacinasPet,
  carregarVencendo,
  consultaIdQuery,
  form,
  navigate,
  novoPetIdQuery,
  petIdQuery,
  petSelecionado,
  pets,
  setErro,
  setForm,
  setNovaAberta,
  setPessoaFiltro,
  setPetSelecionado,
  setSalvando,
  setTutorFiltroSelecionado,
  setTutorFormSelecionado,
  sugestaoDose,
}) {
  const pessoaIdPorPet = useCallback(
    (petId) => {
      if (!petId) return "";
      const pet = pets.find((item) => String(item.id) === String(petId));
      return pet?.cliente_id ? String(pet.cliente_id) : "";
    },
    [pets]
  );

  const setCampo = useCallback(
    (campo, valor) => {
      setForm((prev) => ({ ...prev, [campo]: valor }));
    },
    [setForm]
  );

  const selecionarTutorFiltro = useCallback(
    (cliente) => {
      setTutorFiltroSelecionado(cliente);
      setPessoaFiltro(cliente?.id ? String(cliente.id) : "");
      setPetSelecionado("");
    },
    [setPessoaFiltro, setPetSelecionado, setTutorFiltroSelecionado]
  );

  const selecionarTutorForm = useCallback(
    (cliente) => {
      setTutorFormSelecionado(cliente);
      setForm((prev) => ({
        ...prev,
        pessoa_id: cliente?.id ? String(cliente.id) : "",
        pet_id: "",
      }));
    },
    [setForm, setTutorFormSelecionado]
  );

  const fecharModalVacina = useCallback(() => {
    setNovaAberta(false);
    setTutorFormSelecionado(null);
    setForm(criarFormVacinaInicial());

    if (acaoQuery === "novo" || petIdQuery || novoPetIdQuery || agendamentoIdQuery || consultaIdQuery) {
      navigate("/veterinario/vacinas", { replace: true });
    }
  }, [
    acaoQuery,
    agendamentoIdQuery,
    consultaIdQuery,
    navigate,
    novoPetIdQuery,
    petIdQuery,
    setForm,
    setNovaAberta,
    setTutorFormSelecionado,
  ]);

  const abrirRegistroPrimeiraVacina = useCallback(() => {
    const pessoaIdAtual = pessoaIdPorPet(petSelecionado);
    const petAtual = pets.find((pet) => String(pet.id) === String(petSelecionado));

    setTutorFormSelecionado(
      pessoaIdAtual
        ? { id: pessoaIdAtual, nome: petAtual?.cliente_nome ?? `Pessoa #${pessoaIdAtual}` }
        : null
    );

    setForm((prev) => ({
      ...prev,
      pessoa_id: pessoaIdAtual,
      pet_id: petSelecionado,
    }));
    setNovaAberta(true);
  }, [pessoaIdPorPet, petSelecionado, pets, setForm, setNovaAberta, setTutorFormSelecionado]);

  const salvarVacina = useCallback(async () => {
    if (!form.pet_id || !form.nome_vacina || !form.data_aplicacao) return;

    setSalvando(true);
    setErro(null);

    try {
      await vetApi.registrarVacina({
        pet_id: form.pet_id,
        consulta_id: consultaIdQuery ? Number(consultaIdQuery) : undefined,
        agendamento_id: agendamentoIdQuery ? Number(agendamentoIdQuery) : undefined,
        nome_vacina: form.nome_vacina,
        fabricante: form.fabricante || undefined,
        lote: form.lote || undefined,
        data_aplicacao: form.data_aplicacao,
        data_proxima_dose: form.proxima_dose || sugestaoDose?.proximaDose || undefined,
        veterinario_responsavel: form.veterinario_responsavel || undefined,
        observacoes: form.observacoes || undefined,
      });

      fecharModalVacina();
      if (form.pet_id === petSelecionado) await carregarVacinasPet();
      await carregarVencendo();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar vacina.");
    } finally {
      setSalvando(false);
    }
  }, [
    agendamentoIdQuery,
    carregarVacinasPet,
    carregarVencendo,
    consultaIdQuery,
    fecharModalVacina,
    form,
    petSelecionado,
    setErro,
    setSalvando,
    sugestaoDose?.proximaDose,
  ]);

  return {
    abrirRegistroPrimeiraVacina,
    fecharModalVacina,
    salvarVacina,
    selecionarTutorFiltro,
    selecionarTutorForm,
    setCampo,
  };
}
