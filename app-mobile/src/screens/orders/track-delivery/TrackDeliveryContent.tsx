import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import MapView from "react-native-maps";

import { CORES } from "../../../theme";
import { TrackDeliveryMap } from "./TrackDeliveryMap";
import { trackDeliveryStyles as styles } from "./TrackDeliveryStyles";
import {
  Coordenada,
  formatDataEntrega,
  formatGpsAtualizadoEm,
  formatHoraAtualizacao,
  RastreioData,
  STATUS_PARADA,
  STATUS_ROTA,
} from "./TrackDeliveryUtils";

type TrackDeliveryContentProps = {
  dados: RastreioData | null;
  carregando: boolean;
  refreshing: boolean;
  ultimaAtualizacao: Date | null;
  intervaloMs: number;
  vehiclePosition: Coordenada | null;
  routeTrail: Coordenada[];
  markerHeading: number;
  mapRef: React.MutableRefObject<MapView | null>;
  onOpenMaps: () => void;
  onRefresh: () => void;
};

export function TrackDeliveryContent({
  dados,
  carregando,
  refreshing,
  ultimaAtualizacao,
  intervaloMs,
  vehiclePosition,
  routeTrail,
  markerHeading,
  mapRef,
  onOpenMaps,
  onRefresh,
}: TrackDeliveryContentProps) {
  const refreshControl = (
    <RefreshControl
      refreshing={refreshing}
      onRefresh={onRefresh}
      tintColor={CORES.primario}
    />
  );

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
        <Text style={styles.erroEmoji}>😕</Text>
        <Text style={styles.erroText}>Não foi possível carregar o rastreio.</Text>
      </View>
    );
  }

  if (!dados.tem_entrega) {
    return (
      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={refreshControl}
      >
        <View style={styles.heroCard}>
          <Text style={styles.heroEmoji}>🏪</Text>
          <Text style={styles.heroTitulo}>Retirada na loja</Text>
          <Text style={styles.heroSubtitulo}>{dados.mensagem}</Text>
        </View>

        {dados.palavra_chave_retirada && (
          <View style={styles.palavraChaveCard}>
            <Ionicons name="key" size={28} color={CORES.primario} />
            <View style={styles.flex1}>
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
            Apresente essa tela ou fale a palavra-chave ao atendente para retirar
            seu pedido.
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
        refreshControl={refreshControl}
      >
        <View style={styles.heroCard}>
          <Text style={styles.heroEmoji}>📦</Text>
          <Text style={styles.heroTitulo}>Pedido recebido</Text>
          <Text style={styles.heroSubtitulo}>{dados.mensagem}</Text>
        </View>

        <View style={[styles.infoCard, styles.infoCardSpaced]}>
          <Ionicons
            name="time-outline"
            size={20}
            color={CORES.textoSecundario}
          />
          <Text style={styles.infoTexto}>
            Assim que o entregador sair com seu pedido, o acompanhamento aparece
            aqui.
          </Text>
        </View>

        {ultimaAtualizacao && (
          <Text style={styles.atualizadoEm}>
            Atualizado às {formatHoraAtualizacao(ultimaAtualizacao)}
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
  const gpsAtualizadoEm = formatGpsAtualizadoEm(
    rota.ultima_posicao_gps?.atualizada_em,
  );

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={refreshControl}
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
        <View style={styles.flex1}>
          <Text style={styles.entregadorNome}>{rota.entregador_nome}</Text>
          <Text style={styles.entregadorLabel}>Entregador responsável</Text>
        </View>
        <View
          style={[
            styles.statusBadge,
            { backgroundColor: `${statusRotaCfg.cor}22` },
          ]}
        >
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
            {rota.entregues} de {rota.total_paradas} entregas concluídas
          </Text>
          {rota.paradas_antes > 0 && (
            <Text style={styles.progressoAntes}>
              {rota.paradas_antes}{" "}
              {rota.paradas_antes === 1 ? "parada" : "paradas"} antes da sua
            </Text>
          )}
          {rota.paradas_antes === 0 && rota.status_parada === "pendente" && (
            <Text style={[styles.progressoAntes, { color: "#0F5F66" }]}>
              Você é o próximo da rota.
            </Text>
          )}
        </View>
      )}

      {rota.endereco_entrega && (
        <View style={styles.enderecoCard}>
          <Ionicons name="location" size={20} color={CORES.primario} />
          <View style={styles.flex1}>
            <Text style={styles.enderecoLabel}>Entregar em</Text>
            <Text style={styles.enderecoTexto}>{rota.endereco_entrega}</Text>
          </View>
          {podeAbrirMapa ? (
            <TouchableOpacity onPress={onOpenMaps} style={styles.btnMaps}>
              <Ionicons name="map" size={16} color={CORES.primario} />
              <Text style={styles.btnMapsTexto}>Maps</Text>
            </TouchableOpacity>
          ) : null}
        </View>
      )}

      <TrackDeliveryMap
        gpsAtualizadoEm={gpsAtualizadoEm}
        gpsTempoReal={gpsTempoReal}
        mapRef={mapRef}
        markerHeading={markerHeading}
        routeTrail={routeTrail}
        vehiclePosition={vehiclePosition}
      />

      {rota.data_entrega && (
        <View style={styles.entregueCard}>
          <Ionicons name="checkmark-circle" size={24} color="#10B981" />
          <View>
            <Text style={styles.entregueLabel}>Entregue em</Text>
            <Text style={styles.entregueData}>
              {formatDataEntrega(rota.data_entrega)}
            </Text>
          </View>
        </View>
      )}

      {ultimaAtualizacao && (
        <Text style={styles.atualizadoEm}>
          Atualizado às {formatHoraAtualizacao(ultimaAtualizacao)}
        </Text>
      )}

      {rota.status_parada !== "entregue" && (
        <Text style={styles.autoAtualizaAviso}>
          Atualização automática a cada {intervaloMs / 1000} segundos
        </Text>
      )}
    </ScrollView>
  );
}
