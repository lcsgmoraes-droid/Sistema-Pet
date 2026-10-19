import {
  CalendarClock,
  History,
  MessageCircle,
  RefreshCw,
  Search,
  Users,
  Wallet,
} from "lucide-react";
import DataTable from "../../ui/DataTable";
import CustomerIdentity from "../../ui/CustomerIdentity";
import BotaoInteracao from "../../v2/BotaoInteracao/BotaoInteracao";
import CartaoIndicador from "../../v2/CartaoIndicador/CartaoIndicador";
import InputCombobox from "../../v2/InputCombobox/InputCombobox";
import InputTexto from "../../v2/InputTexto/InputTexto";
import InputTextoLongo from "../../v2/InputTextoLongo/InputTextoLongo";
import { formatMoneyBRL } from "../../../utils/formatters";
import CashbackCrmContatoModal from "./CashbackCrmContatoModal";
import CashbackCrmPaginacao from "./CashbackCrmPaginacao";
import { CASHBACK_STATUS, dataCashback, rotuloStatus } from "./cashbackCrmUtils";
import useCashbackCrm from "./useCashbackCrm";

export default function CashbackCrmTab() {
  const c = useCashbackCrm();
  const columns = [
    {
      key: "acoes",
      header: "Ações",
      render: (cliente) => (
        <div className="flex gap-2">
          <BotaoInteracao
            icon={MessageCircle}
            tamanho="pequeno"
            onClick={() => c.abrirCliente(cliente)}
            disabled={!c.podeEditar || !cliente.whatsapp_disponivel}
            title={
              !c.podeEditar
                ? "É necessária permissão para editar clientes"
                : cliente.motivo_bloqueio || "Revisar mensagem e abrir conversa"
            }
          >
            WhatsApp
          </BotaoInteracao>
          <BotaoInteracao icon={History} tamanho="pequeno" onClick={() => c.abrirCliente(cliente)}>
            Histórico
          </BotaoInteracao>
        </div>
      ),
    },
    {
      key: "cliente",
      header: "Cliente",
      render: (cliente) => (
        <div>
          <CustomerIdentity
            name={cliente.nome}
            code={cliente.codigo}
            nameClassName="font-medium text-slate-900 dark:text-slate-100"
          />
          {cliente.ativo === false && (
            <span className="mt-1 block text-xs font-semibold text-amber-700 dark:text-amber-300">
              Cadastro inativo
            </span>
          )}
        </div>
      ),
    },
    {
      key: "telefone",
      header: "Telefone",
      render: (cliente) => (
        <span className="whitespace-nowrap">
          {cliente.telefone || "Sem telefone"}
          {cliente.motivo_bloqueio && (
            <span className="mt-1 block max-w-48 whitespace-normal text-xs text-amber-700 dark:text-amber-300">
              {cliente.motivo_bloqueio}
            </span>
          )}
        </span>
      ),
    },
    {
      key: "saldo",
      header: "Saldo disponível",
      align: "right",
      render: (cliente) => (
        <span className="whitespace-nowrap font-semibold text-emerald-700 dark:text-emerald-300">
          {formatMoneyBRL(cliente.saldo_cashback)}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (cliente) => (
        <span className="inline-flex rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
          {rotuloStatus(cliente.status)}
        </span>
      ),
    },
    {
      key: "ultimo_contato",
      header: "Última conversa",
      render: (cliente) => (
        <span className="whitespace-nowrap">
          {dataCashback(cliente.ultimo_contato, true)}
          <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">
            {cliente.total_contatos || 0} registro(s)
          </span>
        </span>
      ),
    },
    {
      key: "retorno",
      header: "Próximo retorno",
      render: (cliente) => (
        <span className="whitespace-nowrap">{dataCashback(cliente.proximo_contato_em)}</span>
      ),
    },
    {
      key: "expiracao",
      header: "Próximo vencimento",
      render: (cliente) => (
        <span className="whitespace-nowrap">
          {dataCashback(cliente.proxima_expiracao)}
          {cliente.proxima_expiracao && (
            <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">
              {formatMoneyBRL(cliente.valor_a_expirar)}
            </span>
          )}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="v2-titulo-secao">Cashback e contatos</h2>
          <p className="v2-subtitulo mt-1">
            Clientes com saldo disponível para usar. Prepare uma conversa e acompanhe cada retorno.
          </p>
        </div>
        <BotaoInteracao icon={RefreshCw} onClick={c.recarregar} loading={c.loading}>
          Atualizar
        </BotaoInteracao>
      </header>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <InputTextoLongo
          id="cashback-modelo"
          label="Modelo de mensagem"
          value={c.modelo}
          onChange={c.setModelo}
          linhas={3}
          maxLength={2000}
          help="Use {nome} e {saldo} para personalizar. O modelo vale nesta sessão; cada mensagem também pode ser editada antes da conversa."
        />
      </div>

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900 md:grid-cols-3">
        <InputTexto
          id="cashback-busca"
          label="Buscar cliente"
          placeholder="Nome, código ou telefone"
          maxLength={120}
          value={c.busca}
          onChange={c.setBusca}
          left={<Search className="h-4 w-4 text-slate-400" />}
        />
        <InputCombobox
          id="cashback-filtro-status"
          label="Status do relacionamento"
          value={c.status}
          onChange={c.mudarStatus}
          opcoes={[{ value: "", label: "Todos os status" }, ...CASHBACK_STATUS]}
          placeholder="Todos os status"
        />
        <InputCombobox
          id="cashback-filtro-retorno"
          label="Retornos"
          value={c.retorno}
          onChange={c.mudarRetorno}
          permitirLimpar={false}
          opcoes={[
            { value: "todos", label: "Todos" },
            { value: "pendentes", label: "Até hoje (pendentes)" },
          ]}
        />
      </div>

      {c.loading ? (
        <p role="status" className="py-12 text-center text-sm text-slate-500 dark:text-slate-400">
          Carregando clientes com cashback...
        </p>
      ) : c.erro ? (
        <p
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300"
        >
          {c.erro}
        </p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <CartaoIndicador
              titulo="Clientes com saldo"
              icone={Users}
              detalhe="Total geral, antes dos filtros"
            >
              <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
                {c.resumo.total_clientes}
              </p>
            </CartaoIndicador>
            <CartaoIndicador
              titulo="Cashback disponível"
              icone={Wallet}
              tom="sucesso"
              detalhe="Saldo geral, antes dos filtros"
            >
              <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
                {formatMoneyBRL(c.resumo.saldo_total)}
              </p>
            </CartaoIndicador>
            <CartaoIndicador
              titulo="Ainda sem contato"
              icone={MessageCircle}
              detalhe="Status inicial do relacionamento"
            >
              <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
                {c.resumo.sem_contato}
              </p>
            </CartaoIndicador>
            <CartaoIndicador
              titulo="Retornos pendentes"
              icone={CalendarClock}
              tom="atencao"
              detalhe="Agendados para hoje ou dias anteriores"
            >
              <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
                {c.resumo.retornos_pendentes}
              </p>
            </CartaoIndicador>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <DataTable
              columns={columns}
              data={c.clientes}
              getRowKey={(cliente) => cliente.cliente_id}
              emptyMessage="Nenhum cliente com saldo disponível para estes filtros."
            />
            <CashbackCrmPaginacao
              pagina={c.pagina}
              paginacao={c.paginacao}
              onChange={c.setPagina}
            />
          </div>
          <p className="v2-texto-ajuda">
            O saldo considera os créditos disponíveis. Valores vencidos e usados não entram nesta
            lista.
          </p>
        </>
      )}
      <CashbackCrmContatoModal controller={c} />
    </div>
  );
}
