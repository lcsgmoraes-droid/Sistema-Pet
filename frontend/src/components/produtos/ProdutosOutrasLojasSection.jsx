import { Building2 } from "lucide-react";
import { formatarMoeda } from "../../api/produtos";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";

// Resultados de busca encontrados em OUTRAS lojas do mesmo grupo comercial,
// que esta loja nunca cadastrou (por isso nunca apareceriam na tabela
// principal, que e sempre escopada a propria loja — ver
// app/services/produto_busca_grupo_service.py). Preco/estoque aqui sao só
// referencia da loja de origem; a acao "Cadastrar aqui" cria um cadastro
// LOCAL novo, pre-preenchido com os dados inerentes (nome, codigo de
// barras/GTIN, peso, foto) — preco e estoque ficam sempre em branco, pra
// esta loja preencher do zero.
export default function ProdutosOutrasLojasSection({ navigate, produtosOutrasLojas }) {
  if (!produtosOutrasLojas || produtosOutrasLojas.length === 0) return null;

  return (
    <div className="mb-4 rounded-xl border border-indigo-200 bg-indigo-50/60 p-4 dark:border-indigo-900 dark:bg-indigo-950/20">
      <div className="mb-3 flex items-center gap-2">
        <Building2 className="h-4 w-4 flex-none text-indigo-600 dark:text-indigo-300" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-indigo-900 dark:text-indigo-200">
          Encontrado em outras lojas do grupo
        </h3>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {produtosOutrasLojas.map((produto) => (
          <div
            key={`${produto.tenant_id}-${produto.id}`}
            className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900"
          >
            <div className="h-12 w-12 flex-none overflow-hidden rounded-lg border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-800">
              {produto.imagem_principal ? (
                <img
                  src={produto.imagem_principal}
                  alt={produto.nome}
                  loading="lazy"
                  className="h-full w-full object-cover"
                />
              ) : null}
            </div>
            <div className="min-w-0 flex-1">
              <p
                className="truncate text-sm font-medium text-gray-900 dark:text-slate-100"
                title={produto.nome}
              >
                {produto.nome}
              </p>
              <p className="truncate text-xs text-gray-500 dark:text-slate-400">
                {produto.loja_nome}
                {produto.preco_venda != null
                  ? ` · ${formatarMoeda(produto.preco_venda)} lá`
                  : ""}
              </p>
            </div>
            <BotaoInteracao
              tamanho="pequeno"
              onClick={() =>
                navigate(
                  `/produtos/novo?pre_cadastro_grupo=${produto.id}&tenant_origem=${produto.tenant_id}`,
                )
              }
            >
              Cadastrar aqui
            </BotaoInteracao>
          </div>
        ))}
      </div>
    </div>
  );
}
