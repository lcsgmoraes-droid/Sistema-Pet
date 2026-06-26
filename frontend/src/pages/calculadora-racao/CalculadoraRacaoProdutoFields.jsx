import RacaoSearchInput from "./RacaoSearchInput";

export default function CalculadoraRacaoProdutoFields({
  form,
  loading,
  loadingBuscaPrincipal,
  opcoesRacaoPrincipal,
  resumoAptidao,
  onBuscaChange,
  onCalcular,
  onClear,
  onSelect,
}) {
  return (
    <>
      <hr />

      <h3>Racao</h3>

      <div className="form-group">
        <RacaoSearchInput
          id="racao-produto-principal"
          name="racao_produto_principal"
          label="Selecionar Racao"
          value={form.produto_nome || ""}
          onChange={onBuscaChange}
          onSelect={onSelect}
          onClear={onClear}
          produtos={opcoesRacaoPrincipal}
          loading={loadingBuscaPrincipal}
          placeholder="Digite ou selecione uma racao"
          hint={`${resumoAptidao.aptas} aptas para analise · ${resumoAptidao.incompletas} com cadastro incompleto`}
        />
        {form.categoria_racao === "filhote" && (
          <small className="form-hint" style={{ color: "#ff6b6b", fontWeight: "bold" }}>
            Racao de filhote - idade e obrigatoria!
          </small>
        )}
      </div>

      <div className="button-group">
        <button type="button" onClick={onCalcular} disabled={loading} className="btn-primary">
          {loading ? "Calculando..." : "Calcular"}
        </button>
      </div>
    </>
  );
}
