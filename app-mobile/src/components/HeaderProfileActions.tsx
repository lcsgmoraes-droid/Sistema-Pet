import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, Alert, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import * as Notifications from "expo-notifications";
import * as AuthService from "../services/auth.service";
import { ensurePushNotificationsRegistered } from "../services/pushNotifications.service";
import { useAuthStore } from "../store/auth.store";
import { confirmLogoutWithNotificationChoice } from "../utils/logoutNotifications";

type HeaderProfileActionsProps = {
  logoutContextLabel: string;
  color?: string;
  showLogout?: boolean;
};

export default function HeaderProfileActions({
  logoutContextLabel,
  color = "#fff",
  showLogout = true,
}: HeaderProfileActionsProps) {
  const { user, logout, selectProfile, updateUser } = useAuthStore();
  const [loadingProfiles, setLoadingProfiles] = useState(false);
  const [activatingNotifications, setActivatingNotifications] = useState(false);
  const [notificacoesAtivadas, setNotificacoesAtivadas] = useState(false);
  const available_profiles = user?.available_profiles ?? [];
  const currentProfile = user?.selected_profile ?? user?.perfil_operacional ?? "cliente";
  const canSwitch = available_profiles.length > 1;

  useEffect(() => {
    let mounted = true;

    Notifications.getPermissionsAsync()
      .then((permission) => {
        if (mounted) setNotificacoesAtivadas(permission.status === "granted");
      })
      .catch(() => {
        if (mounted) setNotificacoesAtivadas(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const trocarPerfil = async () => {
    setLoadingProfiles(true);
    try {
      const freshUser = await AuthService.getProfile();
      updateUser(freshUser);
      const freshProfiles = freshUser.available_profiles ?? [];
      const freshCurrentProfile = freshUser.selected_profile ?? freshUser.perfil_operacional ?? currentProfile;
      const profileOptions = freshProfiles
        .filter((profile) => profile.type !== freshCurrentProfile)
        .map((profile) => ({
          text: profile.label,
          onPress: () => {
            selectProfile(profile.type).catch(() => {
              Alert.alert("Erro", "Nao foi possivel trocar o perfil agora.");
            });
          },
        }));

      if (profileOptions.length === 0) {
        Alert.alert("Trocar perfil", "Sem outros acessos liberados para esta conta.");
        return;
      }

      Alert.alert("Trocar perfil", "Escolha como entrar no app.", [
        ...profileOptions,
        { text: "Cancelar", style: "cancel" },
      ]);
    } catch {
      Alert.alert("Erro", "Nao foi possivel carregar os acessos agora.");
    } finally {
      setLoadingProfiles(false);
    }
  };

  const confirmarLogout = () => {
    confirmLogoutWithNotificationChoice(logout, logoutContextLabel);
  };

  const ativarNotificacoes = async () => {
    setActivatingNotifications(true);
    try {
      const result = await ensurePushNotificationsRegistered();
      setNotificacoesAtivadas(result.status === "registered" || result.permissionStatus === "granted");
      Alert.alert("Notificacoes", result.message);
    } catch (err: any) {
      setNotificacoesAtivadas(false);
      Alert.alert(
        "Notificacoes",
        err?.message || "Nao foi possivel ativar notificacoes.",
      );
    } finally {
      setActivatingNotifications(false);
    }
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity
        accessibilityLabel="Ativar notificacoes"
        onPress={ativarNotificacoes}
        style={styles.action}
        disabled={activatingNotifications}
      >
        {activatingNotifications ? (
          <ActivityIndicator color={color} size="small" />
        ) : (
          <Ionicons name={notificacoesAtivadas ? "notifications" : "notifications-outline"} size={18} color={color} />
        )}
        <Text style={[styles.text, { color }]}>Notif.</Text>
      </TouchableOpacity>
      {canSwitch && (
        <TouchableOpacity
          accessibilityLabel="Trocar perfil do app"
          onPress={trocarPerfil}
          style={styles.action}
          disabled={loadingProfiles}
        >
          <Ionicons name="swap-horizontal-outline" size={18} color={color} />
          <Text style={[styles.text, { color }]}>
            {loadingProfiles ? "..." : "Trocar"}
          </Text>
        </TouchableOpacity>
      )}
      {showLogout && (
        <TouchableOpacity
          accessibilityLabel="Sair da conta"
          onPress={confirmarLogout}
          style={styles.action}
        >
          <Text style={[styles.text, { color }]}>Sair</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    flexDirection: "row",
    gap: 14,
  },
  action: {
    alignItems: "center",
    flexDirection: "row",
    gap: 4,
    minHeight: 36,
  },
  text: {
    fontWeight: "800",
  },
});
