import { useCallback } from "react";

import { vetApi } from "../vetApi";
import { FORM_INSUMO_RAPIDO_INICIAL } from "./internacoesInitialState";
import { formatQuantity, parseQuantity } from "./internacaoUtils";

export function useInternacoesInsumoRapidoAcoes({
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
}) {
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
      setErro("Selecione o internado para lancar o insumo.");
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
      setErro(e?.response?.data?.detail ?? "Erro ao lancar insumo rapido.");
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

  return {
    abrirModalInsumoRapido,
    confirmarInsumoRapido,
  };
}
