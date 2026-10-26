import { Search } from "lucide-react";
import DataTable from "../ui/DataTable";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import InputCheck from "../v2/InputCheck/InputCheck";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputTexto from "../v2/InputTexto/InputTexto";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";
import { moedaIfood } from "./ifoodPresentation";
import { dataFinanceira } from "./ifoodFinanceiroPresentation";

export default function IfoodCustosHistoricos({ order, vinculo }) {
  const historico = order.historical_cost;
  const venda = vinculo.sales.find((sale) => String(sale.venda_id) === String(vinculo.vendaId));
  const origem =
    order.effective_cmv_source === "manual"
      ? "CMV informado manualmente"
      : order.effective_cmv_source === "erp_original_stock_out"
        ? "CMV histórico automático do ERP"
        : "CMV pendente de comprovação";
  return (
    <section className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
      <h3 className="v2-titulo-secao">Origem do CMV desta venda</h3>
      <p className="v2-texto font-medium">
        {origem} · {moedaIfood(order.effective_cmv)}
      </p>
      <p className="v2-texto-ajuda">
        Pedidos recebidos pelo CorePet são vinculados automaticamente à venda criada no PDV. Para
        pedidos históricos, confira o vínculo com a venda do ERP. O CMV é consultado nas saídas
        originais do estoque. Custo atual do produto não substitui o histórico. Um CMV manual
        informado, inclusive zero, tem prioridade; sem ele, o histórico comprovado pode ser usado.
      </p>
      {historico?.sale ? (
        <p className="v2-texto">
          Venda ERP {historico.sale.number ?? historico.sale.id} ·{" "}
          {dataFinanceira(historico.sale.date)}
          {" · "}
          {historico.sale.status} ·{" "}
          {historico.status === "verified" ? "Histórico comprovado" : "Histórico pendente"}
          {" · "}CMV histórico: {moedaIfood(historico.cmv)}
        </p>
      ) : (
        <p className="v2-texto-ajuda">Nenhuma venda ERP vinculada e comprovada.</p>
      )}
      {historico?.link ? (
        <p className="v2-texto-ajuda">
          {historico.link.source === "pdv_bridge"
            ? "Vínculo automático pela entrada do pedido no PDV"
            : historico.link.source === "explicit_confirmation"
              ? "Vínculo conferido manualmente"
              : "Vínculo registrado"}
          {" em "}
          {dataFinanceira(historico.link.linked_at)} · {historico.link.source_note}
        </p>
      ) : null}
      {historico?.missing?.length ? (
        <p role="status" className="v2-texto text-amber-800 dark:text-amber-200">
          {historico.missing.join(" · ")}
        </p>
      ) : null}
      {historico?.items?.length ? (
        <DataTable
          data={historico.items}
          getRowKey={(item) => item.sale_item_id}
          columns={[
            { key: "product_id", header: "Produto ERP", render: (item) => `#${item.product_id}` },
            {
              key: "quantity",
              header: "Quantidade histórica",
              render: (item) =>
                item.quantity !== null &&
                item.quantity !== undefined &&
                Number.isFinite(Number(item.quantity))
                  ? new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(
                      Number(item.quantity),
                    )
                  : "Não informada",
            },
            { key: "cost", header: "CMV total do item", render: (item) => moedaIfood(item.cost) },
            {
              key: "proof_captured_at",
              header: "Prova registrada em",
              render: (item) => dataFinanceira(item.proof_captured_at),
            },
            {
              key: "missing",
              header: "Comprovação",
              render: (item) =>
                item.missing?.length
                  ? item.missing.join(" · ")
                  : item.status === "verified"
                    ? "Comprovado"
                    : "Pendente",
            },
          ]}
        />
      ) : null}
      {vinculo.podeEditar ? (
        <div className="space-y-3">
          <h4 className="v2-rotulo">Confirmar vínculo com venda ERP</h4>
          <p className="v2-texto-ajuda">
            Busque pelo número ou ID da venda e confira os itens antes de confirmar.
          </p>
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-52 flex-1">
              <InputTexto
                id="ifood-vinculo-busca"
                label="Número ou ID da venda ERP"
                value={vinculo.busca}
                disabled={vinculo.ocupado}
                onChange={(value) => vinculo.alterar("busca", value)}
              />
            </div>
            <BotaoInteracao
              icon={Search}
              disabled={vinculo.ocupado || !vinculo.busca.trim()}
              loading={vinculo.ocupado}
              onClick={vinculo.buscar}
            >
              Buscar venda ERP
            </BotaoInteracao>
          </div>
          <InputCombobox
            id="ifood-vinculo-venda"
            label="Venda encontrada"
            value={vinculo.vendaId}
            disabled={vinculo.ocupado}
            onChange={(value) => vinculo.alterar("vendaId", value)}
            opcoes={vinculo.sales.map((sale) => ({
              value: sale.venda_id,
              label: `Venda ${sale.numero ?? sale.venda_id} · ${dataFinanceira(sale.data)} · ${sale.status}${sale.linkable ? "" : " · Com pendências"}`,
            }))}
            help="Nenhuma venda é selecionada automaticamente. A venda precisa estar finalizada no canal iFood e ter custos históricos comprovados."
          />
          {venda?.missing?.length ? (
            <p role="status" className="v2-texto text-amber-800 dark:text-amber-200">
              {venda.missing.join(" · ")}
            </p>
          ) : null}
          <InputTextoLongo
            id="ifood-vinculo-fonte"
            label="Fonte e justificativa do vínculo"
            value={vinculo.sourceNote}
            disabled={vinculo.ocupado}
            maxLength={1000}
            onChange={(value) => vinculo.alterar("sourceNote", value)}
            help="Registre como conferiu que o pedido iFood corresponde a esta venda do ERP."
          />
          <InputCheck
            id="ifood-vinculo-confirmado"
            label="Conferi que o pedido e a venda ERP correspondem à mesma venda"
            checked={vinculo.confirmado}
            disabled={vinculo.ocupado || !venda?.linkable}
            onChange={(value) => vinculo.alterar("confirmado", value)}
          />
          <BotaoInteracao
            disabled={vinculo.ocupado || !venda?.linkable || !vinculo.confirmado}
            loading={vinculo.ocupado}
            onClick={vinculo.confirmar}
          >
            Confirmar vínculo com venda ERP
          </BotaoInteracao>
        </div>
      ) : null}
      {vinculo.erro ? (
        <p role="alert" className="v2-texto text-red-700 dark:text-red-300">
          {vinculo.erro}
        </p>
      ) : null}
      {vinculo.sucesso ? (
        <p role="status" className="v2-texto">
          {vinculo.sucesso}
        </p>
      ) : null}
    </section>
  );
}
