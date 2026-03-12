import L from "leaflet";
import "leaflet/dist/leaflet.css";
import axios from "axios";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

// Instância sem autenticação — endpoint público
const apiPublica = axios.create({ baseURL: "/api" });

export default function RastreioPublico() {
  const { token } = useParams();
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const mapaRef = useRef(null);
  const leafletMapRef = useRef(null);
  const leafletMarkerRef = useRef(null);

  useEffect(() => {
    if (!token) return;
    carregarRastreio();
    // Atualizar a cada 10 segundos
    const interval = setInterval(carregarRastreio, 10000);
    return () => clearInterval(interval);
  }, [token]);

  // Inicializa ou atualiza o mapa Leaflet a cada atualização de GPS
  useEffect(() => {
    if (!dados?.ultima_posicao_gps || !mapaRef.current) return;
    const { lat, lon } = dados.ultima_posicao_gps;
    if (!leafletMapRef.current) {
      const map = L.map(mapaRef.current, {
        dragging: false,
        scrollWheelZoom: false,
        zoomControl: true,
        attributionControl: false,
      }).setView([lat, lon], 15);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
      const motoIcon = L.divIcon({
        html: '<div style="font-size:28px;line-height:1;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.4))">🛵</div>',
        className: "",
        iconSize: [32, 32],
        iconAnchor: [16, 28],
      });
      leafletMarkerRef.current = L.marker([lat, lon], { icon: motoIcon }).addTo(map);
      leafletMapRef.current = map;
    } else {
      leafletMarkerRef.current.setLatLng([lat, lon]);
      leafletMapRef.current.setView([lat, lon], leafletMapRef.current.getZoom());
    }
  }, [dados]);

  // Limpa o mapa ao sair da página
  useEffect(() => {
    return () => {
      if (leafletMapRef.current) {
        leafletMapRef.current.remove();
        leafletMapRef.current = null;
        leafletMarkerRef.current = null;
      }
    };
  }, []);

  async function carregarRastreio() {
    try {
      const res = await apiPublica.get(`/rotas-entrega/rastreio/${token}`);
      setDados(res.data);
      setErro(null);
    } catch (err) {
      if (err.response?.status === 404) {
        setErro("Link de rastreio inválido ou expirado.");
      } else {
        setErro("Não foi possível carregar o rastreio. Tente novamente.");
      }
    } finally {
      setCarregando(false);
    }
  }

  const getStatusLabel = (status) => {
    const labels = {
      pendente: "🟠 Aguardando saída",
      em_rota: "🔵 Em rota",
      em_andamento: "🔵 Em rota",
      concluida: "✅ Entregue",
      cancelada: "❌ Cancelada",
    };
    return labels[status] || status;
  };

  const getParadaStatusIcon = (status) => {
    if (status === "entregue") return "✅";
    if (status === "tentativa") return "🔁";
    return "⏳";
  };

  if (carregando) {
    return (
      <div style={styles.page}>
        <div style={styles.card}>
          <div style={styles.logo}>🐾 Sistema Pet</div>
          <p style={{ textAlign: "center", color: "#666" }}>Carregando rastreio...</p>
        </div>
      </div>
    );
  }

  if (erro) {
    return (
      <div style={styles.page}>
        <div style={styles.card}>
          <div style={styles.logo}>🐾 Sistema Pet</div>
          <div style={styles.erroBanner}>❌ {erro}</div>
        </div>
      </div>
    );
  }

  if (!dados) return null;

  const progresso = dados.total_paradas > 0
    ? Math.round((dados.entregues / dados.total_paradas) * 100)
    : 0;

  const linkMaps = dados.ultima_posicao_gps
    ? `https://www.google.com/maps?q=${dados.ultima_posicao_gps.lat},${dados.ultima_posicao_gps.lon}`
    : null;

  const gpsFonte = dados.ultima_posicao_gps?.fonte || null;
  const gpsAtualizadoEm = dados.ultima_posicao_gps?.atualizada_em
    ? new Date(dados.ultima_posicao_gps.atualizada_em).toLocaleString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;
  const gpsEhTempoReal = gpsFonte === "rota_atual";
  const distanciaTotalReal = Number(dados.distancia_total_km_real || 0);
  const distanciaRetornoReal = Number(dados.distancia_retorno_km_real || 0);
  const distanciaAteUltima = Number(
    dados.distancia_ate_ultima_entrega_km_real || 0,
  );

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.logo}>🐾 Sistema Pet</div>
          <div style={styles.statusBadge(dados.status)}>
            {getStatusLabel(dados.status)}
          </div>
        </div>

        {/* Info do entregador */}
        <div style={styles.infoBox}>
          <div style={styles.infoRow}>
            <span style={styles.label}>Entregador:</span>
            <span style={styles.value}>🏍️ {dados.entregador_nome}</span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.label}>Rota:</span>
            <span style={styles.value}>{dados.rota_numero}</span>
          </div>
        </div>

        {/* Progresso */}
        <div style={styles.progressoBox}>
          <div style={styles.progressoTexto}>
            <span>📦 {dados.entregues} de {dados.total_paradas} entregas</span>
            <span style={{ fontWeight: "bold" }}>{progresso}%</span>
          </div>
          <div style={styles.progressoBar}>
            <div style={styles.progressoFill(progresso)} />
          </div>
          {dados.pendentes > 0 && (
            <p style={styles.pendentesTexto}>
              ⏳ {dados.pendentes} entrega{dados.pendentes !== 1 ? "s" : ""} ainda a caminho
            </p>
          )}
        </div>

        {/* Última posição GPS */}
        {linkMaps && (
          <div style={styles.gpsBox}>
            <p style={styles.gpsTexto}>
              {gpsEhTempoReal
                ? "🏍️ 📍 GPS ao vivo do entregador"
                : "📍 Última posição registrada na rota"}
            </p>
            {gpsAtualizadoEm && (
              <p style={styles.gpsSubtexto}>
                Atualizado em {gpsAtualizadoEm}
              </p>
            )}
            <a
              href={linkMaps}
              target="_blank"
              rel="noopener noreferrer"
              style={styles.btnMaps}
            >
              🗺️ Abrir no Google Maps
            </a>
            <div style={styles.mapaEmbedWrap}>
              <div style={styles.mapaBadgeMoto}>
                {gpsEhTempoReal ? "🏍️ Entregador ao vivo" : "📌 Último ponto confirmado"}
              </div>
              <div ref={mapaRef} style={styles.mapaLeaflet} />
            </div>
          </div>
        )}

        {(distanciaTotalReal > 0 || distanciaRetornoReal > 0 || distanciaAteUltima > 0) && (
          <div style={styles.distBox}>
            <div style={styles.distTitulo}>📏 Distância percorrida na rota</div>
            <div style={styles.distLinha}>
              <span>Total rodado</span>
              <strong>{distanciaTotalReal.toFixed(2)} km</strong>
            </div>
            <div style={styles.distLinha}>
              <span>Até última entrega</span>
              <strong>{distanciaAteUltima.toFixed(2)} km</strong>
            </div>
            <div style={styles.distLinha}>
              <span>Retorno vazio</span>
              <strong>{distanciaRetornoReal.toFixed(2)} km</strong>
            </div>
          </div>
        )}

        {/* Lista de paradas */}
        <div style={styles.paradasBox}>
          <h3 style={styles.paradasTitulo}>Sequência de entregas</h3>
          {dados.paradas.map((parada) => (
            <div key={parada.ordem} style={styles.paradaItem(parada.status)}>
              <div style={styles.paradaOrdem}>{parada.ordem}</div>
              <div style={styles.paradaInfo}>
                <div style={styles.paradaEndereco}>{parada.endereco}</div>
                {parada.status === "entregue" && Number(parada.distancia_trecho_real_km) > 0 && (
                  <div style={styles.paradaDistanciaReal}>
                    {`Trecho: ${Number(parada.distancia_trecho_real_km).toFixed(2)} km`}
                    {parada.distancia_acumulada_real_km > 0
                      ? ` • Acumulado: ${Number(parada.distancia_acumulada_real_km).toFixed(2)} km`
                      : ""}
                  </div>
                )}
                <div style={styles.paradaStatusRow}>
                  <span style={styles.paradaStatus(parada.status)}>
                    {getParadaStatusIcon(parada.status)}{" "}
                    {parada.status === "entregue" ? "Entregue" :
                     parada.status === "tentativa" ? "Tentativa" : "A caminho"}
                  </span>
                  {parada.data_entrega && (
                    <span style={styles.paradaHora}>
                      {new Date(parada.data_entrega).toLocaleTimeString("pt-BR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}          {/* Retorno vazio ao estabelecimento */}
          {distanciaRetornoReal > 0 && (
            <div style={{...styles.paradaItem("entregue"), opacity: 0.8}}>
              <div style={{...styles.paradaOrdem, backgroundColor: "#6b7280"}}>↩</div>
              <div style={styles.paradaInfo}>
                <div style={styles.paradaEndereco}>Retorno ao estabelecimento</div>
                <div style={styles.paradaDistanciaReal}>
                  {`Trecho: ${distanciaRetornoReal.toFixed(2)} km`}
                </div>
                <div style={styles.paradaStatusRow}>
                  <span style={{fontSize: 12, fontWeight: "600", color: "#6b7280"}}>🏠 Retorno vazio</span>
                </div>
              </div>
            </div>
          )}        </div>

        {/* Rodapé */}
        <p style={styles.atualizacao}>
          🔄 Atualiza automaticamente a cada 10 segundos
        </p>
      </div>
    </div>
  );
}

// ── Estilos inline ────────────────────────────────────────────────────────────
const styles = {
  page: {
    minHeight: "100vh",
    backgroundColor: "#f5f5f5",
    display: "flex",
    justifyContent: "center",
    alignItems: "flex-start",
    padding: "20px 16px",
    fontFamily: "system-ui, sans-serif",
  },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 24,
    maxWidth: 480,
    width: "100%",
    boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  logo: {
    fontSize: 20,
    fontWeight: "700",
    color: "#333",
  },
  statusBadge: (status) => ({
    padding: "4px 12px",
    borderRadius: 20,
    fontSize: 13,
    fontWeight: "600",
    backgroundColor:
      status === "concluida" ? "#d4edda" :
      status === "em_rota" || status === "em_andamento" ? "#cce5ff" :
      status === "cancelada" ? "#f8d7da" : "#fff3cd",
    color:
      status === "concluida" ? "#155724" :
      status === "em_rota" || status === "em_andamento" ? "#004085" :
      status === "cancelada" ? "#721c24" : "#856404",
  }),
  erroBanner: {
    padding: 16,
    backgroundColor: "#f8d7da",
    color: "#721c24",
    borderRadius: 8,
    textAlign: "center",
  },
  infoBox: {
    backgroundColor: "#f8f9fa",
    borderRadius: 8,
    padding: "12px 16px",
    marginBottom: 16,
  },
  infoRow: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  label: { color: "#666", fontSize: 14 },
  value: { fontWeight: "600", fontSize: 14 },
  progressoBox: {
    marginBottom: 20,
  },
  progressoTexto: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: 14,
    marginBottom: 8,
    color: "#333",
  },
  progressoBar: {
    height: 10,
    backgroundColor: "#e9ecef",
    borderRadius: 5,
    overflow: "hidden",
  },
  progressoFill: (pct) => ({
    height: "100%",
    width: `${pct}%`,
    backgroundColor: pct === 100 ? "#28a745" : "#007bff",
    borderRadius: 5,
    transition: "width 0.3s ease",
  }),
  pendentesTexto: {
    fontSize: 13,
    color: "#666",
    marginTop: 6,
    textAlign: "center",
  },
  gpsBox: {
    backgroundColor: "#e8f4fd",
    borderRadius: 8,
    padding: 14,
    marginBottom: 20,
    textAlign: "center",
  },
  gpsTexto: {
    fontSize: 13,
    color: "#333",
    marginBottom: 4,
  },
  gpsSubtexto: {
    fontSize: 12,
    color: "#6b7280",
    marginTop: 0,
    marginBottom: 8,
  },
  btnMaps: {
    display: "inline-block",
    padding: "8px 20px",
    backgroundColor: "#007bff",
    color: "#fff",
    borderRadius: 6,
    textDecoration: "none",
    fontWeight: "600",
    fontSize: 14,
  },
  mapaEmbedWrap: {
    marginTop: 12,
    position: "relative",
    borderRadius: 12,
    overflow: "hidden",
    border: "1px solid #dbeafe",
    backgroundColor: "#fff",
  },
  mapaLeaflet: {
    width: "100%",
    height: 240,
  },
  mapaBadgeMoto: {
    position: "absolute",
    zIndex: 1000,
    top: 10,
    left: 10,
    backgroundColor: "rgba(17,24,39,0.8)",
    color: "#fff",
    fontSize: 12,
    fontWeight: "700",
    padding: "6px 10px",
    borderRadius: 999,
  },
  distBox: {
    backgroundColor: "#f8fafc",
    border: "1px solid #e5e7eb",
    borderRadius: 8,
    padding: 12,
    marginBottom: 18,
  },
  distTitulo: {
    fontSize: 14,
    fontWeight: "700",
    marginBottom: 8,
    color: "#1f2937",
  },
  distLinha: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: 13,
    color: "#374151",
    marginBottom: 4,
  },
  paradasBox: {
    marginBottom: 16,
  },
  paradasTitulo: {
    fontSize: 15,
    fontWeight: "600",
    marginBottom: 12,
    color: "#333",
  },
  paradaItem: (status) => ({
    display: "flex",
    gap: 12,
    padding: "10px 12px",
    borderRadius: 8,
    marginBottom: 8,
    backgroundColor:
      status === "entregue" ? "#f0fff4" :
      status === "tentativa" ? "#fff5f5" : "#fafafa",
    border: "1px solid",
    borderColor:
      status === "entregue" ? "#c3e6cb" :
      status === "tentativa" ? "#f5c6cb" : "#e9ecef",
  }),
  paradaOrdem: {
    width: 28,
    height: 28,
    borderRadius: "50%",
    backgroundColor: "#007bff",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: "700",
    fontSize: 13,
    flexShrink: 0,
  },
  paradaInfo: {
    flex: 1,
    minWidth: 0,
  },
  paradaEndereco: {
    fontSize: 13,
    color: "#333",
    marginBottom: 4,
    wordBreak: "break-word",
  },
  paradaStatusRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  paradaDistanciaReal: {
    fontSize: 12,
    color: "#0f766e",
    marginBottom: 4,
    fontWeight: "600",
  },
  paradaStatus: (status) => ({
    fontSize: 12,
    fontWeight: "600",
    color:
      status === "entregue" ? "#28a745" :
      status === "tentativa" ? "#dc3545" : "#666",
  }),
  paradaHora: {
    fontSize: 12,
    color: "#888",
  },
  atualizacao: {
    textAlign: "center",
    fontSize: 12,
    color: "#aaa",
    marginTop: 8,
  },
};
