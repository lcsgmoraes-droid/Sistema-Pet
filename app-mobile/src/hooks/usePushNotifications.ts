/**
 * Hook responsavel por registrar push notifications e configurar listeners.
 */
import * as Notifications from "expo-notifications";
import { useEffect, useRef } from "react";
import { navigateWhenReady } from "../navigation/navigationRef";
import { ensurePushNotificationsRegistered } from "../services/pushNotifications.service";
import {
  appointmentNotificationTarget,
  campaignNotificationTarget,
  recurrenceNotificationToProductId,
  stockNotificationToProductId,
} from "../utils/notificationNavigation";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export function usePushNotifications(isAuthenticated: boolean) {
  const notificationListener = useRef<Notifications.EventSubscription | null>(
    null,
  );
  const responseListener = useRef<Notifications.EventSubscription | null>(null);
  const handledResponses = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!isAuthenticated) return;

    async function setup() {
      try {
        await ensurePushNotificationsRegistered();
      } catch (_) {
        // Push e opcional e nao deve bloquear login/navegacao.
      }
    }

    setup();

    function handleNotificationResponse(response: Notifications.NotificationResponse) {
      const request = response.notification.request;
      const identifier = request.identifier;
      if (identifier && handledResponses.current.has(identifier)) return;
      if (identifier) handledResponses.current.add(identifier);

      const data = request.content.data || {};
      const produtoId =
        recurrenceNotificationToProductId(data) ??
        stockNotificationToProductId(data);
      if (produtoId) {
        navigateWhenReady("Loja", {
          screen: "DetalhesProduto",
          params: { produtoId },
        });
        return;
      }
      if (data.source === "order") {
        navigateWhenReady("Pedidos");
        return;
      }
      const appointmentTarget = appointmentNotificationTarget(data);
      if (appointmentTarget) {
        navigateWhenReady(appointmentTarget.route, appointmentTarget.params);
        return;
      }
      const campaignTarget = campaignNotificationTarget(data);
      if (campaignTarget) {
        navigateWhenReady(campaignTarget.route, campaignTarget.params);
        return;
      }
      if (data.source !== "app-vet") return;
      if (data.kind === "procedimento") {
        navigateWhenReady("VetProcedimentos");
      } else if (data.kind === "agendamento") {
        navigateWhenReady("VetAgenda");
      }
    }

    notificationListener.current =
      Notifications.addNotificationReceivedListener((_notification) => {
        // A notificacao ja aparece pela config do setNotificationHandler acima.
      });

    responseListener.current =
      Notifications.addNotificationResponseReceivedListener(handleNotificationResponse);

    Notifications.getLastNotificationResponseAsync()
      .then((response) => {
        if (response) handleNotificationResponse(response);
      })
      .catch(() => {});

    return () => {
      notificationListener.current?.remove();
      responseListener.current?.remove();
    };
  }, [isAuthenticated]);
}
