import ExtratoAtendimentoPanel from "../extratos/ExtratoAtendimentoPanel";
import OrcamentoMvpPanel from "../orcamentos/OrcamentoMvpPanel";

export default function ConsultaFinanceiroTab({ consulta }) {
  const contextoOrcamento = {
    consultaId: consulta.consultaIdAtual,
    petId: consulta.form.pet_id ? Number(consulta.form.pet_id) : null,
    clienteId: consulta.tutorSelecionado?.id ?? null,
    veterinarioId: consulta.form.veterinario_id ? Number(consulta.form.veterinario_id) : null,
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
        <h2 className="text-lg font-semibold text-slate-800">Valores desta consulta</h2>
        <p className="mt-1 text-sm text-slate-600">
          Esta área é opcional e serve para planejar e conferir valores. Salvar um orçamento não
          registra uma venda ou cobrança.
        </p>
      </div>

      <div className="space-y-3">
        <div>
          <h3 className="font-semibold text-slate-800">1. Orçamento: o que você pretende cobrar</h3>
          <p className="mt-1 text-sm text-slate-600">
            {consulta.modoSomenteLeitura
              ? "A consulta está assinada; o orçamento pode ser apenas consultado."
              : "Escolha um procedimento ou produto, informe a quantidade, clique em adicionar e revise o preço. Depois, use “Salvar orçamento”. Os valores são uma previsão."}
          </p>
        </div>
        <OrcamentoMvpPanel
          contexto={contextoOrcamento}
          procedimentosCatalogo={consulta.procedimentosCatalogo}
          modoSomenteLeitura={consulta.modoSomenteLeitura}
          titulo="Orçamento da consulta"
        />
      </div>

      <div className="space-y-3">
        <div>
          <h3 className="font-semibold text-slate-800">2. Extrato: o que foi realizado</h3>
          <p className="mt-1 text-sm text-slate-600">
            O extrato reúne automaticamente os procedimentos e insumos registrados como realizados.
            Use “Atualizar” para conferir os dados recentes e exporte o resumo em PDF ou Excel, se
            precisar. Ele não é o prontuário nem a receita.
          </p>
        </div>
        <ExtratoAtendimentoPanel
          contexto={{ consultaId: consulta.consultaIdAtual }}
          titulo="Extrato financeiro da consulta"
        />
      </div>
    </div>
  );
}
