import { Ionicons } from "@expo/vector-icons";
import { useRoute } from "@react-navigation/native";
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import MapView, { Marker, Polyline } from "react-native-maps";
import api from "../../services/api";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

type Coordenada = {
  latitude: number;
  longitude: number;
};

type GpsPosicao = {
  lat: number;
  lon: number;
  atualizada_em?: string | null;
  fonte?: string | null;
};

const STATUS_ROTA: Record<string, { label: string; cor: string }> = {
  pendente: { label: "Preparando", cor: "#F59E0B" },
  em_andamento: { label: "Em rota", cor: "#3B82F6" },
  em_rota: { label: "A caminho", cor: "#3B82F6" },
  concluida: { label: "Entregue", cor: "#10B981" },
  entregue: { label: "Entregue", cor: "#10B981" },
};

const STATUS_PARADA: Record<
  string,
  { emoji: string; label: string; cor: string; corFundo: string }
> = {
  pendente: {
    emoji: "⏳",
    label: "Aguardando",
    cor: "#92400E",
    corFundo: "#FEF3C7",
  },
  entregue: {
    emoji: "✅",
    label: "Entregue",
    cor: "#065F46",
    corFundo: "#D1FAE5",
  },
  em_rota: {
    emoji: "🛵",
    label: "A caminho",
    cor: "#1E40AF",
    corFundo: "#DBEAFE",
  },
};

interface RastreioData {
  status_pedido: string;
  tem_entrega: boolean;
  mensagem: string;
  tipo_retirada?: string;
  palavra_chave_retirada?: string;
  rota?: {
    numero: string;
    status: string;
    token_rastreio?: string;
    entregador_nome: string;
    total_paradas: number;
    entregues: number;
    posicao_cliente?: number;
    paradas_antes: number;
    status_parada: string;
    endereco_entrega?: string;
    data_entrega?: string;
    ultima_posicao_gps?: GpsPosicao;
  };
}

function easeInOut(progress: number) {
  if (progress < 0.5) {
    return 2 * progress * progress;
  }
  return 1 - Math.pow(-2 * progress + 2, 2) / 2;
}

function samePoint(a: Coordenada | null, b: Coordenada) {
  if (!a) return false;
  return (
    Math.abs(a.latitude - b.latitude) < 0.000001 &&
    Math.abs(a.longitude - b.longitude) < 0.000001
  );
}

function computeBearing(from: Coordenada, to: Coordenada) {
  const toRad = (value: number) => (value * Math.PI) / 180;
  const toDeg = (value: number) => (value * 180) / Math.PI;
  const lat1 = toRad(from.latitude);
  const lat2 = toRad(to.latitude);
  const diffLong = toRad(to.longitude - from.longitude);
  const y = Math.sin(diffLong) * Math.cos(lat2);
  const x =
    Math.cos(lat1) * Math.sin(lat2) -
    Math.sin(lat1) * Math.cos(lat2) * Math.cos(diffLong);

  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}

function appendTrailPoint(points: Coordenada[], next: Coordenada) {
  const last = points[points.length - 1];
  if (last && samePoint(last, next)) {
    return points;
  }
  return [...points, next].slice(-40);
}

export default function TrackDeliveryScreen() {
  const route = useRoute<any>();
  const { pedidoId } = route.params;

  const [dados, setDados] = useState<RastreioData | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState<Date | null>(null);
  const [intervaloMs, setIntervaloMs] = useState(6_000);
  const [vehiclePosition, setVehiclePosition] = useState<Coordenada | null>(null);
  const [routeTrail, setRouteTrail] = useState<Coordenada[]>([]);
  const [markerHeading, setMarkerHeading] = useState(0);
  const mapRef = useRef<MapView | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const livePointRef = useRef<Coordenada | null>(null);

  const carregar = useCallback(async () => {
    try {
      const resp = await api.get(`/app/pedidos/${pedidoId}/rastreio`);
      setDados(resp.data);
      setUltimaAtualizacao(new Date());
    } catch {
      // Mantem o ultimo estado exibido se a rede oscilar.
    } finally {
      setCarregando(false);
      setRefreshing(false);
    }
  }, [pedidoId]);

  useEffect(() => {
    const paradasAntes = dados?.rota?.paradas_antes ?? 99;
    setIntervaloMs(paradasAntes <= 1 ? 3_000 : 6_000);
  }, [dados?.rota?.paradas_antes]);

  useEffect(() => {
    carregar();
    const interval = setInterval(() => {
      if (dados?.rota?.status_parada !== "entregue") {
        void carregar();
      }
    }, intervaloMs);
    return () => clearInterval(interval);
  }, [carregar, dados?.rota?.status_parada, intervaloMs]);

  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const gps = dados?.rota?.ultima_posicao_gps;
    if (!gps) {
      livePointRef.current = null;
      setVehiclePosition(null);
      setRouteTrail([]);
      return;
    }

    const nextPoint = {
      latitude: gps.lat,
      longitude: gps.lon,
    };

    if (!livePointRef.current) {
      livePointRef.current = nextPoint;
      setVehiclePosition(nextPoint);
      setRouteTrail([nextPoint]);
      return;
    }

    if (samePoint(livePointRef.current, nextPoint)) {
      return;
    }

    const startPoint = livePointRef.current;
    setMarkerHeading(computeBearing(startPoint, nextPoint));
    setRouteTrail((prev) => appendTrailPoint(prev, nextPoint));

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    const startedAt = Date.now();
    const duration = 1600;

    mapRef.current?.animateCamera({ center: nextPoint }, { duration });

    const animate = () => {
      const progress = Math.min((Date.now() - startedAt) / duration, 1);
      const eased = easeInOut(progress);
      const currentPoint = {
        latitude:
          startPoint.latitude + (nextPoint.latitude - startPoint.latitude) * eased,
        longitude:
          startPoint.longitude + (nextPoint.longitude - startPoint.longitude) * eased,
      };

      livePointRef.current = currentPoint;
      setVehiclePosition(currentPoint);

      if (progress < 1) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        livePointRef.current = nextPoint;
        setVehiclePosition(nextPoint);
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);
  }, [
    dados?.rota?.ultima_posicao_gps?.lat,
    dados?.rota?.ultima_posicao_gps?.lon,
    dados?.rota?.ultima_posicao_gps?.atualizada_em,
  ]);

  function abrirGoogleMaps() {
    const gps = dados?.rota?.ultima_posicao_gps;
    const endereco = dados?.rota?.endereco_entrega;

    let url = "";
    if (gps) {
      url = `https://www.google.com/maps?q=${gps.lat},${gps.lon}`;
    } else if (endereco) {
      url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(endereco)}`;
    }

    if (url) Linking.openURL(url);
  }

  if (carregando) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color={CORES.primario} />
        <Text style={styles.loadingText}>Consultando rastreio...</Text>
      </View>
    );
  }

  if (!dados) {
    return (
      <View style={styles.loading}>
        <Text style={{ fontSize: 40 }}>😕</Text>
        <Text style={styles.erroText}>Nao foi possivel carregar o rastreio.</Text>
      </View>
    );
  }

  if (!dados.tem_entrega) {
    return (
      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              void carregar();
            }}
            tintColor={CORES.primario}
          />
        }
      >
        <View style={styles.heroCard}>
          <Text style={styles.heroEmoji}>🏪</Text>
          <Text style={styles.heroTitulo}>Retirada na loja</Text>
          <Text style={styles.heroSubtitulo}>{dados.mensagem}</Text>
        </View>

        {dados.palavra_chave_retirada && (
          <View style={styles.palavraChaveCard}>
            <Ionicons name="key" size={28} color={CORES.primario} />
            <View style={{ flex: 1 }}>
              <Text style={styles.palavraChaveLabel}>Fale essa palavra no caixa:</Text>
              <Text style={styles.palavraChaveValor}>
                {dados.palavra_chave_retirada.toUpperCase()}
              </Text>
            </View>
          </View>
        )}

        <View style={styles.infoCard}>
          <Ionicons
            name="information-circle-outline"
            size={20}
            color={CORES.textoSecundario}
          />
          <Text style={styles.infoTexto}>
            Apresente essa tela ou fale a palavra-chave ao atendente para retirar seu
            pedido.
          </Text>
        </View>
      </ScrollView>
    );
  }

  const rota = dados.rota;

  if (!rota) {
    return (
      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              void carregar();
            }}
            tintColor={CORES.primario}
          />
        }
      >
        <View style={styles.heroCard}>
          <Text style={styles.heroEmoji}>📦</Text>
          <Text style={styles.heroTitulo}>Pedido recebido</Text>
          <Text style={styles.heroSubtitulo}>{dados.mensagem}</Text>
        </View>

        <View style={[styles.infoCard, { marginTop: ESPACO.md }]}>
          <Ionicons
            name="time-outline"
            size={20}
            color={CORES.textoSecundario}
          />
          <Text style={styles.infoTexto}>
            Assim que o entregador sair com seu pedido, o acompanhamento aparece aqui.
          </Text>
        </View>

        {ultimaAtualizacao && (
          <Text style={styles.atualizadoEm}>
            Atualizado as{" "}
            {ultimaAtualizacao.toLocaleTimeString("pt-BR", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </Text>
        )}
      </ScrollView>
    );
  }

  const statusRotaCfg = STATUS_ROTA[rota.status] ?? STATUS_ROTA.pendente;
  const statusParadaCfg =
    STATUS_PARADA[rota.status_parada] ?? STATUS_PARADA.pendente;
  const progresso =
    rota.total_paradas > 0 ? rota.entregues / rota.total_paradas : 0;
  const podeAbrirMapa =
    rota.ultima_posicao_gps !== undefined || Boolean(rota.endereco_entrega);
  const gpsTempoReal = rota.ultima_posicao_gps?.fonte === "rota_atual";
  const gpsAtualizadoEm = rota.ultima_posicao_gps?.atualizada_em
    ? new Date(rota.ultima_posicao_gps.atualizada_em).toLocaleString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            void carregar();
          }}
          tintColor={CORES.primario}
        />
      }
    >
      <View
        style={[
          styles.heroCard,
          { borderTopColor: statusParadaCfg.cor, borderTopWidth: 4 },
        ]}
      >
        <Text style={styles.heroEmoji}>{statusParadaCfg.emoji}</Text>
        <Text style={styles.heroTitulo}>{statusParadaCfg.label}</Text>
        <Text style={styles.heroSubtitulo}>{dados.mensagem}</Text>
      </View>

      <View style={styles.entregadorCard}>
        <View style={styles.entregadorIcone}>
          <Ionicons name="bicycle" size={24} color={CORES.primario} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.entregadorNome}>{rota.entregador_nome}</Text>
          <Text style={styles.entregadorLabel}>Entregador responsavel</Text>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: `${statusRotaCfg.cor}22` }]}>
          <Text style={[styles.statusBadgeTexto, { color: statusRotaCfg.cor }]}>
            {statusRotaCfg.label}
          </Text>
        </View>
      </View>

      {rota.total_paradas > 1 && rota.status_parada !== "entregue" && (
        <View style={styles.progressoCard}>
          <Text style={styles.progressoTitulo}>Progresso da rota</Text>
          <View style={styles.progressoBar}>
            <View
              style={[
                styles.progressoPreenchido,
                { width: `${progresso * 100}%` as any },
              ]}
            />
          </View>
          <Text style={styles.progressoTexto}>
            {rota.entregues} de {rota.total_paradas} entregas concluidas
          </Text>
          {rota.paradas_antes > 0 && (
            <Text style={styles.progressoAntes}>
              {rota.paradas_antes} {rota.paradas_antes === 1 ? "parada" : "paradas"} antes
              da sua
            </Text>
          )}
          {rota.paradas_antes === 0 && rota.status_parada === "pendente" && (
            <Text style={[styles.progressoAntes, { color: "#2563EB" }]}>
              Voce e o proximo da rota.
            </Text>
          )}
        </View>
      )}

      {rota.endereco_entrega && (
        <View style={styles.enderecoCard}>
          <Ionicons name="location" size={20} color={CORES.primario} />
          <View style={{ flex: 1 }}>
            <Text style={styles.enderecoLabel}>Entregar em</Text>
            <Text style={styles.enderecoTexto}>{rota.endereco_entrega}</Text>
          </View>
          {podeAbrirMapa ? (
            <TouchableOpacity onPress={abrirGoogleMaps} style={styles.btnMaps}>
              <Ionicons name="map" size={16} color={CORES.primario} />
              <Text style={styles.btnMapsTexto}>Maps</Text>
            </TouchableOpacity>
          ) : null}
        </View>
      )}

      {vehiclePosition && (
        <View style={styles.mapaCard}>
          <Text style={styles.mapaTitulo}>Rota ao vivo do entregador</Text>
          <Text style={styles.mapaSubtitulo}>
            {gpsTempoReal
              ? "Atualizando com o GPS corrente do celular do entregador."
              : "Exibindo o ultimo ponto confirmado da rota."}
          </Text>
          {gpsAtualizadoEm && (
            <Text style={styles.mapaLegenda}>Ultima leitura: {gpsAtualizadoEm}</Text>
          )}

          <MapView
            ref={mapRef}
            style={styles.mapa}
            initialRegion={{
              latitude: vehiclePosition.latitude,
              longitude: vehiclePosition.longitude,
              latitudeDelta: 0.01,
              longitudeDelta: 0.01,
            }}
          >
            {routeTrail.length > 1 && (
              <Polyline
                coordinates={routeTrail}
                strokeColor="#2563EB"
                strokeWidth={4}
                lineDashPattern={[1]}
              />
            )}
            <Marker coordinate={vehiclePosition} anchor={{ x: 0.5, y: 0.5 }} flat>
              <View style={styles.markerWrap}>
                <View style={styles.markerPulse} />
                <View style={styles.markerIconCircle}>
                  <Ionicons
                    name="car-sport"
                    size={14}
                    color="#fff"
                    style={{ transform: [{ rotate: `${markerHeading}deg` }] }}
                  />
                </View>
              </View>
            </Marker>
          </MapView>
        </View>
      )}

      {rota.data_entrega && (
        <View style={styles.entregueCard}>
          <Ionicons name="checkmark-circle" size={24} color="#10B981" />
          <View>
            <Text style={styles.entregueLabel}>Entregue em</Text>
            <Text style={styles.entregueData}>
              {new Date(rota.data_entrega).toLocaleString("pt-BR", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </Text>
          </View>
        </View>
      )}

      {ultimaAtualizacao && (
        <Text style={styles.atualizadoEm}>
          Atualizado as{" "}
          {ultimaAtualizacao.toLocaleTimeString("pt-BR", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </Text>
      )}

      {rota.status_parada !== "entregue" && (
        <Text style={styles.autoAtualizaAviso}>
          Atualizacao automatica a cada {intervaloMs / 1000} segundos
        </Text>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: ESPACO.md, gap: ESPACO.sm },
  loading: { flex: 1, justifyContent: "center", alignItems: "center", gap: 12 },
  loadingText: { fontSize: FONTE.normal, color: CORES.textoSecundario },
  erroText: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    textAlign: "center",
  },
  heroCard: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.lg,
    alignItems: "center",
    gap: 8,
    ...SOMBRA,
  },
  heroEmoji: { fontSize: 52 },
  heroTitulo: { fontSize: 22, fontWeight: "700", color: CORES.texto },
  heroSubtitulo: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    textAlign: "center",
  },
  entregadorCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    gap: ESPACO.sm,
    ...SOMBRA,
  },
  entregadorIcone: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: CORES.primarioClaro,
    justifyContent: "center",
    alignItems: "center",
  },
  entregadorNome: {
    fontSize: FONTE.normal,
    fontWeight: "700",
    color: CORES.texto,
  },
  entregadorLabel: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: RAIO.circulo,
  },
  statusBadgeTexto: { fontSize: FONTE.pequena, fontWeight: "600" },
  progressoCard: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    gap: 8,
    ...SOMBRA,
  },
  progressoTitulo: {
    fontSize: FONTE.normal,
    fontWeight: "600",
    color: CORES.texto,
  },
  progressoBar: {
    height: 8,
    backgroundColor: "#E5E7EB",
    borderRadius: 4,
    overflow: "hidden",
  },
  progressoPreenchido: {
    height: "100%",
    backgroundColor: CORES.primario,
    borderRadius: 4,
  },
  progressoTexto: { fontSize: FONTE.normal, color: CORES.textoSecundario },
  progressoAntes: {
    fontSize: FONTE.normal,
    fontWeight: "600",
    color: "#92400E",
  },
  enderecoCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    gap: ESPACO.sm,
    ...SOMBRA,
  },
  enderecoLabel: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  enderecoTexto: {
    fontSize: FONTE.normal,
    color: CORES.texto,
    fontWeight: "500",
  },
  btnMaps: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    padding: 8,
    backgroundColor: CORES.primarioClaro,
    borderRadius: RAIO.sm,
  },
  btnMapsTexto: {
    fontSize: FONTE.pequena,
    color: CORES.primario,
    fontWeight: "600",
  },
  mapaCard: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    gap: 8,
    ...SOMBRA,
  },
  mapaTitulo: {
    fontSize: FONTE.normal,
    fontWeight: "700",
    color: CORES.texto,
  },
  mapaSubtitulo: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
  },
  mapaLegenda: {
    fontSize: FONTE.pequena,
    color: CORES.primario,
    fontWeight: "600",
  },
  mapa: {
    width: "100%",
    height: 220,
    borderRadius: RAIO.md,
  },
  markerWrap: {
    alignItems: "center",
    justifyContent: "center",
  },
  markerPulse: {
    position: "absolute",
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: "rgba(37,99,235,0.18)",
  },
  markerIconCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: "#2563EB",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: "#fff",
  },
  palavraChaveCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: CORES.primarioClaro,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    gap: ESPACO.md,
    ...SOMBRA,
  },
  palavraChaveLabel: { fontSize: FONTE.normal, color: CORES.primario },
  palavraChaveValor: {
    fontSize: 24,
    fontWeight: "800",
    color: CORES.primario,
    letterSpacing: 2,
  },
  infoCard: {
    flexDirection: "row",
    gap: ESPACO.sm,
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    alignItems: "flex-start",
    ...SOMBRA,
  },
  infoTexto: { fontSize: FONTE.normal, color: CORES.textoSecundario, flex: 1 },
  entregueCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#D1FAE5",
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    gap: ESPACO.sm,
  },
  entregueLabel: { fontSize: FONTE.pequena, color: "#065F46" },
  entregueData: { fontSize: FONTE.normal, fontWeight: "700", color: "#065F46" },
  atualizadoEm: {
    textAlign: "center",
    fontSize: FONTE.pequena,
    color: CORES.textoClaro,
  },
  autoAtualizaAviso: {
    textAlign: "center",
    fontSize: 11,
    color: CORES.textoClaro,
    marginTop: -4,
  },
});
