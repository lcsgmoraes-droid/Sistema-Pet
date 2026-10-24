import { useState } from "react";
import { Eye, RefreshCw } from "lucide-react";
import DataTable from "../ui/DataTable";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import CartaoIndicador from "../v2/CartaoIndicador/CartaoIndicador";
import EstadoVazio from "../v2/EstadoVazio/EstadoVazio";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputPeriodo from "../v2/InputPeriodo/InputPeriodo";
import InputTexto from "../v2/InputTexto/InputTexto";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";
import { useEscapeToClose } from "../../utils/modalEscape";
import { moedaIfood } from "./ifoodPresentation";
import { competenciaFinanceira, dataFinanceira } from "./ifoodFinanceiroPresentation";
import useIfoodRepasses from "./useIfoodRepasses";

const ESTADOS = {
  matched: { label: "Conciliado no iFood", color: "text-emerald-800 dark:text-emerald-200" },
  different: { label: "Com diferença", color: "text-red-700 dark:text-red-300" },
  pending: { label: "Pendente", color: "text-amber-800 dark:text-amber-200" },
};
const BASIS = [
  { value: "calculation", label: "Período de cálculo" },
  { value: "payment", label: "Data prevista de pagamento" },
];
const JOBS = {
  created: "Solicitação criada",
  enqueue: "Arquivo em preparação",
  processed: "Arquivo processado",
  error: "Falha ao processar arquivo",
  conflict: "Solicitação com conflito · requer conferência",
};
const mes = (title) =>
  title.reference_months?.length
    ? title.reference_months.map(competenciaFinanceira).join(", ")
    : "Não informada";

function EstadoRepasse({ value }) {
  const estado = ESTADOS[value] || ESTADOS.pending;
  return <span className={`text-sm font-semibold ${estado.color}`}>{estado.label}</span>;
}

function DetalheRepasse({ title, onFechar }) {
  useEscapeToClose({ onClose: onFechar });
  return (
    <ModalPadrao
      titulo={`Conferir repasse · ${title.id}`}
      tamanho="ampla"
      onFechar={onFechar}
      rodape={<BotaoCancelar onClick={onFechar}>Fechar</BotaoCancelar>}
    >
      <div className="space-y-4">
        <p className="v2-texto font-semibold text-amber-800 dark:text-amber-200">
          Homologação iFood · recebimento no banco não conferido
        </p>
        <p>
          <EstadoRepasse value={title.reconciliation_status} />
        </p>
        <p className="v2-texto">
          Situação informada pelo iFood: {title.provider_status || "Não informada"}. Esse estado não
          comprova crédito na conta bancária nem que todo o valor pertence à loja.
        </p>
        <dl className="grid gap-3 sm:grid-cols-2">
          {[
            ["Tipo do título", title.title_type || "Não informado"],
            ["Parcela", "Não informada pelo iFood"],
            ["Competência dos arquivos", mes(title)],
            ["Data prevista de pagamento", dataFinanceira(title.payment_date)],
            [
              "Período de cálculo",
              title.calculation_period
                ? `${dataFinanceira(title.calculation_period.begin)} a ${dataFinanceira(title.calculation_period.end)}`
                : "Não informado",
            ],
            ["Valor do título", moedaIfood(title.amount)],
            ["Total do título declarado no arquivo", moedaIfood(title.statement_amount)],
            ["Soma das linhas do arquivo", moedaIfood(title.statement_lines_sum)],
            ["Eventos de toda a apuração (todos os títulos)", moedaIfood(title.events_period_sum)],
            ["Diferença título − linhas vinculadas", moedaIfood(title.difference)],
            ["Linhas do arquivo", title.statement_row_count ?? "Não informado"],
            ["Eventos considerados", title.event_count ?? "Não informado"],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="v2-rotulo">{label}</dt>
              <dd className="v2-texto">{value}</dd>
            </div>
          ))}
        </dl>
        <p className="v2-texto-ajuda">
          {title.link_method === "legacy_title"
            ? "Correspondência explícita do título encontrada no arquivo legado."
            : "A relação entre saldo e título ainda precisa ser comprovada."}{" "}
          O total dos eventos cobre toda a apuração e pode incluir outros títulos. A diferença
          compara o valor deste título com suas linhas vinculadas no arquivo. Os valores são
          fornecidos pelo servidor. Um saldo sem vínculo explícito permanece pendente.
        </p>
        {title.issues?.length ? (
          <div role="status" className="v2-texto text-amber-800 dark:text-amber-200">
            {title.issues.map((issue, index) => (
              <p key={index}>{issue}</p>
            ))}
          </div>
        ) : null}
      </div>
    </ModalPadrao>
  );
}

export default function IfoodRepasses({ ativo = false, status, periodoSugerido = null }) {
  const c = useIfoodRepasses({
    enabled: ativo,
    canSync: Boolean(status?.can_sync_payouts),
    periodoSugerido,
  });
  const [detalhe, setDetalhe] = useState(null);
  const report = c.relatorio;
  const title = report?.titles?.find((item) => item.id === detalhe);
  const ocupado = c.sincronizando || c.consultandoJob;
  return (
    <section
      aria-label="Repasses do iFood"
      className="space-y-4 rounded-xl border border-slate-200 p-4 dark:border-slate-700"
    >
      <div className="space-y-1">
        <h2 className="v2-titulo-secao">Repasses do iFood</h2>
        <p className="v2-texto-ajuda">
          Confira os eventos e os títulos de repasse informados pelo iFood. O recebimento no banco
          continua não conferido nesta etapa.
        </p>
      </div>
      <div className="grid items-end gap-3 lg:grid-cols-2">
        <InputPeriodo
          id="ifood-repasses-periodo"
          label="Período dos repasses"
          value={c.periodo}
          onChange={c.alterarPeriodo}
          disabled={ocupado}
          error={c.periodoValido ? "" : "Escolha um período válido de 1 a 90 dias."}
        />
        <InputCombobox
          id="ifood-repasses-base"
          label="Datas usadas na consulta"
          value={c.basis}
          opcoes={BASIS}
          permitirLimpar={false}
          disabled={ocupado}
          onChange={c.alterarBasis}
        />
      </div>
      <div className="flex flex-wrap gap-3">
        <BotaoInteracao
          icon={RefreshCw}
          onClick={c.atualizar}
          disabled={!c.periodoValido || ocupado || c.seguindo}
          loading={c.carregando}
        >
          Atualizar repasses locais
        </BotaoInteracao>
        <BotaoInteracao
          icon={RefreshCw}
          onClick={c.sincronizar}
          disabled={!status?.can_sync_payouts || !c.periodoValido || ocupado || c.carregando}
          loading={c.sincronizando}
        >
          Consultar repasses no iFood
        </BotaoInteracao>
      </div>
      {!status?.can_sync_payouts ? (
        <p className="v2-texto-ajuda">
          Consulta externa de repasses indisponível. Os dados já importados continuam disponíveis.
        </p>
      ) : null}
      {c.erro ? (
        <p role="alert" className="v2-texto text-red-700 dark:text-red-300">
          {c.erro}
        </p>
      ) : null}
      {c.carregando ? (
        <p role="status" className="v2-texto-ajuda">
          Atualizando repasses; os últimos dados foram mantidos.
        </p>
      ) : null}
      {report ? (
        <div className="space-y-3">
          <p className="v2-texto-ajuda">
            Fonte:{" "}
            {report.metadata?.source === "synthetic"
              ? "Dados sintéticos de DEV"
              : report.imported
                ? "iFood Financial · homologação"
                : "Ainda não importado"}
            {" · "}Período exibido: {dataFinanceira(report.begin_date)} a{" "}
            {dataFinanceira(report.end_date)}
            {" · "}Base:{" "}
            {BASIS.find((item) => item.value === report.basis)?.label || "Não informada"}
            {" · "}Atualizado em: {dataFinanceira(report.metadata?.retrieved_at)} · Revisão{" "}
            {report.metadata?.revision ?? "não informada"}
          </p>
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ["matched_titles", "Conciliados no iFood"],
              ["divergent_titles", "Com diferença"],
              ["pending_titles", "Pendentes"],
            ].map(([key, label]) => (
              <CartaoIndicador key={key} titulo={label} icone={RefreshCw}>
                <p className="text-lg font-semibold">{report.summary?.[key] ?? "Não informado"}</p>
              </CartaoIndicador>
            ))}
          </div>
          <DataTable
            data={report.titles || []}
            getRowKey={(item) => item.id}
            emptyMessage="Nenhum título importado para este período."
            columns={[
              {
                key: "id",
                header: "Título",
                render: (item) => <span className="break-all">{item.id}</span>,
              },
              { key: "reference_months", header: "Competência", render: mes },
              {
                key: "payment_date",
                header: "Data prevista",
                render: (item) => dataFinanceira(item.payment_date),
              },
              {
                key: "amount",
                header: "Valor do título",
                render: (item) => moedaIfood(item.amount),
              },
              {
                key: "difference",
                header: "Diferença",
                render: (item) => moedaIfood(item.difference),
              },
              {
                key: "reconciliation_status",
                header: "Conciliação iFood",
                render: (item) => <EstadoRepasse value={item.reconciliation_status} />,
              },
              {
                key: "acoes",
                header: "Ações",
                render: (item) => (
                  <BotaoInteracao icon={Eye} tamanho="pequeno" onClick={() => setDetalhe(item.id)}>
                    Conferir repasse
                  </BotaoInteracao>
                ),
              },
            ]}
          />
          {report.unmatched_balances?.length ? (
            <div role="status" className="space-y-1 v2-texto text-amber-800 dark:text-amber-200">
              <h3 className="v2-titulo-secao">Saldos sem vínculo comprovado com título</h3>
              {report.unmatched_balances.map((item) => (
                <p key={item.balance_id}>
                  {item.balance_id} · {moedaIfood(item.amount)} · {item.issues?.join(" · ")}
                </p>
              ))}
            </div>
          ) : null}
          {report.warnings?.length ? (
            <div role="status" className="v2-texto text-amber-800 dark:text-amber-200">
              {report.warnings.map((warning, index) => (
                <p key={index}>{warning}</p>
              ))}
            </div>
          ) : null}
        </div>
      ) : !c.carregando ? (
        <EstadoVazio
          icone={RefreshCw}
          titulo="Repasses ainda não consultados"
          descricao="Atualize a consulta local para conferir os dados já importados."
        />
      ) : null}
      <div className="space-y-3 border-t border-slate-200 pt-4 dark:border-slate-700">
        <h3 className="v2-titulo-secao">Arquivo de conciliação mensal</h3>
        <p className="v2-texto-ajuda">
          A competência do arquivo é independente do período dos títulos. A preparação pode levar
          alguns instantes; o acompanhamento faz até 8 consultas e respeita a espera informada pelo
          iFood.
        </p>
        <InputTexto
          id="ifood-conciliacao-competencia"
          label="Competência da conciliação (AAAA-MM)"
          value={c.competence}
          placeholder="2025-08"
          maxLength={7}
          disabled={c.consultandoJob || c.seguindo}
          onChange={c.alterarCompetence}
          error={c.mesValido ? "" : "Informe ano e mês válidos no formato AAAA-MM."}
        />
        <div className="flex flex-wrap gap-3">
          <BotaoInteracao
            icon={RefreshCw}
            onClick={c.iniciarConciliacao}
            loading={c.consultandoJob}
            disabled={
              !status?.can_sync_payouts ||
              !c.mesValido ||
              c.consultandoJob ||
              c.aguardandoRetry ||
              c.seguindo
            }
          >
            Consultar arquivo de conciliação
          </BotaoInteracao>
          {c.seguindo ? (
            <BotaoCancelar onClick={c.pausar}>Pausar acompanhamento</BotaoCancelar>
          ) : null}
        </div>
        <p role="status" className="v2-texto-ajuda">
          {c.job
            ? `${JOBS[c.job.status] || "Estado pendente"} · Competência ${competenciaFinanceira(c.job.competence)} · Última consulta ${dataFinanceira(c.job.last_checked_at)}`
            : "Nenhuma solicitação local para esta competência."}
        </p>
        {c.job?.status === "error" ? (
          <p role="alert" className="v2-texto text-red-700 dark:text-red-300">
            O arquivo não foi processado. Confira a solicitação antes de tentar novamente.
          </p>
        ) : null}
        {c.job?.status === "conflict" ? (
          <p role="status" className="v2-texto text-amber-800 dark:text-amber-200">
            O iFood não confirmou o identificador da solicitação existente. O acompanhamento
            automático foi pausado; confira a solicitação antes de tentar novamente.
          </p>
        ) : null}
        {c.job?.last_error ? (
          <p role="status" className="v2-texto text-amber-800 dark:text-amber-200">
            {c.job.last_error}
          </p>
        ) : null}
        {c.aguardandoRetry ? (
          <p className="v2-texto-ajuda">
            Aguardando o intervalo da próxima consulta; a solicitação foi preservada.
          </p>
        ) : null}
        {c.seguindo ? (
          <p className="v2-texto-ajuda">
            Acompanhando a solicitação · {c.tentativas} de 8 consultas.
          </p>
        ) : null}
        {c.limiteAtingido ? (
          <p role="status" className="v2-texto-ajuda">
            Acompanhamento automático pausado após 8 consultas. A solicitação foi preservada;
            consulte novamente mais tarde.
          </p>
        ) : null}
        {c.erroJob ? (
          <p role="alert" className="v2-texto text-red-700 dark:text-red-300">
            {c.erroJob}
          </p>
        ) : null}
      </div>
      {title ? <DetalheRepasse title={title} onFechar={() => setDetalhe(null)} /> : null}
    </section>
  );
}
