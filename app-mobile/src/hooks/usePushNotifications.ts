/**
 * Hook responsavel por registrar push notifications e configurar listeners.
 */
import * as Notifications from "expo-notifications";
import { useEffect, useRef } from "react";
import { navigateWhenReady } from "../navigation/navigationRef";
import { ensurePushNotificationsRegistered } from "../services/pushNotifications.service";

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

    notificationListener.current =
      Notifications.addNotificationReceivedListener((_notification) => {
        // A notificacao ja aparece pela config do setNotificationHandler acima.
      });

    responseListener.current =
      Notifications.addNotificationResponseReceivedListener((response) => {
        const data = response.notification.request.content.data || {};
        if (data.source === "order") {
          navigateWhenReady("Pedidos");
          return;
        }
        if (data.source !== "app-vet") return;
        if (data.kind === "procedimento") {
          navigateWhenReady("VetProcedimentos");
        } else if (data.kind === "agendamento") {
          navigateWhenReady("VetAgenda");
        }
      });

    return () => {
      notificationListener.current?.remove();
      responseListener.current?.remove();
    };
  }, [isAuthenticated]);
}
