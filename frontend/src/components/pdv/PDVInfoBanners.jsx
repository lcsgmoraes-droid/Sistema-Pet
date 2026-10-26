import { AlertCircle, ExternalLink, FileText, RefreshCw } from "lucide-react";
import SaleReference from "../ui/SaleReference";
import {
  obterSituacaoFiscalVenda,
  obterPendenciaCancelamentoFiscal,
  rotaNotaFiscalVenda,
} from "../../utils/pdvFiscalStatus";
import { buildValidadePdvMessage } from "./pdvValidadeAlertUtils";
import { mensagemCaixaIndisponivel } from "../../utils/caixaAbertoMonitor";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import { obterSituacaoEstorno } from "../../utils/nfeEstorno";

const ESTILOS_FISCAIS = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  info: "border-blue-200 bg-blue-50 text-blue-800",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  danger: "border-red-200 bg-red-50 text-red-800",
  neutral: "border-slate-200 bg-slate-50 text-slate-800",
};

function formatarDataVenda(dataVenda) {
  if (!dataVenda) {
    return null;
  }

  if (typeof dataVenda === "string" && dataVenda.includes("T")) {
    const [date] = dataVenda.split("T");
    const [, month, day] = date.split("-");
    return `${day}/${month}/${date.slice(0, 4)}`;
  }

  return new Date(dataVenda).toLocaleDateString("pt-BR");
}

export default function PDVInfoBanners({
  temCaixaAberto,
  statusConsultaCaixa,
  atualizandoCaixa,
  onAtualizarCaixa,
  modoVisualizacao,
  vendaAtual,
  onRecarregarVenda,
  loading = false,
  validadeAlertas = [],
}) {
  const mensagemValidade = buildValidadePdvMessage(validadeAlertas);
  const situacaoFiscal = modoVisualizacao ? obterSituacaoFiscalVenda(vendaAtual) : null;
  const rotaNotaFiscal = situacaoFiscal ? rotaNotaFiscalVenda(vendaAtual) : null;
  const pendenciaFiscal = obterPendenciaCancelamentoFiscal(vendaAtual);
  const situacaoEstorno = obterSituacaoEstorno(vendaAtual);

  return (
    <>
      {statusConsultaCaixa !== "pronto" && !modoVisualizacao && (
        <div role="status" className="border-b border-amber-200 bg-amber-50 px-6 py-3">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-center gap-3 text-amber-900">
            <span className="text-sm">
              {temCaixaAberto
                ? "Não foi possível atualizar a consulta. O último caixa confirmado continua aberto."
                : mensagemCaixaIndisponivel(statusConsultaCaixa)}
            </span>
            {statusConsultaCaixa === "erro" && (
              <button
                type="button"
                disabled={atualizandoCaixa}
                onClick={() => onAtualizarCaixa()}
                className="inline-flex items-center gap-1 rounded border border-amber-300 px-2 py-1 text-sm font-semibold disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${atualizandoCaixa ? "animate-spin" : ""}`} />
                Tentar novamente
              </button>
            )}
          </div>
        </div>
      )}
      {!temCaixaAberto && statusConsultaCaixa === "pronto" && !modoVisualizacao && (
        <div className="border-b border-red-200 bg-red-50 px-6 py-3">
          <div className="mx-auto flex max-w-5xl items-center justify-center">
            <div className="flex items-center space-x-2 text-red-800">
              <AlertCircle className="h-5 w-5" />
              <span className="text-lg font-bold">CAIXA FECHADO</span>
              <span className="text-sm">
                - e necessario abrir o caixa para registrar vendas e recebimentos
              </span>
            </div>
          </div>
        </div>
      )}

      {mensagemValidade && (
        <div className="border-b border-amber-200 bg-amber-50 px-6 py-3">
          <div className="mx-auto flex max-w-5xl items-center justify-center">
            <div className="flex items-center gap-2 text-amber-900">
              <AlertCircle className="h-5 w-5 shrink-0" />
              <span className="text-sm font-semibold">{mensagemValidade}</span>
            </div>
          </div>
        </div>
      )}

      {vendaAtual.id && vendaAtual.numero_venda && (
        <div className="border-b border-blue-200 bg-blue-50 px-4 py-1.5">
          <div className="mx-auto flex max-w-5xl items-center justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-blue-800">Venda:</span>
              <div className="flex items-center gap-1.5 rounded border border-blue-300 bg-white px-2 py-0.5">
                <SaleReference
                  buttonClassName="text-blue-600 hover:text-blue-800"
                  sale={vendaAtual}
                  showPrefix={false}
                  valueClassName="text-sm font-bold text-blue-700"
                />
              </div>
            </div>
            {vendaAtual.data_venda && (
              <span className="text-xs text-blue-600">
                {formatarDataVenda(vendaAtual.data_venda)}
              </span>
            )}
          </div>
        </div>
      )}

      {situacaoFiscal && (
        <div
          className={`border-b px-4 py-2 ${ESTILOS_FISCAIS[situacaoFiscal.intent] || ESTILOS_FISCAIS.info}`}
        >
          <div className="mx-auto flex max-w-5xl flex-wrap items-start justify-between gap-2">
            <div className="flex min-w-0 items-start gap-2">
              <FileText className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <div className="min-w-0">
                <div className="text-sm font-semibold">{situacaoFiscal.titulo}</div>
                {situacaoFiscal.detalhe && (
                  <div className="mt-0.5 text-xs">{situacaoFiscal.detalhe}</div>
                )}
                {pendenciaFiscal && (
                  <div
                    role="alert"
                    className="mt-2 rounded border border-amber-400 bg-amber-50 p-2 text-amber-950 dark:border-amber-600 dark:bg-amber-950 dark:text-amber-100"
                  >
                    <div className="font-semibold">{pendenciaFiscal.label}</div>
                    <div className="text-xs">
                      {["cancelada", "cancelado"].includes(vendaAtual.status)
                        ? "A venda está cancelada, mas a nota mantém a situação fiscal acima até a confirmação do emissor."
                        : "A nota mantém a situação fiscal acima até o emissor confirmar seu cancelamento."}
                    </div>
                    {pendenciaFiscal.detalhe && (
                      <div className="mt-1 text-xs">{pendenciaFiscal.detalhe}</div>
                    )}
                  </div>
                )}
                {situacaoEstorno && (
                  <div className="mt-2 rounded border border-slate-300 bg-white/70 p-2 text-sm text-slate-800 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100">
                    <div className="font-semibold">
                      {situacaoEstorno.status === "autorizado" &&
                      vendaAtual.pendencia_fiscal_cancelamento === false
                        ? "Regularizada por estorno"
                        : situacaoEstorno.label}
                    </div>
                    {situacaoEstorno.estorno.numero && (
                      <div className="text-xs">
                        NF-e {situacaoEstorno.estorno.numero} · Série{" "}
                        {situacaoEstorno.estorno.serie}
                      </div>
                    )}
                    <div className="text-xs">A nota original mantém a situação fiscal acima.</div>
                  </div>
                )}
                {vendaAtual.nfe_atualizacao_falhou && (
                  <div role="alert" className="mt-1 text-xs font-semibold">
                    Não foi possível consultar o emissor. Esta é a última situação registrada;
                    atualize para confirmar o cancelamento da nota.
                  </div>
                )}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {onRecarregarVenda && (
                <BotaoInteracao
                  icon={RefreshCw}
                  tamanho="pequeno"
                  loading={loading}
                  onClick={() => onRecarregarVenda(vendaAtual.id)}
                >
                  Atualizar situação
                </BotaoInteracao>
              )}
              {rotaNotaFiscal && (
                <a
                  className="inline-flex items-center gap-1 rounded-md border border-current bg-white/70 px-2 py-1 text-xs font-semibold transition-colors hover:bg-white"
                  href={rotaNotaFiscal}
                  rel="noopener noreferrer"
                  target="_blank"
                  title="Abrir esta nota fiscal em uma nova aba"
                >
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                  {situacaoFiscal.status === "rejeitada"
                    ? "Corrigir erro"
                    : `Abrir ${situacaoFiscal.documento}`}
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
