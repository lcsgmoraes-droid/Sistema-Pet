import { useCallback } from "react";

import { vetApi } from "../vetApi";
import {
  FORM_FEITO_INICIAL,
  FORM_INSUMO_RAPIDO_INICIAL,
} from "./internacoesInitialState";
import { formatQuantity, parseQuantity } from "./internacaoUtils";

function horarioAtualLocal() {
  const agora = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return `${agora.getFullYear()}-${pad(agora.getMonth() + 1)}-${pad(agora.getDate())}T${pad(agora.getHours())}:${pad(agora.getMinutes())}`;
}

export function useInternacoesProcedimentosAcoes({
  agendaForm,
  carregarAgendaProcedimentos,
  carregarDetalheInternacao,
  expandida,
  formFeito,
  formInsumoRapido,
  insumoRapidoSelecionado,
  modalFeito,
  setAgendaForm,
  setAgendaProcedimentos,
  setErro,
  setFormFeito,
  setFormInsumoRapido,
  setInsumoRapidoSelecionado,
  setModalFeito,
  setModalInsumoRapido,
  setSalvando,
  sugestaoHorario,
}) {
  const adicionarProcedimentoAgenda = useCallback(async () => {
    if (!agendaForm.internacao_id || !agendaForm.horario || !agendaForm.medicamento) {
      setErro("Preencha internação, horário e medicamento na agenda de procedimentos.");
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

  const abrirModalFeito = useCallback(
    (item) => {
      setModalFeito(item);
      setFormFeito({
        feito_por: item?.feito_por || "",
        horario_execucao: item?.horario_execucao || horarioAtualLocal(),
        observacao_execucao: item?.observacao_execucao || "",
        quantidade_prevista: item?.quantidade_prevista ?? "",
        quantidade_executada: item?.quantidade_executada ?? item?.quantidade_prevista ?? "",
        quantidade_desperdicio: item?.quantidade_desperdicio ?? "",
        unidade_quantidade: item?.unidade_quantidade ?? "",
      });
    },
    [setFormFeito, setModalFeito]
  );

  const confirmarProcedimentoFeito = useCallback(async () => {
    if (!modalFeito) return;
    if (!formFeito.feito_por.trim()) {
      setErro("Informe quem executou o procedimento.");
      return;
    }
    if (!formFeito.horario_execucao) {
      setErro("Informe o horário da execução.");
      return;
    }

    setSalvando(true);

    try {
      const response = await vetApi.concluirProcedimentoAgendaInternacao(modalFeito.id, {
        quantidade_prevista: parseQuantity(formFeito.quantidade_prevista) ?? undefined,
        quantidade_executada: parseQuantity(formFeito.quantidade_executada) ?? undefined,
        quantidade_desperdicio: parseQuantity(formFeito.quantidade_desperdicio) ?? undefined,
        unidade_quantidade: formFeito.unidade_quantidade?.trim() || undefined,
        executado_por: formFeito.feito_por.trim(),
        horario_execucao: formFeito.horario_execucao,
        observacao_execucao: formFeito.observacao_execucao?.trim() || undefined,
      });

      await carregarDetalheInternacao(
        modalFeito.internacao_id,
        String(expandida) === String(modalFeito.internacao_id)
      );

      setAgendaProcedimentos((prev) =>
        prev.map((procedimento) => {
          if (String(procedimento.id) !== String(modalFeito.id)) return procedimento;
          return response.data?.id
            ? response.data
            : {
                ...procedimento,
                feito: true,
                status: "concluido",
                feito_por: formFeito.feito_por.trim(),
                horario_execucao: formFeito.horario_execucao,
                observacao_execucao: formFeito.observacao_execucao?.trim() || "",
                quantidade_prevista: formFeito.quantidade_prevista,
                quantidade_executada: formFeito.quantidade_executada,
                quantidade_desperdicio: formFeito.quantidade_desperdicio,
                unidade_quantidade: formFeito.unidade_quantidade,
              };
        })
      );
      setModalFeito(null);
      setFormFeito({ ...FORM_FEITO_INICIAL });
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar procedimento concluído.");
    } finally {
      setSalvando(false);
    }
  }, [
    carregarDetalheInternacao,
    expandida,
    formFeito,
    modalFeito,
    setAgendaProcedimentos,
    setErro,
    setFormFeito,
    setModalFeito,
    setSalvando,
  ]);

  const abrirModalInsumoRapido = useCallback(
    (internacaoId = "") => {
      setModalInsumoRapido(true);
      setInsumoRapidoSelecionado(null);
      setFormInsumoRapido({
        ...FORM_INSUMO_RAPIDO_INICIAL,
        internacao_id: internacaoId ? String(internacaoId) : "",
        horario_execucao: sugestaoHorario,
      });
    },
    [setFormInsumoRapido, setInsumoRapidoSelecionado, setModalInsumoRapido, sugestaoHorario]
  );

  const confirmarInsumoRapido = useCallback(async () => {
    if (!formInsumoRapido.internacao_id) {
      setErro("Selecione o internado para lançar o insumo.");
      return;
    }
    if (!insumoRapidoSelecionado?.id) {
      setErro("Selecione o insumo/produto utilizado.");
      return;
    }
    if (!formInsumoRapido.responsavel.trim()) {
      setErro("Informe quem realizou o uso do insumo.");
      return;
    }

    const quantidadeUtilizada = parseQuantity(formInsumoRapido.quantidade_utilizada);
    const quantidadeDesperdicio = parseQuantity(formInsumoRapido.quantidade_desperdicio) ?? 0;
    const quantidadeConsumida = (quantidadeUtilizada ?? 0) + quantidadeDesperdicio;

    if (!quantidadeUtilizada || quantidadeUtilizada <= 0) {
      setErro("Informe a quantidade efetivamente utilizada do insumo.");
      return;
    }
    if (quantidadeConsumida <= 0) {
      setErro("A baixa total do insumo precisa ser maior que zero.");
      return;
    }

    setSalvando(true);
    try {
      const unidade = insumoRapidoSelecionado.unidade || "un";
      const internacaoId = String(formInsumoRapido.internacao_id);

      await vetApi.registrarProcedimentoInternacao(internacaoId, {
        status: "concluido",
        tipo_registro: "insumo",
        medicamento: `Insumo: ${insumoRapidoSelecionado.nome}`,
        dose: formatQuantity(quantidadeUtilizada, unidade),
        quantidade_prevista: quantidadeUtilizada,
        quantidade_executada: quantidadeUtilizada,
        quantidade_desperdicio: quantidadeDesperdicio || undefined,
        unidade_quantidade: unidade,
        executado_por: formInsumoRapido.responsavel.trim(),
        horario_execucao: formInsumoRapido.horario_execucao,
        observacao_execucao: formInsumoRapido.observacoes?.trim() || undefined,
        insumos: [
          {
            produto_id: insumoRapidoSelecionado.id,
            nome: insumoRapidoSelecionado.nome,
            unidade,
            quantidade: quantidadeConsumida,
            baixar_estoque: true,
          },
        ],
      });

      await carregarDetalheInternacao(Number(internacaoId), expandida === Number(internacaoId));
      setModalInsumoRapido(false);
      setInsumoRapidoSelecionado(null);
      setFormInsumoRapido({
        ...FORM_INSUMO_RAPIDO_INICIAL,
        horario_execucao: sugestaoHorario,
      });
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao lançar insumo rápido.");
    } finally {
      setSalvando(false);
    }
  }, [
    carregarDetalheInternacao,
    expandida,
    formInsumoRapido,
    insumoRapidoSelecionado,
    setErro,
    setFormInsumoRapido,
    setInsumoRapidoSelecionado,
    setModalInsumoRapido,
    setSalvando,
    sugestaoHorario,
  ]);

  const reabrirProcedimento = useCallback(() => {
    setErro("Procedimento concluído já faz parte do histórico clínico. Para corrigir, registre um novo ajuste/evolução.");
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
    abrirModalFeito,
    abrirModalInsumoRapido,
    adicionarProcedimentoAgenda,
    confirmarInsumoRapido,
    confirmarProcedimentoFeito,
    reabrirProcedimento,
    removerProcedimentoAgenda,
  };
}
