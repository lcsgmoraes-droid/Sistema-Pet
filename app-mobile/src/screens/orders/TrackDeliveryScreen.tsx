import { useRoute } from "@react-navigation/native";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Linking } from "react-native";
import MapView from "react-native-maps";

import api from "../../services/api";
import { TrackDeliveryContent } from "./track-delivery/TrackDeliveryContent";
import {
  appendTrailPoint,
  buildGoogleMapsUrl,
  computeBearing,
  Coordenada,
  easeInOut,
  getTrackingIntervalMs,
  RastreioData,
  samePoint,
} from "./track-delivery/TrackDeliveryUtils";

export default function TrackDeliveryScreen() {
  const route = useRoute<any>();
  const { pedidoId } = route.params;

  const [dados, setDados] = useState<RastreioData | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState<Date | null>(null);
  const [intervaloMs, setIntervaloMs] = useState(6_000);
  const [vehiclePosition, setVehiclePosition] = useState<Coordenada | null>(
    null,
  );
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
    setIntervaloMs(getTrackingIntervalMs(dados?.rota?.paradas_antes));
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
          startPoint.latitude +
          (nextPoint.latitude - startPoint.latitude) * eased,
        longitude:
          startPoint.longitude +
          (nextPoint.longitude - startPoint.longitude) * eased,
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

  function handleRefresh() {
    setRefreshing(true);
    void carregar();
  }

  function abrirGoogleMaps() {
    const url = buildGoogleMapsUrl(
      dados?.rota?.ultima_posicao_gps,
      dados?.rota?.endereco_entrega,
    );
    if (url) void Linking.openURL(url);
  }

  return (
    <TrackDeliveryContent
      dados={dados}
      carregando={carregando}
      refreshing={refreshing}
      ultimaAtualizacao={ultimaAtualizacao}
      intervaloMs={intervaloMs}
      vehiclePosition={vehiclePosition}
      routeTrail={routeTrail}
      markerHeading={markerHeading}
      mapRef={mapRef}
      onOpenMaps={abrirGoogleMaps}
      onRefresh={handleRefresh}
    />
  );
}
