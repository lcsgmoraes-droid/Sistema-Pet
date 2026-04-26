import { useCallback } from "react";

import { vetApi } from "../vetApi";
import { FORM_FEITO_INICIAL } from "./internacoesInitialState";
import { parseQuantity } from "./internacaoUtils";

function horarioAtualLocal() {
  const agora = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return `${agora.getFullYear()}-${pad(agora.getMonth() + 1)}-${pad(agora.getDate())}T${pad(agora.getHours())}:${pad(agora.getMinutes())}`;
}

export function useInternacoesProcedimentoFeitoAcoes({
  carregarDetalheInternacao,
  expandida,
  formFeito,
  modalFeito,
  setAgendaProcedimentos,
  setErro,
  setFormFeito,
  setModalFeito,
  setSalvando,
}) {
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
      setErro("Informe o horario da execucao.");
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
      setErro(e?.response?.data?.detail ?? "Erro ao registrar procedimento concluido.");
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

  return {
    abrirModalFeito,
    confirmarProcedimentoFeito,
  };
}
