import CalculadoraRacaoComparativoFields from "./CalculadoraRacaoComparativoFields";
import CalculadoraRacaoPetFields from "./CalculadoraRacaoPetFields";
import CalculadoraRacaoProdutoFields from "./CalculadoraRacaoProdutoFields";

export default function CalculadoraRacaoForm({ calculadora }) {
  return (
    <div className="form-card">
      <h2>Dados do Pet</h2>

      <CalculadoraRacaoPetFields
        form={calculadora.form}
        pets={calculadora.pets}
        onCampoChange={calculadora.setCampo}
        onPetNomeChange={calculadora.alterarPetNome}
      />

      <CalculadoraRacaoProdutoFields
        form={calculadora.form}
        loading={calculadora.loading}
        loadingBuscaPrincipal={calculadora.loadingBuscaPrincipal}
        opcoesRacaoPrincipal={calculadora.opcoesRacaoPrincipal}
        resumoAptidao={calculadora.resumoAptidao}
        onBuscaChange={calculadora.alterarBuscaRacaoPrincipal}
        onCalcular={calculadora.calcular}
        onClear={calculadora.limparRacaoPrincipal}
        onSelect={calculadora.selecionarRacaoPrincipal}
      />

      <CalculadoraRacaoComparativoFields
        form={calculadora.form}
        loading={calculadora.loading}
        loadingBuscaComparativo={calculadora.loadingBuscaComparativo}
        opcoesRacaoComparativo={calculadora.opcoesRacaoComparativo}
        onBuscaChange={calculadora.alterarBuscaRacaoComparativo}
        onCampoChange={calculadora.setCampo}
        onClassificacaoChange={calculadora.alterarClassificacao}
        onComparar={calculadora.compararRacoes}
        onLimparClassificacao={calculadora.limparClassificacao}
        onClearRacao={calculadora.limparRacaoComparativo}
        onSelect={calculadora.selecionarRacaoComparativo}
      />
    </div>
  );
}
