import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import { registerPushToken } from "./auth.service";

export type PushRegistrationStatus =
  | "registered"
  | "expo_go"
  | "permission_denied"
  | "token_error"
  | "backend_error";

export interface PushRegistrationResult {
  status: PushRegistrationStatus;
  message: string;
  tokenPreview?: string;
  permissionStatus?: Notifications.PermissionStatus | string;
  canAskAgain?: boolean;
}

const isExpoGo = Constants.appOwnership === "expo";

async function ensureAndroidChannel() {
  if (Platform.OS !== "android") return;
  await Notifications.setNotificationChannelAsync("default", {
    name: "Padrao",
    importance: Notifications.AndroidImportance.MAX,
    vibrationPattern: [0, 250, 250, 250],
    lightColor: "#FF6B35",
  });
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "Nao foi possivel ativar notificacoes neste aparelho.";
}

export async function ensurePushNotificationsRegistered(): Promise<PushRegistrationResult> {
  await ensureAndroidChannel();

  if (isExpoGo) {
    return {
      status: "expo_go",
      message: "Push remoto nao funciona no Expo Go. Use o APK de teste instalado.",
    };
  }

  const currentPermission = await Notifications.getPermissionsAsync();
  let finalStatus = currentPermission.status;
  let canAskAgain = currentPermission.canAskAgain;

  if (finalStatus !== "granted") {
    const requested = await Notifications.requestPermissionsAsync();
    finalStatus = requested.status;
    canAskAgain = requested.canAskAgain;
  }

  if (finalStatus !== "granted") {
    return {
      status: "permission_denied",
      message: canAskAgain
        ? "Permissao de notificacoes nao liberada."
        : "Permissao de notificacoes bloqueada nas configuracoes do aparelho.",
      permissionStatus: finalStatus,
      canAskAgain,
    };
  }

  const projectId =
    Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;

  if (!projectId) {
    return {
      status: "token_error",
      message: "Projeto Expo sem projectId para gerar token de push.",
    };
  }

  let tokenData: Notifications.ExpoPushToken;
  try {
    tokenData = await Notifications.getExpoPushTokenAsync({ projectId });
  } catch (error) {
    return {
      status: "token_error",
      message: errorMessage(error),
    };
  }

  try {
    await registerPushToken(tokenData.data);
  } catch (error) {
    return {
      status: "backend_error",
      message: errorMessage(error),
      tokenPreview: `${tokenData.data.slice(0, 18)}...`,
    };
  }

  return {
    status: "registered",
    message: "Notificacoes ativadas.",
    tokenPreview: `${tokenData.data.slice(0, 18)}...`,
  };
}
