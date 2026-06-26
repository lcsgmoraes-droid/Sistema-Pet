import "../../styles/Lembretes.css";
import LembretesBlingAutocadastros from "./LembretesBlingAutocadastros";
import LembretesCampanhasAlertas from "./LembretesCampanhasAlertas";
import LembretesDrePendentes from "./LembretesDrePendentes";
import LembretesHeader from "./LembretesHeader";
import LembretesList from "./LembretesList";
import LembretesValidadeSection from "./LembretesValidadeSection";
import useLembretesController from "./useLembretesController";

export default function LembretesPage() {
  const controller = useLembretesController();

  return (
    <div className="lembretes-container">
      <LembretesHeader controller={controller} />
      <LembretesCampanhasAlertas alertasCampanhas={controller.alertasCampanhas} />
      <LembretesBlingAutocadastros
        autocadastrosBling={controller.autocadastrosBling}
        onAbrirProduto={controller.irProdutoBling}
      />
      <LembretesDrePendentes
        dresPendentes={controller.dresPendentes}
        onAbrirDre={controller.irDre}
      />
      <LembretesValidadeSection controller={controller} />
      <LembretesList controller={controller} />
    </div>
  );
}
