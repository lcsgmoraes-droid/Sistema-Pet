import { useCallback } from "react";

import { vetApi } from "../vetApi";
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
  setAgendaDiaModal,
  setAgendamentoEditandoId,
  setAgendamentoSelecionado,
  setErro,
  setErroNovo,
  setFormNovo,
  setNovoAberto,
  setPetsDoTutor,
  setSalvandoNovo,
  setTutorSelecionado,
  sugerirHoraLivre,
  tutorSelecionado,
}) {
  const abrirModalNovo = useCallback(
    (dataBase = dataRef, agendamentoBase = null) => {
      setErro(null);
      setErroNovo(null);
      setAgendamentoSelecionado(null);
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
      setAgendamentoEditandoId(null);
      setTutorSelecionado(null);
      setPetsDoTutor([]);
      setAgendaDiaModal([]);
      setFormNovo(FORM_NOVO_INICIAL);
      await carregar();
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
    petSelecionadoModal?.cliente_id,
    setAgendaDiaModal,
    setAgendamentoEditandoId,
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
    setAgendamentoEditandoId(null);
    setTutorSelecionado(null);
    setPetsDoTutor([]);
    setAgendaDiaModal([]);
    setFormNovo(FORM_NOVO_INICIAL);
  }, [
    setAgendaDiaModal,
    setAgendamentoEditandoId,
    setErroNovo,
    setFormNovo,
    setNovoAberto,
    setPetsDoTutor,
    setTutorSelecionado,
  ]);

  const abrirConfiguracoesVet = useCallback(() => {
    setNovoAberto(false);
    navigate("/veterinario/configuracoes");
  }, [navigate, setNovoAberto]);

  return {
    abrirConfiguracoesVet,
    abrirModalNovo,
    criarAgendamento,
    fecharModalNovo,
  };
}
