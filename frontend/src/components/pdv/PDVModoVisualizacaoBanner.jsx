import { AlertCircle, FileText, X } from "lucide-react";
import ImprimirCupom from "../ImprimirCupom";

export default function PDVModoVisualizacaoBanner({
  ativo,
  vendaAtual,
  onVoltar,
  emitirNotaVendaFinalizada,
  mudarStatusParaAberta,
  habilitarEdicao,
}) {
  if (!ativo) {
    return null;
  }

  return (
    <div className="bg-yellow-50 border-b border-yellow-200 px-6 py-3">
      <div className="flex items-center justify-between max-w-5xl mx-auto">
        <div className="flex items-center space-x-2 text-yellow-800">
          <AlertCircle className="w-5 h-5" />
          <span className="font-medium">
            Modo Visualização - Venda{" "}
            {vendaAtual.status === "finalizada"
              ? "Finalizada"
              : vendaAtual.status === "baixa_parcial"
                ? "com Baixa Parcial"
                : "Aberta"}
          </span>
          <span className="text-sm">(Clique em Editar para modificar)</span>
        </div>
        <div className="flex items-center gap-2">
          <ImprimirCupom venda={vendaAtual} />

          <button
            onClick={onVoltar}
            className="h-11 min-w-[132px] px-4 inline-flex items-center justify-center gap-2 rounded-xl border border-slate-500 bg-slate-600 text-white font-semibold shadow-sm hover:bg-slate-700 hover:shadow-md transition-all duration-200"
            type="button"
          >
            <X className="w-4 h-4" />
            Voltar
          </button>

          {(vendaAtual.status === "finalizada" ||
            vendaAtual.status === "baixa_parcial") && (
            <button
              onClick={emitirNotaVendaFinalizada}
              className="h-11 min-w-[132px] px-4 inline-flex items-center justify-center gap-2 rounded-xl border border-emerald-500 bg-emerald-600 text-white font-semibold shadow-sm hover:bg-emerald-700 hover:shadow-md transition-all duration-200"
              type="button"
            >
              <FileText className="w-4 h-4" />
              Emitir NF
            </button>
          )}

          {(vendaAtual.status === "finalizada" ||
            vendaAtual.status === "baixa_parcial") && (
            <button
              onClick={mudarStatusParaAberta}
              className="h-11 min-w-[132px] px-4 inline-flex items-center justify-center gap-2 rounded-xl border border-orange-500 bg-orange-600 text-white font-semibold shadow-sm hover:bg-orange-700 hover:shadow-md transition-all duration-200"
              type="button"
            >
              <AlertCircle className="w-4 h-4" />
              Reabrir Venda
            </button>
          )}

          {vendaAtual.status === "aberta" && (
            <button
              onClick={habilitarEdicao}
              className="h-11 min-w-[132px] px-4 inline-flex items-center justify-center rounded-xl border border-amber-500 bg-amber-600 text-white font-semibold shadow-sm hover:bg-amber-700 hover:shadow-md transition-all duration-200"
              type="button"
            >
              Editar
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
