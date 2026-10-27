import BuscaEntidade from "../BuscaEntidade/BuscaEntidade";
import { obterCodigoProdutoPublico } from "../../../utils/codigosPublicos";

export default function BuscaProduto({ id, inputId, ...props }) {
  return (
    <BuscaEntidade
      tipo="produto"
      containerId={id}
      inputId={inputId}
      placeholder="Nome, código, SKU ou código de barras..."
      {...props}
      renderDefault={(produto) => (
        <>
          <span className="block font-medium text-slate-900 dark:text-slate-100">
            {produto.nome}
          </span>
          {obterCodigoProdutoPublico(produto) && (
            <span className="block text-sm text-slate-500 dark:text-slate-400">
              Cód.: {obterCodigoProdutoPublico(produto)}
            </span>
          )}
        </>
      )}
    />
  );
}
