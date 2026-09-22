import { AlertCircle, ExternalLink, FileText } from "lucide-react";
import SaleReference from "../ui/SaleReference";
import { obterSituacaoFiscalVenda, rotaNotaFiscalVenda } from "../../utils/pdvFiscalStatus";
import { buildValidadePdvMessage } from "./pdvValidadeAlertUtils";

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
  modoVisualizacao,
  vendaAtual,
  validadeAlertas = [],
}) {
  const mensagemValidade = buildValidadePdvMessage(validadeAlertas);
  const situacaoFiscal = modoVisualizacao ? obterSituacaoFiscalVenda(vendaAtual) : null;
  const rotaNotaFiscal = situacaoFiscal ? rotaNotaFiscalVenda(vendaAtual) : null;

  return (
    <>
      {!temCaixaAberto && !modoVisualizacao && (
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
              </div>
            </div>
            {rotaNotaFiscal && (
              <a
                className="inline-flex items-center gap-1 rounded-md border border-current bg-white/70 px-2 py-1 text-xs font-semibold transition-colors hover:bg-white"
                href={rotaNotaFiscal}
                rel="noopener noreferrer"
                target="_blank"
                title="Abrir esta nota fiscal em uma nova aba"
              >
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                Abrir {situacaoFiscal.documento}
              </a>
            )}
          </div>
        </div>
      )}
    </>
  );
}
