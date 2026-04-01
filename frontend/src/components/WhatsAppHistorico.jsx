import { useEffect, useState } from "react";
import { FiMessageCircle } from "react-icons/fi";
import api from "../api";

export default function WhatsAppHistorico({ clienteId }) {
  const [mensagens, setMensagens] = useState([]);
  const [loadingMensagens, setLoadingMensagens] = useState(true);

  useEffect(() => {
    if (clienteId) {
      loadMensagens();
    }
  }, [clienteId]);

  const loadMensagens = async () => {
    try {
      setLoadingMensagens(true);
      const response = await api.get(
        `/whatsapp/clientes/${clienteId}/whatsapp/ultimas?limit=5`,
      );
      setMensagens(response.data);
    } catch (err) {
      console.error("Erro ao carregar mensagens:", err);
      setMensagens([]);
    } finally {
      setLoadingMensagens(false);
    }
  };

  if (loadingMensagens) {
    return (
      <div className="text-center py-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
        <p className="text-sm text-gray-600 mt-2">Carregando mensagens...</p>
      </div>
    );
  }

  if (mensagens.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        <FiMessageCircle size={32} className="mx-auto mb-2 text-gray-400" />
        <p className="text-sm">Nenhuma mensagem registrada ainda</p>
        <p className="text-xs mt-1">
          As mensagens enviadas e recebidas aparecerao aqui
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-gray-700 mb-3">
        Ultimas 5 mensagens:
      </p>
      {mensagens.map((msg) => (
        <div
          key={msg.id}
          className={`p-3 rounded-lg border ${
            msg.direcao === "enviada"
              ? "bg-green-50 border-green-200 ml-6"
              : "bg-blue-50 border-blue-200 mr-6"
          }`}
        >
          <div className="flex items-start justify-between gap-2 mb-1">
            <div className="flex items-center gap-2">
              <span
                className={`text-xs font-semibold ${
                  msg.direcao === "enviada"
                    ? "text-green-700"
                    : "text-blue-700"
                }`}
              >
                {msg.direcao === "enviada" ? "-> Enviada" : "<- Recebida"}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  msg.status === "lido"
                    ? "bg-green-200 text-green-800"
                    : msg.status === "enviado"
                      ? "bg-yellow-200 text-yellow-800"
                      : msg.status === "recebido"
                        ? "bg-blue-200 text-blue-800"
                        : "bg-red-200 text-red-800"
                }`}
              >
                {msg.status}
              </span>
            </div>
            <span className="text-xs text-gray-500">
              {new Date(msg.created_at).toLocaleString("pt-BR")}
            </span>
          </div>
          <p className="text-sm text-gray-700">{msg.preview || msg.conteudo}</p>
        </div>
      ))}
    </div>
  );
}
