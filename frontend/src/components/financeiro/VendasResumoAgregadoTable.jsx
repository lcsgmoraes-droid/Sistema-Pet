import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";
import NumberCell from "../ui/NumberCell";

function criarLinhaTotal(linhas, labelKey, includeQuantidade) {
  return {
    [labelKey]: "TOTAL",
    desconto: linhas.reduce((sum, item) => sum + Number(item.desconto || 0), 0),
    isTotal: true,
    quantidade: includeQuantidade
      ? linhas.reduce((sum, item) => sum + Number(item.quantidade || 0), 0)
      : undefined,
    valor_bruto: linhas.reduce((sum, item) => sum + Number(item.valor_bruto || 0), 0),
    valor_liquido: linhas.reduce((sum, item) => sum + Number(item.valor_liquido || 0), 0),
  };
}

export default function VendasResumoAgregadoTable({
  emptyMessage = "Nenhum registro encontrado",
  includePercentual = false,
  includeQuantidade = false,
  labelHeader,
  labelKey,
  linhas = [],
  rowKeyPrefix,
}) {
  const linhasComTotal =
    linhas.length > 0 ? [...linhas, criarLinhaTotal(linhas, labelKey, includeQuantidade)] : linhas;

  const columns = [
    {
      key: "label",
      header: labelHeader,
      accessor: (item) => item[labelKey] || "-",
    },
  ];

  if (includeQuantidade) {
    columns.push({
      key: "quantidade",
      header: "Qtd",
      align: "right",
      render: (item) => <NumberCell value={item.quantidade} zeroAsDash />,
    });
  }

  if (includePercentual) {
    columns.push({
      key: "percentual",
      header: "Percentual",
      align: "right",
      render: (item) => (item.isTotal ? "-" : `${item.percentual}%`),
    });
  }

  columns.push(
    {
      key: "valor_bruto",
      header: "Vl. bruto",
      align: "right",
      render: (item) => <MoneyCell value={item.valor_bruto} zeroAsDash />,
    },
    {
      key: "desconto",
      header: "Desconto",
      align: "right",
      render: (item) => <MoneyCell value={item.desconto} zeroAsDash />,
    },
    {
      key: "valor_liquido",
      header: "Vl. líquido",
      align: "right",
      render: (item) => <MoneyCell value={item.valor_liquido} zeroAsDash />,
    },
  );

  return (
    <DataTable
      columns={columns}
      data={linhasComTotal}
      emptyMessage={emptyMessage}
      getRowKey={(item, index) =>
        item.isTotal ? "total" : `${rowKeyPrefix}-${item[labelKey] || index}`
      }
      rowClassName={(item) =>
        item.isTotal ? "bg-slate-200 font-bold text-slate-800 hover:bg-slate-200" : ""
      }
      theadClassName="bg-gray-100"
    />
  );
}
