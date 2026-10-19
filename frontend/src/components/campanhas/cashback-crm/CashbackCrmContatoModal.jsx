import { History, MessageCircle, RefreshCw } from "lucide-react";
import BotaoCancelar from "../../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../../v2/BotaoSalva/BotaoSalva";
import InputCombobox from "../../v2/InputCombobox/InputCombobox";
import InputData from "../../v2/InputData/InputData";
import InputTextoLongo from "../../v2/InputTextoLongo/InputTextoLongo";
import ModalPadrao from "../../v2/ModalPadrao/ModalPadrao";
import EstadoVazio from "../../v2/EstadoVazio/EstadoVazio";
import { formatMoneyBRL } from "../../../utils/formatters";
import CashbackCrmPaginacao from "./CashbackCrmPaginacao";
import { CASHBACK_STATUS, dataCashback, mensagemCashback, rotuloStatus } from "./cashbackCrmUtils";

export default function CashbackCrmContatoModal({ controller }) {
  const c = controller;
  const cliente = c.selecionado;
  if (!cliente) return null;
  const ocupado = Boolean(c.ocupado);
  const bloqueado =
    !c.podeEditar || !cliente.whatsapp_disponivel || cliente.status === "nao_contatar";
  const atualizarCampo = (campo, valor) => c.setForm((atual) => ({ ...atual, [campo]: valor }));
  const semAgenda = ["sem_contato", "concluido", "sem_interesse", "nao_contatar"].includes(
    c.form.status,
  );

  return (
    <ModalPadrao
      titulo={`${cliente.nome} · Cashback e contatos`}
      tamanho="grande"
      onFechar={c.fecharCliente}
      rodape={
        <BotaoCancelar disabled={ocupado} onClick={c.fecharCliente}>
          Fechar
        </BotaoCancelar>
      }
    >
      {!c.historicoInicializado && c.carregandoHistorico ? (
        <p className="py-12 text-center text-sm text-slate-500 dark:text-slate-400" role="status">
          Carregando acompanhamento e histórico...
        </p>
      ) : !c.historicoInicializado && c.erroHistorico ? (
        <div className="space-y-3" role="alert">
          <p className="text-sm text-red-700 dark:text-red-300">{c.erroHistorico}</p>
          <BotaoInteracao icon={RefreshCw} onClick={c.recarregar}>
            Tentar novamente
          </BotaoInteracao>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-950/50">
            <p className="font-semibold text-slate-900 dark:text-slate-100">
              Saldo disponível: {formatMoneyBRL(cliente.saldo_cashback)}
            </p>
            <p className="mt-1 text-slate-500 dark:text-slate-400">
              {cliente.telefone || "Sem telefone cadastrado"} · {rotuloStatus(cliente.status)}
            </p>
          </div>

          <section className="space-y-3">
            <h3 className="v2-titulo-secao">Preparar conversa no WhatsApp</h3>
            <InputTextoLongo
              id="cashback-mensagem"
              label="Mensagem para este cliente"
              value={c.mensagem}
              onChange={c.setMensagem}
              linhas={6}
              maxLength={2000}
              error={c.mensagem.length > 2000 ? "Reduza a mensagem para até 2000 caracteres." : ""}
              disabled={ocupado || !c.podeEditar}
              help={`${c.mensagem.length}/2000 caracteres. Revise livremente antes de abrir a conversa.`}
            />
            <div className="flex flex-wrap gap-2">
              <BotaoInteracao
                icon={MessageCircle}
                onClick={c.abrirWhatsApp}
                loading={c.ocupado === "whatsapp"}
                disabled={ocupado || bloqueado || !c.mensagem.trim() || c.mensagem.length > 2000}
                title={
                  bloqueado
                    ? cliente.motivo_bloqueio || "Contato não permitido para este cliente"
                    : undefined
                }
              >
                Abrir WhatsApp e registrar
              </BotaoInteracao>
              <BotaoInteracao
                icon={RefreshCw}
                disabled={ocupado || !c.podeEditar}
                onClick={() => c.setMensagem(mensagemCashback(c.modelo, cliente))}
              >
                Restaurar sugestão
              </BotaoInteracao>
            </div>
            {bloqueado && (
              <p className="text-xs text-amber-800 dark:text-amber-300">
                {!c.podeEditar
                  ? "Seu acesso permite consultar o histórico. Para registrar contatos, é necessária permissão para editar clientes."
                  : cliente.motivo_bloqueio ||
                    "Este cliente está marcado para não receber contatos."}
              </p>
            )}
            <p className="v2-texto-ajuda">
              A abertura fica no histórico. Você confirma o envio no WhatsApp e pode marcar
              “Mensagem enviada” abaixo depois de enviar.
            </p>
          </section>

          {c.podeEditar && (
            <section className="space-y-3 border-t border-slate-200 pt-5 dark:border-slate-700">
              <h3 className="v2-titulo-secao">Acompanhar relacionamento</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                <InputCombobox
                  id="cashback-contato-status"
                  label="Status"
                  value={c.form.status}
                  onChange={(valor) =>
                    c.setForm((atual) => ({
                      ...atual,
                      status: valor,
                      proximo_contato_em: [
                        "sem_contato",
                        "concluido",
                        "sem_interesse",
                        "nao_contatar",
                      ].includes(valor)
                        ? ""
                        : atual.proximo_contato_em,
                    }))
                  }
                  opcoes={CASHBACK_STATUS}
                  permitirLimpar={false}
                  disabled={ocupado}
                />
                <InputData
                  id="cashback-contato-retorno"
                  label="Próximo retorno"
                  value={c.form.proximo_contato_em}
                  onChange={(valor) => atualizarCampo("proximo_contato_em", valor)}
                  disabled={ocupado || semAgenda}
                  required={c.form.status === "retornar_depois"}
                  help={
                    semAgenda
                      ? "Este status encerra os retornos agendados."
                      : c.form.status === "retornar_depois"
                        ? "Informe quando retomar o contato."
                        : "Opcional. Limpe a data para retirar o retorno."
                  }
                />
              </div>
              <InputTextoLongo
                id="cashback-contato-observacao"
                label="Observação para o histórico"
                value={c.form.observacao}
                onChange={(valor) => atualizarCampo("observacao", valor)}
                linhas={3}
                maxLength={2000}
                disabled={ocupado}
                placeholder="Ex.: cliente pediu para conversar na sexta-feira."
              />
              <BotaoSalva
                type="button"
                onClick={c.salvarAcompanhamento}
                loading={c.ocupado === "salvar"}
                disabled={ocupado}
              >
                Salvar acompanhamento
              </BotaoSalva>
            </section>
          )}

          <section className="space-y-3 border-t border-slate-200 pt-5 dark:border-slate-700">
            <h3 className="v2-titulo-secao">Histórico de comunicação</h3>
            {c.carregandoHistorico ? (
              <p role="status" className="py-6 text-sm text-slate-500 dark:text-slate-400">
                Atualizando histórico...
              </p>
            ) : c.erroHistorico ? (
              <p role="alert" className="text-sm text-red-700 dark:text-red-300">
                {c.erroHistorico}
              </p>
            ) : c.contatos.length === 0 ? (
              <EstadoVazio
                icone={History}
                titulo="Nenhum contato registrado"
                descricao="As conversas abertas e os acompanhamentos aparecerão aqui."
              />
            ) : (
              <ol className="space-y-3">
                {c.contatos.map((contato) => (
                  <li
                    key={contato.id}
                    className="rounded-xl border border-slate-200 p-3 dark:border-slate-700"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                        {contato.acao === "conversa_aberta"
                          ? "Conversa aberta no WhatsApp"
                          : "Acompanhamento atualizado"}
                      </p>
                      <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                        {rotuloStatus(contato.status)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {dataCashback(contato.criado_em, true)} ·{" "}
                      {contato.operador_nome || "Operador"} · Saldo na ocasião:{" "}
                      {formatMoneyBRL(contato.saldo_cashback)}
                    </p>
                    {contato.mensagem && (
                      <p className="mt-3 whitespace-pre-wrap break-words text-sm text-slate-600 dark:text-slate-300">
                        {contato.mensagem}
                      </p>
                    )}
                    {contato.observacao && (
                      <p className="mt-2 whitespace-pre-wrap break-words text-sm text-slate-600 dark:text-slate-300">
                        {contato.observacao}
                      </p>
                    )}
                    {contato.proximo_contato_em && (
                      <p className="mt-2 text-xs font-medium text-blue-700 dark:text-blue-300">
                        Retorno: {dataCashback(contato.proximo_contato_em)}
                      </p>
                    )}
                  </li>
                ))}
              </ol>
            )}
            <CashbackCrmPaginacao
              pagina={c.paginaHistorico}
              paginacao={c.paginacaoHistorico}
              onChange={c.setPaginaHistorico}
              disabled={ocupado || c.carregandoHistorico}
            />
          </section>
        </div>
      )}
    </ModalPadrao>
  );
}
