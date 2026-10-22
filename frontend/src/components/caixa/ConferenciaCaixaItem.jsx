import { useEffect, useId, useRef, useState } from "react";
import { AlertCircle, CheckCircle2, Clock, ExternalLink } from "lucide-react";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputRadio from "../v2/InputRadio/InputRadio";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";
import { estadoConferenciaCaixa } from "../../utils/conferenciaFechamentoUtils";

const ESTADOS = {
  pendente: {
    rotulo: "Pendente",
    icone: Clock,
    classe:
      "border-slate-200 bg-slate-50 text-slate-800 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200",
  },
  ok: {
    rotulo: "OK — conferido",
    icone: CheckCircle2,
    classe:
      "border-emerald-300 bg-emerald-50 text-emerald-950 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-100",
  },
  divergencia: {
    rotulo: "Com divergência",
    icone: AlertCircle,
    classe:
      "border-red-300 bg-red-50 text-red-950 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100",
  },
};

const TIPOS = new Set(["venda", "pagamento", "movimentacao"]);
const idValido = (valor) => Number.isSafeInteger(Number(valor)) && Number(valor) > 0;

function formatarDataConferencia(valor) {
  if (!valor) return "Data não informada";
  const data = new Date(valor);
  if (!Number.isFinite(data.getTime())) return "Data não informada";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  }).format(data);
}

// onSalvar resolve true após salvar e atualizar o item do servidor.
// false, undefined ou erro mantêm o rascunho para uma nova tentativa.
export default function ConferenciaCaixaItem({
  item,
  tipo,
  vendaId,
  salvando = false,
  bloqueado = false,
  onSalvar,
  onAbrirVenda,
}) {
  const campoId = useId();
  const observacaoRef = useRef(null);
  const montadoRef = useRef(false);
  const envioRef = useRef(false);
  const [rascunho, setRascunho] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);
  const chave = `${tipo}:${item?.id ?? "sem-identificacao"}`;
  const edicao = rascunho?.chave === chave ? rascunho : null;
  const erroAtual = erro?.chave === chave ? erro.mensagem : "";
  const estadoSalvo = estadoConferenciaCaixa(item);
  const estado = ESTADOS[estadoSalvo];
  const IconeEstado = estado.icone;
  const identificavel =
    TIPOS.has(tipo) &&
    idValido(item?.id) &&
    typeof item?.assinatura === "string" &&
    item.assinatura.length === 64;
  const indisponivel = !identificavel || bloqueado || typeof onSalvar !== "function";
  const ocupado = salvando || enviando;
  const desabilitado = indisponivel || ocupado;
  const conferencia = item?.conferencia;

  useEffect(() => {
    montadoRef.current = true;
    return () => {
      montadoRef.current = false;
    };
  }, []);

  const selecionarEstado = (proximoEstado) => {
    if (desabilitado || !Object.hasOwn(ESTADOS, proximoEstado)) return;
    setErro(null);
    setRascunho((atual) => ({
      chave,
      estado: proximoEstado,
      observacao: atual?.chave === chave ? atual.observacao : conferencia?.observacao || "",
    }));
  };

  const confirmar = async () => {
    if (desabilitado || envioRef.current || !edicao) return;
    const observacao = edicao.observacao.trim();
    if (edicao.estado === "divergencia" && !observacao) {
      setErro({ chave, mensagem: "Descreva a divergência antes de confirmar." });
      observacaoRef.current?.focus();
      return;
    }
    const enviado = edicao;
    envioRef.current = true;
    setEnviando(true);
    setErro(null);
    try {
      const salvo = await onSalvar(tipo, item, enviado.estado, observacao);
      if (salvo === true && montadoRef.current) {
        setRascunho((atual) => (atual === enviado ? null : atual));
      }
    } catch (error) {
      if (montadoRef.current) {
        const detalhe = error?.response?.data?.detail;
        setErro({
          chave,
          mensagem:
            (typeof detalhe === "string" ? detalhe : "") ||
            error?.message ||
            "Não foi possível salvar a conferência. O rascunho foi mantido.",
        });
      }
    } finally {
      envioRef.current = false;
      if (montadoRef.current) setEnviando(false);
    }
  };

  return (
    <section
      aria-label="Conferência do lançamento"
      aria-busy={ocupado}
      className={`space-y-3 rounded-xl border p-3 ${estado.classe}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-sm font-semibold" role="status">
          <IconeEstado className="h-4 w-4 shrink-0" aria-hidden="true" />
          {estado.rotulo}
        </p>
        {idValido(vendaId) && typeof onAbrirVenda === "function" && (
          <BotaoInteracao
            tamanho="pequeno"
            icon={ExternalLink}
            onClick={() => onAbrirVenda(Number(vendaId))}
            aria-label={`Abrir venda ${vendaId} no PDV em outra aba`}
          >
            Abrir venda no PDV
          </BotaoInteracao>
        )}
      </div>
      {item?.conferencia_alterada && (
        <p className="text-sm font-semibold" role="status">
          Confira novamente este lançamento. A conferência anterior precisa ser atualizada.
        </p>
      )}
      {conferencia ? (
        <div className="space-y-1 text-xs">
          <p>
            Último registro: {conferencia.usuario_nome || "Usuário não informado"} ·{" "}
            {formatarDataConferencia(conferencia.data)}
          </p>
          {conferencia.observacao && (
            <p className="whitespace-pre-wrap break-words">{conferencia.observacao}</p>
          )}
        </div>
      ) : (
        <p className="text-xs">Ainda não há registro de conferência deste lançamento.</p>
      )}
      {!identificavel ? (
        <p className="text-sm" role="status">
          Não foi possível identificar este lançamento para conferência. Atualize o caixa e tente
          novamente.
        </p>
      ) : indisponivel ? (
        <p className="text-sm" role="status">
          A conferência deste lançamento está indisponível no momento.
        </p>
      ) : null}
      <InputRadio
        name={`conferencia-${campoId}`}
        label="Marcar conferência"
        value={edicao?.estado || ""}
        onChange={selecionarEstado}
        disabled={desabilitado}
        opcoes={Object.entries(ESTADOS).map(([valor, dados]) => {
          const Icone = dados.icone;
          return {
            value: valor,
            label: (
              <span className="inline-flex items-center gap-1.5">
                <Icone className="h-3.5 w-3.5" aria-hidden="true" />
                {dados.rotulo}
              </span>
            ),
          };
        })}
        help="Escolha um estado e confirme para salvar a conferência."
      />
      {edicao && (
        <div className="space-y-3 rounded-lg border border-slate-300 bg-white/70 p-3 dark:border-slate-700 dark:bg-slate-900/70">
          <p className="text-xs font-semibold">Alteração ainda não salva.</p>
          <InputTextoLongo
            ref={observacaoRef}
            id={`observacao-conferencia-${campoId}`}
            label={
              edicao.estado === "divergencia"
                ? "Motivo da divergência"
                : "Observação da conferência (opcional)"
            }
            required={edicao.estado === "divergencia"}
            maxLength={1000}
            linhas={3}
            value={edicao.observacao}
            disabled={desabilitado}
            onChange={(observacao) => {
              setErro(null);
              setRascunho((atual) => (atual?.chave === chave ? { ...atual, observacao } : atual));
            }}
            error={erroAtual}
            help="A observação fica registrada com o responsável e a data da conferência."
          />
          <div className="flex flex-wrap gap-2">
            <BotaoSalva
              type="button"
              tamanho="pequeno"
              onClick={confirmar}
              disabled={desabilitado}
              loading={ocupado}
            >
              Confirmar conferência
            </BotaoSalva>
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
    </section>
  );
}
