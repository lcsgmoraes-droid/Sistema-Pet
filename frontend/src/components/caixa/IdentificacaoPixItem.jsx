import { useEffect, useId, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, History } from "lucide-react";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputCheckbox from "../v2/InputCheckbox/InputCheckbox";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";

const ESTADOS = {
  nao_conferido: {
    rotulo: "Pix ainda não conferido",
    classe: "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-950",
  },
  identificado: {
    rotulo: "Pix identificado",
    classe: "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/40",
  },
  nao_identificado: {
    rotulo: "Pix não identificado",
    classe: "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/40",
  },
};

function dataHora(valor) {
  const data = new Date(valor);
  return valor && Number.isFinite(data.getTime())
    ? data.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" })
    : "Data não informada";
}

// A identificação do comprovante Pix é independente do OK/divergência do caixa.
// Só pagamentos explicitamente elegíveis na auditoria exibem este controle.
export default function IdentificacaoPixItem({
  item,
  bloqueado = false,
  salvando = false,
  onSalvar,
}) {
  const id = useId();
  const motivoRef = useRef(null);
  const envioRef = useRef(false);
  const montadoRef = useRef(false);
  const [rascunho, setRascunho] = useState(null);
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [mostrarHistorico, setMostrarHistorico] = useState(false);
  const identificacao = item?.identificacao_pix;
  const estadoSalvo = identificacao?.estado;
  const valido =
    Number.isSafeInteger(Number(item?.id)) &&
    Number(item.id) > 0 &&
    typeof item?.assinatura === "string" &&
    /^[a-f0-9]{64}$/i.test(item.assinatura) &&
    Object.hasOwn(ESTADOS, estadoSalvo);
  const chave = `pix:${item?.id}`;
  const baseAtual = `${item?.assinatura}:${identificacao?.registro_id ?? "inicial"}`;
  const edicao = rascunho?.chave === chave ? rascunho : null;
  const erroAtual = erro?.chave === chave ? erro.mensagem : "";
  const desatualizado = Boolean(edicao && edicao.base !== baseAtual);
  const ocupado = salvando || enviando;
  const desabilitado = bloqueado || ocupado || typeof onSalvar !== "function";

  useEffect(() => {
    montadoRef.current = true;
    return () => {
      montadoRef.current = false;
    };
  }, []);

  if (!valido) return null;

  const iniciar = (estado) => {
    if (desabilitado || envioRef.current || estado === estadoSalvo) return;
    setErro(null);
    setRascunho((atual) => ({
      chave,
      estado,
      base: baseAtual,
      justificativa: atual?.chave === chave ? atual.justificativa : "",
    }));
  };
  const salvar = async () => {
    if (desabilitado || envioRef.current || !edicao || desatualizado) return;
    if (edicao.estado === estadoSalvo) {
      setRascunho(null);
      return;
    }
    const justificativa = edicao.justificativa.trim();
    if (!justificativa || justificativa.length > 1000) {
      setErro({ chave, mensagem: "Informe o motivo da identificação, com até 1000 caracteres." });
      motivoRef.current?.focus();
      return;
    }
    envioRef.current = true;
    setEnviando(true);
    setErro(null);
    try {
      const salvo = await onSalvar(item, edicao.estado, justificativa);
      if (!montadoRef.current) return;
      if (salvo === true) setRascunho((atual) => (atual === edicao ? null : atual));
      else
        setErro({
          chave,
          mensagem:
            "Não foi possível confirmar a gravação. Confira os dados atualizados antes de tentar novamente.",
        });
    } catch (error) {
      if (montadoRef.current) {
        const detalhe = error?.response?.data?.detail;
        setErro({
          chave,
          mensagem:
            typeof detalhe === "string"
              ? detalhe
              : "Não foi possível salvar a identificação. O motivo foi preservado para uma nova tentativa.",
        });
      }
    } finally {
      envioRef.current = false;
      if (montadoRef.current) setEnviando(false);
    }
  };
  const historico = Array.isArray(identificacao.historico) ? identificacao.historico : [];

  return (
    <section
      aria-label="Identificação do Pix"
      aria-busy={ocupado}
      className={`space-y-2 rounded-lg border p-3 text-slate-800 dark:text-slate-100 ${ESTADOS[estadoSalvo].classe}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="inline-flex items-center text-sm font-medium">
          <InputCheckbox
            id={`identificacao-${id}`}
            rotulo="Pix identificado"
            checked={estadoSalvo === "identificado"}
            disabled={desabilitado}
            onChange={(evento) =>
              iniciar(evento.target.checked ? "identificado" : "nao_identificado")
            }
          />
          <span>Pix identificado</span>
        </div>
        <BotaoInteracao
          tamanho="pequeno"
          disabled={desabilitado || estadoSalvo === "nao_identificado"}
          onClick={() => iniciar("nao_identificado")}
        >
          Não identificado
        </BotaoInteracao>
      </div>
      <p role="status" className="flex items-center gap-1.5 text-xs font-semibold">
        {estadoSalvo === "identificado" && (
          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
        )}
        {estadoSalvo === "nao_identificado" && (
          <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
        )}
        {ESTADOS[estadoSalvo].rotulo}
      </p>
      {estadoSalvo === "nao_identificado" && (
        <p className="text-xs text-amber-900 dark:text-amber-200">
          Pendência nos Alertas do gestor até identificar o Pix. Não impede o fechamento do caixa.
        </p>
      )}
      {identificacao.pagamento_alterado && (
        <p role="status" className="text-xs text-amber-900 dark:text-amber-200">
          O pagamento foi alterado. Confira novamente a identificação do Pix.
        </p>
      )}
      {identificacao.registro_id && (
        <div className="space-y-1 text-xs">
          <p>
            {identificacao.usuario_nome || "Usuário não informado"} · {dataHora(identificacao.data)}
          </p>
          <p className="whitespace-pre-wrap break-words">{identificacao.justificativa}</p>
        </div>
      )}
      {edicao && (
        <div className="space-y-3 rounded-lg border border-slate-300 bg-white/70 p-3 dark:border-slate-700 dark:bg-slate-900/70">
          <p className="text-xs font-semibold">
            Alteração ainda não salva: {ESTADOS[edicao.estado].rotulo}.
          </p>
          {desatualizado && (
            <p role="alert" className="text-xs text-amber-900 dark:text-amber-200">
              Este Pix foi atualizado. Revise o registro antes de confirmar novamente.
            </p>
          )}
          <InputTextoLongo
            ref={motivoRef}
            id={`motivo-identificacao-${id}`}
            label="Motivo da identificação"
            required
            maxLength={1000}
            linhas={2}
            value={edicao.justificativa}
            disabled={desabilitado}
            error={erroAtual}
            help="Toda mudança registra o motivo, o responsável e a data."
            onChange={(justificativa) => {
              setErro(null);
              setRascunho((atual) =>
                atual?.chave === chave ? { ...atual, justificativa } : atual,
              );
            }}
          />
          <div className="flex flex-wrap gap-2">
            {desatualizado ? (
              <BotaoInteracao
                tamanho="pequeno"
                disabled={desabilitado}
                onClick={() => {
                  setRascunho((atual) =>
                    atual?.chave === chave ? { ...atual, base: baseAtual } : atual,
                  );
                  setErro(null);
                }}
              >
                Revisar com os dados atuais
              </BotaoInteracao>
            ) : (
              <BotaoSalva
                tamanho="pequeno"
                loading={ocupado}
                disabled={desabilitado}
                onClick={salvar}
              >
                Salvar identificação
              </BotaoSalva>
            )}
            <BotaoCancelar
              tamanho="pequeno"
              disabled={ocupado}
              onClick={() => {
                setRascunho(null);
                setErro(null);
              }}
            />
          </div>
        </div>
      )}
      {!edicao && erroAtual && (
        <p role="alert" className="text-xs text-red-700 dark:text-red-300">
          {erroAtual}
        </p>
      )}
      {historico.length > 0 && (
        <>
          <BotaoInteracao
            tamanho="pequeno"
            icon={History}
            aria-expanded={mostrarHistorico}
            onClick={() => setMostrarHistorico((atual) => !atual)}
          >
            {mostrarHistorico ? "Ocultar histórico do Pix" : "Histórico do Pix"}
          </BotaoInteracao>
          {mostrarHistorico && (
            <ol className="space-y-2 border-t border-slate-200 pt-2 text-xs dark:border-slate-700">
              {historico.map((registro, indice) => (
                <li key={registro.registro_id ?? registro.id ?? indice} className="space-y-1">
                  <p className="font-semibold">
                    {ESTADOS[registro.estado]?.rotulo || registro.estado} ·{" "}
                    {registro.usuario_nome || "Usuário não informado"} · {dataHora(registro.data)}
                  </p>
                  <p className="whitespace-pre-wrap break-words">{registro.justificativa}</p>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  );
}
