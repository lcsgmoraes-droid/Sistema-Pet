import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";

function criarLinhaTotal(linhas) {
  return {
    forma_pagamento: "TOTAL",
    isTotal: true,
    valor_total: linhas.reduce((sum, item) => sum + Number(item.valor_total || 0), 0),
  };
}

export default function FormasRecebimentoTable({ linhas = [] }) {
  const linhasComTotal = linhas.length > 0 ? [...linhas, criarLinhaTotal(linhas)] : linhas;

  const columns = [
    {
      key: "forma",
      header: "Forma",
      accessor: "forma_pagamento",
    },
    {
      key: "valor_total",
      header: "Valor pago",
      align: "right",
      render: (item) => <MoneyCell value={item.valor_total} zeroAsDash />,
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={linhasComTotal}
      emptyMessage="Nenhuma forma de recebimento encontrada"
      getRowKey={(item, index) =>
        item.isTotal ? "total" : `forma-row-${item.forma_pagamento || index}`
      }
      rowClassName={(item) =>
        item.isTotal ? "bg-slate-200 font-bold text-slate-800 hover:bg-slate-200" : ""
      }
      theadClassName="bg-gray-100"
    />
  );
}
