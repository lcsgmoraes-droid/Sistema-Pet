import { Copy, Download, Eye, Printer, RefreshCw, Send, XCircle } from "lucide-react";
import { useRef, useState } from "react";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";
import { confirmarCorePet } from "../../services/corepetDialog";
import { formatMoneyBRL } from "../../utils/formatters";
import { textoRespostaFiscal } from "../../utils/pdvFiscalStatus";
import { resumirCancelamentoNota } from "../../utils/nfeCancelamentoFeedback";
import { totalClonagem } from "./clonagemNotaUtils";
import NFSaidaCloneFormulario from "./NFSaidaCloneFormulario";
import useClonagemNota from "./useClonagemNota";

export default function NFSaidaClonagem({ nota, aoFechar, aoAtualizar }) {
  const clone = useClonagemNota(nota, aoFechar, aoAtualizar);
  const { registro } = clone;
  const confirmandoRef = useRef(false);
  const [justificativa, setJustificativa] = useState("");
  const editavel = registro && (!registro.id || registro.status === "rascunho");
  const cancelamentoEmAndamento = ["pendente", "solicitado"].includes(
    registro?.cancelamento_status,
  );
  const statusOriginal = registro?.origem?.status || nota?.status || "não informada";
  const originalAtiva = [
    "autorizada",
    "emitida danfe",
    "processando",
    "pendente",
    "enviando",
    "inconclusiva",
    "contingencia",
  ].includes(statusOriginal.toLowerCase());

  async function confirmarEmissao() {
    if (confirmandoRef.current) return;
    confirmandoRef.current = true;
    try {
      if (
        await confirmarCorePet(
          "Emitir esta cópia como uma nova nota fiscal? Será usada a próxima numeração disponível no ambiente fiscal configurado. Confira os valores e os tributos antes de continuar.",
        )
      ) {
        await clone.emitir();
      }
    } finally {
      confirmandoRef.current = false;
    }
  }

  return (
    <>
      {clone.registros.length > 0 && (
        <section
          className="mb-6 space-y-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900"
          aria-label="Notas clonadas"
        >
          <h2 className="text-lg font-semibold">Notas clonadas</h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Retome os rascunhos ou acompanhe as notas criadas por clonagem.
          </p>
          {clone.registros.map((item) => (
            <div
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-3 text-sm dark:border-slate-700"
            >
              <span>
                Origem: NF #{item.origem?.numero} ·{" "}
                {item.numero ? `Nova NF #${item.numero}` : "Próxima numeração automática"} ·{" "}
                {item.status} · {formatMoneyBRL(item.total ?? totalClonagem(item.dados))}
              </span>
              <BotaoInteracao
                icon={Eye}
                tamanho="pequeno"
                onClick={() => clone.abrirSalvo(item.id)}
                disabled={clone.ocupado}
              >
                Abrir cópia
              </BotaoInteracao>
            </div>
          ))}
        </section>
      )}
      {clone.aberto && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="clonar-nota-titulo"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        >
          <div className="flex max-h-[92vh] w-full max-w-4xl flex-col rounded-xl bg-white text-slate-900 shadow-xl dark:bg-slate-900 dark:text-slate-100">
            <div className="border-b border-slate-200 p-5 dark:border-slate-700">
              <h3 id="clonar-nota-titulo" className="flex items-center gap-2 text-xl font-bold">
                <Copy className="h-5 w-5" />
                Clonar nota fiscal
              </h3>
              <p className="mt-2 text-sm">
                A cópia mantém os dados da nota original e usa a próxima numeração disponível ao
                emitir. A nota original continua com a situação atual.
              </p>
            </div>
            <div className="space-y-4 overflow-y-auto p-5">
              {clone.carregando ? (
                <p role="status">Carregando todos os dados da nota...</p>
              ) : (
                registro && (
                  <>
                    <p className="rounded-lg bg-slate-100 p-3 text-sm dark:bg-slate-800">
                      Origem: NF #{registro.origem?.numero} · Série {registro.dados.serie} ·{" "}
                      {Number(registro.origem?.modelo) === 65 ? "NFC-e" : "NF-e"} · Ambiente:{" "}
                      {registro.dados.ambienteCodigo === 1 ? "Produção" : "Homologação"}
                      <br />
                      Situação da nota original: {statusOriginal}
                      <br />
                      Nova nota: {registro.numero || "numeração automática na emissão"}
                      {registro.status ? ` · ${registro.status}` : ""}
                    </p>
                    {originalAtiva && (
                      <p
                        role="note"
                        className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100"
                      >
                        A nota original continua com efeito fiscal até o cancelamento ser
                        confirmado. Emitir a cópia gera outra nota fiscal.
                      </p>
                    )}
                    {(registro.avisos || []).map((aviso, indice) => (
                      <p key={indice} className="text-sm text-amber-800 dark:text-amber-200">
                        {typeof aviso === "string" ? aviso : aviso.mensagem}
                      </p>
                    ))}
                    {registro.motivo && (
                      <p role="alert" className="text-sm text-amber-800 dark:text-amber-200">
                        {textoRespostaFiscal(registro.motivo)}
                      </p>
                    )}
                    {registro.cancelamento_status && (
                      <p
                        role="status"
                        className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100"
                      >
                        {
                          resumirCancelamentoNota({ ...registro, situacao: registro.status })
                            .mensagem
                        }
                      </p>
                    )}
                    <NFSaidaCloneFormulario
                      dados={registro.dados}
                      alterar={clone.alterar}
                      alterarCanal={clone.alterarCanal}
                      modelo={registro.modelo || registro.origem?.modelo}
                      disabled={clone.ocupado || !editavel}
                    />
                  </>
                )
              )}
              {clone.erro && (
                <p
                  role="alert"
                  className="rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-100"
                >
                  {clone.erro}
                </p>
              )}
              {clone.mensagem && (
                <p
                  role="status"
                  className="rounded-lg bg-blue-50 p-3 text-sm text-blue-900 dark:bg-blue-950 dark:text-blue-100"
                >
                  {clone.mensagem}
                </p>
              )}
              {registro?.status === "autorizada" && (
                <details className="rounded-lg border border-red-200 p-3 text-sm dark:border-red-900">
                  <summary className="cursor-pointer font-semibold">
                    Cancelar esta nova nota
                  </summary>
                  <div className="mt-3 space-y-3">
                    <p>
                      O cancelamento será enviado ao emissor e depende de confirmação. A nota
                      original mantém sua situação atual.
                    </p>
                    <InputTextoLongo
                      label="Justificativa do cancelamento da cópia"
                      value={justificativa}
                      onChange={setJustificativa}
                      disabled={clone.ocupado}
                      help="Mínimo de 15 caracteres"
                      linhas={3}
                    />
                    <BotaoInteracao
                      icon={XCircle}
                      disabled={
                        clone.ocupado || cancelamentoEmAndamento || justificativa.trim().length < 15
                      }
                      onClick={async () => {
                        if (
                          await confirmarCorePet(
                            "Enviar o cancelamento desta nova nota fiscal ao emissor?",
                          )
                        )
                          await clone.cancelar(justificativa);
                      }}
                    >
                      Confirmar cancelamento da cópia
                    </BotaoInteracao>
                  </div>
                </details>
              )}
            </div>
            <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 p-5 dark:border-slate-700">
              <BotaoCancelar onClick={clone.fechar} disabled={clone.ocupado}>
                Fechar
              </BotaoCancelar>
              {editavel && (
                <BotaoSalva
                  onClick={clone.salvar}
                  disabled={clone.carregando || clone.ocupado}
                  loading={clone.ocupado}
                >
                  Salvar rascunho
                </BotaoSalva>
              )}
              {editavel && (
                <BotaoInteracao
                  icon={Send}
                  onClick={confirmarEmissao}
                  disabled={
                    clone.carregando || clone.ocupado || Boolean(registro.bloqueios?.length)
                  }
                  loading={clone.ocupado}
                >
                  Emitir nova nota
                </BotaoInteracao>
              )}
              {registro?.id && !editavel && (
                <BotaoInteracao
                  icon={RefreshCw}
                  onClick={clone.consultar}
                  disabled={clone.ocupado}
                  loading={clone.ocupado}
                >
                  Consultar situação
                </BotaoInteracao>
              )}
              {registro?.id && ["autorizada", "cancelada"].includes(registro.status) && (
                <>
                  <BotaoInteracao
                    icon={Printer}
                    onClick={() => clone.baixarDocumento("danfe")}
                    disabled={clone.ocupado || registro.status !== "autorizada"}
                  >
                    Baixar DANFE
                  </BotaoInteracao>
                  <BotaoInteracao
                    icon={Download}
                    onClick={() => clone.baixarDocumento("xml")}
                    disabled={clone.ocupado}
                  >
                    Baixar XML
                  </BotaoInteracao>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
