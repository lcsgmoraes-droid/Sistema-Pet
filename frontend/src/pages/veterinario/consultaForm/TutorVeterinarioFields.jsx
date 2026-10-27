import BuscaPessoa from "../../../components/v2/BuscaPessoa/BuscaPessoa";
import InputCombobox from "../../../components/v2/InputCombobox/InputCombobox";
import BotaoCancelar from "../../../components/v2/BotaoCancelar/BotaoCancelar";
import { deveBuscarTutores } from "./tutorPetSelectionUtils";

export default function TutorVeterinarioFields({
  isEdicao,
  form,
  setCampo,
  css: _css,
  renderCampo,
  buscaTutor,
  setBuscaTutor,
  tutorSelecionado,
  setTutorSelecionado,
  tutoresSugeridos,
  selecionarTutor,
  limparTutor,
  veterinarios,
}) {
  function handleBuscaTutorChange(valor) {
    setBuscaTutor(valor);
    if (tutorSelecionado) {
      setTutorSelecionado(null);
      setCampo("pet_id", "");
    }
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      {renderCampo(
        "Tutor (nome/telefone)",
        true,
      )(
        <div className="space-y-2">
          <BuscaPessoa
            value={buscaTutor}
            onChange={handleBuscaTutorChange}
            disabled={isEdicao}
            suggestions={tutoresSugeridos}
            showSuggestions={!isEdicao && deveBuscarTutores(buscaTutor) && !tutorSelecionado}
            onSelect={selecionarTutor}
            placeholder="Código, nome ou telefone do tutor..."
          />
          {!isEdicao && tutorSelecionado && (
            <BotaoCancelar tamanho="pequeno" onClick={limparTutor}>
              Limpar tutor
            </BotaoCancelar>
          )}
        </div>,
      )}

      {renderCampo("Veterin\u00e1rio")(
        <InputCombobox
          value={form.veterinario_id}
          onChange={(veterinarioId) => setCampo("veterinario_id", veterinarioId)}
          opcoes={veterinarios.map((veterinario) => ({
            value: veterinario.id,
            label: veterinario.nome,
          }))}
          placeholder={"Digite para buscar veterin\u00e1rio..."}
        />,
      )}
    </div>
  );
}
