/**
 * Hook responsável por:
 * 1. Pedir permissão de notificação ao usuário
 * 2. Obter o Expo Push Token do dispositivo
 * 3. Enviar o token ao backend para ser salvo no perfil do usuário
 * 4. Configurar listeners para exibir notificações quando o app está aberto
 */
import { useEffect, useRef } from 'react';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import Constants from 'expo-constants';
import { registerPushToken } from '../services/auth.service';

// Detecta se está rodando no Expo Go (SDK 53+ não suporta push remoto no Expo Go)
const isExpoGo = Constants.appOwnership === 'expo';

// Configuração de como as notificações aparecem quando o app está ABERTO
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export function usePushNotifications(isAuthenticated: boolean) {
  const notificationListener = useRef<Notifications.EventSubscription>();
  const responseListener = useRef<Notifications.EventSubscription>();

  useEffect(() => {
    if (!isAuthenticated) return;

    async function setup() {
      try {
        // Android precisa de canal de notificação
        if (Platform.OS === 'android') {
          await Notifications.setNotificationChannelAsync('default', {
            name: 'Padrão',
            importance: Notifications.AndroidImportance.MAX,
            vibrationPattern: [0, 250, 250, 250],
            lightColor: '#FF6B35',
          });
        }

        // Expo Go a partir do SDK 53 não suporta push remoto.
        // Pula o registro do token silenciosamente.
        if (isExpoGo) return;

        // Solicitar permissão
        const { status: existingStatus } = await Notifications.getPermissionsAsync();
        let finalStatus = existingStatus;

        if (existingStatus !== 'granted') {
          const { status } = await Notifications.requestPermissionsAsync();
          finalStatus = status;
        }

        if (finalStatus !== 'granted') return;

        // Obter o Expo Push Token
        const projectId =
          Constants.expoConfig?.extra?.eas?.projectId ??
          Constants.easConfig?.projectId;

        const tokenData = projectId
          ? await Notifications.getExpoPushTokenAsync({ projectId })
          : await Notifications.getExpoPushTokenAsync();

        await registerPushToken(tokenData.data);
      } catch (_) {
        // Silencioso — push é opcional
      }
    }

    setup();

    // Listener: notificação recebida com app ABERTO (exibe automaticamente)
    notificationListener.current = Notifications.addNotificationReceivedListener(
      (_notification) => {
        // A notificação já aparece pela config do setNotificationHandler acima
      }
    );

    // Listener: usuário tocou na notificação
    responseListener.current = Notifications.addNotificationResponseReceivedListener(
      (_response) => {
        // Espaço para futura navegação ao tocar na notificação
      }
    );

    return () => {
      notificationListener.current?.remove();
      responseListener.current?.remove();
    };
  }, [isAuthenticated]);
}
