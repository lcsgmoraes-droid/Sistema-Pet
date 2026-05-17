import { useCallback } from "react";

import { vetApi } from "../vetApi";
import {
  FORM_CONSULTORIO_AGENDA_INICIAL,
  inserirConsultorioAgenda,
  montarPayloadConsultorioAgenda,
} from "./agendaConsultoriosUtils";
import { FORM_NOVO_INICIAL, isoDate, normalizarTipoAgendamento } from "./agendaUtils";

export function useAgendaFormularioAcoes({
  agendamentoEditandoId,
  bloqueioCamposAgendamento,
  carregar,
  conflitoHorarioSelecionado,
  dataRef,
  formNovo,
  navigate,
  petSelecionadoModal,
  returnToQuery,
  setAgendaDiaModal,
  setAgendamentoEditandoId,
  setAgendamentoSelecionado,
  setConsultorioInlineAberto,
  setConsultorioInlineErro,
  setConsultorioInlineForm,
  setConsultorios,
  setErro,
  setErroNovo,
  setFormNovo,
  setNovoAberto,
  setPetsDoTutor,
  setSalvandoConsultorioInline,
  setSalvandoNovo,
  setTutorSelecionado,
  sugerirHoraLivre,
  tutorSelecionado,
  consultorioInlineForm,
}) {
  function voltarParaOrigemSeExistir() {
    if (returnToQuery && String(returnToQuery).startsWith("/veterinario/consultas/")) {
      navigate(returnToQuery, { replace: true });
      return true;
    }
    return false;
  }

  const abrirModalNovo = useCallback(
    (dataBase = dataRef, agendamentoBase = null) => {
      setErro(null);
      setErroNovo(null);
      setAgendamentoSelecionado(null);
      setConsultorioInlineAberto(false);
      setConsultorioInlineErro(null);
      setConsultorioInlineForm(FORM_CONSULTORIO_AGENDA_INICIAL);
      setNovoAberto(true);

      if (agendamentoBase) {
        const dataHoraTexto = String(agendamentoBase.data_hora || "");
        setAgendamentoEditandoId(agendamentoBase.id);
        setTutorSelecionado({
          id: agendamentoBase.cliente_id,
          nome: agendamentoBase.cliente_nome || `Tutor #${agendamentoBase.cliente_id}`,
        });
        setFormNovo({
          pet_id: String(agendamentoBase.pet_id || ""),
          veterinario_id: String(agendamentoBase.veterinario_id || ""),
          consultorio_id: String(agendamentoBase.consultorio_id || ""),
          consulta_origem_id: String(agendamentoBase.consulta_origem_id || ""),
          tipo: normalizarTipoAgendamento(agendamentoBase.tipo),
          data: dataHoraTexto.slice(0, 10) || isoDate(dataBase),
          hora: dataHoraTexto.slice(11, 16) || sugerirHoraLivre(dataBase),
          motivo: agendamentoBase.motivo || "",
          emergencia: Boolean(agendamentoBase.is_emergencia),
        });
        return;
      }

      setAgendamentoEditandoId(null);
      setTutorSelecionado(null);
      setPetsDoTutor([]);
      setFormNovo({
        ...FORM_NOVO_INICIAL,
        data: isoDate(dataBase),
        hora: sugerirHoraLivre(dataBase),
      });
    },
    [
      dataRef,
      setAgendamentoEditandoId,
      setAgendamentoSelecionado,
      setConsultorioInlineAberto,
      setConsultorioInlineErro,
      setConsultorioInlineForm,
      setErro,
      setErroNovo,
      setFormNovo,
      setNovoAberto,
      setPetsDoTutor,
      setTutorSelecionado,
      sugerirHoraLivre,
    ]
  );

  const criarAgendamento = useCallback(async () => {
    if (!formNovo.pet_id || !formNovo.data || !formNovo.hora) return;
    if (bloqueioCamposAgendamento.veterinario || bloqueioCamposAgendamento.consultorio || conflitoHorarioSelecionado) {
      return;
    }

    setSalvandoNovo(true);
    setErroNovo(null);
    try {
      const payload = {
        pet_id: Number(formNovo.pet_id),
        cliente_id: tutorSelecionado?.id || petSelecionadoModal?.cliente_id,
        veterinario_id: formNovo.veterinario_id ? Number(formNovo.veterinario_id) : undefined,
        consultorio_id: formNovo.consultorio_id ? Number(formNovo.consultorio_id) : undefined,
        consulta_origem_id: formNovo.consulta_origem_id ? Number(formNovo.consulta_origem_id) : undefined,
        data_hora: `${formNovo.data}T${formNovo.hora}`,
        tipo: normalizarTipoAgendamento(formNovo.tipo),
        motivo: formNovo.motivo || undefined,
        is_emergencia: formNovo.emergencia,
      };

      if (agendamentoEditandoId) {
        await vetApi.atualizarAgendamento(agendamentoEditandoId, payload);
      } else {
        await vetApi.criarAgendamento(payload);
      }

      setNovoAberto(false);
      setConsultorioInlineAberto(false);
      setConsultorioInlineErro(null);
      setConsultorioInlineForm(FORM_CONSULTORIO_AGENDA_INICIAL);
      setAgendamentoEditandoId(null);
      setTutorSelecionado(null);
      setPetsDoTutor([]);
      setAgendaDiaModal([]);
      setFormNovo(FORM_NOVO_INICIAL);
      await carregar();
      voltarParaOrigemSeExistir();
    } catch (e) {
      setErroNovo(e?.response?.data?.detail ?? "Erro ao criar agendamento.");
    } finally {
      setSalvandoNovo(false);
    }
  }, [
    agendamentoEditandoId,
    bloqueioCamposAgendamento.consultorio,
    bloqueioCamposAgendamento.veterinario,
    carregar,
    conflitoHorarioSelecionado,
    formNovo,
    navigate,
    petSelecionadoModal?.cliente_id,
    returnToQuery,
    setAgendaDiaModal,
    setAgendamentoEditandoId,
    setConsultorioInlineAberto,
    setConsultorioInlineErro,
    setConsultorioInlineForm,
    setErroNovo,
    setFormNovo,
    setNovoAberto,
    setPetsDoTutor,
    setSalvandoNovo,
    setTutorSelecionado,
    tutorSelecionado?.id,
  ]);

  const fecharModalNovo = useCallback(() => {
    setNovoAberto(false);
    setErroNovo(null);
    setConsultorioInlineAberto(false);
    setConsultorioInlineErro(null);
    setConsultorioInlineForm(FORM_CONSULTORIO_AGENDA_INICIAL);
    setAgendamentoEditandoId(null);
    setTutorSelecionado(null);
    setPetsDoTutor([]);
    setAgendaDiaModal([]);
    setFormNovo(FORM_NOVO_INICIAL);
    voltarParaOrigemSeExistir();
  }, [
    navigate,
    returnToQuery,
    setAgendaDiaModal,
    setAgendamentoEditandoId,
    setConsultorioInlineAberto,
    setConsultorioInlineErro,
    setConsultorioInlineForm,
    setErroNovo,
    setFormNovo,
    setNovoAberto,
    setPetsDoTutor,
    setTutorSelecionado,
  ]);

  const abrirConsultorioInline = useCallback(() => {
    setConsultorioInlineErro(null);
    setConsultorioInlineForm(FORM_CONSULTORIO_AGENDA_INICIAL);
    setConsultorioInlineAberto(true);
  }, [setConsultorioInlineAberto, setConsultorioInlineErro, setConsultorioInlineForm]);

  const fecharConsultorioInline = useCallback(() => {
    setConsultorioInlineAberto(false);
    setConsultorioInlineErro(null);
    setConsultorioInlineForm(FORM_CONSULTORIO_AGENDA_INICIAL);
  }, [setConsultorioInlineAberto, setConsultorioInlineErro, setConsultorioInlineForm]);

  const atualizarConsultorioInlineForm = useCallback(
    (patch) => {
      setConsultorioInlineForm((prev) => ({ ...prev, ...patch }));
    },
    [setConsultorioInlineForm]
  );

  const salvarConsultorioInline = useCallback(async () => {
    const payload = montarPayloadConsultorioAgenda(consultorioInlineForm);
    if (!payload.nome) {
      setConsultorioInlineErro("Informe o nome do consultorio.");
      return;
    }

    try {
      setSalvandoConsultorioInline(true);
      setConsultorioInlineErro(null);
      const resposta = await vetApi.criarConsultorio(payload);
      const consultorioCriado = resposta.data;

      setConsultorios((prev) => inserirConsultorioAgenda(prev, consultorioCriado));
      setFormNovo((prev) => ({
        ...prev,
        consultorio_id: consultorioCriado?.id ? String(consultorioCriado.id) : prev.consultorio_id,
      }));
      fecharConsultorioInline();
    } catch (e) {
      setConsultorioInlineErro(e?.response?.data?.detail || "Erro ao cadastrar consultorio.");
    } finally {
      setSalvandoConsultorioInline(false);
    }
  }, [
    consultorioInlineForm,
    fecharConsultorioInline,
    setConsultorioInlineErro,
    setConsultorios,
    setFormNovo,
    setSalvandoConsultorioInline,
  ]);

  return {
    abrirConsultorioInline,
    abrirModalNovo,
    atualizarConsultorioInlineForm,
    fecharConsultorioInline,
    criarAgendamento,
    fecharModalNovo,
    salvarConsultorioInline,
  };
}
