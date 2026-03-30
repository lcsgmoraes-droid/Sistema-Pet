import { ChevronRight, User } from "lucide-react";
import ClienteInfoWidget from "../ClienteInfoWidget";

export default function PDVClienteSidebar({
  clienteId,
  painelClienteAberto,
  setPainelClienteAberto,
}) {
  if (!clienteId) {
    return null;
  }

  return (
    <>
      {painelClienteAberto && (
        <div className="w-80 bg-gray-50 border-l flex flex-col overflow-hidden">
          <ClienteInfoWidget clienteId={clienteId} />
        </div>
      )}

      <button
        onClick={() => setPainelClienteAberto(!painelClienteAberto)}
        className="fixed right-0 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-l-lg shadow-lg transition-all z-10"
        style={{ right: painelClienteAberto ? "320px" : "0" }}
        title={
          painelClienteAberto
            ? "Recolher informações do cliente"
            : "Expandir informações do cliente"
        }
        type="button"
      >
        {painelClienteAberto ? (
          <ChevronRight className="w-5 h-5" />
        ) : (
          <User className="w-5 h-5" />
        )}
      </button>
    </>
  );
}
