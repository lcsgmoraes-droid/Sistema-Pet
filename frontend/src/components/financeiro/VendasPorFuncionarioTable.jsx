import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";
import NumberCell from "../ui/NumberCell";

function criarLinhaTotal(linhas) {
  return {
    funcionario: "TOTAL",
    isTotal: true,
    desconto: linhas.reduce((sum, item) => sum + Number(item.desconto || 0), 0),
    quantidade: linhas.reduce((sum, item) => sum + Number(item.quantidade || 0), 0),
    valor_bruto: linhas.reduce((sum, item) => sum + Number(item.valor_bruto || 0), 0),
    valor_liquido: linhas.reduce((sum, item) => sum + Number(item.valor_liquido || 0), 0),
  };
}

export default function VendasPorFuncionarioTable({ linhas = [] }) {
  const linhasComTotal = linhas.length > 0 ? [...linhas, criarLinhaTotal(linhas)] : linhas;

  const columns = [
    {
      key: "funcionario",
      header: "Nome",
      accessor: "funcionario",
    },
    {
      key: "quantidade",
      header: "Qtd",
      align: "right",
      render: (item) => <NumberCell value={item.quantidade} zeroAsDash />,
    },
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
  ];

  return (
    <DataTable
      columns={columns}
      data={linhasComTotal}
      emptyMessage="Nenhum funcionário encontrado"
      getRowKey={(item, index) =>
        item.isTotal ? "total" : `func-row-${item.funcionario || index}`
      }
      rowClassName={(item) =>
        item.isTotal ? "bg-slate-200 font-bold text-slate-800 hover:bg-slate-200" : ""
      }
      theadClassName="bg-gray-100"
    />
  );
}
