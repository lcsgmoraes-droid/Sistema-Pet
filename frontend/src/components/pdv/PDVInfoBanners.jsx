import { AlertCircle } from "lucide-react";

function formatarDataVenda(dataVenda) {
  if (!dataVenda) {
    return null;
  }

  if (typeof dataVenda === "string" && dataVenda.includes("T")) {
    const [date] = dataVenda.split("T");
    const [year, month, day] = date.split("-");
    return `${day}/${month}/${year}`;
  }

  return new Date(dataVenda).toLocaleDateString("pt-BR");
}

export default function PDVInfoBanners({
  temCaixaAberto,
  modoVisualizacao,
  vendaAtual,
}) {
  const handleCopiarNumeroVenda = (event) => {
    if (!vendaAtual.numero_venda) {
      return;
    }

    navigator.clipboard.writeText(vendaAtual.numero_venda);
    const botao = event.currentTarget;
    const originalText = botao.innerHTML;
    botao.innerHTML = "✓";
    botao.classList.add("text-green-600");

    setTimeout(() => {
      botao.innerHTML = originalText;
      botao.classList.remove("text-green-600");
    }, 1500);
  };

  return (
    <>
      {!temCaixaAberto && !modoVisualizacao && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3">
          <div className="flex items-center justify-center max-w-5xl mx-auto">
            <div className="flex items-center space-x-2 text-red-800">
              <AlertCircle className="w-5 h-5" />
              <span className="font-bold text-lg">🔒 CAIXA FECHADO</span>
              <span className="text-sm">
                - É necessário abrir o caixa para registrar vendas e
                recebimentos
              </span>
            </div>
          </div>
        </div>
      )}

      {vendaAtual.id && vendaAtual.numero_venda && (
        <div className="bg-blue-50 border-b border-blue-200 px-4 py-1.5">
          <div className="flex items-center justify-between max-w-5xl mx-auto">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-blue-800">Venda:</span>
              <div className="flex items-center gap-1.5 bg-white px-2 py-0.5 rounded border border-blue-300">
                <span className="font-bold text-blue-700 text-sm">
                  #{vendaAtual.numero_venda}
                </span>
                <button
                  onClick={handleCopiarNumeroVenda}
                  className="text-blue-600 hover:text-blue-800 transition-colors text-xs"
                  title="Copiar número da venda"
                >
                  📋
                </button>
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
