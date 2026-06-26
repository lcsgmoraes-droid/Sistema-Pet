import ProdutosValidadeFiltros from "./ProdutosValidadeFiltros";
import ProdutosValidadeHeader from "./ProdutosValidadeHeader";
import ProdutosValidadeLotesPanel from "./ProdutosValidadeLotesPanel";
import ProdutosValidadeResumoGrid from "./ProdutosValidadeResumoGrid";
import ProdutosValidadeRuleBanner from "./ProdutosValidadeRuleBanner";
import useProdutosValidadeProximaController from "./useProdutosValidadeProximaController";

export default function ProdutosValidadeProximaPage({ embedded = false, reloadSignal = 0 }) {
  const controller = useProdutosValidadeProximaController({ reloadSignal });

  return (
    <div className={embedded ? "space-y-4 md:space-y-6" : "space-y-4 p-3 md:space-y-6 md:p-6"}>
      {!embedded && <ProdutosValidadeHeader controller={controller} />}
      <ProdutosValidadeRuleBanner controller={controller} embedded={embedded} />
      <ProdutosValidadeFiltros controller={controller} />
      <ProdutosValidadeResumoGrid controller={controller} />
      <ProdutosValidadeLotesPanel controller={controller} />
    </div>
  );
}
