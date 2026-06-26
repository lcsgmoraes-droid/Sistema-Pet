import "../../styles/CalculadoraRacao.css";
import CalculadoraRacaoComparativoCard from "./CalculadoraRacaoComparativoCard";
import CalculadoraRacaoForm from "./CalculadoraRacaoForm";
import CalculadoraRacaoHeader from "./CalculadoraRacaoHeader";
import CalculadoraRacaoResultadoCard from "./CalculadoraRacaoResultadoCard";
import useCalculadoraRacaoController from "./useCalculadoraRacaoController";

export default function CalculadoraRacaoPage() {
  const calculadora = useCalculadoraRacaoController();

  return (
    <div className="calculadora-racao-container">
      <CalculadoraRacaoHeader />

      <div className="calculadora-grid">
        <CalculadoraRacaoForm calculadora={calculadora} />

        <div>
          <CalculadoraRacaoResultadoCard resultado={calculadora.resultado} />
          <CalculadoraRacaoComparativoCard
            comparativo={calculadora.comparativo}
            produtoIdSelecionado={calculadora.form.produto_id}
          />
        </div>
      </div>
    </div>
  );
}
