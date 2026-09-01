import { FiBell, FiCopy, FiMessageCircle, FiSend, FiSmartphone, FiX } from "react-icons/fi";
import { formatarDataHora } from "./lembretesFormatters";

const CHANNEL_LABELS = { push: "Notificação no app", whatsapp: "WhatsApp" };
const STATUS_LABELS = {
  aberto: "Conversa aberta",
  enviado: "Enviado",
  falhou: "Falhou",
  ignorado: "Ignorado",
  pendente: "Na fila",
  registrado: "Registrado",
};

export default function LembreteContatoModal({ controller }) {
  const reminder = controller.contatoAberto;
  if (!reminder) return null;
  const busy = Boolean(controller.acaoContato);
  const emptyMessage = !controller.mensagemContato.trim();

  return (
    <div
      aria-labelledby="lembrete-contato-title"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/55 p-0 backdrop-blur-[1px] sm:items-center sm:p-4"
      role="dialog"
    >
      <div className="flex max-h-[94vh] w-full max-w-4xl flex-col overflow-hidden rounded-t-2xl bg-white shadow-2xl dark:bg-slate-900 sm:rounded-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4 dark:border-slate-700 sm:px-6">
          <div>
            <p className="m-0 text-xs font-bold uppercase tracking-[0.14em] text-teal-700 dark:text-teal-300">
              Mensagem sugerida
            </p>
            <h2
              className="mt-1 text-xl font-semibold text-slate-900 dark:text-slate-100"
              id="lembrete-contato-title"
            >
              {reminder.cliente_nome || "Cliente"} · {reminder.produto_nome}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Revise o texto antes de escolher o canal.
            </p>
          </div>
          <button
            aria-label="Fechar"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            disabled={busy}
            onClick={controller.fecharContato}
            type="button"
          >
            <FiX aria-hidden="true" />
          </button>
        </header>

        <div className="grid min-h-0 flex-1 overflow-y-auto lg:grid-cols-[minmax(0,1.25fr)_minmax(280px,0.75fr)]">
          <section className="p-5 sm:p-6">
            {reminder.contatado_hoje && (
              <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
                Já houve contato com este cliente hoje. Confira o histórico antes de insistir.
              </div>
            )}
            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200">
              Texto da mensagem
              <textarea
                className="mt-2 min-h-48 w-full resize-y rounded-xl border border-slate-200 bg-white p-3 text-sm leading-6 text-slate-800 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                maxLength={2000}
                onChange={(event) => controller.setMensagemContato(event.target.value)}
                value={controller.mensagemContato}
              />
            </label>
            <div className="mt-2 flex items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
              <span>O texto é apenas uma sugestão e pode ser editado.</span>
              <span>{controller.mensagemContato.length}/2000</span>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <button
                className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                disabled={emptyMessage || busy}
                onClick={controller.copiarMensagem}
                type="button"
              >
                <FiCopy aria-hidden="true" /> Copiar
              </button>
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-45"
                disabled={emptyMessage || busy || !reminder.cliente_telefone}
                onClick={controller.abrirWhatsApp}
                type="button"
              >
                <FiSend aria-hidden="true" />
                {controller.acaoContato === "whatsapp" ? "Abrindo..." : "Abrir WhatsApp"}
              </button>
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-45"
                disabled={emptyMessage || busy || !reminder.cliente_tem_app}
                onClick={() => controller.enviarPush(reminder, controller.mensagemContato)}
                type="button"
              >
                <FiBell aria-hidden="true" /> Enviar push
              </button>
            </div>
            {!reminder.cliente_tem_app && (
              <p className="mt-3 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                <FiSmartphone aria-hidden="true" /> Push indisponível: cliente sem conta vinculada
                no app.
              </p>
            )}
          </section>

          <aside className="border-t border-slate-200 bg-slate-50/70 p-5 dark:border-slate-700 dark:bg-slate-950/40 sm:p-6 lg:border-l lg:border-t-0">
            <div className="flex items-center justify-between gap-3">
              <h3 className="m-0 text-sm font-semibold text-slate-900 dark:text-slate-100">
                Histórico deste ciclo
              </h3>
              <span className="rounded-full bg-white px-2 py-0.5 text-xs font-bold text-slate-600 ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700">
                {controller.contatos.length}
              </span>
            </div>
            {controller.carregandoContatos ? (
              <p className="mt-5 text-sm text-slate-500">Carregando...</p>
            ) : controller.contatos.length === 0 ? (
              <div className="mt-5 rounded-xl border border-dashed border-slate-300 p-4 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                <FiMessageCircle className="mx-auto mb-2" aria-hidden="true" />
                Nenhum contato registrado ainda.
              </div>
            ) : (
              <ol className="mt-4 grid gap-3">
                {controller.contatos.map((contact) => (
                  <li
                    className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900"
                    key={contact.id}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                        {CHANNEL_LABELS[contact.canal] || contact.canal}
                      </span>
                      <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                        {STATUS_LABELS[contact.status] || contact.status}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {formatarDataHora(contact.criado_em)}
                      {contact.operador_nome ? ` · ${contact.operador_nome}` : " · Automático"}
                    </p>
                    {contact.resultado && (
                      <p className="mt-2 text-xs leading-5 text-slate-600 dark:text-slate-300">
                        {contact.resultado}
                      </p>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}
