import { useMemo, useState } from "react";
import {
  CANAL_APP,
  CANAL_ECOMMERCE,
  CANAL_LOJA_FISICA,
  normalizeSalesChannel,
} from "../../utils/salesChannel";
import { formatMoneyCellValue, isZeroMoneyValue } from "../ui/MoneyCell";
import VendasListaPanel from "./VendasListaPanel";
import {
  calcularTotalizadoresListaVendasFinanceiro,
  formatarDataVendaFinanceiro,
  getStatusVendaMeta,
  montarCardsTotalizadoresListaVendasFinanceiro,
} from "./vendasFinanceiroUtils";

function arredondar(valor) {
  return Math.round(Number(valor || 0) * 100) / 100;
}

function percentual(parte, total) {
  if (!Number(total || 0)) return 0;
  return arredondar((Number(parte || 0) / Number(total || 1)) * 100);
}

function criarItemDemo({
  custoUnitario,
  id,
  imposto = 0,
  nome,
  precoUnitario,
  quantidade,
  sku,
  taxaPagamento = 0,
}) {
  const vendaBruta = arredondar(Number(precoUnitario || 0) * Number(quantidade || 0));
  const custoTotal = arredondar(Number(custoUnitario || 0) * Number(quantidade || 0));
  const valorLiquido = arredondar(vendaBruta - Number(taxaPagamento || 0) - Number(imposto || 0));
  const lucro = arredondar(valorLiquido - custoTotal);

  return {
    produto_id: id,
    produto_nome: nome,
    sku,
    categoria: "Racoes e petiscos",
    quantidade,
    preco_unitario: precoUnitario,
    venda_bruta: vendaBruta,
    taxa_loja: 0,
    desconto: 0,
    taxa_entrega: 0,
    taxa_operacional: 0,
    taxa_cartao: taxaPagamento,
    comissao: 0,
    imposto,
    campanha: 0,
    valor_liquido: valorLiquido,
    custo_unitario: custoUnitario,
    custo_total: custoTotal,
    lucro,
    lucro_unitario: arredondar(lucro / Number(quantidade || 1)),
    margem_sobre_venda: percentual(lucro, vendaBruta),
    margem_sobre_custo: percentual(lucro, custoTotal),
  };
}

function criarVendaDemo({
  canal,
  cliente,
  codigo,
  data,
  formaPagamento,
  gateway,
  id,
  itens,
  nfEmitida = false,
  pagamentoLabel,
  status = "finalizada",
  taxaGateway = 0,
}) {
  const vendaBruta = arredondar(
    itens.reduce((total, item) => total + Number(item.venda_bruta || 0), 0),
  );
  const imposto = arredondar(itens.reduce((total, item) => total + Number(item.imposto || 0), 0));
  const custoProdutos = arredondar(
    itens.reduce((total, item) => total + Number(item.custo_total || 0), 0),
  );
  const vendaLiquida = arredondar(vendaBruta - Number(taxaGateway || 0) - imposto);
  const lucro = arredondar(vendaLiquida - custoProdutos);

  return {
    id,
    numero_venda: codigo,
    data_venda: data,
    cliente_nome: cliente,
    cliente_id: id.replace("demo-", ""),
    status,
    canal_venda: normalizeSalesChannel(canal, CANAL_LOJA_FISICA),
    origem: canal,
    forma_pagamento: formaPagamento,
    pagamento_principal: pagamentoLabel || formaPagamento,
    gateway_pagamento: gateway,
    adquirente: gateway,
    venda_bruta: vendaBruta,
    taxa_loja: 0,
    desconto: 0,
    taxa_entrega: 0,
    taxa_operacional: 0,
    taxa_cartao: taxaGateway,
    taxa_gateway: taxaGateway,
    taxa_mercado_pago: gateway === "mercadopago" ? taxaGateway : 0,
    valor_liquido_gateway: gateway === "mercadopago" ? vendaLiquida : undefined,
    valor_recebido: vendaLiquida,
    comissao: 0,
    imposto,
    imposto_aplicado: true,
    custo_campanha: 0,
    venda_liquida: vendaLiquida,
    custo_produtos: custoProdutos,
    lucro,
    margem_sobre_venda: percentual(lucro, vendaBruta),
    margem_sobre_custo: percentual(lucro, custoProdutos),
    nf_emitida: nfEmitida,
    itens,
  };
}

const VENDAS_PREVIEW = [
  criarVendaDemo({
    id: "demo-erp-001",
    codigo: "202606020490",
    data: "2026-06-02T10:18:00",
    cliente: "Juliana Duarte",
    canal: CANAL_LOJA_FISICA,
    formaPagamento: "Cartao Debito",
    pagamentoLabel: "Maquininha",
    gateway: "stone",
    taxaGateway: 1.68,
    nfEmitida: true,
    itens: [
      criarItemDemo({
        id: 205,
        nome: "Racao Special Dog Ultralife Adultos 15kg",
        sku: "205",
        quantidade: 1,
        precoUnitario: 174.9,
        custoUnitario: 132.4,
        taxaPagamento: 1.68,
        imposto: 8.74,
      }),
    ],
  }),
  criarVendaDemo({
    id: "demo-app-001",
    codigo: "202606020501",
    data: "2026-06-02T13:28:00",
    cliente: "Gabrielle App",
    canal: CANAL_APP,
    formaPagamento: "Pix",
    pagamentoLabel: "Mercado Pago Pix",
    gateway: "mercadopago",
    taxaGateway: 0.14,
    itens: [
      criarItemDemo({
        id: 4682,
        nome: "Sache Gran Plus Gourmet Gato Adulto Frango 85g",
        sku: "4682",
        quantidade: 1,
        precoUnitario: 2.02,
        custoUnitario: 1.41,
        taxaPagamento: 0.14,
        imposto: 0.08,
      }),
    ],
  }),
  criarVendaDemo({
    id: "demo-ecommerce-001",
    codigo: "202606020502",
    data: "2026-06-02T15:01:00",
    cliente: "Lucas Ecommerce",
    canal: CANAL_ECOMMERCE,
    formaPagamento: "Pix",
    pagamentoLabel: "Mercado Pago Pix",
    gateway: "mercadopago",
    taxaGateway: 0.23,
    itens: [
      criarItemDemo({
        id: 4682,
        nome: "Sache Gran Plus Gourmet Gato Adulto Frango 85g",
        sku: "4682",
        quantidade: 2,
        precoUnitario: 1.99,
        custoUnitario: 1.37,
        taxaPagamento: 0.23,
        imposto: 0.16,
      }),
    ],
  }),
];

const formatarMoeda = (valor) => formatMoneyCellValue(valor);
const formatarMoedaOuTraco = (valor) => formatMoneyCellValue(valor, { zeroAsDash: true });
const formatarMoedaComSinalOuTraco = (valor, sinal) =>
  formatMoneyCellValue(valor, { sign: sinal, zeroAsDash: true });
const formatarPercentualOuTraco = (valor) => {
  if (isZeroMoneyValue(valor)) return "-";
  return `${Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`;
};

export default function VendasCanaisPreview() {
  const [filtroCanalVenda, setFiltroCanalVenda] = useState("");
  const [filtroStatusLista, setFiltroStatusLista] = useState("");
  const [mostrarImpostoTodasVendas, setMostrarImpostoTodasVendas] = useState(true);
  const [vendasExpandidas, setVendasExpandidas] = useState(new Set());

  const listaVendasFiltrada = useMemo(() => {
    const porCanal = filtroCanalVenda
      ? VENDAS_PREVIEW.filter((venda) => venda.canal_venda === filtroCanalVenda)
      : VENDAS_PREVIEW;

    if (filtroStatusLista !== "em_aberto") return porCanal;

    return porCanal.filter((venda) =>
      ["aberta", "pendente", "em_aberto"].includes(String(venda.status || "").toLowerCase()),
    );
  }, [filtroCanalVenda, filtroStatusLista]);

  const totalizadores = useMemo(
    () => calcularTotalizadoresListaVendasFinanceiro(listaVendasFiltrada),
    [listaVendasFiltrada],
  );

  const cardsTotalizadoresLista = useMemo(
    () =>
      montarCardsTotalizadoresListaVendasFinanceiro(totalizadores, {
        formatarMoedaOuTraco,
        formatarMoedaComSinalOuTraco,
        formatarPercentualOuTraco,
      }),
    [totalizadores],
  );

  const toggleVendaExpandida = (id) => {
    setVendasExpandidas((vendasAtuais) => {
      const proximasVendas = new Set(vendasAtuais);
      if (proximasVendas.has(id)) {
        proximasVendas.delete(id);
      } else {
        proximasVendas.add(id);
      }
      return proximasVendas;
    });
  };

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-5 text-slate-900">
      <div className="mx-auto max-w-[1600px] space-y-4">
        <section className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Preview local
          </div>
          <h1 className="mt-1 text-xl font-bold text-slate-900">
            Lista de vendas por canal, sem nova coluna
          </h1>
          <p className="mt-1 max-w-4xl text-sm text-slate-600">
            ERP/PDV, App e E-commerce aparecem como etiquetas dentro da coluna Codigo. As taxas do
            Mercado Pago ficam na coluna Tx. Pagto, junto com o valor liquido recebido.
          </p>
        </section>

        <VendasListaPanel
          abrirVendaNoPdv={() => {}}
          cardsTotalizadoresLista={cardsTotalizadoresLista}
          filtroCanalVenda={filtroCanalVenda}
          filtroStatusLista={filtroStatusLista}
          formatarData={formatarDataVendaFinanceiro}
          formatarMoeda={formatarMoeda}
          getStatusVendaMeta={getStatusVendaMeta}
          limparFiltroStatusLista={() => setFiltroStatusLista("")}
          listaVendasFiltrada={listaVendasFiltrada}
          listaVendasVisiveis={VENDAS_PREVIEW}
          mostrarImpostoTodasVendas={mostrarImpostoTodasVendas}
          setFiltroCanalVenda={setFiltroCanalVenda}
          setFiltroStatusLista={setFiltroStatusLista}
          setMostrarImpostoTodasVendas={setMostrarImpostoTodasVendas}
          toggleVendaExpandida={toggleVendaExpandida}
          vendasExpandidas={vendasExpandidas}
        />
      </div>
    </main>
  );
}
