import MotivoConsultaField from "./MotivoConsultaField";
import PetConsultaSelector from "./PetConsultaSelector";
import SinaisVitaisFields from "./SinaisVitaisFields";
import TutorVeterinarioFields from "./TutorVeterinarioFields";

export default function TriagemInicialSection({
  modoSomenteLeitura,
  isEdicao,
  form,
  setCampo,
  css,
  renderCampo,
  buscaTutor,
  setBuscaTutor,
  tutorSelecionado,
  setTutorSelecionado,
  tutoresSugeridos,
  selecionarTutor,
  limparTutor,
  veterinarios,
  listaPetsExpandida,
  setListaPetsExpandida,
  petSelecionadoLabel,
  petsDoTutor,
  abrirModalNovoPet,
}) {
  return (
    <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4 disabled:opacity-100">
      <h2 className="font-semibold text-gray-700">Triagem inicial</h2>

      <TutorVeterinarioFields
        isEdicao={isEdicao}
        form={form}
        setCampo={setCampo}
        css={css}
        renderCampo={renderCampo}
        buscaTutor={buscaTutor}
        setBuscaTutor={setBuscaTutor}
        tutorSelecionado={tutorSelecionado}
        setTutorSelecionado={setTutorSelecionado}
        tutoresSugeridos={tutoresSugeridos}
        selecionarTutor={selecionarTutor}
        limparTutor={limparTutor}
        veterinarios={veterinarios}
      />

      <PetConsultaSelector
        isEdicao={isEdicao}
        form={form}
        setCampo={setCampo}
        renderCampo={renderCampo}
        tutorSelecionado={tutorSelecionado}
        listaPetsExpandida={listaPetsExpandida}
        setListaPetsExpandida={setListaPetsExpandida}
        petSelecionadoLabel={petSelecionadoLabel}
        petsDoTutor={petsDoTutor}
        abrirModalNovoPet={abrirModalNovoPet}
      />

      <MotivoConsultaField
        form={form}
        setCampo={setCampo}
        css={css}
        renderCampo={renderCampo}
      />

      <SinaisVitaisFields
        form={form}
        setCampo={setCampo}
        css={css}
        renderCampo={renderCampo}
      />
    </fieldset>
  );
}
