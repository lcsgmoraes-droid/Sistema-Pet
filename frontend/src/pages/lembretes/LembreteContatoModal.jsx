import { Bell, Copy, MessageCircle, Send, Smartphone } from "lucide-react";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import Etiqueta from "../../components/v2/Etiqueta/Etiqueta";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import FaixaAviso from "../../components/v2/FaixaAviso/FaixaAviso";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
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
    <ModalPadrao
      onFechar={controller.fecharContato}
      rodape={<BotaoCancelar onClick={controller.fecharContato}>Fechar</BotaoCancelar>}
      tamanho="grande"
      titulo={`${reminder.cliente_nome || "Cliente"} · ${
        reminder.contexto_nome || reminder.produto_nome || "Contato"
      }`}
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(240px,0.75fr)]">
        <section className="grid content-start gap-4">
          <p className="v2-texto-ajuda">Revise o texto antes de escolher o canal.</p>
          {reminder.contatado_hoje && (
            <FaixaAviso icone={MessageCircle} tom="atencao">
              Já houve contato com este cliente hoje. Confira o histórico antes de insistir.
            </FaixaAviso>
          )}
          <InputTextoLongo
            help={`O texto é apenas uma sugestão e pode ser editado. ${controller.mensagemContato.length}/2000`}
            id="lembrete-contato-mensagem"
            label="Texto da mensagem"
            linhas={8}
            maxLength={2000}
            onChange={controller.setMensagemContato}
            value={controller.mensagemContato}
          />
          <div className="flex flex-wrap gap-2">
            <BotaoInteracao
              disabled={emptyMessage || busy}
              icon={Copy}
              onClick={controller.copiarMensagem}
            >
              Copiar
            </BotaoInteracao>
            <BotaoInteracao
              disabled={emptyMessage || busy || !reminder.cliente_telefone}
              icon={Send}
              onClick={controller.abrirWhatsApp}
            >
              {controller.acaoContato === "whatsapp" ? "Abrindo..." : "Abrir WhatsApp"}
            </BotaoInteracao>
            <BotaoInteracao
              disabled={emptyMessage || busy || !reminder.cliente_tem_app}
              icon={Bell}
              onClick={() => controller.enviarPush(reminder, controller.mensagemContato)}
            >
              Enviar push
            </BotaoInteracao>
          </div>
          {!reminder.cliente_tem_app && (
            <p className="v2-texto-ajuda flex items-center gap-2">
              <Smartphone className="h-3.5 w-3.5" aria-hidden="true" /> Push indisponível: cliente
              sem conta vinculada no app.
            </p>
          )}
        </section>

        <aside className="grid content-start gap-3">
          <div className="flex items-center justify-between gap-3">
            <h4 className="m-0 text-sm font-semibold text-slate-900 dark:text-slate-100">
              {reminder.historico_titulo || "Histórico deste ciclo"}
            </h4>
            <Etiqueta>{controller.contatos.length}</Etiqueta>
          </div>
          {controller.carregandoContatos ? (
            <EstadoVazio icone={MessageCircle} titulo="Carregando..." />
          ) : controller.contatos.length === 0 ? (
            <EstadoVazio icone={MessageCircle} titulo="Nenhum contato registrado ainda." />
          ) : (
            <ol className="m-0 grid list-none gap-3 p-0">
              {controller.contatos.map((contact) => (
                <li
                  className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900"
                  key={contact.id}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                      {CHANNEL_LABELS[contact.canal] || contact.canal}
                    </span>
                    <Etiqueta tom={contact.status === "falhou" ? "perigo" : "neutro"}>
                      {STATUS_LABELS[contact.status] || contact.status}
                    </Etiqueta>
                  </div>
                  <p className="v2-texto-ajuda mt-1">
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
    </ModalPadrao>
  );
}
