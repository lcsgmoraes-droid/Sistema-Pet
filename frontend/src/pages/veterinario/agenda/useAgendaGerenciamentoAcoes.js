import { useCallback } from "react";

import { vetApi } from "../vetApi";
import { normalizarTipoAgendamento } from "./agendaUtils";

export function useAgendaGerenciamentoAcoes({
  agendamentoSelecionado,
  carregar,
  navigate,
  setAbrindoAgendamentoId,
  setAgendamentoSelecionado,
  setErro,
  setErroNovo,
  setProcessandoAgendamentoId,
}) {
  const abrirGerenciarAgendamento = useCallback(
    (ag) => {
      setErro(null);
      setAgendamentoSelecionado(ag);
    },
    [setAgendamentoSelecionado, setErro]
  );

  const fecharGerenciarAgendamento = useCallback(() => {
    setAgendamentoSelecionado(null);
  }, [setAgendamentoSelecionado]);

  const abrirFluxoAgendamento = useCallback(
    async (ag) => {
      if (!ag?.id) return;
      const tipoAgendamento = normalizarTipoAgendamento(ag.tipo);
      setErro(null);
      setErroNovo(null);
      setAbrindoAgendamentoId(ag.id);

      try {
        if (ag.consulta_id) {
          if (ag.status !== "em_atendimento" && ag.status !== "finalizado") {
            await vetApi.atualizarAgendamento(ag.id, { status: "em_atendimento" });
            await carregar();
          }
          navigate(`/veterinario/consultas/${ag.consulta_id}`);
          return;
        }

        if (tipoAgendamento === "consulta" || tipoAgendamento === "retorno") {
          const res = await vetApi.criarConsulta({
            pet_id: ag.pet_id,
            cliente_id: ag.cliente_id,
            veterinario_id: ag.veterinario_id || undefined,
            tipo: tipoAgendamento,
            agendamento_id: ag.id,
            queixa_principal: ag.motivo || undefined,
          });
          await carregar();
          navigate(`/veterinario/consultas/${res.data.id}`);
          return;
        }

        if (tipoAgendamento === "vacina") {
          navigate(`/veterinario/vacinas?pet_id=${ag.pet_id}&acao=novo&agendamento_id=${ag.id}`);
          return;
        }

        if (tipoAgendamento === "exame") {
          navigate(`/veterinario/exames?pet_id=${ag.pet_id}&acao=novo&agendamento_id=${ag.id}`);
          return;
        }

        navigate(`/veterinario/consultas/nova?pet_id=${ag.pet_id}`);
      } catch (e) {
        setErro(e?.response?.data?.detail ?? "Nao foi possivel abrir o fluxo deste agendamento.");
      } finally {
        setAbrindoAgendamentoId(null);
      }
    },
    [carregar, navigate, setAbrindoAgendamentoId, setErro, setErroNovo]
  );

  const iniciarAgendamentoSelecionado = useCallback(async () => {
    if (!agendamentoSelecionado) return;
    const ag = agendamentoSelecionado;
    setAgendamentoSelecionado(null);
    await abrirFluxoAgendamento(ag);
  }, [abrirFluxoAgendamento, agendamentoSelecionado, setAgendamentoSelecionado]);

  const voltarStatusAgendamento = useCallback(async () => {
    if (!agendamentoSelecionado?.id) return;
    setProcessandoAgendamentoId(agendamentoSelecionado.id);
    setErro(null);
    try {
      const res = await vetApi.desfazerInicioAgendamento(agendamentoSelecionado.id);
      setAgendamentoSelecionado(res.data);
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Nao foi possivel desfazer o inicio do atendimento.");
    } finally {
      setProcessandoAgendamentoId(null);
    }
  }, [
    agendamentoSelecionado?.id,
    carregar,
    setAgendamentoSelecionado,
    setErro,
    setProcessandoAgendamentoId,
  ]);

  const excluirAgendamentoSelecionado = useCallback(async () => {
    if (!agendamentoSelecionado?.id) return;
    const confirmado = window.confirm("Deseja excluir este agendamento?");
    if (!confirmado) return;
    setProcessandoAgendamentoId(agendamentoSelecionado.id);
    setErro(null);
    try {
      await vetApi.removerAgendamento(agendamentoSelecionado.id);
      setAgendamentoSelecionado(null);
      await carregar();
    } catch (e) {
      setErro(
        e?.response?.data?.detail ||
          "Nao foi possivel excluir o agendamento. Se ele ja gerou atendimento, desfaca o inicio primeiro."
      );
    } finally {
      setProcessandoAgendamentoId(null);
    }
  }, [
    agendamentoSelecionado?.id,
    carregar,
    setAgendamentoSelecionado,
    setErro,
    setProcessandoAgendamentoId,
  ]);

  return {
    abrirFluxoAgendamento,
    abrirGerenciarAgendamento,
    excluirAgendamentoSelecionado,
    fecharGerenciarAgendamento,
    iniciarAgendamentoSelecionado,
    voltarStatusAgendamento,
  };
}
