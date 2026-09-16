import { AlertTriangle, CheckCircle2, FileText, Loader2, Receipt, RefreshCw } from "lucide-react";
import { listarPendenciasFiscais } from "../utils/nfeFiscalAssistida";

const MODELOS = [
  {
    tipo: "nfce",
    titulo: "NFC-e",
    modelo: "Modelo 65",
    destaque: "Padrão do caixa",
    descricao: "Venda presencial comum ao consumidor final.",
    icon: Receipt,
    selecionadoClasses: "border-green-600 bg-green-50 text-green-950",
    badgeClasses: "bg-green-100 text-green-800",
  },
  {
    tipo: "nfe",
    titulo: "NF-e",
    modelo: "Modelo 55",
    destaque: "Nota completa",
    descricao: "Comum em vendas para empresas, entregas, transporte ou quando o cliente solicitar.",
    icon: FileText,
    selecionadoClasses: "border-blue-600 bg-blue-50 text-blue-950",
    badgeClasses: "bg-blue-100 text-blue-800",
  },
];

export default function SeletorModeloDocumentoFiscal({
  clienteIdentificado = false,
  disabled = false,
  fiscalStatuses = {},
  onChange,
  onResolvePending,
  onRetryValidation,
  value = "nfce",
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-semibold text-gray-800">Modelos disponíveis</legend>
      <div className="space-y-2">
        {MODELOS.map((opcao) => {
          const selecionado = value === opcao.tipo;
          const fiscalStatus = fiscalStatuses[opcao.tipo] || {};
          const pendencias = listarPendenciasFiscais(fiscalStatus.validation);
          const temPendencias = pendencias.length > 0;
          const clientePendente = opcao.tipo === "nfe" && !clienteIdentificado;
          const bloqueado =
            disabled ||
            fiscalStatus.loading ||
            Boolean(fiscalStatus.error) ||
            temPendencias ||
            clientePendente;
          const Icone = opcao.icon;
          const cardClasses = temPendencias
            ? "border-amber-300 bg-amber-50 text-amber-950"
            : fiscalStatus.error
              ? "border-red-200 bg-red-50 text-red-950"
              : selecionado
                ? opcao.selecionadoClasses
                : "border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50";

          return (
            <div
              key={opcao.tipo}
              className={`overflow-hidden rounded-xl border-2 transition-colors ${cardClasses}`}
            >
              <button
                type="button"
                aria-pressed={selecionado}
                onClick={() => onChange(opcao.tipo)}
                disabled={bloqueado}
                className="flex w-full items-start gap-3 px-4 py-3 text-left disabled:cursor-not-allowed"
              >
                <span className="mt-0.5 rounded-lg bg-white p-2 shadow-sm">
                  <Icone className="h-5 w-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-bold">{opcao.titulo}</span>
                    <span className="text-sm text-gray-500">{opcao.modelo}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${opcao.badgeClasses}`}
                    >
                      {opcao.destaque}
                    </span>
                  </span>
                  <span className="mt-1 block text-xs leading-5 text-gray-600">
                    {opcao.descricao}
                  </span>
                  {clientePendente && (
                    <span className="mt-1 block text-xs font-medium text-amber-700">
                      Selecione um cliente com CPF ou CNPJ para liberar este modelo.
                    </span>
                  )}
                  {fiscalStatus.loading && (
                    <span className="mt-2 flex items-center gap-1.5 text-xs font-medium text-gray-500">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Verificando pendências…
                    </span>
                  )}
                </span>
                <span
                  className={`mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                    selecionado && !bloqueado ? "border-current bg-white" : "border-gray-300"
                  }`}
                >
                  {selecionado && !bloqueado && <CheckCircle2 className="h-4 w-4" />}
                </span>
              </button>

              {temPendencias && (
                <div className="border-t border-amber-200 px-4 py-3 text-xs">
                  <p className="flex items-center gap-2 font-semibold text-amber-900">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    {pendencias.length === 1
                      ? "1 pendência impede a emissão"
                      : `${pendencias.length} pendências impedem a emissão`}
                  </p>
                  <ul className="mt-2 space-y-1 text-amber-900">
                    {pendencias.slice(0, 2).map((item, index) => (
                      <li key={`${item.campo || "pendencia"}-${index}`}>
                        • {item.produto_nome ? `${item.produto_nome}: ` : ""}
                        {item.mensagem || item.campo}
                      </li>
                    ))}
                    {pendencias.length > 2 && <li>• Mais {pendencias.length - 2} pendência(s)</li>}
                  </ul>
                  <button
                    type="button"
                    onClick={() => onResolvePending?.(opcao.tipo)}
                    disabled={disabled}
                    className="mt-3 inline-flex items-center gap-2 rounded-lg bg-amber-700 px-3 py-2 font-semibold text-white hover:bg-amber-800 disabled:opacity-50"
                  >
                    Resolver pendências
                  </button>
                </div>
              )}

              {fiscalStatus.error && (
                <div className="border-t border-red-200 px-4 py-3 text-xs text-red-800">
                  <p className="font-semibold">Não foi possível verificar a emissão agora.</p>
                  <button
                    type="button"
                    onClick={onRetryValidation}
                    disabled={disabled}
                    className="mt-2 inline-flex items-center gap-2 font-semibold underline disabled:opacity-50"
                  >
                    <RefreshCw className="h-3.5 w-3.5" /> Verificar novamente
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}
