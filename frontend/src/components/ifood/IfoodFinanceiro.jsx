import { useState } from "react";
import { AlertTriangle, DollarSign, Eye, RefreshCw } from "lucide-react";
import DataTable from "../ui/DataTable";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import CartaoIndicador from "../v2/CartaoIndicador/CartaoIndicador";
import EstadoVazio from "../v2/EstadoVazio/EstadoVazio";
import InputCheck from "../v2/InputCheck/InputCheck";
import InputMoeda from "../v2/InputMoeda/InputMoeda";
import InputPeriodo from "../v2/InputPeriodo/InputPeriodo";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";
import { useEscapeToClose } from "../../utils/modalEscape";
import { moedaIfood, percentualIfood, valorConhecido } from "./ifoodPresentation";
import useIfoodFinanceiro from "./useIfoodFinanceiro";

const TOTAIS = [
  ["registered_payments", "Recebimentos registrados"],
  ["fees", "Taxas informadas pelo iFood"],
  ["store_subsidy", "Subsídios da loja"],
  ["ifood_subsidy", "Subsídios do iFood"],
  ["transfer_impact", "Impacto informado no repasse"],
];
const CUSTOS = [
  ["revenue", "Receita da loja antes das taxas"],
  ["cmv", "CMV desta venda"],
  ["tax", "Tributos desta venda"],
  ["other_costs", "Outros custos desta venda"],
];
const NOMES_EVENTOS = {
  ORDER_PAYMENT: "Pagamento do pedido",
  ORDER_COMMISSION: "Comissão iFood",
  PAYMENT_TRANSACTION_FEE: "Taxa de pagamento",
  IFOOD_SUBSIDY: "Subsídio do iFood",
  STORE_SUBSIDY: "Promoção da loja",
};

function dataFinanceira(value) {
  if (!value) return "Não informado";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value.split("-").reverse().join("/");
  const data = new Date(value);
  return Number.isNaN(data.getTime())
    ? "Não informado"
    : data.toLocaleString("pt-BR", {
        timeZone: "America/Sao_Paulo",
      });
}

function Contribuicao({ contribution }) {
  return contribution?.calculated ? (
    <span>
      {moedaIfood(contribution.amount)} · {percentualIfood(contribution.percent)}
    </span>
  ) : (
    <span className="v2-texto-ajuda">Não calculada · faltam dados</span>
  );
}

const eventColumns = [
  {
    key: "name",
    header: "Evento",
    render: (event) => (
      <div>
        <p className="font-medium">
          {Object.hasOwn(NOMES_EVENTOS, event.name)
            ? NOMES_EVENTOS[event.name]
            : event.name || "Não informado"}
        </p>
        {Object.hasOwn(NOMES_EVENTOS, event.name) ? (
          <p className="v2-texto-ajuda">{event.name}</p>
        ) : null}
        <p className="v2-texto-ajuda">{event.description || event.trigger || ""}</p>
      </div>
    ),
  },
  {
    key: "amount",
    header: "Valor informado",
    align: "right",
    render: (event) => moedaIfood(event.amount),
  },
  {
    key: "billing",
    header: "Base e taxa observada",
    render: (event) => (
      <div>
        <p>{moedaIfood(event.billing?.base_value)}</p>
        <p className="v2-texto-ajuda">{percentualIfood(event.billing?.fee_percentage)}</p>
      </div>
    ),
  },
  {
    key: "payment",
    header: "Pagamento",
    render: (event) => (
      <div>
        <p>{event.payment_method || "Não informado"}</p>
        <p className="v2-texto-ajuda">
          {event.payment_liability === "MERCHANT"
            ? "Recebido pela loja"
            : event.payment_liability === "IFOOD"
              ? "Recebido pelo iFood"
              : "Recebedor não informado"}
        </p>
      </div>
    ),
  },
  {
    key: "impact",
    header: "Impacta repasse?",
    render: (event) =>
      event.has_transfer_impact === true
        ? "Sim"
        : event.has_transfer_impact === false
          ? "Não"
          : "Não informado",
  },
  {
    key: "settlement",
    header: "Previsão informada",
    render: (event) => dataFinanceira(event.expected_settlement_date),
  },
];

function VendaFinanceira({ order, c }) {
  const editar = c.pedido === order.order_id;
  const podeSalvar = Boolean(c.status?.can_edit_costs);
  useEscapeToClose({ onClose: () => c.fecharDetalhe(), disabled: c.ocupado });
  return (
    <ModalPadrao
      titulo={`Eventos da venda · ${order.order_id}`}
      tamanho="ampla"
      onFechar={() => {
        if (!c.ocupado) c.fecharDetalhe();
      }}
      rodape={
        <BotaoCancelar disabled={c.ocupado} onClick={c.fecharDetalhe}>
          Fechar
        </BotaoCancelar>
      }
    >
      <div className="space-y-5">
        <p className="v2-texto font-semibold text-amber-800 dark:text-amber-200">
          Homologação iFood · ainda não confirmado no banco
        </p>
        <DataTable
          columns={eventColumns}
          data={order.events || []}
          getRowKey={(event) => event.position}
          emptyMessage="Nenhum evento vinculado a esta venda."
        />
        <section className="space-y-2">
          <h3 className="v2-titulo-secao">Contribuição com custos informados</h3>
          <p>
            <Contribuicao contribution={order.contribution} />
          </p>
          {order.pending?.length || order.contribution?.missing?.length ? (
            <p className="v2-texto text-amber-800 dark:text-amber-200">
              {[
                ...new Set([...(order.pending || []), ...(order.contribution?.missing || [])]),
              ].join(" · ")}
            </p>
          ) : null}
          <p className="v2-texto-ajuda">
            Cálculo fornecido pelo servidor com os eventos e custos informados desta venda.
            Recebimentos e subsídios não são somados novamente. Não representa lucro final nem
            confirmação de recebimento bancário. Custos manuais são informados pelo usuário para o
            pedido inteiro. O vínculo automático com custos ERP é uma etapa seguinte.
          </p>
          {order.manual_costs ? (
            <p className="v2-texto-ajuda">
              Custos versão {order.manual_costs.version} ·{" "}
              {dataFinanceira(order.manual_costs.recorded_at)}
              {" · "}
              {order.manual_costs.source_note}
            </p>
          ) : (
            <p className="v2-texto-ajuda">Nenhuma versão de custos informada para esta venda.</p>
          )}
        </section>
        {c.status?.can_edit_costs && !editar ? (
          <BotaoInteracao onClick={() => c.abrirCustos(order.order_id, order.manual_costs)}>
            Informar custos desta venda
          </BotaoInteracao>
        ) : null}
        {editar ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              c.salvarCustos();
            }}
            className="space-y-4"
          >
            <h3 className="v2-titulo-secao">Custos informados desta venda</h3>
            <p className="v2-texto-ajuda">
              Salvar cria uma versão auditável; não modifica os eventos do iFood, as regras da loja
              ou o cadastro dos produtos. Todos os valores são totais do pedido, não por unidade.
              Desconhecido permanece sem informar; zero confirma que aquele custo não se aplica.
            </p>
            <p className="v2-texto-ajuda">
              Receita da loja antes das taxas inclui os créditos e subsídios devidos à loja, com os
              descontos financiados pela loja já descontados, e exclui taxas exclusivas do
              consumidor. Informe a receita antes de descontar comissão e taxa de pagamento, que são
              descontadas pelo cálculo do servidor. Esse valor não é o repasse nem o total pago pelo
              consumidor.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              {CUSTOS.map(([key, label]) => (
                <div
                  key={key}
                  className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700"
                >
                  <p className="v2-rotulo">{label}</p>
                  <InputCheck
                    id={`ifood-financeiro-${key}`}
                    checked={valorConhecido(c.rascunho[key])}
                    disabled={c.ocupado || !podeSalvar}
                    label={valorConhecido(c.rascunho[key]) ? "Informado" : "Não informado"}
                    onChange={(checked) => c.alterarCusto(key, checked ? 0 : null)}
                  />
                  {valorConhecido(c.rascunho[key]) ? (
                    <InputMoeda
                      id={`ifood-financeiro-valor-${key}`}
                      label={label}
                      value={c.rascunho[key]}
                      disabled={c.ocupado || !podeSalvar}
                      onChange={(value) => c.alterarCusto(key, value)}
                    />
                  ) : null}
                </div>
              ))}
            </div>
            <InputTextoLongo
              id="ifood-financeiro-fonte"
              label="Fonte e justificativa dos valores"
              value={c.rascunho.source_note}
              required
              maxLength={1000}
              disabled={c.ocupado || !podeSalvar}
              onChange={(value) => c.alterarCusto("source_note", value)}
              help="Registre a origem da receita e dos custos desta venda, sem credenciais ou dados bancários."
            />
            {c.erroCustos ? (
              <p role="alert" className="text-sm text-red-700 dark:text-red-300">
                {c.erroCustos}
              </p>
            ) : null}
            {!podeSalvar ? (
              <p role="status" className="v2-texto-ajuda">
                Não foi possível confirmar a permissão de salvar. Atualize a consulta; seu rascunho
                foi mantido.
              </p>
            ) : null}
            <BotaoSalva disabled={c.ocupado || !podeSalvar} loading={c.ocupado}>
              Salvar versão dos custos
            </BotaoSalva>
          </form>
        ) : null}
      </div>
    </ModalPadrao>
  );
}

export default function IfoodFinanceiro({ ativo = false, periodoSugerido = null }) {
  const c = useIfoodFinanceiro({ enabled: ativo, periodoSugerido });
  const [detalhe, setDetalhe] = useState(null);
  const report = c.relatorio;
  const order = report?.orders?.find((item) => item.order_id === detalhe);
  const sintetico = report?.metadata?.source === "synthetic";
  const columns = [
    {
      key: "order_id",
      header: "Venda",
      render: (item) => <span className="break-all">{item.order_id}</span>,
    },
    ...TOTAIS.map(([key, header]) => ({
      key,
      header,
      align: "right",
      render: (item) => moedaIfood(item.totals?.[key]),
    })),
    {
      key: "contribution",
      header: "Contribuição com custos informados",
      render: (item) => <Contribuicao contribution={item.contribution} />,
    },
    {
      key: "acoes",
      header: "Ações",
      render: (item) => (
        <BotaoInteracao icon={Eye} tamanho="pequeno" onClick={() => setDetalhe(item.order_id)}>
          Conferir venda
        </BotaoInteracao>
      ),
    },
  ];
  return (
    <section className="space-y-5" aria-label="Financeiro do iFood">
      <div
        role="status"
        className="space-y-1 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200"
      >
        <h2 className="v2-titulo-secao">Homologação iFood · ainda não confirmado no banco</h2>
        <p className="text-sm">
          {sintetico
            ? "Dados sintéticos de teste. Não refletem vendas reais da loja."
            : "Consulta de eventos financeiros de homologação. Os valores não confirmam recebimento bancário."}
        </p>
        <p className="v2-texto-ajuda">
          Sales, conciliação e repasses completos são etapas seguintes. Esta entrega consulta
          somente eventos e custos informados.
        </p>
        {report?.imported ? (
          <p className="text-sm font-semibold">Eventos importados · conciliação pendente</p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-64 flex-1">
          <InputPeriodo
            id="ifood-financeiro-periodo"
            label="Período dos eventos"
            value={c.periodo}
            onChange={c.alterarPeriodo}
            disabled={c.ocupado}
            error={!c.periodoValido ? "Escolha um período válido de 1 a 33 dias." : ""}
          />
        </div>
        <BotaoInteracao
          icon={RefreshCw}
          loading={c.carregando}
          disabled={!c.periodoValido || c.ocupado}
          onClick={c.atualizar}
        >
          Atualizar consulta local
        </BotaoInteracao>
        <BotaoInteracao
          icon={RefreshCw}
          disabled={!c.status?.can_sync || !c.periodoValido || c.carregando}
          loading={c.ocupado}
          onClick={c.sincronizar}
        >
          Consultar eventos no iFood
        </BotaoInteracao>
      </div>
      {c.status?.message ? <p className="v2-texto-ajuda">{c.status.message}</p> : null}
      {c.erro ? (
        <p
          role="alert"
          className="rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-500/10 dark:text-red-200"
        >
          {c.erro}
        </p>
      ) : null}
      {c.sucesso ? (
        <p role="status" className="v2-texto">
          {c.sucesso}
        </p>
      ) : null}
      {c.carregando ? (
        <p role="status" className="v2-texto-ajuda">
          Atualizando o financeiro. Os últimos dados e os custos em edição foram mantidos.
        </p>
      ) : null}
      {report ? (
        <div className="space-y-4">
          <p className="v2-texto-ajuda">
            Fonte:{" "}
            {sintetico
              ? "Dados sintéticos de teste"
              : report.metadata?.source === "ifood_financial_events"
                ? "iFood Financial · eventos de homologação"
                : "Ainda não importado"}
            {" · "}Período exibido: {dataFinanceira(report.begin_date)} a{" "}
            {dataFinanceira(report.end_date)}
            {" · "}Última consulta: {dataFinanceira(report.metadata?.retrieved_at)}
            {" · "}Revisão: {report.metadata?.revision ?? "Não informada"}
          </p>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {TOTAIS.map(([key, label]) => (
              <CartaoIndicador key={key} titulo={label} icone={DollarSign}>
                <p className="text-lg font-semibold">{moedaIfood(report.summary?.[key])}</p>
              </CartaoIndicador>
            ))}
          </div>
          {report.warnings?.length ? (
            <div role="status" className="v2-texto text-amber-800 dark:text-amber-200">
              {report.warnings.map((warning, index) => (
                <p key={index}>{warning}</p>
              ))}
            </div>
          ) : null}
          <DataTable
            columns={columns}
            data={report.orders || []}
            getRowKey={(item) => item.order_id}
            emptyMessage={
              report.imported
                ? "Nenhuma venda vinculada aos eventos deste período."
                : "Nenhuma consulta de eventos foi importada para este período."
            }
          />
          {report.unallocated_events?.length ? (
            <section className="space-y-2">
              <h3 className="v2-titulo-secao">Eventos sem vínculo com uma venda</h3>
              <p className="v2-texto-ajuda">
                Mantidos separados. Não foram rateados entre produtos ou pedidos.
              </p>
              <DataTable
                columns={eventColumns}
                data={report.unallocated_events}
                getRowKey={(event) => event.position}
              />
            </section>
          ) : null}
        </div>
      ) : !c.carregando ? (
        <EstadoVazio
          icone={AlertTriangle}
          titulo="Financeiro ainda não consultado"
          descricao="Confira o estado da integração e tente consultar o período novamente."
        />
      ) : null}
      {order ? (
        <VendaFinanceira
          order={order}
          c={{
            ...c,
            fecharDetalhe: () => {
              if (!c.ocupado) {
                c.fecharCustos();
                setDetalhe(null);
              }
            },
          }}
        />
      ) : null}
    </section>
  );
}
