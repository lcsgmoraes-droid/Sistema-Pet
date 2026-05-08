import { AlertCircle } from "lucide-react";
import CopyableValue from "../ui/CopyableValue";

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
}) {
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

      {vendaAtual.id && vendaAtual.numero_venda && (
        <div className="border-b border-blue-200 bg-blue-50 px-4 py-1.5">
          <div className="mx-auto flex max-w-5xl items-center justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-blue-800">Venda:</span>
              <div className="flex items-center gap-1.5 rounded border border-blue-300 bg-white px-2 py-0.5">
                <CopyableValue
                  title="Copiar numero da venda"
                  value={vendaAtual.numero_venda}
                  valueClassName="text-sm font-bold text-blue-700"
                  buttonClassName="text-blue-600 hover:text-blue-800"
                >
                  #{vendaAtual.numero_venda}
                </CopyableValue>
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
    </>
  );
}
