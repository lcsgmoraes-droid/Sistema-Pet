import { History, RefreshCw, XCircle } from "lucide-react";
import Panel from "../../components/ui/Panel";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import { formatarDataContabilidade } from "./xmlContabilidadeUtils.mjs";

const STATUS = {
  pendente: ["Na fila", "bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-200"],
  agendado: ["Agendado", "bg-violet-50 text-violet-800 dark:bg-violet-950 dark:text-violet-200"],
  processando: ["Processando", "bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-200"],
  enviado: ["Enviado", "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"],
  falhou: ["Falhou", "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-200"],
  cancelado: ["Cancelado", "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"],
  sem_notas: [
    "Sem notas no período",
    "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  ],
};

const ORIGENS = {
  automatico: "Envio antigo",
  manual: "Manual",
  agendado: "Envio antigo",
  mensal: "Mensal — mês anterior completo",
};

export default function XmlContabilidadeHistorico({
  envios,
  atualizando,
  erro,
  onAtualizar,
  onAcao,
  operacao,
  bloqueioEnvio,
}) {
  return (
    <Panel
      title="3. Histórico de envios"
      subtitle="Datas no horário de Brasília. Uma nova tentativa usa o e-mail atual da configuração."
      actions={
        <BotaoInteracao
          icon={RefreshCw}
          onClick={onAtualizar}
          loading={atualizando}
          disabled={Boolean(operacao)}
          tamanho="pequeno"
        >
          Atualizar
        </BotaoInteracao>
      }
    >
      {erro ? (
        <p role="alert" className="mb-3 text-sm text-red-700 dark:text-red-300">
          {erro}
        </p>
      ) : null}
      {envios.length === 0 ? (
        <EstadoVazio
          icone={History}
          titulo="Nenhum envio registrado"
          descricao="Os envios manuais e os envios mensais automáticos aparecerão aqui."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
              <tr>
                <th scope="col" className="p-3">
                  Ações
                </th>
                <th scope="col" className="p-3">
                  Período e origem
                </th>
                <th scope="col" className="p-3">
                  Destinatário
                </th>
                <th scope="col" className="p-3">
                  Situação
                </th>
                <th scope="col" className="p-3">
                  Notas no lote
                </th>
                <th scope="col" className="p-3">
                  Data
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {envios.map((envio) => {
                const [rotulo, cor] = STATUS[envio.status] || [
                  envio.status,
                  "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
                ];
                const podeCancelar = ["pendente", "agendado"].includes(envio.status);
                return (
                  <tr key={envio.id} className="align-top text-slate-700 dark:text-slate-300">
                    <td className="p-3">
                      {envio.status === "falhou" ? (
                        <BotaoInteracao
                          icon={RefreshCw}
                          tamanho="pequeno"
                          onClick={() => onAcao(envio.id, "reenviar")}
                          loading={operacao === `reenviar-${envio.id}`}
                          disabled={Boolean(operacao) || Boolean(bloqueioEnvio)}
                          title={bloqueioEnvio || undefined}
                        >
                          Tentar novamente
                        </BotaoInteracao>
                      ) : podeCancelar ? (
                        <BotaoInteracao
                          icon={XCircle}
                          tamanho="pequeno"
                          onClick={() => onAcao(envio.id, "cancelar")}
                          loading={operacao === `cancelar-${envio.id}`}
                          disabled={Boolean(operacao)}
                        >
                          Cancelar
                        </BotaoInteracao>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap p-3">
                      <p>
                        {formatarDataContabilidade(envio.data_inicio)} a{" "}
                        {formatarDataContabilidade(envio.data_fim)}
                      </p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {ORIGENS[envio.origem] || envio.origem}
                      </p>
                    </td>
                    <td className="p-3">{envio.email_destino}</td>
                    <td className="min-w-48 p-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${cor}`}
                      >
                        {rotulo}
                      </span>
                      {envio.ultimo_erro ? (
                        <p className="mt-2 max-w-sm break-words text-xs text-red-700 dark:text-red-300">
                          {envio.ultimo_erro}
                        </p>
                      ) : null}
                    </td>
                    <td className="p-3">
                      {envio.quantidade_xml == null
                        ? "—"
                        : Number(envio.quantidade_xml).toLocaleString("pt-BR")}
                    </td>
                    <td className="whitespace-nowrap p-3">
                      {formatarDataContabilidade(
                        envio.enviado_em || envio.agendado_para || envio.created_at,
                        true,
                      )}
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {envio.enviado_em
                          ? "Enviado em"
                          : envio.agendado_para
                            ? "Programado para"
                            : "Criado em"}
                      </p>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
