import { getPetLabel } from "./calculadoraRacaoState";

export default function CalculadoraRacaoPetFields({ form, pets, onCampoChange, onPetNomeChange }) {
  return (
    <>
      <div className="form-group">
        <label htmlFor="racao-pet-search">Buscar Pet Cadastrado</label>
        <input
          id="racao-pet-search"
          name="racao_pet_search"
          type="text"
          list="pets-list"
          value={form.pet_nome || ""}
          onChange={(event) => onPetNomeChange(event.target.value)}
          placeholder="Digite ou selecione um pet"
          className="pet-select"
        />
        <datalist id="pets-list">
          {pets.map((pet) => (
            <option key={pet.id} value={getPetLabel(pet)} />
          ))}
        </datalist>
        <small className="form-hint">
          Digite ou selecione um pet para preencher automaticamente peso e idade
        </small>
      </div>

      <div className="form-group">
        <label htmlFor="racao-peso-pet">Peso do Pet (kg) *</label>
        <input
          id="racao-peso-pet"
          name="racao_peso_pet_kg"
          type="number"
          step="0.1"
          value={form.peso_pet_kg}
          onChange={(event) => onCampoChange("peso_pet_kg", event.target.value)}
          placeholder="Ex: 8.5"
        />
      </div>

      <div className="form-group">
        <label htmlFor="racao-idade-meses">
          Idade (meses)
          {form.categoria_racao === "filhote" && <span style={{ color: "#ff6b6b" }}> *</span>}
        </label>
        <input
          id="racao-idade-meses"
          name="racao_idade_meses"
          type="number"
          value={form.idade_meses}
          onChange={(event) => onCampoChange("idade_meses", event.target.value)}
          placeholder={
            form.categoria_racao === "filhote" ? "Obrigatorio para filhotes!" : "Ex: 24 (opcional)"
          }
          required={form.categoria_racao === "filhote"}
          style={
            form.categoria_racao === "filhote" ? { borderColor: "#ff6b6b", borderWidth: "2px" } : {}
          }
        />
      </div>

      <div className="form-group">
        <label htmlFor="racao-nivel-atividade">Nivel de Atividade</label>
        <select
          id="racao-nivel-atividade"
          name="racao_nivel_atividade"
          value={form.nivel_atividade}
          onChange={(event) => onCampoChange("nivel_atividade", event.target.value)}
        >
          <option value="baixo">Baixo</option>
          <option value="normal">Normal</option>
          <option value="alto">Alto</option>
        </select>
      </div>
    </>
  );
}
