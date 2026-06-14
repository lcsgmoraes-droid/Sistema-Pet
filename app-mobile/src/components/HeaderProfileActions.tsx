import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Alert, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useAuthStore } from "../store/auth.store";

type HeaderProfileActionsProps = {
  logoutContextLabel: string;
  color?: string;
};

export default function HeaderProfileActions({
  logoutContextLabel,
  color = "#fff",
}: HeaderProfileActionsProps) {
  const { user, logout, selectProfile } = useAuthStore();
  const available_profiles = user?.available_profiles ?? [];
  const currentProfile = user?.selected_profile ?? user?.perfil_operacional ?? "cliente";
  const canSwitch = available_profiles.length > 1;

  const trocarPerfil = () => {
    const profileOptions = available_profiles
      .filter((profile) => profile.type !== currentProfile)
      .map((profile) => ({
        text: profile.label,
        onPress: () => {
          selectProfile(profile.type).catch(() => {
            Alert.alert("Erro", "Nao foi possivel trocar o perfil agora.");
          });
        },
      }));

    Alert.alert("Trocar perfil", "Escolha como entrar no app.", [
      ...profileOptions,
      { text: "Cancelar", style: "cancel" },
    ]);
  };

  const confirmarLogout = () => {
    Alert.alert("Sair da conta", `Deseja sair da conta de ${logoutContextLabel}?`, [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Sair",
        style: "destructive",
        onPress: () => {
          logout().catch(() => {
            Alert.alert("Erro", "Nao foi possivel sair agora.");
          });
        },
      },
    ]);
  };

  return (
    <View style={styles.container}>
      {canSwitch && (
        <TouchableOpacity
          accessibilityLabel="Trocar perfil do app"
          onPress={trocarPerfil}
          style={styles.action}
        >
          <Ionicons name="swap-horizontal-outline" size={18} color={color} />
          <Text style={[styles.text, { color }]}>Trocar</Text>
        </TouchableOpacity>
      )}
      <TouchableOpacity
        accessibilityLabel="Sair da conta"
        onPress={confirmarLogout}
        style={styles.action}
      >
        <Text style={[styles.text, { color }]}>Sair</Text>
      </TouchableOpacity>
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
