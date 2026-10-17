import { Bell, CheckCircle2, MessageCircle, RefreshCw, Trash2 } from "lucide-react";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoMenuAcoes from "../../components/v2/BotaoMenuAcoes/BotaoMenuAcoes";
import Etiqueta from "../../components/v2/Etiqueta/Etiqueta";
import { formatarDataHora, formatarMoeda } from "./lembretesFormatters";
import { TIPOS_LEMBRETE } from "./lembretesUtils";

const PUSH_INDISPONIVEL =
  "Push indisponível: será habilitado quando o cliente tiver uma conta vinculada no app.";

export default function LembreteCard({ controller, lembrete }) {
  const days = lembrete.dias_restantes;
  const dueDate = new Date(lembrete.data_proxima_dose).toLocaleDateString("pt-BR");
  const lastContact = lembrete.ultimo_contato;
  const pushLoading = controller.acaoContato === `push-${lembrete.id}`;
  const pushUnavailable = !lembrete.cliente_tem_app;

  const acoes = [
    {
      icon: Bell,
      label: pushLoading ? "Enviando push..." : "Enviar push no app",
      disabled: pushUnavailable || pushLoading,
      title: pushUnavailable ? PUSH_INDISPONIVEL : "Enviar notificação no app",
      onClick: () => controller.enviarPush(lembrete),
    },
    {
      icon: CheckCircle2,
      label: "Registrar recompra",
      onClick: () => controller.completarLembrete(lembrete.id),
    },
    {
      icon: RefreshCw,
      label: "Criar próximo ciclo",
      onClick: () => controller.renovarLembrete(lembrete.id),
    },
    {
      icon: Trash2,
      label: "Cancelar lembrete",
      tom: "perigo",
      onClick: () => controller.cancelarLembrete(lembrete.id),
    },
  ];

  return (
    <article className="grid gap-4 p-4 transition hover:bg-slate-50/70 dark:hover:bg-slate-800/30 sm:p-5 xl:grid-cols-[160px_minmax(0,1fr)_auto] xl:items-center">
      <div>
        <Etiqueta tom={deadlineTom(days)}>{deadlineLabel(days)}</Etiqueta>
        <p className="mt-2 text-sm font-semibold text-slate-800 dark:text-slate-200">{dueDate}</p>
        <p className="v2-texto-ajuda mt-0.5">Previsão de retorno</p>
      </div>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="m-0 truncate text-base font-semibold text-slate-900 dark:text-slate-100">
            {lembrete.cliente_nome || "Cliente não informado"}
          </h3>
          {lembrete.pet_nome && (
            <span className="text-sm text-slate-500 dark:text-slate-400">
              • {lembrete.pet_nome}
            </span>
          )}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <p className="m-0 text-sm font-medium text-slate-700 dark:text-slate-300">
            {lembrete.produto_nome}
          </p>
          <Etiqueta>{TIPOS_LEMBRETE[lembrete.tipo_lembrete] || "Recorrência"}</Etiqueta>
          {lembrete.dose_total > 1 && (
            <Etiqueta tom="informativo">
              Dose {lembrete.dose_atual}/{lembrete.dose_total}
            </Etiqueta>
          )}
        </div>
        <div className="v2-texto-ajuda mt-2 flex flex-wrap gap-x-4 gap-y-1">
          {lembrete.intervalo_estimado_dias && (
            <span>Ciclo de {lembrete.intervalo_estimado_dias} dias</span>
          )}
          {lembrete.preco_estimado > 0 && (
            <span>Valor previsto {formatarMoeda(lembrete.preco_estimado)}</span>
          )}
          <span
            className={
              lembrete.contatado_hoje ? "font-semibold text-amber-700 dark:text-amber-300" : ""
            }
          >
            <MessageCircle aria-hidden="true" className="mr-1 inline h-3 w-3" />
            {lembrete.contatos_total || 0} contato(s) neste ciclo
            {lastContact?.criado_em
              ? ` · último em ${formatarDataHora(lastContact.criado_em)}`
              : ""}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 xl:justify-end">
        <BotaoInteracao icon={MessageCircle} onClick={() => controller.abrirContato(lembrete)}>
          Criar mensagem
        </BotaoInteracao>
        <BotaoMenuAcoes
          acoes={acoes}
          rotulo={`Mais ações para ${lembrete.cliente_nome || "o lembrete"}`}
        />
      </div>
    </article>
  );
}

function deadlineLabel(days) {
  if (days < 0) return `${Math.abs(days)} dia(s) atrasado`;
  if (days === 0) return "Retorno hoje";
  return `Faltam ${days} dia(s)`;
}

function deadlineTom(days) {
  if (days < 0) return "perigo";
  if (days <= 7) return "atencao";
  return "neutro";
}
