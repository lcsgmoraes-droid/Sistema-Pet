import { useEffect, useState } from "react";
import api from "../api";
import { SegmentoBadge } from "./ClienteSegmentos";

export default function ClienteSegmentoBadgeWrapper({ clienteId }) {
  const [segmento, setSegmento] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (clienteId && !loaded) {
      loadSegmento();
    }
  }, [clienteId, loaded]);

  const loadSegmento = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/segmentacao/clientes/${clienteId}`);
      setSegmento(response.data.segmento);
    } catch (err) {
      if (err.response?.status !== 404) {
        console.error("Erro ao carregar segmento:", err);
      }
    } finally {
      setLoading(false);
      setLoaded(true);
    }
  };

  if (loading) {
    return <span className="text-xs text-gray-400">...</span>;
  }

  if (!segmento) {
    return <span className="text-xs text-gray-400">-</span>;
  }

  return <SegmentoBadge segmento={segmento} size="sm" />;
}
