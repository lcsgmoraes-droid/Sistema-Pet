import AgendaProcedimentosPanel from "./AgendaProcedimentosPanel";
import CentroInternacaoTabs from "./CentroInternacaoTabs";
import InternacoesListaPanel from "./InternacoesListaPanel";
import { InternacoesEmptyState, InternacoesLoadingState } from "./InternacoesLoadingEmpty";
import InternacoesWidgetPanel from "./InternacoesWidgetPanel";
import MapaInternacaoPanel from "./MapaInternacaoPanel";

export default function InternacoesConteudo({
  aba,
  agendaCarregando,
  agendaForm,
  agendaOrdenada,
  centroAba,
  carregando,
  evolucoes,
  expandida,
  indicadoresInternacao,
  internacaoPorId,
  internacaoSelecionadaAgenda,
  internacoes,
  internacoesOrdenadas,
  mapaInternacao,
  onAbrirAlta,
  onAbrirDetalhe,
  onAbrirEvolucao,
  onAbrirFichaPet,
  onAbrirHistoricoPet,
  onAbrirInsumoRapido,
  onAbrirModalFeito,
  onAdicionarProcedimentoAgenda,
  onChangeCentroAba,
  onReabrirProcedimento,
  onRemoverProcedimentoAgenda,
  onSelecionarInternacaoMapa,
  procedimentosInternacao,
  salvando,
  setAgendaForm,
  setTotalBaias,
  totalBaias,
}) {
  if (carregando) {
    return <InternacoesLoadingState />;
  }

  if (internacoes.length === 0) {
    return <InternacoesEmptyState aba={aba} />;
  }

  return (
    <div className="space-y-3">
      {aba === "ativas" && (
        <CentroInternacaoTabs
          centroAba={centroAba}
          onChangeCentroAba={onChangeCentroAba}
        />
      )}

      {aba === "ativas" && centroAba === "mapa" && (
        <MapaInternacaoPanel
          mapaInternacao={mapaInternacao}
          totalBaias={totalBaias}
          setTotalBaias={setTotalBaias}
          onSelecionarInternacao={onSelecionarInternacaoMapa}
        />
      )}

      {(aba === "historico" || (aba === "ativas" && centroAba === "lista")) && (
        <InternacoesListaPanel
          aba={aba}
          internacoesOrdenadas={internacoesOrdenadas}
          expandida={expandida}
          evolucoes={evolucoes}
          procedimentosInternacao={procedimentosInternacao}
          onAbrirDetalhe={onAbrirDetalhe}
          onAbrirInsumoRapido={onAbrirInsumoRapido}
          onAbrirEvolucao={onAbrirEvolucao}
          onAbrirAlta={onAbrirAlta}
          onAbrirFichaPet={onAbrirFichaPet}
          onAbrirHistoricoPet={onAbrirHistoricoPet}
        />
      )}

      {aba === "ativas" && centroAba === "widget" && (
        <InternacoesWidgetPanel
          indicadoresInternacao={indicadoresInternacao}
          internacoesOrdenadas={internacoesOrdenadas}
        />
      )}

      {aba === "ativas" && centroAba === "agenda" && (
        <AgendaProcedimentosPanel
          agendaForm={agendaForm}
          setAgendaForm={setAgendaForm}
          internacoesOrdenadas={internacoesOrdenadas}
          internacaoSelecionadaAgenda={internacaoSelecionadaAgenda}
          agendaCarregando={agendaCarregando}
          agendaOrdenada={agendaOrdenada}
          internacaoPorId={internacaoPorId}
          salvando={salvando}
          onAdicionarProcedimentoAgenda={onAdicionarProcedimentoAgenda}
          onAbrirInsumoRapido={onAbrirInsumoRapido}
          onReabrirProcedimento={onReabrirProcedimento}
          onAbrirModalFeito={onAbrirModalFeito}
          onRemoverProcedimentoAgenda={onRemoverProcedimentoAgenda}
        />
      )}
    </div>
  );
}
