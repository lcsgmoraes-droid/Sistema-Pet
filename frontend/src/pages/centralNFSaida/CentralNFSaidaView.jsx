import CentralNFSaidaHeader from "./CentralNFSaidaHeader";
import NFSaidaCancelamentoModal from "./NFSaidaCancelamentoModal";
import NFSaidaDetalhesModal from "./NFSaidaDetalhesModal";
import NFSaidaFilters from "./NFSaidaFilters";
import NFSaidaList from "./NFSaidaList";
import SefazConsultasSessao from "./SefazConsultasSessao";
import SefazToolsPanel from "./SefazToolsPanel";

export default function CentralNFSaidaView({
  painelSefazAberto,
  setPainelSefazAberto,
  consultarChave,
  chave,
  setChave,
  consultando,
  erroConsulta,
  cfgLoading,
  cfg,
  setCfg,
  msgRotina,
  salvarRotina,
  salvandoRotina,
  sincronizarAgora,
  sincronizando,
  consultasSessao,
  listaConsultasRef,
  consultaExpandidaId,
  setConsultaExpandidaId,
  busca,
  setBusca,
  dataInicial,
  setDataInicial,
  dataFinal,
  setDataFinal,
  filtroSituacao,
  setFiltroSituacao,
  carregarNotas,
  loading,
  erro,
  notasFiltradas,
  setModalCancelar,
  excluirNota,
  reconciliarFluxoNota,
  reconciliandoNotaId,
  baixarDanfe,
  baixarXml,
  abrirDetalhes,
  notaSelecionada,
  detalheNota,
  carregandoDetalhe,
  erroDetalhe,
  fecharDetalhes,
  modalCancelar,
  justificativa,
  setJustificativa,
  cancelando,
  cancelarNota,
}) {
  return (
    <div className="p-6">
      <CentralNFSaidaHeader />

      <SefazToolsPanel
        painelSefazAberto={painelSefazAberto}
        setPainelSefazAberto={setPainelSefazAberto}
        consultarChave={consultarChave}
        chave={chave}
        setChave={setChave}
        consultando={consultando}
        erroConsulta={erroConsulta}
        cfgLoading={cfgLoading}
        cfg={cfg}
        setCfg={setCfg}
        msgRotina={msgRotina}
        salvarRotina={salvarRotina}
        salvandoRotina={salvandoRotina}
        sincronizarAgora={sincronizarAgora}
        sincronizando={sincronizando}
      />

      <SefazConsultasSessao
        consultasSessao={consultasSessao}
        listaConsultasRef={listaConsultasRef}
        consultaExpandidaId={consultaExpandidaId}
        setConsultaExpandidaId={setConsultaExpandidaId}
      />

      <NFSaidaFilters
        busca={busca}
        setBusca={setBusca}
        dataInicial={dataInicial}
        setDataInicial={setDataInicial}
        dataFinal={dataFinal}
        setDataFinal={setDataFinal}
        filtroSituacao={filtroSituacao}
        setFiltroSituacao={setFiltroSituacao}
        carregarNotas={carregarNotas}
        loading={loading}
      />

      <NFSaidaList
        erro={erro}
        loading={loading}
        notasFiltradas={notasFiltradas}
        busca={busca}
        filtroSituacao={filtroSituacao}
        dataInicial={dataInicial}
        dataFinal={dataFinal}
        setModalCancelar={setModalCancelar}
        excluirNota={excluirNota}
        reconciliarFluxoNota={reconciliarFluxoNota}
        reconciliandoNotaId={reconciliandoNotaId}
        baixarDanfe={baixarDanfe}
        baixarXml={baixarXml}
        abrirDetalhes={abrirDetalhes}
      />

      <NFSaidaDetalhesModal
        notaSelecionada={notaSelecionada}
        detalheNota={detalheNota}
        carregandoDetalhe={carregandoDetalhe}
        erroDetalhe={erroDetalhe}
        fecharDetalhes={fecharDetalhes}
        baixarDanfe={baixarDanfe}
        baixarXml={baixarXml}
      />

      <NFSaidaCancelamentoModal
        modalCancelar={modalCancelar}
        setModalCancelar={setModalCancelar}
        justificativa={justificativa}
        setJustificativa={setJustificativa}
        cancelando={cancelando}
        cancelarNota={cancelarNota}
      />
    </div>
  );
}
