import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";
import NumberCell from "../ui/NumberCell";

function toNumber(value) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : 0;
}

function RankBadge({ index }) {
  const tone =
    index === 0
      ? "bg-yellow-100 text-yellow-800"
      : index === 1
        ? "bg-slate-100 text-slate-800"
        : index === 2
          ? "bg-orange-100 text-orange-800"
          : "bg-blue-50 text-blue-800";

  return (
    <span
      className={[
        "inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold",
        tone,
      ].join(" ")}
    >
      {index + 1}
    </span>
  );
}

function MargemBadge({ value }) {
  const margem = toNumber(value);
  const tone =
    margem >= 50
      ? "bg-emerald-100 text-emerald-800"
      : margem >= 30
        ? "bg-amber-100 text-amber-800"
        : "bg-red-100 text-red-800";

  return (
    <span className={["inline-block rounded px-2 py-1 text-xs font-semibold", tone].join(" ")}>
      {margem.toFixed(1)}%
    </span>
  );
}

export default function TopProdutosLucroTable({ produtos = [] }) {
  return (
    <DataTable
      columns={[
        {
          key: "rank",
          header: "#",
          render: (_, index) => <RankBadge index={index} />,
        },
        {
          key: "produto",
          header: "Produto",
          className: "font-medium text-slate-800",
          accessor: "nome",
        },
        {
          key: "marca",
          header: "Marca",
          className: "text-slate-600",
          accessor: (produto) => produto.marca || "-",
        },
        {
          key: "quantidade",
          header: "Qtd",
          align: "right",
          render: (produto) => <NumberCell value={toNumber(produto.quantidade)} zeroAsDash />,
        },
        {
          key: "custo",
          header: "Custo unit.",
          align: "right",
          render: (produto) => (
            <MoneyCell
              className="text-red-600"
              value={toNumber(produto.custo)}
              zeroAsDash
            />
          ),
        },
        {
          key: "preco",
          header: "Preço venda",
          align: "right",
          render: (produto) => (
            <MoneyCell
              className="text-emerald-700"
              value={toNumber(produto.preco)}
              zeroAsDash
            />
          ),
        },
        {
          key: "margem",
          header: "Margem %",
          align: "right",
          render: (produto) => <MargemBadge value={produto.margem} />,
        },
        {
          key: "lucro",
          header: "Lucro total",
          align: "right",
          render: (produto) => (
            <MoneyCell
              className="font-bold text-emerald-700"
              value={toNumber(produto.lucro_total)}
              zeroAsDash
            />
          ),
        },
      ]}
      data={produtos}
      emptyMessage="Nenhum produto com lucro encontrado"
      getRowKey={(produto, index) => `${produto.nome || "produto"}-${produto.marca || "sem-marca"}-${index}`}
      theadClassName="bg-slate-100"
    />
  );
}
