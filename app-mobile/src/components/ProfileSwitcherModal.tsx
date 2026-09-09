import React, { useEffect, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../theme";
import type { AppAccessProfile } from "../types";
import AppUpdatesEntry from "./AppUpdatesEntry";
import AppUpdatesScreen from "./AppUpdatesScreen";

type ProfileSwitcherModalProps = {
  visible: boolean;
  profiles: AppAccessProfile[];
  onSelect: (profile: AppAccessProfile) => void;
  onClose: () => void;
  showUpdates?: boolean;
  loadingProfiles?: boolean;
  profilesError?: string | null;
};

export default function ProfileSwitcherModal({
  visible,
  profiles,
  onSelect,
  onClose,
  showUpdates = false,
  loadingProfiles = false,
  profilesError,
}: ProfileSwitcherModalProps) {
  const [atualizacoes, setAtualizacoes] = useState(false);
  useEffect(() => { if (!visible) setAtualizacoes(false); }, [visible]);
  const voltar = () => { if (atualizacoes) setAtualizacoes(false); else onClose(); };
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent
      onRequestClose={voltar}
    >
      {atualizacoes ? <AppUpdatesScreen onClose={() => setAtualizacoes(false)} /> : (
        <View style={styles.overlay}>
          <Pressable
            accessibilityLabel="Fechar troca de perfil"
            style={StyleSheet.absoluteFill}
            onPress={onClose}
          />

          <View accessibilityViewIsModal style={styles.card}>
            <Text style={styles.title}>{showUpdates ? "Perfil" : "Trocar perfil"}</Text>
            {showUpdates && <AppUpdatesEntry onPress={() => setAtualizacoes(true)} />}
            <Text style={styles.subtitle}>{loadingProfiles ? "Carregando acessos…" : profilesError ?? (profiles.length ? "Escolha como entrar no app." : "Você está usando o acesso disponível para esta conta.")}</Text>

            <ScrollView
              contentContainerStyle={styles.options}
              showsVerticalScrollIndicator={profiles.length > 5}
              style={styles.optionsScroll}
            >
              {profiles.map((profile) => (
                <TouchableOpacity
                  key={profile.type}
                  accessibilityRole="button"
                  accessibilityLabel={`Entrar como ${profile.label || profile.type}`}
                  activeOpacity={0.75}
                  style={styles.option}
                  onPress={() => onSelect(profile)}
                  disabled={loadingProfiles}
                >
                  <Text style={styles.optionText}>{profile.label || profile.type}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>

            <TouchableOpacity
              accessibilityRole="button"
              activeOpacity={0.75}
              style={[styles.option, styles.cancelOption]}
              onPress={onClose}
            >
              <Text style={styles.optionText}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    alignItems: "center",
    backgroundColor: "rgba(17, 24, 39, 0.45)",
    flex: 1,
    justifyContent: "center",
    padding: ESPACO.lg,
  },
  card: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.lg,
    maxHeight: "88%",
    maxWidth: 420,
    padding: ESPACO.lg,
    width: "100%",
    ...SOMBRA,
  },
  title: {
    color: CORES.texto,
    fontSize: FONTE.titulo,
    fontWeight: "800",
  },
  subtitle: {
    color: CORES.textoSecundario,
    fontSize: FONTE.media,
    marginBottom: ESPACO.lg,
    marginTop: ESPACO.sm,
  },
  options: {
    gap: ESPACO.sm,
  },
  optionsScroll: {
    flexShrink: 1,
  },
  option: {
    alignItems: "center",
    backgroundColor: CORES.fundo,
    borderColor: CORES.borda,
    borderRadius: RAIO.circulo,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: 56,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
  },
  cancelOption: {
    marginTop: ESPACO.sm,
  },
  optionText: {
    color: CORES.texto,
    fontSize: FONTE.grande,
    fontWeight: "700",
    textAlign: "center",
  },
});
