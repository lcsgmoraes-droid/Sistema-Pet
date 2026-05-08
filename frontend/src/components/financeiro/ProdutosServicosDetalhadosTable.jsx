import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";
import NumberCell from "../ui/NumberCell";
import ProductIdentity, { getProductIdentityCode } from "../ui/ProductIdentity";

function criarLinhas(linhas = []) {
  return linhas.flatMap((categoria, catIdx) => {
    const resultado = [
      {
        bruto: categoria.total_bruto,
        desconto: categoria.total_desconto,
        key: `cat-${catIdx}`,
        liquido: categoria.total_liquido,
        level: 0,
        nome: categoria.categoria,
        quantidade: categoria.total_quantidade,
        type: "categoria",
      },
    ];

    categoria.subcategorias?.forEach((sub, subIdx) => {
      resultado.push({
        bruto: sub.total_bruto,
        desconto: sub.total_desconto,
        key: `sub-${catIdx}-${subIdx}`,
        liquido: sub.total_liquido,
        level: 1,
        nome: sub.subcategoria,
        quantidade: sub.total_quantidade,
        type: "subcategoria",
      });

      sub.produtos?.forEach((produto, prodIdx) => {
        resultado.push({
          bruto: produto.valor_bruto,
          desconto: produto.desconto,
          key: `prod-${catIdx}-${subIdx}-${prodIdx}`,
          liquido: produto.valor_liquido,
          level: 2,
          codigo: getProductIdentityCode(produto),
          nome: produto.produto,
          quantidade: produto.quantidade,
          type: "produto",
        });
      });
    });

    categoria.produtos?.forEach((produto, prodIdx) => {
      resultado.push({
        bruto: produto.valor_bruto,
        desconto: produto.desconto,
        key: `prod-${catIdx}-${prodIdx}`,
        liquido: produto.valor_liquido,
        level: 1,
        codigo: getProductIdentityCode(produto),
        nome: produto.produto,
        quantidade: produto.quantidade,
        type: "produto",
      });
    });

    return resultado;
  });
}

function criarLinhaTotal(linhas = []) {
  if (linhas.length === 0) return null;

  return {
    bruto: linhas.reduce((sum, categoria) => sum + Number(categoria.total_bruto || 0), 0),
    desconto: linhas.reduce(
      (sum, categoria) => sum + Number(categoria.total_desconto || 0),
      0,
    ),
    key: "total-geral",
    liquido: linhas.reduce(
      (sum, categoria) => sum + Number(categoria.total_liquido || 0),
      0,
    ),
    level: 0,
    nome: "TOTAL GERAL",
    quantidade: linhas.reduce(
      (sum, categoria) => sum + Number(categoria.total_quantidade || 0),
      0,
    ),
    type: "total",
  };
}

function nomeClassName(item) {
  const padding = item.level === 2 ? "pl-10" : item.level === 1 ? "pl-6" : "";
  const tone = item.type === "produto" ? "text-slate-700" : "text-slate-900";
  return [padding, tone].filter(Boolean).join(" ");
}

export default function ProdutosServicosDetalhadosTable({
  linhas = [],
  linhasTotal = [],
}) {
  const linhaTotal = criarLinhaTotal(linhasTotal);
  const data = linhaTotal ? [...criarLinhas(linhas), linhaTotal] : criarLinhas(linhas);

  return (
    <DataTable
      columns={[
        {
          key: "nome",
          header: "Produtos/Serviços",
          render: (item) => {
            if (item.type !== "produto") {
              return <span className={nomeClassName(item)}>{item.nome || "-"}</span>;
            }

            return (
              <ProductIdentity
                className={nomeClassName(item)}
                code={item.codigo}
                name={item.nome}
              />
            );
          },
        },
        {
          key: "quantidade",
          header: "Itens",
          align: "right",
          render: (item) => <NumberCell value={item.quantidade} />,
        },
        {
          key: "bruto",
          header: "Bruto",
          align: "right",
          render: (item) => <MoneyCell value={item.bruto} />,
        },
        {
          key: "desconto",
          header: "Desconto",
          align: "right",
          render: (item) => <MoneyCell value={item.desconto} />,
        },
        {
          key: "liquido",
          header: "Líquido",
          align: "right",
          render: (item) => <MoneyCell value={item.liquido} />,
        },
      ]}
      data={data}
      emptyMessage="Nenhum produto ou serviço encontrado"
      getRowKey={(item) => item.key}
      rowClassName={(item) => {
        if (item.type === "total") {
          return "bg-slate-200 font-bold text-slate-800 hover:bg-slate-200";
        }
        if (item.type === "categoria") {
          return "bg-blue-50 font-semibold text-slate-800 hover:bg-blue-50";
        }
        if (item.type === "subcategoria") {
          return "bg-slate-50 font-medium text-slate-700 hover:bg-slate-50";
        }
        return "";
      }}
      theadClassName="bg-slate-100"
    />
  );
}
