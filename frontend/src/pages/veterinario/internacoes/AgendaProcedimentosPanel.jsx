import AgendaProcedimentoForm from "./AgendaProcedimentoForm";
import AgendaProcedimentosLista from "./AgendaProcedimentosLista";

export default function AgendaProcedimentosPanel({
  agendaForm,
  setAgendaForm,
  internacoesOrdenadas,
  internacaoSelecionadaAgenda,
  agendaCarregando,
  agendaOrdenada,
  internacaoPorId,
  salvando,
  onAdicionarProcedimentoAgenda,
  onAbrirInsumoRapido,
  onReabrirProcedimento,
  onAbrirModalFeito,
  onRemoverProcedimentoAgenda,
}) {
  return (
    <div className="space-y-3">
      <AgendaProcedimentoForm
        agendaForm={agendaForm}
        setAgendaForm={setAgendaForm}
        internacoesOrdenadas={internacoesOrdenadas}
        internacaoSelecionadaAgenda={internacaoSelecionadaAgenda}
        salvando={salvando}
        onAdicionarProcedimentoAgenda={onAdicionarProcedimentoAgenda}
        onAbrirInsumoRapido={onAbrirInsumoRapido}
      />
      <AgendaProcedimentosLista
        agendaCarregando={agendaCarregando}
        agendaOrdenada={agendaOrdenada}
        internacaoPorId={internacaoPorId}
        salvando={salvando}
        onReabrirProcedimento={onReabrirProcedimento}
        onAbrirModalFeito={onAbrirModalFeito}
        onRemoverProcedimentoAgenda={onRemoverProcedimentoAgenda}
      />
    </div>
  );
}
