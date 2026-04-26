import AltaInternacaoModal from "./AltaInternacaoModal";
import ConcluirProcedimentoModal from "./ConcluirProcedimentoModal";
import EvolucaoInternacaoModal from "./EvolucaoInternacaoModal";
import HistoricoInternacoesPetModal from "./HistoricoInternacoesPetModal";
import InsumoRapidoInternacaoModal from "./InsumoRapidoInternacaoModal";
import NovaInternacaoModal from "./NovaInternacaoModal";

export default function InternacoesModais({
  carregandoHistoricoPet,
  consultaIdQuery,
  formAlta,
  formEvolucao,
  formFeito,
  formInsumoRapido,
  formNova,
  historicoPet,
  insumoRapidoSelecionado,
  internacaoPorId,
  internacoesOrdenadas,
  mapaInternacao,
  modalAlta,
  modalEvolucao,
  modalFeito,
  modalHistoricoPet,
  modalInsumoRapido,
  modalNova,
  onCloseAlta,
  onCloseEvolucao,
  onCloseFeito,
  onCloseHistoricoPet,
  onCloseInsumoRapido,
  onCloseNova,
  onConfirmAlta,
  onConfirmEvolucao,
  onConfirmFeito,
  onConfirmInsumoRapido,
  onConfirmNova,
  onHideNovaForNovoPet,
  petsDaPessoa,
  retornoNovoPet,
  salvando,
  setFormAlta,
  setFormEvolucao,
  setFormFeito,
  setFormInsumoRapido,
  setFormNova,
  setInsumoRapidoSelecionado,
  setTotalBaias,
  setTutorNovaSelecionado,
  totalBaias,
  tutorAtualInternacao,
  tutorNovaSelecionado,
  veterinarios,
}) {
  return (
    <>
      <NovaInternacaoModal
        isOpen={modalNova}
        consultaIdQuery={consultaIdQuery}
        tutorNovaSelecionado={tutorNovaSelecionado}
        setTutorNovaSelecionado={setTutorNovaSelecionado}
        formNova={formNova}
        setFormNova={setFormNova}
        tutorAtualInternacao={tutorAtualInternacao}
        retornoNovoPet={retornoNovoPet}
        petsDaPessoa={petsDaPessoa}
        mapaInternacao={mapaInternacao}
        totalBaias={totalBaias}
        setTotalBaias={setTotalBaias}
        onClose={onCloseNova}
        onHideForNovoPet={onHideNovaForNovoPet}
        onConfirm={onConfirmNova}
        salvando={salvando}
      />

      <AltaInternacaoModal
        isOpen={Boolean(modalAlta)}
        formAlta={formAlta}
        setFormAlta={setFormAlta}
        onClose={onCloseAlta}
        onConfirm={onConfirmAlta}
        salvando={salvando}
      />

      <EvolucaoInternacaoModal
        isOpen={Boolean(modalEvolucao)}
        formEvolucao={formEvolucao}
        setFormEvolucao={setFormEvolucao}
        onClose={onCloseEvolucao}
        onConfirm={onConfirmEvolucao}
        salvando={salvando}
      />

      <ConcluirProcedimentoModal
        procedimento={modalFeito}
        baiaExibicao={
          modalFeito
            ? (internacaoPorId.get(String(modalFeito.internacao_id))?.box || modalFeito.baia || "Sem baia")
            : "Sem baia"
        }
        formFeito={formFeito}
        setFormFeito={setFormFeito}
        veterinarios={veterinarios}
        onClose={onCloseFeito}
        onConfirm={onConfirmFeito}
        salvando={salvando}
      />

      <HistoricoInternacoesPetModal
        historicoPetInfo={modalHistoricoPet}
        historicoPet={historicoPet}
        carregando={carregandoHistoricoPet}
        onClose={onCloseHistoricoPet}
      />

      <InsumoRapidoInternacaoModal
        isOpen={modalInsumoRapido}
        onClose={onCloseInsumoRapido}
        formInsumoRapido={formInsumoRapido}
        setFormInsumoRapido={setFormInsumoRapido}
        internacoesOrdenadas={internacoesOrdenadas}
        veterinarios={veterinarios}
        insumoRapidoSelecionado={insumoRapidoSelecionado}
        setInsumoRapidoSelecionado={setInsumoRapidoSelecionado}
        onConfirm={onConfirmInsumoRapido}
        salvando={salvando}
      />
    </>
  );
}
