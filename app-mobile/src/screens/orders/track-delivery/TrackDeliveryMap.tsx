import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Text, View } from "react-native";
import MapView, { Marker, Polyline } from "react-native-maps";

import { trackDeliveryStyles as styles } from "./TrackDeliveryStyles";
import { Coordenada } from "./TrackDeliveryUtils";

type TrackDeliveryMapProps = {
  gpsAtualizadoEm: string | null;
  gpsTempoReal: boolean;
  mapRef: React.MutableRefObject<MapView | null>;
  markerHeading: number;
  routeTrail: Coordenada[];
  vehiclePosition: Coordenada | null;
};

export function TrackDeliveryMap({
  gpsAtualizadoEm,
  gpsTempoReal,
  mapRef,
  markerHeading,
  routeTrail,
  vehiclePosition,
}: TrackDeliveryMapProps) {
  if (!vehiclePosition) return null;

  return (
    <View style={styles.mapaCard}>
      <Text style={styles.mapaTitulo}>Rota ao vivo do entregador</Text>
      <Text style={styles.mapaSubtitulo}>
        {gpsTempoReal
          ? "Atualizando com o GPS corrente do celular do entregador."
          : "Exibindo o último ponto confirmado da rota."}
      </Text>
      {gpsAtualizadoEm && (
        <Text style={styles.mapaLegenda}>Última leitura: {gpsAtualizadoEm}</Text>
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
            strokeColor="#0F5F66"
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
  );
}
