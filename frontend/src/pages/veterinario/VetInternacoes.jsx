import InternacoesAlert from "./internacoes/InternacoesAlert";
import InternacoesConteudo from "./internacoes/InternacoesConteudo";
import HistoricoInternacoesFiltros from "./internacoes/HistoricoInternacoesFiltros";
import InternacoesHeader from "./internacoes/InternacoesHeader";
import InternacoesModais from "./internacoes/InternacoesModais";
import InternacoesTabs from "./internacoes/InternacoesTabs";
import useInternacoesController from "./internacoes/useInternacoesController";

export default function VetInternacoes() {
  const internacoes = useInternacoesController();

  return (
    <div className="p-6 space-y-5">
      <InternacoesHeader onNovaInternacao={internacoes.abrirNovaInternacao} />

      <InternacoesTabs aba={internacoes.aba} onChangeAba={internacoes.setAba} />

      <InternacoesAlert erro={internacoes.erro} onClose={() => internacoes.setErro(null)} />

      {internacoes.aba === "historico" && (
        <HistoricoInternacoesFiltros
          pessoas={internacoes.pessoas}
          petsHistoricoDaPessoa={internacoes.petsHistoricoDaPessoa}
          filtroDataAltaInicio={internacoes.filtroDataAltaInicio}
          filtroDataAltaFim={internacoes.filtroDataAltaFim}
          filtroPessoaHistorico={internacoes.filtroPessoaHistorico}
          filtroPetHistorico={internacoes.filtroPetHistorico}
          onChangeDataAltaInicio={internacoes.setFiltroDataAltaInicio}
          onChangeDataAltaFim={internacoes.setFiltroDataAltaFim}
          onChangePessoaHistorico={internacoes.selecionarPessoaHistorico}
          onChangePetHistorico={internacoes.setFiltroPetHistorico}
        />
      )}

      <InternacoesConteudo
        aba={internacoes.aba}
        agendaCarregando={internacoes.agendaCarregando}
        agendaForm={internacoes.agendaForm}
        agendaOrdenada={internacoes.agendaOrdenada}
        centroAba={internacoes.centroAba}
        carregando={internacoes.carregando}
        evolucoes={internacoes.evolucoes}
        expandida={internacoes.expandida}
        indicadoresInternacao={internacoes.indicadoresInternacao}
        internacaoPorId={internacoes.internacaoPorId}
        internacaoSelecionadaAgenda={internacoes.internacaoSelecionadaAgenda}
        internacoes={internacoes.internacoes}
        internacoesOrdenadas={internacoes.internacoesOrdenadas}
        mapaInternacao={internacoes.mapaInternacao}
        onAbrirAlta={internacoes.setModalAlta}
        onAbrirDetalhe={internacoes.abrirDetalhe}
        onAbrirEvolucao={internacoes.setModalEvolucao}
        onAbrirFichaPet={internacoes.onAbrirFichaPet}
        onAbrirHistoricoPet={internacoes.abrirHistoricoPet}
        onAbrirInsumoRapido={internacoes.abrirModalInsumoRapido}
        onAbrirModalFeito={internacoes.abrirModalFeito}
        onAdicionarProcedimentoAgenda={internacoes.adicionarProcedimentoAgenda}
        onChangeCentroAba={internacoes.setCentroAba}
        onReabrirProcedimento={internacoes.reabrirProcedimento}
        onRemoverProcedimentoAgenda={internacoes.removerProcedimentoAgenda}
        onSelecionarInternacaoMapa={internacoes.selecionarInternacaoNoMapa}
        procedimentosInternacao={internacoes.procedimentosInternacao}
        salvando={internacoes.salvando}
        setAgendaForm={internacoes.setAgendaForm}
        setTotalBaias={internacoes.setTotalBaias}
        totalBaias={internacoes.totalBaias}
      />

      <InternacoesModais
        carregandoHistoricoPet={internacoes.carregandoHistoricoPet}
        consultaIdQuery={internacoes.consultaIdQuery}
        formAlta={internacoes.formAlta}
        formEvolucao={internacoes.formEvolucao}
        formFeito={internacoes.formFeito}
        formInsumoRapido={internacoes.formInsumoRapido}
        formNova={internacoes.formNova}
        historicoPet={internacoes.historicoPet}
        insumoRapidoSelecionado={internacoes.insumoRapidoSelecionado}
        internacaoPorId={internacoes.internacaoPorId}
        internacoesOrdenadas={internacoes.internacoesOrdenadas}
        mapaInternacao={internacoes.mapaInternacao}
        modalAlta={internacoes.modalAlta}
        modalEvolucao={internacoes.modalEvolucao}
        modalFeito={internacoes.modalFeito}
        modalHistoricoPet={internacoes.modalHistoricoPet}
        modalInsumoRapido={internacoes.modalInsumoRapido}
        modalNova={internacoes.modalNova}
        onCloseAlta={() => internacoes.setModalAlta(null)}
        onCloseEvolucao={() => internacoes.setModalEvolucao(null)}
        onCloseFeito={() => internacoes.setModalFeito(null)}
        onCloseHistoricoPet={() => internacoes.setModalHistoricoPet(null)}
        onCloseInsumoRapido={() => internacoes.setModalInsumoRapido(false)}
        onCloseNova={internacoes.fecharModalNovaInternacao}
        onConfirmAlta={internacoes.darAlta}
        onConfirmEvolucao={internacoes.registrarEvolucao}
        onConfirmFeito={internacoes.confirmarProcedimentoFeito}
        onConfirmInsumoRapido={internacoes.confirmarInsumoRapido}
        onConfirmNova={internacoes.criarInternacao}
        onHideNovaForNovoPet={() => internacoes.setModalNova(false)}
        petsDaPessoa={internacoes.petsDaPessoa}
        retornoNovoPet={internacoes.retornoNovoPet}
        salvando={internacoes.salvando}
        setFormAlta={internacoes.setFormAlta}
        setFormEvolucao={internacoes.setFormEvolucao}
        setFormFeito={internacoes.setFormFeito}
        setFormInsumoRapido={internacoes.setFormInsumoRapido}
        setFormNova={internacoes.setFormNova}
        setInsumoRapidoSelecionado={internacoes.setInsumoRapidoSelecionado}
        setTotalBaias={internacoes.setTotalBaias}
        setTutorNovaSelecionado={internacoes.setTutorNovaSelecionado}
        totalBaias={internacoes.totalBaias}
        tutorAtualInternacao={internacoes.tutorAtualInternacao}
        tutorNovaSelecionado={internacoes.tutorNovaSelecionado}
        veterinarios={internacoes.veterinarios}
      />
    </div>
  );
}
