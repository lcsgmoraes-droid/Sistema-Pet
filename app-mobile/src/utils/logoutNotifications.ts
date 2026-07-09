import { Alert } from "react-native";
import { unregisterPushToken } from "../services/auth.service";

type LogoutFn = () => Promise<void> | void;

async function executarLogout(logout: LogoutFn) {
  await Promise.resolve(logout());
}

async function sairSemReceberNotificacoes(logout: LogoutFn) {
  try {
    await unregisterPushToken();
    await executarLogout(logout);
  } catch {
    Alert.alert(
      "Erro",
      "Nao foi possivel desativar as notificacoes desta conta agora.",
    );
  }
}

async function sairMantendoNotificacoes(logout: LogoutFn) {
  try {
    await executarLogout(logout);
  } catch {
    Alert.alert("Erro", "Nao foi possivel sair agora.");
  }
}

export function confirmLogoutWithNotificationChoice(
  logout: LogoutFn,
  contextLabel = "conta",
) {
  Alert.alert(
    "Sair da conta",
    `Deseja continuar recebendo notificacoes da ${contextLabel} neste aparelho mesmo apos sair? Outras pessoas que usarem este aparelho poderao ver essas notificacoes.`,
    [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Nao receber",
        style: "destructive",
        onPress: () => {
          void sairSemReceberNotificacoes(logout);
        },
      },
      {
        text: "Continuar recebendo",
        onPress: () => {
          void sairMantendoNotificacoes(logout);
        },
      },
    ],
  );
}
