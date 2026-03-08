import { Ionicons } from "@expo/vector-icons";
import { useRoute } from "@react-navigation/native";
import React, { useCallback, useEffect, useState } from "react";
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
import MapView, { Marker } from "react-native-maps";
import api from "../../services/api";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

const STATUS_ROTA: Record<
  string,
  { emoji: string; label: string; cor: string }
> = {
  pendente: { emoji: "📦", label: "Preparando", cor: "#F59E0B" },
  em_andamento: { emoji: "🛵", label: "Em rota", cor: "#3B82F6" },
  em_rota: { emoji: "🛵", label: "A caminho", cor: "#3B82F6" },
  concluida: { emoji: "✅", label: "Entregue", cor: "#10B981" },
  entregue: { emoji: "✅", label: "Entregue", cor: "#10B981" },
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
    label: "A caminho!",
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
    ultima_posicao_gps?: { lat: number; lon: number };
  };
}

export default function TrackDeliveryScreen() {
  const route = useRoute<any>();
  const { pedidoId } = route.params;

  const [dados, setDados] = useState<RastreioData | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState<Date | null>(null);
  const [intervaloMs, setIntervaloMs] = useState(10_000);

  const carregar = useCallback(async () => {
    try {
      const resp = await api.get(`/app/pedidos/${pedidoId}/rastreio`);
      setDados(resp.data);
      setUltimaAtualizacao(new Date());
    } catch {
      // silencioso — mostra o que tem
    } finally {
      setCarregando(false);
      setRefreshing(false);
    }
  }, [pedidoId]);

  useEffect(() => {
    const paradasAntes = dados?.rota?.paradas_antes ?? 99;
    setIntervaloMs(paradasAntes <= 1 ? 5_000 : 10_000);
  }, [dados?.rota?.paradas_antes]);

  useEffect(() => {
    carregar();
    // Polling adaptativo: 10s quando longe, 5s quando perto.
    const interval = setInterval(() => {
      if (dados?.rota?.status_parada !== "entregue") {
        carregar();
      }
    }, intervaloMs);
    return () => clearInterval(interval);
  }, [carregar, dados?.rota?.status_parada, intervaloMs]);

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
        <Text style={styles.erroText}>
          Não foi possível carregar o rastreio
        </Text>
      </View>
    );
  }

  // Pedido sem entrega (retirada na loja)
  if (!dados.tem_entrega) {
    return (
      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              carregar();
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
              <Text style={styles.palavraChaveLabel}>
                Fale essa palavra no caixa:
              </Text>
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
            Apresente essa tela ou fale a palavra-chave ao atendente para
            retirar seu pedido.
          </Text>
        </View>
      </ScrollView>
    );
  }

  const rota = dados.rota;

  // Pedido pago mas sem rota ainda
  if (!rota) {
    return (
      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              carregar();
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
            Assim que o entregador sair com seu pedido, você poderá acompanhar
            aqui.
          </Text>
        </View>

        {ultimaAtualizacao && (
          <Text style={styles.atualizadoEm}>
            🔄 Atualizado às{" "}
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

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            carregar();
          }}
          tintColor={CORES.primario}
        />
      }
    >
      {/* Hero status */}
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

      {/* Entregador */}
      <View style={styles.entregadorCard}>
        <View style={styles.entregadorIcone}>
          <Ionicons name="bicycle" size={24} color={CORES.primario} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.entregadorNome}>{rota.entregador_nome}</Text>
          <Text style={styles.entregadorLabel}>Entregador responsável</Text>
        </View>
        <View
          style={[
            styles.statusBadge,
            { backgroundColor: statusRotaCfg.cor + "22" },
          ]}
        >
          <Text style={[styles.statusBadgeTexto, { color: statusRotaCfg.cor }]}>
            {statusRotaCfg.emoji} {statusRotaCfg.label}
          </Text>
        </View>
      </View>

      {/* Progresso da rota */}
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
            {rota.entregues} de {rota.total_paradas} entregas concluídas
          </Text>
          {rota.paradas_antes > 0 && (
            <Text style={styles.progressoAntes}>
              📍 {rota.paradas_antes}{" "}
              {rota.paradas_antes === 1 ? "parada" : "paradas"} antes da sua
            </Text>
          )}
          {rota.paradas_antes === 0 && rota.status_parada === "pendente" && (
            <Text style={[styles.progressoAntes, { color: "#2563EB" }]}>
              🎯 Você é o próximo!
            </Text>
          )}
        </View>
      )}

      {/* Endereço de entrega */}
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

      {!!rota.ultima_posicao_gps && (
        <View style={styles.mapaCard}>
          <Text style={styles.mapaTitulo}>Posição atual do entregador</Text>
          <MapView
            style={styles.mapa}
            initialRegion={{
              latitude: rota.ultima_posicao_gps.lat,
              longitude: rota.ultima_posicao_gps.lon,
              latitudeDelta: 0.01,
              longitudeDelta: 0.01,
            }}
            region={{
              latitude: rota.ultima_posicao_gps.lat,
              longitude: rota.ultima_posicao_gps.lon,
              latitudeDelta: 0.01,
              longitudeDelta: 0.01,
            }}
          >
            <Marker
              coordinate={{
                latitude: rota.ultima_posicao_gps.lat,
                longitude: rota.ultima_posicao_gps.lon,
              }}
              title="Entregador"
              description="Posição atual"
            />
          </MapView>
        </View>
      )}

      {/* Data de entrega */}
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
          🔄 Atualizado às{" "}
          {ultimaAtualizacao.toLocaleTimeString("pt-BR", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </Text>
      )}

      {rota.status_parada !== "entregue" && (
        <Text style={styles.autoAtualizaAviso}>
          Atualizado automaticamente a cada {intervaloMs / 1000} segundos
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
    fontWeight: "600",
    color: CORES.texto,
  },
  mapa: {
    width: "100%",
    height: 220,
    borderRadius: RAIO.md,
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
