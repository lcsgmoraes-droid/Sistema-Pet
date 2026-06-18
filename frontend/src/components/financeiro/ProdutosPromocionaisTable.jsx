import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";
import NumberCell from "../ui/NumberCell";
import ProductIdentity from "../ui/ProductIdentity";

export default function ProdutosPromocionaisTable({ produtos = [] }) {
  return (
    <DataTable
      columns={[
        {
          key: "produto",
          header: "Produto",
          className: "font-medium text-slate-800",
          render: (produto) => <ProductIdentity product={produto} />,
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
            <MoneyCell className="text-amber-700" value={produto.desconto} zeroAsDash />
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
