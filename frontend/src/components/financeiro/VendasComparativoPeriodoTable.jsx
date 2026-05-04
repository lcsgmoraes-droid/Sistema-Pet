import { ArrowDown, ArrowUp } from "lucide-react";
import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";
import NumberCell from "../ui/NumberCell";

function calcularVariacao(valorAtual, valorAnterior) {
  const anterior = Number(valorAnterior || 0);
  if (!anterior) return { valor: 0, percentual: 0 };

  const atual = Number(valorAtual || 0);
  const valor = atual - anterior;
  const percentual = Number.parseFloat(((valor / anterior) * 100).toFixed(1));
  return { valor, percentual };
}

function VariacaoBadge({ percentual }) {
  const positivo = percentual >= 0;
  const Icon = positivo ? ArrowUp : ArrowDown;

  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold",
        positivo ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700",
      ].join(" ")}
    >
      <Icon className="h-4 w-4" />
      {Math.abs(percentual)}%
    </span>
  );
}

export default function VendasComparativoPeriodoTable({
  emptyMessage = "Nenhum registro encontrado",
  includeQuantidade = false,
  labelHeader,
  labelKey,
  linhasAnteriores = [],
  linhasAtuais = [],
  quantityKey = "quantidade",
  rowKeyPrefix,
  valueKey,
}) {
  const linhas = linhasAtuais.map((linhaAtual) => {
    const linhaAnterior = linhasAnteriores.find(
      (item) => item[labelKey] === linhaAtual[labelKey],
    ) || { [quantityKey]: 0, [valueKey]: 0 };
    const variacao = calcularVariacao(linhaAtual[valueKey], linhaAnterior[valueKey]);

    return {
      ...linhaAtual,
      quantidadeAnterior: Number(linhaAnterior[quantityKey] || 0),
      quantidadeAtual: Number(linhaAtual[quantityKey] || 0),
      valorAnterior: Number(linhaAnterior[valueKey] || 0),
      valorAtual: Number(linhaAtual[valueKey] || 0),
      variacao,
    };
  });

  const columns = [
    {
      key: "label",
      header: labelHeader,
      className: "font-medium text-slate-800",
      accessor: (item) => item[labelKey] || "-",
    },
  ];

  if (includeQuantidade) {
    columns.push(
      {
        key: "quantidadeAnterior",
        header: "Qtd ant.",
        align: "right",
        render: (item) => <NumberCell value={item.quantidadeAnterior} zeroAsDash />,
      },
      {
        key: "quantidadeAtual",
        header: "Qtd atual",
        align: "right",
        className: "font-semibold text-slate-800",
        render: (item) => <NumberCell value={item.quantidadeAtual} zeroAsDash />,
      },
    );
  }

  columns.push(
    {
      key: "valorAnterior",
      header: includeQuantidade ? "Vl. ant." : "Anterior",
      align: "right",
      className: "text-slate-600",
      render: (item) => <MoneyCell value={item.valorAnterior} zeroAsDash />,
    },
    {
      key: "valorAtual",
      header: includeQuantidade ? "Vl. atual" : "Atual",
      align: "right",
      className: "font-semibold text-slate-800",
      render: (item) => <MoneyCell value={item.valorAtual} zeroAsDash />,
    },
  );

  if (!includeQuantidade) {
    columns.push({
      key: "diferenca",
      header: "Diferença",
      align: "right",
      render: (item) => (
        <MoneyCell
          className={item.variacao.valor < 0 ? "text-red-600" : "text-emerald-700"}
          value={item.variacao.valor}
          zeroAsDash
        />
      ),
    });
  }

  columns.push({
    key: "variacao",
    header: "Variação",
    align: "center",
    render: (item) => <VariacaoBadge percentual={item.variacao.percentual} />,
  });

  return (
    <DataTable
      columns={columns}
      data={linhas}
      emptyMessage={emptyMessage}
      getRowKey={(item, index) => `${rowKeyPrefix}-${item[labelKey] || index}`}
      theadClassName="bg-slate-100"
    />
  );
}
