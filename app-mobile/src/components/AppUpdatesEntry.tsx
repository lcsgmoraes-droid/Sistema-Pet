import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { Modal, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useAppUpdatesContext } from "./AppUpdatesProvider";
import AppUpdatesScreen from "./AppUpdatesScreen";

export default function AppUpdatesEntry({ onPress }: { onPress?: () => void }) {
  const update = useAppUpdatesContext();
  const [aberto, setAberto] = useState(false);
  if (!update.enabled) return null;
  const abrir = () => {
    if (onPress) onPress();
    else setAberto(true);
    void update.verificar(true);
  };
  const fechar = () => { if (!update.reiniciando) setAberto(false); };
  return (
    <>
      <TouchableOpacity accessibilityRole="button" accessibilityLabel="Atualizações do app" onPress={abrir} style={styles.entrada}>
        <Ionicons name="sync-outline" size={22} color="#0f766e" />
        <View style={styles.textos}>
          <Text style={styles.titulo}>Atualizações do app</Text>
          {update.pronto && <Text style={styles.aviso}>Atualização pronta para aplicar</Text>}
        </View>
        <Ionicons name="chevron-forward" size={20} color="#64748b" />
      </TouchableOpacity>
      {!onPress && <Modal visible={aberto} animationType="slide" onRequestClose={fechar}>
        <AppUpdatesScreen onClose={fechar} />
      </Modal>}
    </>
  );
}

const styles = StyleSheet.create({
  entrada: { minHeight: 56, flexDirection: "row", alignItems: "center", gap: 12, padding: 16, marginVertical: 8, borderWidth: 1, borderColor: "#e2e8f0", borderRadius: 12, backgroundColor: "#fff" },
  textos: { flex: 1, gap: 4 },
  titulo: { fontSize: 16, fontWeight: "700", color: "#0f766e" },
  aviso: { fontSize: 13, color: "#15803d" },
});
