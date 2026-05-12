import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";
import NumberCell from "../ui/NumberCell";

function DiaCell({ item }) {
  if (item.isTotal) return "";

  const badgeClass = item.feriado_aberto
    ? "bg-emerald-100 text-emerald-700"
    : item.fim_de_semana
      ? "bg-purple-100 text-purple-700"
      : item.feriado_nome
        ? "bg-amber-100 text-amber-700"
        : "bg-emerald-100 text-emerald-700";

  return (
    <div className="flex flex-wrap gap-1">
      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${badgeClass}`}>
        {item.feriado_nome || item.dia_semana}
      </span>
      {item.sem_movimento && item.dia_util && (
        <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">
          Sem venda
        </span>
      )}
      {item.feriado_aberto && (
        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
          Aberto
        </span>
      )}
    </div>
  );
}

function criarLinhaTotal(linhas) {
  const quantidade = linhas.reduce((sum, item) => sum + item.quantidade, 0);
  const valorBruto = linhas.reduce((sum, item) => sum + item.valor_bruto, 0);
  const desconto = linhas.reduce((sum, item) => sum + item.desconto, 0);
  const valorLiquido = linhas.reduce((sum, item) => sum + item.valor_liquido, 0);

  return {
    data: "total",
    desconto,
    isTotal: true,
    percentual_desconto: valorBruto > 0 ? (desconto / valorBruto) * 100 : 0,
    quantidade,
    saldo_aberto: linhas.reduce((sum, item) => sum + item.saldo_aberto, 0),
    taxa_entrega: linhas.reduce((sum, item) => sum + item.taxa_entrega, 0),
    ticket_medio: quantidade > 0 ? valorLiquido / quantidade : 0,
    valor_bruto: valorBruto,
    valor_liquido: valorLiquido,
    valor_recebido: linhas.reduce((sum, item) => sum + item.valor_recebido, 0),
  };
}

export default function VendasPorDataTable({ formatarData, linhas = [] }) {
  const linhasComTotal = linhas.length > 0 ? [...linhas, criarLinhaTotal(linhas)] : linhas;

  const columns = [
    {
      key: "data",
      header: "Data",
      className: "whitespace-nowrap",
      render: (item) => (item.isTotal ? "TOTAL" : formatarData(item.data)),
    },
    {
      key: "dia",
      header: "Dia",
      render: (item) => <DiaCell item={item} />,
    },
    {
      key: "quantidade",
      header: "Qtd",
      align: "right",
      render: (item) => <NumberCell value={item.quantidade} zeroAsDash />,
    },
    {
      key: "ticket_medio",
      header: "Tkt. Médio",
      align: "right",
      render: (item) => <MoneyCell value={item.ticket_medio} zeroAsDash />,
    },
    {
      key: "valor_bruto",
      header: "Vl. bruto",
      align: "right",
      render: (item) => <MoneyCell value={item.valor_bruto} zeroAsDash />,
    },
    {
      key: "taxa_entrega",
      header: "Taxa entrega",
      align: "right",
      render: (item) => <MoneyCell value={item.taxa_entrega} zeroAsDash />,
    },
    {
      key: "desconto",
      header: "Desconto",
      align: "right",
      render: (item) => <MoneyCell value={item.desconto} zeroAsDash />,
    },
    {
      key: "percentual_desconto",
      header: "(%)",
      align: "right",
      render: (item) => (
        <NumberCell value={item.percentual_desconto} decimals={1} suffix="%" zeroAsDash />
      ),
    },
    {
      key: "valor_liquido",
      header: "Vl. líquido",
      align: "right",
      render: (item) => <MoneyCell value={item.valor_liquido} zeroAsDash />,
    },
    {
      key: "valor_recebido",
      header: "Vl. recebido",
      align: "right",
      render: (item) => <MoneyCell value={item.valor_recebido} zeroAsDash />,
    },
    {
      key: "saldo_aberto",
      header: "Saldo aberto",
      align: "right",
      render: (item) => <MoneyCell value={item.saldo_aberto} zeroAsDash />,
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={linhasComTotal}
      emptyMessage="Nenhuma venda encontrada no período"
      getRowKey={(item, index) => (item.isTotal ? "total" : `dia-${item.data || index}`)}
      rowClassName={(item) =>
        item.isTotal
          ? "bg-slate-200 font-bold text-slate-800 hover:bg-slate-200"
          : item.sem_movimento
            ? "bg-slate-50/60 text-slate-500"
            : ""
      }
      theadClassName="bg-gray-100"
    />
  );
}
