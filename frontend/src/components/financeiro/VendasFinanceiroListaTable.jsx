import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CreditCard,
  ExternalLink,
  ShoppingCart,
  Smartphone,
  Store,
} from "lucide-react";
import CustomerIdentity from "../ui/CustomerIdentity";
import DataTable from "../ui/DataTable";
import MoneyCell from "../ui/MoneyCell";
import NumberCell from "../ui/NumberCell";
import SaleReference from "../ui/SaleReference";
import StatusBadge from "../ui/StatusBadge";
import ProductIdentity from "../ui/ProductIdentity";
import {
  CANAL_APP,
  CANAL_ECOMMERCE,
  CANAL_LOJA_FISICA,
  normalizeSalesChannel,
} from "../../utils/salesChannel";

const CANAL_CONFIG = {
  [CANAL_LOJA_FISICA]: {
    label: "ERP/PDV",
    className: "border-blue-200 bg-blue-50 text-blue-700",
    rowClassName: "border-l-4 border-l-blue-500",
    icon: Store,
  },
  [CANAL_APP]: {
    label: "App",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
    rowClassName: "border-l-4 border-l-emerald-500",
    icon: Smartphone,
  },
  [CANAL_ECOMMERCE]: {
    label: "E-commerce",
    className: "border-purple-200 bg-purple-50 text-purple-700",
    rowClassName: "border-l-4 border-l-purple-500",
    icon: ShoppingCart,
  },
};

function obterCanalVenda(venda) {
  return normalizeSalesChannel(
    venda?.canal_venda ||
      venda?.origem_canal_venda ||
      venda?.canal ||
      venda?.origem ||
      venda?.origem_loja_virtual,
    CANAL_LOJA_FISICA,
  );
}

function getCanalConfig(venda) {
  const canal = obterCanalVenda(venda);
  return CANAL_CONFIG[canal] || CANAL_CONFIG[CANAL_LOJA_FISICA];
}

function CanalVendaBadge({ venda }) {
  const config = getCanalConfig(venda);
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase leading-none ${config.className}`}
      title="Canal de origem desta venda"
    >
      <Icon className="h-3 w-3" />
      {config.label}
    </span>
  );
}

function normalizarGateway(venda) {
  return String(
    venda?.gateway_pagamento ||
      venda?.gateway_provider ||
      venda?.gateway ||
      venda?.adquirente ||
      venda?.operadora ||
      "",
  )
    .trim()
    .toLowerCase();
}

function isMercadoPago(venda) {
  const gateway = normalizarGateway(venda);
  return gateway.includes("mercado") || gateway.includes("mp");
}

function hasValorInformado(valor) {
  return valor !== null && valor !== undefined && valor !== "";
}

function obterTaxaGatewayInformada(venda) {
  const camposTaxa = [
    venda?.taxa_gateway,
    venda?.taxa_mercado_pago,
    venda?.taxa_pagamento,
  ];
  return camposTaxa.find(hasValorInformado);
}

function obterTaxaGateway(venda) {
  const taxaGatewayInformada = obterTaxaGatewayInformada(venda);
  const taxa = hasValorInformado(taxaGatewayInformada)
    ? taxaGatewayInformada
    : isMercadoPago(venda)
      ? 0
      : venda?.taxa_cartao;
  return Number(taxa || 0);
}

function obterLiquidoGateway(venda, taxaGateway) {
  const valor =
    venda?.valor_liquido_gateway ??
    venda?.gateway_valor_liquido ??
    venda?.valor_recebido;
  if (valor !== null && valor !== undefined && valor !== "") return Number(valor || 0);
  return Number(venda?.venda_bruta || 0) - Number(taxaGateway || 0);
}

function CodigoVendaCell({ abrirVendaNoPdv, venda }) {
  const saleNumber = venda.numero_venda || venda.id;

  return (
    <div className="min-w-[120px]">
      <SaleReference
        sale={venda}
        showPrefix={false}
        value={saleNumber}
        valueClassName=""
      >
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            abrirVendaNoPdv?.(venda);
          }}
          className="inline-flex items-center gap-1 border-0 bg-transparent p-0 font-medium text-blue-700 hover:text-blue-900 hover:underline"
          title="Abrir venda no PDV"
        >
          #{saleNumber}
          <ExternalLink className="h-3.5 w-3.5" />
        </button>
      </SaleReference>
      <div className="mt-1">
        <CanalVendaBadge venda={venda} />
      </div>
    </div>
  );
}

function CustoCampanhaCell({ venda }) {
  const cupomCode = venda.cupom_code ? String(venda.cupom_code).trim().toUpperCase() : "";

  return (
    <div className="flex flex-col items-end leading-tight">
      <MoneyCell value={venda.custo_campanha} sign="-" zeroAsDash />
      {cupomCode && Number(venda.custo_campanha || 0) > 0 && (
        <span className="mt-0.5 max-w-[110px] truncate rounded bg-teal-50 px-1.5 py-0.5 text-[10px] font-semibold text-teal-700">
          {cupomCode}
        </span>
      )}
    </div>
  );
}

function StatusVendaCell({ getStatusVendaMeta, status }) {
  const statusMeta = getStatusVendaMeta(status);

  return (
    <StatusBadge intent={statusMeta.intent} size="xs">
      {statusMeta.label}
    </StatusBadge>
  );
}

function TaxaPagamentoCell({ venda }) {
  const taxaGateway = obterTaxaGateway(venda);
  const liquidoGateway = obterLiquidoGateway(venda, taxaGateway);
  const mercadoPago = isMercadoPago(venda);
  const taxaPendente = mercadoPago && !hasValorInformado(obterTaxaGatewayInformada(venda));

  if (!mercadoPago) {
    return <MoneyCell value={venda.taxa_cartao} sign="-" zeroAsDash />;
  }

  return (
    <div className="flex min-w-[110px] flex-col items-end leading-tight">
      <div className="inline-flex items-center gap-1 text-purple-700">
        <CreditCard className="h-3.5 w-3.5" />
        <MoneyCell value={taxaGateway} sign="-" zeroAsDash />
      </div>
      <span
        className={`mt-0.5 inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
          taxaPendente ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"
        }`}
        title={
          taxaPendente
            ? "Pagamento via Mercado Pago sem taxa conciliada ainda"
            : "Taxa do Mercado Pago conciliada nesta venda"
        }
      >
        {taxaPendente ? (
          <AlertCircle className="h-3 w-3" />
        ) : (
          <CheckCircle2 className="h-3 w-3" />
        )}
        {taxaPendente ? "Taxa pend." : "MP"}
      </span>
      {!taxaPendente && (
        <span className="mt-0.5 text-[10px] font-semibold text-slate-500">
          Liq. <MoneyCell value={liquidoGateway} zeroAsDash />
        </span>
      )}
    </div>
  );
}

function ItensVendaDetalhes({ colSpan, formatarMoeda, venda }) {
  if (!Array.isArray(venda.itens) || venda.itens.length === 0) return null;

  return (
    <tr className="bg-blue-50">
      <td colSpan={colSpan} className="px-2 py-3 sm:px-4">
        <div className="pl-0 sm:pl-8">
          <div className="mb-2 font-semibold text-slate-700">Produtos desta venda:</div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1280px] text-xs">
            <thead className="bg-blue-100">
              <tr>
                <th className="px-1 py-1 text-left">Produto</th>
                <th className="px-1 py-1 text-center">Qtd</th>
                <th className="px-1 py-1 text-right">Preço Unit.</th>
                <th className="px-1 py-1 text-right">Venda Bruta</th>
                <th className="px-1 py-1 text-right">Tx Loja</th>
                <th className="px-1 py-1 text-right">Desconto</th>
                <th className="px-1 py-1 text-right">Tx. Entr.</th>
                <th className="px-1 py-1 text-right">Tx. Oper.</th>
                <th className="px-1 py-1 text-right">Tx. Cartão</th>
                <th className="px-1 py-1 text-right">Comissão</th>
                <th className="px-1 py-1 text-right">Imposto</th>
                <th
                  className="px-1 py-1 text-right"
                  title="Cashback/cupom rateado neste item"
                >
                  Campanha
                </th>
                <th className="px-1 py-1 text-right">Líquido</th>
                <th className="px-1 py-1 text-right">Custo Unit.</th>
                <th className="px-1 py-1 text-right">Custo Total</th>
                <th className="px-1 py-1 text-right">Lucro</th>
                <th className="px-1 py-1 text-right">MG Venda</th>
                <th className="px-1 py-1 text-right">MG Custo</th>
              </tr>
            </thead>
            <tbody>
              {venda.itens.map((item, idx) => (
                <tr
                  key={`${venda.id}-item-${item.produto_id || item.produto_nome || idx}`}
                  className="border-b border-blue-200 hover:bg-blue-100"
                >
                  <td className="px-1 py-1">
                    <ProductIdentity product={item}>
                      {item.em_promocao && (
                        <span
                          className="rounded-full bg-cyan-100 px-2 py-0.5 text-[10px] font-bold uppercase text-cyan-700"
                          title={item.promocao_origem || "Item vendido por preço promocional ativo"}
                        >
                          Promo
                        </span>
                      )}
                    </ProductIdentity>
                  </td>
                  <td className="px-1 py-1 text-center">
                    <NumberCell value={item.quantidade} zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right whitespace-nowrap">
                    <MoneyCell value={item.preco_unitario} zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right font-medium whitespace-nowrap">
                    <MoneyCell value={item.venda_bruta} zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right text-green-700 whitespace-nowrap">
                    <MoneyCell value={item.taxa_loja || 0} sign="+" zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right text-red-600 whitespace-nowrap">
                    <MoneyCell value={item.desconto} sign="-" zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right text-blue-600 whitespace-nowrap">
                    <MoneyCell value={item.taxa_entrega} sign="-" zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right text-orange-500 whitespace-nowrap">
                    <MoneyCell value={item.taxa_operacional || 0} sign="-" zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right text-purple-600 whitespace-nowrap">
                    <MoneyCell value={item.taxa_cartao} sign="-" zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right text-blue-600 whitespace-nowrap">
                    <MoneyCell value={item.comissao} sign="-" zeroAsDash />
                  </td>
                  <td
                    className="px-1 py-1 text-right text-pink-600 whitespace-nowrap"
                    title={
                      venda.imposto_aplicado
                        ? "Impostos rateados neste item"
                        : "Imposto oculto porque a venda não tem NF/NFC-e emitida"
                    }
                  >
                    <MoneyCell value={item.imposto || 0} sign="-" zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right text-teal-600 whitespace-nowrap">
                    <MoneyCell value={item.campanha} sign="-" zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right font-medium whitespace-nowrap">
                    <MoneyCell value={item.valor_liquido} zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right text-orange-600 whitespace-nowrap">
                    <MoneyCell value={item.custo_unitario} zeroAsDash />
                  </td>
                  <td className="px-1 py-1 text-right text-orange-600 font-medium whitespace-nowrap">
                    <MoneyCell value={item.custo_total} sign="-" zeroAsDash />
                  </td>
                  <td
                    className={`px-1 py-1 text-right font-bold whitespace-nowrap ${item.lucro >= 0 ? "text-green-600" : "text-red-600"} cursor-help`}
                    title={`Lucro unitário: ${formatarMoeda(item.lucro_unitario)}`}
                  >
                    <MoneyCell value={item.lucro} zeroAsDash />
                  </td>
                  <td
                    className="px-1 py-1 text-right whitespace-nowrap cursor-help"
                    title={`Margem: ${item.margem_sobre_venda}%`}
                  >
                    <NumberCell
                      value={item.margem_sobre_venda}
                      decimals={1}
                      suffix="%"
                      zeroAsDash
                    />
                  </td>
                  <td
                    className="px-1 py-1 text-right whitespace-nowrap cursor-help"
                    title={`Markup: ${item.margem_sobre_custo}%`}
                  >
                    <NumberCell
                      value={item.margem_sobre_custo}
                      decimals={1}
                      suffix="%"
                      zeroAsDash
                    />
                  </td>
                </tr>
              ))}
            </tbody>
            </table>
          </div>
        </div>
      </td>
    </tr>
  );
}

export default function VendasFinanceiroListaTable({
  abrirVendaNoPdv,
  formatarData,
  formatarMoeda,
  getStatusVendaMeta,
  onToggleVenda,
  vendas = [],
  vendasExpandidas,
}) {
  const columns = [
    {
      key: "expandir",
      header: "",
      headerClassName: "w-8",
      className: "w-8",
      render: (venda) =>
        vendasExpandidas.has(venda.id) ? (
          <ChevronDown className="h-4 w-4 text-slate-600" />
        ) : (
          <ChevronRight className="h-4 w-4 text-slate-600" />
        ),
    },
    {
      key: "data",
      header: "Data",
      className: "whitespace-nowrap",
      render: (venda) => formatarData(venda.data_venda),
    },
    {
      key: "codigo",
      header: "Código",
      className: "whitespace-nowrap",
      render: (venda) => (
        <CodigoVendaCell
          abrirVendaNoPdv={abrirVendaNoPdv}
          venda={venda}
        />
      ),
    },
    {
      key: "cliente",
      header: "Cliente",
      render: (venda) => (
        <CustomerIdentity
          nameClassName="font-medium text-slate-800"
          venda={venda}
        />
      ),
    },
    {
      key: "venda_bruta",
      header: "Venda Bruta",
      align: "right",
      className: "font-medium whitespace-nowrap",
      render: (venda) => <MoneyCell value={venda.venda_bruta} zeroAsDash />,
    },
    {
      key: "taxa_loja",
      header: "Tx Loja",
      align: "right",
      className: "text-green-700 whitespace-nowrap",
      cellTitle: "Taxa de entrega total cobrada do cliente",
      render: (venda) => <MoneyCell value={venda.taxa_loja || 0} sign="+" zeroAsDash />,
    },
    {
      key: "desconto",
      header: "Desconto",
      align: "right",
      className: "text-red-600 whitespace-nowrap",
      render: (venda) => <MoneyCell value={venda.desconto} sign="-" zeroAsDash />,
    },
    {
      key: "taxa_entrega",
      header: "Tx. Entrega",
      align: "right",
      className: "text-blue-600 whitespace-nowrap",
      cellTitle: "Comissão repassada ao entregador",
      render: (venda) => <MoneyCell value={venda.taxa_entrega} sign="-" zeroAsDash />,
    },
    {
      key: "taxa_operacional",
      header: "Tx. Operac.",
      align: "right",
      className: "text-orange-500 whitespace-nowrap",
      cellTitle: "Custo operacional da entrega (empresa)",
      render: (venda) => (
        <MoneyCell value={venda.taxa_operacional || 0} sign="-" zeroAsDash />
      ),
    },
    {
      key: "taxa_cartao",
      header: "Tx. Pagto",
      align: "right",
      className: "text-purple-600 whitespace-nowrap",
      title:
        "Taxa da operadora/adquirente. Para Mercado Pago, mostra taxa e valor liquido quando conciliado.",
      render: (venda) => <TaxaPagamentoCell venda={venda} />,
    },
    {
      key: "comissao",
      header: "Comissão",
      align: "right",
      className: "text-blue-600 whitespace-nowrap",
      render: (venda) => <MoneyCell value={venda.comissao} sign="-" zeroAsDash />,
    },
    {
      key: "imposto",
      header: "Imposto",
      align: "right",
      className: "text-pink-600 whitespace-nowrap",
      cellTitle: (venda) =>
        venda.imposto_aplicado
          ? "Impostos sobre faturamento"
          : "Imposto oculto porque a venda não tem NF/NFC-e emitida",
      render: (venda) => <MoneyCell value={venda.imposto || 0} sign="-" zeroAsDash />,
    },
    {
      key: "custo_campanha",
      header: "Custo Camp.",
      align: "right",
      headerClassName: "whitespace-nowrap",
      title: "Cashback / cupons resgatados nesta venda",
      className: "text-teal-600 whitespace-nowrap",
      cellTitle: (venda) =>
        venda.cupom_code
          ? `Custo com campanha por cupom ${String(venda.cupom_code).trim().toUpperCase()}`
          : "Custo com campanhas (cashback/cupom resgatado)",
      render: (venda) => <CustoCampanhaCell venda={venda} />,
    },
    {
      key: "venda_liquida",
      header: "Líquida",
      align: "right",
      className: "font-medium whitespace-nowrap",
      render: (venda) => <MoneyCell value={venda.venda_liquida} zeroAsDash />,
    },
    {
      key: "custo",
      header: "Custo",
      align: "right",
      className: "text-orange-600 whitespace-nowrap",
      render: (venda) => <MoneyCell value={venda.custo_produtos} sign="-" zeroAsDash />,
    },
    {
      key: "lucro",
      header: "Lucro",
      align: "right",
      className: (venda) =>
        `font-bold whitespace-nowrap ${venda.lucro >= 0 ? "text-green-600" : "text-red-600"}`,
      render: (venda) => <MoneyCell value={venda.lucro} zeroAsDash />,
    },
    {
      key: "margem_venda",
      header: "MG Venda",
      align: "right",
      className: "whitespace-nowrap",
      render: (venda) => (
        <NumberCell value={venda.margem_sobre_venda} decimals={1} suffix="%" zeroAsDash />
      ),
    },
    {
      key: "margem_custo",
      header: "MG Custo",
      align: "right",
      className: "whitespace-nowrap",
      render: (venda) => (
        <NumberCell value={venda.margem_sobre_custo} decimals={1} suffix="%" zeroAsDash />
      ),
    },
    {
      key: "status",
      header: "Status",
      align: "center",
      render: (venda) => (
        <StatusVendaCell getStatusVendaMeta={getStatusVendaMeta} status={venda.status} />
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={vendas}
      emptyMessage="Nenhuma venda encontrada"
      getRowKey={(venda) => venda.id}
      isRowExpanded={(venda) => vendasExpandidas.has(venda.id)}
      onRowClick={(venda) => onToggleVenda(venda.id)}
      renderExpandedRow={(venda, _rowIndex, colSpan) => (
        <ItensVendaDetalhes colSpan={colSpan} formatarMoeda={formatarMoeda} venda={venda} />
      )}
      rowClassName={(venda) => getCanalConfig(venda).rowClassName}
      tableClassName="min-w-[1500px]"
      theadClassName="bg-gray-100"
    />
  );
}
