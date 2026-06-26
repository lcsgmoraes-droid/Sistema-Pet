import RacaoSearchInput from "./RacaoSearchInput";

export default function CalculadoraRacaoComparativoFields({
  form,
  loading,
  loadingBuscaComparativo,
  opcoesRacaoComparativo,
  onBuscaChange,
  onCampoChange,
  onClassificacaoChange,
  onComparar,
  onLimparClassificacao,
  onClearRacao,
  onSelect,
}) {
  return (
    <>
      <hr />

      <h3>Comparar Racoes</h3>

      <div className="info-box">
        <strong>Dica:</strong> escolha uma racao especifica para comparar ou use os filtros gerais
        para ver todas de uma categoria.
      </div>

      <div className="form-group">
        <div style={{ display: "flex", gap: "8px" }}>
          <RacaoSearchInput
            id="racao-produto-comparar"
            name="racao_produto_comparar"
            label="Comparar Racao Especifica"
            value={form.produto_comparar_nome || ""}
            onChange={onBuscaChange}
            onSelect={onSelect}
            onClear={onClearRacao}
            produtos={opcoesRacaoComparativo}
            loading={loadingBuscaComparativo}
            placeholder="Digite ou selecione uma racao"
            disabled={form.classificacao !== ""}
            warning={
              form.classificacao ? "Limpe o filtro de classificacao para usar esta opcao" : ""
            }
            hint={
              !form.produto_comparar_id && !form.classificacao
                ? "Deixe vazio para comparar por classificacao abaixo"
                : ""
            }
          />
        </div>
      </div>

      <div className="divider-text">OU</div>

      <div className="form-group">
        <label htmlFor="racao-filtro-classificacao">Filtro por Classificacao</label>
        <div style={{ display: "flex", gap: "8px" }}>
          <select
            id="racao-filtro-classificacao"
            name="racao_filtro_classificacao"
            value={form.classificacao}
            onChange={(event) => onClassificacaoChange(event.target.value)}
            disabled={form.produto_comparar_id !== ""}
            style={{ flex: 1 }}
          >
            <option value="">Todas as classificacoes</option>
            <option value="super_premium">Super Premium</option>
            <option value="premium">Premium</option>
            <option value="especial">Especial</option>
            <option value="standard">Standard</option>
          </select>
          {form.classificacao && (
            <button
              type="button"
              onClick={onLimparClassificacao}
              className="btn-clear"
              title="Limpar filtro"
            >
              x
            </button>
          )}
        </div>
        {form.produto_comparar_id && (
          <small className="form-warning">
            Limpe a racao especifica acima para usar este filtro
          </small>
        )}
      </div>

      <div className="form-group">
        <label htmlFor="racao-especie">Especie</label>
        <select
          id="racao-especie"
          name="racao_especie"
          value={form.especies}
          onChange={(event) => onCampoChange("especies", event.target.value)}
        >
          <option value="dog">Caes</option>
          <option value="cat">Gatos</option>
          <option value="both">Ambos</option>
        </select>
      </div>

      <div className="button-group">
        <button type="button" onClick={onComparar} disabled={loading} className="btn-secondary">
          {loading ? "Comparando..." : "Comparar Todas"}
        </button>
      </div>
    </>
  );
}
