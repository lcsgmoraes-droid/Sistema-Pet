import L from "leaflet";
import "leaflet/dist/leaflet.css";
import axios from "axios";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

const apiPublica = axios.create({ baseURL: "/api" });
const TRAIL_LIMIT = 50;

function easeInOut(progress) {
  if (progress < 0.5) {
    return 2 * progress * progress;
  }
  return 1 - Math.pow(-2 * progress + 2, 2) / 2;
}

function samePoint(a, b) {
  if (!a || !b) return false;
  return Math.abs(a.lat - b.lat) < 0.000001 && Math.abs(a.lon - b.lon) < 0.000001;
}

function computeBearing(from, to) {
  const toRad = (value) => (value * Math.PI) / 180;
  const toDeg = (value) => (value * 180) / Math.PI;
  const lat1 = toRad(from.lat);
  const lat2 = toRad(to.lat);
  const diffLong = toRad(to.lon - from.lon);
  const y = Math.sin(diffLong) * Math.cos(lat2);
  const x =
    Math.cos(lat1) * Math.sin(lat2) -
    Math.sin(lat1) * Math.cos(lat2) * Math.cos(diffLong);
  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}

function createVehicleIcon() {
  return L.divIcon({
    html: `
      <div style="display:flex;align-items:center;justify-content:center;">
        <div style="position:absolute;width:34px;height:34px;border-radius:999px;background:rgba(37,99,235,0.18);"></div>
        <div style="width:28px;height:28px;border-radius:999px;background:#2563eb;border:2px solid #fff;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 10px rgba(37,99,235,0.28);">
          <div class="tracker-vehicle-icon" style="font-size:14px;line-height:1;transform:rotate(0deg);transition:transform 0.45s ease;">🚚</div>
        </div>
      </div>
    `,
    className: "",
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
}

export default function RastreioPublico() {
  const { token } = useParams();
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const mapaRef = useRef(null);
  const leafletMapRef = useRef(null);
  const leafletMarkerRef = useRef(null);
  const leafletTrailRef = useRef(null);
  const latestPointRef = useRef(null);
  const animationFrameRef = useRef(null);

  const carregarRastreio = useCallback(async () => {
    try {
      const res = await apiPublica.get(`/rotas-entrega/rastreio/${token}`);
      setDados(res.data);
      setErro(null);
    } catch (err) {
      if (err.response?.status === 404) {
        setErro("Link de rastreio invalido ou expirado.");
      } else {
        setErro("Nao foi possivel carregar o rastreio. Tente novamente.");
      }
    } finally {
      setCarregando(false);
    }
  }, [token]);

  useEffect(() => {
    if (!token) return;

    void carregarRastreio();
    const pollingMs =
      dados?.status === "em_rota" || dados?.status === "em_andamento" ? 4000 : 10000;
    const interval = setInterval(() => {
      void carregarRastreio();
    }, pollingMs);

    return () => clearInterval(interval);
  }, [token, dados?.status, carregarRastreio]);

  useEffect(() => {
    const gps = dados?.ultima_posicao_gps;
    if (!gps || !mapaRef.current) return;

    const nextPoint = { lat: Number(gps.lat), lon: Number(gps.lon) };

    if (!leafletMapRef.current) {
      const map = L.map(mapaRef.current, {
        dragging: false,
        scrollWheelZoom: false,
        zoomControl: true,
        attributionControl: false,
      }).setView([nextPoint.lat, nextPoint.lon], 15);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

      leafletMarkerRef.current = L.marker([nextPoint.lat, nextPoint.lon], {
        icon: createVehicleIcon(),
      }).addTo(map);

      leafletTrailRef.current = L.polyline([[nextPoint.lat, nextPoint.lon]], {
        color: "#2563eb",
        weight: 4,
        opacity: 0.8,
      }).addTo(map);

      leafletMapRef.current = map;
      latestPointRef.current = nextPoint;
      return;
    }

    if (!latestPointRef.current) {
      latestPointRef.current = nextPoint;
      leafletMarkerRef.current?.setLatLng([nextPoint.lat, nextPoint.lon]);
      leafletTrailRef.current?.setLatLngs([[nextPoint.lat, nextPoint.lon]]);
      return;
    }

    if (samePoint(latestPointRef.current, nextPoint)) {
      return;
    }

    const startPoint = latestPointRef.current;
    const bearing = computeBearing(startPoint, nextPoint);
    const markerElement = leafletMarkerRef.current?.getElement();
    const vehicleElement = markerElement?.querySelector(".tracker-vehicle-icon");
    if (vehicleElement) {
      vehicleElement.style.transform = `rotate(${bearing}deg)`;
    }

    const currentTrail = leafletTrailRef.current?.getLatLngs?.() || [];
    const trailPoints = [...currentTrail, L.latLng(nextPoint.lat, nextPoint.lon)].slice(
      -TRAIL_LIMIT,
    );
    leafletTrailRef.current?.setLatLngs(trailPoints);

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    leafletMapRef.current?.panTo([nextPoint.lat, nextPoint.lon], {
      animate: true,
      duration: 1.6,
    });

    const startedAt = performance.now();
    const duration = 1800;

    const animate = (now) => {
      const progress = Math.min((now - startedAt) / duration, 1);
      const eased = easeInOut(progress);
      const currentPoint = {
        lat: startPoint.lat + (nextPoint.lat - startPoint.lat) * eased,
        lon: startPoint.lon + (nextPoint.lon - startPoint.lon) * eased,
      };

      latestPointRef.current = currentPoint;
      leafletMarkerRef.current?.setLatLng([currentPoint.lat, currentPoint.lon]);

      if (progress < 1) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        latestPointRef.current = nextPoint;
        leafletMarkerRef.current?.setLatLng([nextPoint.lat, nextPoint.lon]);
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);
  }, [dados?.ultima_posicao_gps?.lat, dados?.ultima_posicao_gps?.lon, dados?.ultima_posicao_gps?.atualizada_em]);

  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (leafletMapRef.current) {
        leafletMapRef.current.remove();
        leafletMapRef.current = null;
        leafletMarkerRef.current = null;
        leafletTrailRef.current = null;
      }
    };
  }, []);

  const getStatusLabel = (status) => {
    const labels = {
      pendente: "Aguardando saida",
      em_rota: "Em rota",
      em_andamento: "Em rota",
      concluida: "Entregue",
      cancelada: "Cancelada",
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
          <div style={styles.logo}>Sistema Pet</div>
          <p style={{ textAlign: "center", color: "#666" }}>Carregando rastreio...</p>
        </div>
      </div>
    );
  }

  if (erro) {
    return (
      <div style={styles.page}>
        <div style={styles.card}>
          <div style={styles.logo}>Sistema Pet</div>
          <div style={styles.erroBanner}>Erro: {erro}</div>
        </div>
      </div>
    );
  }

  if (!dados) return null;

  const progresso =
    dados.total_paradas > 0
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
  const distanciaAteUltima = Number(dados.distancia_ate_ultima_entrega_km_real || 0);

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div style={styles.logo}>Sistema Pet</div>
          <div style={styles.statusBadge(dados.status)}>{getStatusLabel(dados.status)}</div>
        </div>

        <div style={styles.infoBox}>
          <div style={styles.infoRow}>
            <span style={styles.label}>Entregador:</span>
            <span style={styles.value}>{dados.entregador_nome}</span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.label}>Rota:</span>
            <span style={styles.value}>{dados.rota_numero}</span>
          </div>
        </div>

        <div style={styles.progressoBox}>
          <div style={styles.progressoTexto}>
            <span>{dados.entregues} de {dados.total_paradas} entregas</span>
            <span style={{ fontWeight: "bold" }}>{progresso}%</span>
          </div>
          <div style={styles.progressoBar}>
            <div style={styles.progressoFill(progresso)} />
          </div>
          {dados.pendentes > 0 && (
            <p style={styles.pendentesTexto}>
              {dados.pendentes} entrega{dados.pendentes !== 1 ? "s" : ""} ainda em rota
            </p>
          )}
        </div>

        {linkMaps && (
          <div style={styles.gpsBox}>
            <p style={styles.gpsTexto}>
              {gpsEhTempoReal ? "GPS ao vivo do entregador" : "Ultimo ponto confirmado"}
            </p>
            {gpsAtualizadoEm && <p style={styles.gpsSubtexto}>Atualizado em {gpsAtualizadoEm}</p>}
            <a
              href={linkMaps}
              target="_blank"
              rel="noopener noreferrer"
              style={styles.btnMaps}
            >
              Abrir no Google Maps
            </a>
            <div style={styles.mapaEmbedWrap}>
              <div style={styles.mapaBadgeMoto}>
                {gpsEhTempoReal ? "Rota em movimento" : "Ultimo ponto salvo"}
              </div>
              <div ref={mapaRef} style={styles.mapaLeaflet} />
            </div>
          </div>
        )}

        {(distanciaTotalReal > 0 || distanciaRetornoReal > 0 || distanciaAteUltima > 0) && (
          <div style={styles.distBox}>
            <div style={styles.distTitulo}>Distancia percorrida na rota</div>
            <div style={styles.distLinha}>
              <span>Total rodado</span>
              <strong>{distanciaTotalReal.toFixed(2)} km</strong>
            </div>
            <div style={styles.distLinha}>
              <span>Ate ultima entrega</span>
              <strong>{distanciaAteUltima.toFixed(2)} km</strong>
            </div>
            <div style={styles.distLinha}>
              <span>Retorno vazio</span>
              <strong>{distanciaRetornoReal.toFixed(2)} km</strong>
            </div>
          </div>
        )}

        <div style={styles.paradasBox}>
          <h3 style={styles.paradasTitulo}>Sequencia de entregas</h3>
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
                    {parada.status === "entregue"
                      ? "Entregue"
                      : parada.status === "tentativa"
                        ? "Tentativa"
                        : "A caminho"}
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
          ))}

          {distanciaRetornoReal > 0 && (
            <div style={{ ...styles.paradaItem("entregue"), opacity: 0.82 }}>
              <div style={{ ...styles.paradaOrdem, backgroundColor: "#6b7280" }}>↩</div>
              <div style={styles.paradaInfo}>
                <div style={styles.paradaEndereco}>Retorno ao estabelecimento</div>
                <div style={styles.paradaDistanciaReal}>
                  {`Trecho: ${distanciaRetornoReal.toFixed(2)} km`}
                </div>
                <div style={styles.paradaStatusRow}>
                  <span style={{ fontSize: 12, fontWeight: "600", color: "#6b7280" }}>
                    Retorno vazio
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        <p style={styles.atualizacao}>
          Atualiza automaticamente a cada{" "}
          {dados.status === "em_rota" || dados.status === "em_andamento" ? 4 : 10} segundos
        </p>
      </div>
    </div>
  );
}

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
      status === "concluida"
        ? "#d4edda"
        : status === "em_rota" || status === "em_andamento"
          ? "#cce5ff"
          : status === "cancelada"
            ? "#f8d7da"
            : "#fff3cd",
    color:
      status === "concluida"
        ? "#155724"
        : status === "em_rota" || status === "em_andamento"
          ? "#004085"
          : status === "cancelada"
            ? "#721c24"
            : "#856404",
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
    fontWeight: "700",
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
    height: 260,
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
      status === "entregue"
        ? "#f0fff4"
        : status === "tentativa"
          ? "#fff5f5"
          : "#fafafa",
    border: "1px solid",
    borderColor:
      status === "entregue"
        ? "#c3e6cb"
        : status === "tentativa"
          ? "#f5c6cb"
          : "#e9ecef",
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
      status === "entregue"
        ? "#28a745"
        : status === "tentativa"
          ? "#dc3545"
          : "#666",
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
