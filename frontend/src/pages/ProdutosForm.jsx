import ProdutosFormView from "./produtos/form/ProdutosFormView";
import { useProdutosFormController } from "./produtos/form/useProdutosFormController";

export default function ProdutosForm() {
  const controller = useProdutosFormController();

  return <ProdutosFormView controller={controller} />;
}
