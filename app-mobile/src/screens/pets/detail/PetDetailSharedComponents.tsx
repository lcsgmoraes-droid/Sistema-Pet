import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Text, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import { petDetailStyles as styles } from "./PetDetailStyles";

export function PetDetailSection({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitulo}>{titulo}</Text>
      {children}
    </View>
  );
}

export function PetDetailResumoCard({ titulo, valor, cor }: { titulo: string; valor: string; cor: string }) {
  return (
    <View style={[styles.resumoCard, { borderColor: cor }]}>
      <Text style={[styles.resumoValor, { color: cor }]}>{valor}</Text>
      <Text style={styles.resumoTitulo}>{titulo}</Text>
    </View>
  );
}

export function PetDetailQuickNavButton({
  icon,
  label,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={styles.quickNavButton} onPress={onPress}>
      <Ionicons name={icon} size={16} color={CORES.primario} />
      <Text style={styles.quickNavLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

