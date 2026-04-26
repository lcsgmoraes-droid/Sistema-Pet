import { useCallback } from "react";

import { vetApi } from "../vetApi";
import { parseQuantity } from "./internacaoUtils";

export function useInternacoesAgendaProcedimentosAcoes({
  agendaForm,
  carregarAgendaProcedimentos,
  carregarDetalheInternacao,
  expandida,
  setAgendaForm,
  setAgendaProcedimentos,
  setErro,
  setSalvando,
  sugestaoHorario,
}) {
  const adicionarProcedimentoAgenda = useCallback(async () => {
    if (!agendaForm.internacao_id || !agendaForm.horario || !agendaForm.medicamento) {
      setErro("Preencha internacao, horario e medicamento na agenda de procedimentos.");
      return;
    }

    setSalvando(true);

    try {
      const lembreteMin = Number.parseInt(agendaForm.lembrete_min || "30", 10);
      const response = await vetApi.criarProcedimentoAgendaInternacao(agendaForm.internacao_id, {
        horario_agendado: agendaForm.horario,
        medicamento: agendaForm.medicamento.trim(),
        dose: agendaForm.dose || undefined,
        quantidade_prevista: parseQuantity(agendaForm.quantidade_prevista) ?? undefined,
        unidade_quantidade: agendaForm.unidade_quantidade?.trim() || undefined,
        via: agendaForm.via || undefined,
        lembrete_min: Number.isFinite(lembreteMin) ? lembreteMin : 30,
        observacoes_agenda: agendaForm.observacoes || undefined,
      });

      if (response.data?.id) {
        setAgendaProcedimentos((prev) => [response.data, ...prev]);
      } else {
        await carregarAgendaProcedimentos();
      }
      await carregarDetalheInternacao(
        agendaForm.internacao_id,
        expandida === Number(agendaForm.internacao_id)
      );
      setAgendaForm((prev) => ({
        ...prev,
        horario: sugestaoHorario,
        medicamento: "",
        dose: "",
        quantidade_prevista: "",
        unidade_quantidade: "",
        via: "",
        observacoes: "",
      }));
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar procedimento agendado.");
    } finally {
      setSalvando(false);
    }
  }, [
    agendaForm,
    carregarAgendaProcedimentos,
    carregarDetalheInternacao,
    expandida,
    setAgendaForm,
    setAgendaProcedimentos,
    setErro,
    setSalvando,
    sugestaoHorario,
  ]);

  const reabrirProcedimento = useCallback(() => {
    setErro("Procedimento concluido ja faz parte do historico clinico. Para corrigir, registre um novo ajuste/evolucao.");
  }, [setErro]);

  const removerProcedimentoAgenda = useCallback(
    async (id) => {
      setSalvando(true);
      try {
        await vetApi.removerProcedimentoAgendaInternacao(id);
        setAgendaProcedimentos((prev) =>
          prev.filter((procedimento) => String(procedimento.id) !== String(id))
        );
      } catch (e) {
        setErro(e?.response?.data?.detail ?? "Erro ao remover procedimento da agenda.");
      } finally {
        setSalvando(false);
      }
    },
    [setAgendaProcedimentos, setErro, setSalvando]
  );

  return {
    adicionarProcedimentoAgenda,
    reabrirProcedimento,
    removerProcedimentoAgenda,
  };
}
