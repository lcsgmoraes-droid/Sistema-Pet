import { useEffect, useMemo, useState } from "react";

import { vetApi } from "../vetApi";
import { FORM_EXAME_ANEXADO_INICIAL } from "./examesAnexadosUtils";

export function useExamesAnexadosNovoExame({
  acaoQuery,
  agendamentoIdQuery,
  carregar,
  consultaIdQuery,
  navigate,
  novoPetIdQuery,
  petIdQuery,
  pets,
  tutorIdQuery,
  tutorNomeQuery,
}) {
  const [novaAberta, setNovaAberta] = useState(false);
  const [salvandoNovo, setSalvandoNovo] = useState(false);
  const [erroNovo, setErroNovo] = useState("");
  const [tutorFormSelecionado, setTutorFormSelecionado] = useState(null);
  const [form, setForm] = useState(FORM_EXAME_ANEXADO_INICIAL);
  const [arquivoNovo, setArquivoNovo] = useState(null);

  const petsDoTutor = useMemo(() => {
    if (!tutorFormSelecionado?.id) return [];
    return pets.filter(
      (pet) => String(pet.cliente_id) === String(tutorFormSelecionado.id) && pet.ativo !== false
    );
  }, [pets, tutorFormSelecionado]);

  useEffect(() => {
    const petIdAlvo = novoPetIdQuery || petIdQuery;
    if (!petIdAlvo || !pets.length) return;

    const petEncontrado = pets.find((pet) => String(pet.id) === String(petIdAlvo));
    if (!petEncontrado) return;

    const tutor = petEncontrado?.cliente_id
      ? {
          id: String(petEncontrado.cliente_id),
          nome: petEncontrado.cliente_nome ?? `Tutor #${petEncontrado.cliente_id}`,
          telefone: petEncontrado.cliente_telefone ?? "",
          celular: petEncontrado.cliente_celular ?? "",
        }
      : null;

    setTutorFormSelecionado(tutor);
    setForm((prev) => ({
      ...prev,
      pet_id: String(petEncontrado.id),
    }));

    if (acaoQuery === "novo" || novoPetIdQuery) {
      setNovaAberta(true);
    }
  }, [petIdQuery, novoPetIdQuery, acaoQuery, pets]);

  useEffect(() => {
    if (!tutorIdQuery || tutorFormSelecionado?.id) return;
    setTutorFormSelecionado({
      id: String(tutorIdQuery),
      nome: tutorNomeQuery || `Tutor #${tutorIdQuery}`,
    });
  }, [tutorIdQuery, tutorNomeQuery, tutorFormSelecionado]);

  function abrirNovoExame() {
    setErroNovo("");
    setArquivoNovo(null);
    setNovaAberta(true);
  }

  function fecharNovoExame() {
    setNovaAberta(false);
    setErroNovo("");
    setTutorFormSelecionado(null);
    setForm(FORM_EXAME_ANEXADO_INICIAL);
    setArquivoNovo(null);

    if (acaoQuery === "novo" || petIdQuery || novoPetIdQuery || agendamentoIdQuery || consultaIdQuery) {
      navigate("/veterinario/exames", { replace: true });
    }
  }

  async function salvarExame() {
    if (!form.pet_id || !form.nome) return;
    setSalvandoNovo(true);
    setErroNovo("");

    try {
      const res = await vetApi.criarExame({
        pet_id: Number(form.pet_id),
        consulta_id: consultaIdQuery ? Number(consultaIdQuery) : undefined,
        agendamento_id: agendamentoIdQuery ? Number(agendamentoIdQuery) : undefined,
        tipo: form.tipo,
        nome: form.nome,
        data_solicitacao: form.data_solicitacao || undefined,
        laboratorio: form.laboratorio || undefined,
        observacoes: form.observacoes || undefined,
      });

      if (arquivoNovo) {
        await vetApi.uploadArquivoExame(res.data.id, arquivoNovo);
        try {
          await vetApi.processarArquivoExameIA(res.data.id);
        } catch {}
      }

      fecharNovoExame();
      await carregar();
    } catch (e) {
      setErroNovo(e?.response?.data?.detail || "Erro ao registrar exame.");
    } finally {
      setSalvandoNovo(false);
    }
  }

  return {
    abrirNovoExame,
    erroNovo,
    fecharNovoExame,
    form,
    novaAberta,
    petsDoTutor,
    salvarExame,
    salvandoNovo,
    setArquivoNovo,
    setForm,
    setTutorFormSelecionado,
    tutorFormSelecionado,
  };
}
