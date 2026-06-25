import EstoqueFullNFView from "./estoqueFullNF/EstoqueFullNFView";
import { useEstoqueFullNFController } from "./estoqueFullNF/useEstoqueFullNFController";

export default function EstoqueFullNF() {
  const controller = useEstoqueFullNFController();

  return <EstoqueFullNFView controller={controller} />;
}
