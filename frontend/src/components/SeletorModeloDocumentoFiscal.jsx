import { CheckCircle2, FileText, Receipt } from "lucide-react";

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
  onChange,
  value = "nfce",
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-semibold text-gray-800">Modelos disponíveis</legend>
      <div className="space-y-2">
        {MODELOS.map((opcao) => {
          const selecionado = value === opcao.tipo;
          const bloqueado = disabled || (opcao.tipo === "nfe" && !clienteIdentificado);
          const Icone = opcao.icon;

          return (
            <button
              key={opcao.tipo}
              type="button"
              aria-pressed={selecionado}
              onClick={() => onChange(opcao.tipo)}
              disabled={bloqueado}
              className={`flex w-full items-start gap-3 rounded-xl border-2 px-4 py-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                selecionado
                  ? opcao.selecionadoClasses
                  : "border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50"
              }`}
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
                {opcao.tipo === "nfe" && !clienteIdentificado && (
                  <span className="mt-1 block text-xs font-medium text-amber-700">
                    Selecione um cliente com CPF ou CNPJ para liberar este modelo.
                  </span>
                )}
              </span>
              <span
                className={`mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                  selecionado ? "border-current bg-white" : "border-gray-300"
                }`}
              >
                {selecionado && <CheckCircle2 className="h-4 w-4" />}
              </span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
