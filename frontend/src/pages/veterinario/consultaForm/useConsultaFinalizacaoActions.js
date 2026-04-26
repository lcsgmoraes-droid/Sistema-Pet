import { vetApi } from "../vetApi";
import {
  buildFinalizacaoPayload,
  buildItensPrescricao,
} from "./consultaFormState";

export default function useConsultaFinalizacaoActions({
  carregarTimelineConsulta,
  consultaIdAtual,
  form,
  setErro,
  setFinalizado,
  setSalvando,
  setSucesso,
}) {
  async function finalizar() {
    setSucesso(null);
    if (!consultaIdAtual) {
      setErro("Salve a consulta antes de finalizar.");
      return;
    }
    setSalvando(true);
    setErro(null);
    try {
      await vetApi.atualizarConsulta(consultaIdAtual, buildFinalizacaoPayload(form));

      if (form.prescricao_itens.length > 0) {
        const itensPrescricao = buildItensPrescricao(form.prescricao_itens);

        if (itensPrescricao.length === 0) {
          setErro("Adicione ao menos 1 item de prescricao com nome e posologia.");
          return;
        }

        await vetApi.criarPrescricao({
          consulta_id: consultaIdAtual,
          pet_id: form.pet_id ? Number.parseInt(form.pet_id) : undefined,
          veterinario_id: form.veterinario_id ? Number.parseInt(form.veterinario_id) : undefined,
          tipo_receituario: "simples",
          itens: itensPrescricao,
        });
      }

      if (form.procedimentos_realizados.length > 0) {
        const procedimentosValidos = form.procedimentos_realizados.filter((item) => item.nome?.trim());
        for (const procedimento of procedimentosValidos) {
          await vetApi.adicionarProcedimento({
            consulta_id: consultaIdAtual,
            catalogo_id: procedimento.catalogo_id ? Number.parseInt(procedimento.catalogo_id) : undefined,
            nome: procedimento.nome,
            descricao: procedimento.descricao || undefined,
            valor: procedimento.valor ? Number(String(procedimento.valor).replace(",", ".")) : undefined,
            observacoes: procedimento.observacoes || undefined,
            realizado: true,
            baixar_estoque: procedimento.baixar_estoque !== false,
          });
        }
      }

      await vetApi.finalizarConsulta(consultaIdAtual);
      setFinalizado(true);
      await carregarTimelineConsulta();
    } catch (error) {
      setErro(error?.response?.data?.detail ?? "Erro ao finalizar.");
    } finally {
      setSalvando(false);
    }
  }

  return {
    finalizar,
  };
}
