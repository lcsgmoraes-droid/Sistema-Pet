import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";
import NumberCell from "../ui/NumberCell";
import CopyableCode from "../ui/CopyableCode";
import CopyableValue from "../ui/CopyableValue";

function getCodigoProduto(produto) {
  return (
    produto?.produto_codigo ||
    produto?.produto_sku ||
    produto?.sku ||
    produto?.codigo ||
    produto?.codigo_barras ||
    produto?.ean ||
    ""
  );
}

export default function ProdutosPromocionaisTable({ produtos = [] }) {
  return (
    <DataTable
      columns={[
        {
          key: "produto",
          header: "Produto",
          className: "font-medium text-slate-800",
          render: (produto) => (
            <span className="inline-flex flex-wrap items-center gap-1.5">
              <CopyableValue title="Copiar produto" value={produto.produto_nome} />
              <CopyableCode value={getCodigoProduto(produto)} />
            </span>
          ),
        },
        {
          key: "quantidade",
          header: "Qtd",
          align: "right",
          render: (produto) => <NumberCell value={produto.quantidade} zeroAsDash />,
        },
        {
          key: "valor",
          header: "Valor",
          align: "right",
          className: "font-semibold text-slate-800",
          render: (produto) => <MoneyCell value={produto.valor} zeroAsDash />,
        },
        {
          key: "desconto",
          header: "Desconto",
          align: "right",
          render: (produto) => (
            <MoneyCell
              className="text-amber-700"
              value={produto.desconto}
              zeroAsDash
            />
          ),
        },
        {
          key: "origem",
          header: "Origem",
          accessor: (produto) => produto.origens?.join(", ") || "-",
        },
      ]}
      data={produtos}
      emptyMessage="Nenhum item promocional identificado no periodo."
      getRowKey={(produto, index) => produto.produto_nome || index}
      theadClassName="bg-slate-50 text-xs uppercase text-slate-500"
    />
  );
}
