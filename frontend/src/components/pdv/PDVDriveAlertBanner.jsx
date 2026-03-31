import { X } from "lucide-react";

export default function PDVDriveAlertBanner({
  driveAlertVisible,
  driveAguardando,
  onClose,
  onConfirmarEntregue,
}) {
  if (!driveAlertVisible || driveAguardando.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-red-600 text-white shadow-lg">
      <div className="max-w-4xl mx-auto px-4 py-2 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          <span className="text-2xl animate-bounce">🚗</span>
          <div>
            <div className="font-bold text-base">
              {driveAguardando.length === 1
                ? "1 cliente aguardando no estacionamento (Drive)"
                : `${driveAguardando.length} clientes aguardando no estacionamento (Drive)`}
            </div>
            <div className="text-xs text-red-100 flex flex-wrap gap-3 mt-0.5">
              {driveAguardando.map((pedido) => (
                <span
                  key={pedido.pedido_id}
                  className="flex items-center gap-1.5"
                >
                  <span className="font-semibold">
                    #{pedido.pedido_id.slice(-6)}
                  </span>
                  {pedido.palavra_chave_retirada && (
                    <span className="bg-red-700 px-1 rounded">
                      {pedido.palavra_chave_retirada}
                    </span>
                  )}
                  <button
                    onClick={() => onConfirmarEntregue(pedido.pedido_id)}
                    className="bg-white text-red-700 font-bold text-xs px-2 py-0.5 rounded hover:bg-red-50 transition-colors"
                  >
                    Entreguei
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-red-200 hover:text-white p-1 rounded"
          title="Fechar alerta (não marca como entregue)"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
