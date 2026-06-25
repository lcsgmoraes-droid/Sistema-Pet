import ComissoesListagemView from "./listagem/ComissoesListagemView";
import useComissoesListagemController from "./listagem/useComissoesListagemController";

const ComissoesListagem = () => {
  const controller = useComissoesListagemController();

  return <ComissoesListagemView controller={controller} />;
};

export default ComissoesListagem;
