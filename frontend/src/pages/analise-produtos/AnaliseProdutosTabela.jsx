import { Fragment, useId, useMemo, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import { formatMoneyBRL, formatPercent } from "../../utils/formatters";

const formatarQuantidade = (valor) =>
  new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(Number(valor || 0));

const ORDENACOES = [
  { value: "faturamento", label: "Maior faturamento" },
  { value: "quantidade", label: "Maior quantidade" },
  { value: "lucro_estimado", label: "Maior lucro estimado" },
  { value: "margem_estimada_pct", label: "Maior margem estimada" },
];

function ProdutoComVendedores({ item }) {
  const [expandido, setExpandido] = useState(false);
  const detalhesId = useId();
  const vendedores = Array.isArray(item.vendedores) ? item.vendedores : [];

  return (
    <Fragment>
      <tr className="hover:bg-slate-50 dark:hover:bg-slate-800">
        <td className="px-5 py-3">
          <p className="font-semibold text-slate-900 dark:text-slate-100">{item.produto_nome}</p>
          <p className="mb-2 text-xs text-slate-500">{item.codigo || "Sem código"}</p>
          <BotaoInteracao
            tamanho="pequeno"
            icon={expandido ? ChevronUp : ChevronDown}
            aria-label={`${expandido ? "Ocultar" : "Ver"} vendedores de ${item.produto_nome}`}
            aria-expanded={expandido}
            aria-controls={detalhesId}
            onClick={() => setExpandido((anterior) => !anterior)}
          >
            {expandido ? "Ocultar vendedores" : "Ver vendedores"}
          </BotaoInteracao>
        </td>
        <td className="px-5 py-3 text-sm text-slate-600 dark:text-slate-300">
          <p>{item.categoria_nome || "Sem categoria"}</p>
          <p className="text-xs text-slate-400">{item.marca_nome || "Sem marca"}</p>
        </td>
        <td className="px-5 py-3 text-right text-sm font-semibold text-slate-800 dark:text-slate-200">
          {formatarQuantidade(item.quantidade)}
        </td>
        <td className="px-5 py-3 text-right text-sm font-semibold text-slate-900 dark:text-slate-100">
          {formatMoneyBRL(item.faturamento)}
        </td>
        <td
          className={`px-5 py-3 text-right text-sm font-semibold ${Number(item.lucro_estimado) < 0 ? "text-rose-700 dark:text-rose-400" : "text-emerald-700 dark:text-emerald-400"}`}
        >
          {formatMoneyBRL(item.lucro_estimado)}
        </td>
        <td className="px-5 py-3 text-right text-sm text-slate-700 dark:text-slate-300">
          {formatPercent(item.margem_estimada_pct)}
        </td>
        <td className="px-5 py-3 text-right text-sm text-slate-700 dark:text-slate-300">
          <p>{formatarQuantidade(item.estoque_atual)} un.</p>
          <p className="text-xs text-slate-500">
            {item.cobertura_estoque_dias == null
              ? "Sem giro para estimar"
              : `${formatarQuantidade(item.cobertura_estoque_dias)} dias`}
          </p>
        </td>
      </tr>
      {expandido && (
        <tr>
          <td colSpan={7} className="bg-slate-50 px-5 py-4 dark:bg-slate-900">
            <div id={detalhesId} role="region" aria-label={`Vendedores de ${item.produto_nome}`}>
              <h3 className="font-semibold text-slate-800 dark:text-slate-100">
                Vendas por vendedor
              </h3>
              <p className="mb-3 mt-1 text-xs text-slate-500 dark:text-slate-400">
                Participação no faturamento deste produto, no mesmo período e filtros do relatório.
              </p>
              {vendedores.length ? (
                <table
                  className="w-full text-sm"
                  aria-label={`Vendas por vendedor de ${item.produto_nome}`}
                >
                  <thead className="text-xs text-slate-500 dark:text-slate-400">
                    <tr>
                      <th scope="col" className="py-2 text-left">
                        Vendedor
                      </th>
                      <th scope="col" className="px-4 py-2 text-right">
                        Quantidade
                      </th>
                      <th scope="col" className="px-4 py-2 text-right">
                        Faturamento
                      </th>
                      <th scope="col" className="py-2 text-right">
                        % do produto
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 text-slate-700 dark:divide-slate-700 dark:text-slate-200">
                    {vendedores.map((vendedor) => (
                      <tr key={vendedor.vendedor_id ?? "sem-vendedor"}>
                        <th scope="row" className="py-2 text-left font-medium">
                          {vendedor.vendedor_nome || "Sem vendedor informado"}
                        </th>
                        <td className="px-4 py-2 text-right">
                          {formatarQuantidade(vendedor.quantidade)}
                        </td>
                        <td className="px-4 py-2 text-right">
                          {formatMoneyBRL(vendedor.faturamento)}
                        </td>
                        <td className="py-2 text-right">
                          {formatPercent(vendedor.participacao_faturamento_pct)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Detalhamento de vendedores indisponível para este produto.
                </p>
              )}
            </div>
          </td>
        </tr>
      )}
    </Fragment>
  );
}

export default function AnaliseProdutosTabela({ produtos }) {
  const [ordenacao, setOrdenacao] = useState("faturamento");
  const ordenacaoId = useId();
  const ordenados = useMemo(
    () => [...produtos].sort((a, b) => Number(b[ordenacao] || 0) - Number(a[ordenacao] || 0)),
    [ordenacao, produtos],
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-950">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-start sm:justify-between dark:border-slate-700">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
            Resultado por produto
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {produtos.length} produto(s) com venda no filtro aplicado.
          </p>
        </div>
        <div className="w-full sm:w-56">
          <InputCombobox
            id={ordenacaoId}
            label="Ordenar produtos"
            value={ordenacao}
            onChange={setOrdenacao}
            opcoes={ORDENACOES}
            permitirLimpar={false}
          />
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
            <tr>
              {[
                "Produto",
                "Grupo",
                "Quantidade",
                "Faturamento",
                "Lucro estimado",
                "Margem",
                "Estoque / cobertura",
              ].map((rotulo, indice) => (
                <th
                  key={rotulo}
                  scope="col"
                  className={`px-5 py-3 ${indice < 2 ? "text-left" : "text-right"}`}
                >
                  {rotulo}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {ordenados.map((item) => (
              <ProdutoComVendedores key={item.produto_id} item={item} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
