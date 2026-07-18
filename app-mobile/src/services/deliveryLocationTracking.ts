import * as Location from "expo-location";
import * as SecureStore from "expo-secure-store";
import * as TaskManager from "expo-task-manager";

import api from "./api";


const DELIVERY_LOCATION_TASK = "corepet-entrega-localizacao-ativa";
const ACTIVE_ROUTE_KEY = "active_delivery_route_id";

type DeliveryLocationTaskData = {
  locations?: Location.LocationObject[];
};

if (!TaskManager.isTaskDefined(DELIVERY_LOCATION_TASK)) {
  TaskManager.defineTask<DeliveryLocationTaskData>(
    DELIVERY_LOCATION_TASK,
    async ({ data, error }) => {
      if (error || !data?.locations?.length) return;

      const rotaId = await SecureStore.getItemAsync(ACTIVE_ROUTE_KEY);
      const localizacao = data.locations[data.locations.length - 1];
      if (!rotaId || !localizacao?.coords) return;

      try {
        await api.post(
          `/ecommerce/entregador/rotas/${rotaId}/atualizar-localizacao`,
          {},
          {
            params: {
              lat: localizacao.coords.latitude,
              lon: localizacao.coords.longitude,
            },
          },
        );
      } catch {
        // Rede pode oscilar durante a rota; o proximo ponto tenta novamente.
      }
    },
  );
}

export async function iniciarRastreamentoEntregaEmSegundoPlano(
  rotaId: number | string,
): Promise<boolean> {
  try {
    if (!(await Location.isBackgroundLocationAvailableAsync())) return false;

    const foreground = await Location.requestForegroundPermissionsAsync();
    if (!foreground.granted) return false;

    const background = await Location.requestBackgroundPermissionsAsync();
    if (!background.granted) return false;

    const rotaIdTexto = String(rotaId);
    const rotaAtiva = await SecureStore.getItemAsync(ACTIVE_ROUTE_KEY);
    const iniciou = await Location.hasStartedLocationUpdatesAsync(
      DELIVERY_LOCATION_TASK,
    );
    if (iniciou && rotaAtiva === rotaIdTexto) return true;
    if (iniciou) {
      await Location.stopLocationUpdatesAsync(DELIVERY_LOCATION_TASK);
    }

    await SecureStore.setItemAsync(ACTIVE_ROUTE_KEY, rotaIdTexto);
    await Location.startLocationUpdatesAsync(DELIVERY_LOCATION_TASK, {
      accuracy: Location.Accuracy.High,
      timeInterval: 5000,
      distanceInterval: 10,
      deferredUpdatesInterval: 5000,
      deferredUpdatesDistance: 10,
      pausesUpdatesAutomatically: false,
      showsBackgroundLocationIndicator: true,
      foregroundService: {
        notificationTitle: "CorePet - rota em andamento",
        notificationBody: "Compartilhando a localizacao durante as entregas.",
        notificationColor: "#0F5F66",
        killServiceOnDestroy: false,
      },
    });
    return true;
  } catch {
    return false;
  }
}

export async function pararRastreamentoEntregaEmSegundoPlano(
  rotaId?: number | string,
): Promise<void> {
  try {
    const rotaAtiva = await SecureStore.getItemAsync(ACTIVE_ROUTE_KEY);
    if (rotaId != null && rotaAtiva && rotaAtiva !== String(rotaId)) return;

    if (await Location.hasStartedLocationUpdatesAsync(DELIVERY_LOCATION_TASK)) {
      await Location.stopLocationUpdatesAsync(DELIVERY_LOCATION_TASK);
    }
    await SecureStore.deleteItemAsync(ACTIVE_ROUTE_KEY);
  } catch {
    // A finalizacao da rota nao pode falhar por uma limpeza local do GPS.
  }
}
