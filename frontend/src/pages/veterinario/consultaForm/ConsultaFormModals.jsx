import NovoPetModal from "../../../components/veterinario/NovoPetModal";
import CalculadoraDoseModal from "./CalculadoraDoseModal";
import InsumoRapidoModal from "./InsumoRapidoModal";
import NovoExameConsultaModal from "./NovoExameConsultaModal";

export default function ConsultaFormModals({
  css,
  modalInsumoAberto,
  setModalInsumoAberto,
  consultaIdAtual,
  petSelecionadoLabel,
  insumoRapidoSelecionado,
  setInsumoRapidoSelecionado,
  insumoRapidoForm,
  setInsumoRapidoForm,
  salvarInsumoRapidoConsulta,
  salvandoInsumoRapido,
  modalNovoPetAberto,
  setModalNovoPetAberto,
  tutorSelecionado,
  sugestoesEspecies,
  handleNovoPetCriado,
  modalCalculadoraAberto,
  setModalCalculadoraAberto,
  calculadoraForm,
  setCalculadoraForm,
  medicamentosCatalogo,
  medicamentoCalculadoraSelecionado,
  calculadoraResultado,
  modalNovoExameAberto,
  setModalNovoExameAberto,
  petId,
  novoExameForm,
  setNovoExameForm,
  setNovoExameArquivo,
  salvarNovoExameRapido,
  salvandoNovoExame,
}) {
  return (
    <>
      <InsumoRapidoModal
        isOpen={modalInsumoAberto}
        onClose={() => setModalInsumoAberto(false)}
        css={css}
        consultaIdAtual={consultaIdAtual}
        petSelecionadoLabel={petSelecionadoLabel}
        insumoSelecionado={insumoRapidoSelecionado}
        setInsumoSelecionado={setInsumoRapidoSelecionado}
        insumoForm={insumoRapidoForm}
        setInsumoForm={setInsumoRapidoForm}
        salvarInsumo={salvarInsumoRapidoConsulta}
        salvandoInsumo={salvandoInsumoRapido}
      />

      <NovoPetModal
        isOpen={modalNovoPetAberto}
        tutor={tutorSelecionado}
        sugestoesEspecies={sugestoesEspecies}
        onClose={() => setModalNovoPetAberto(false)}
        onCreated={handleNovoPetCriado}
      />

      <CalculadoraDoseModal
        isOpen={modalCalculadoraAberto}
        onClose={() => setModalCalculadoraAberto(false)}
        css={css}
        petSelecionadoLabel={petSelecionadoLabel}
        calculadoraForm={calculadoraForm}
        setCalculadoraForm={setCalculadoraForm}
        medicamentosCatalogo={medicamentosCatalogo}
        medicamentoSelecionado={medicamentoCalculadoraSelecionado}
        resultado={calculadoraResultado}
      />

      <NovoExameConsultaModal
        isOpen={modalNovoExameAberto}
        onClose={() => setModalNovoExameAberto(false)}
        css={css}
        consultaIdAtual={consultaIdAtual}
        petSelecionadoLabel={petSelecionadoLabel}
        petId={petId}
        novoExameForm={novoExameForm}
        setNovoExameForm={setNovoExameForm}
        setNovoExameArquivo={setNovoExameArquivo}
        salvarNovoExameRapido={salvarNovoExameRapido}
        salvandoNovoExame={salvandoNovoExame}
      />
    </>
  );
}
