import React from "react";
import { ActivityIndicator, Text, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import { profileStyles as styles } from "./ProfileStyles";

export function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.campo}>
      <Text style={styles.campoLabel}>{label}</Text>
      {children}
    </View>
  );
}

export function InfoRow({ label, valor }: { label: string; valor?: string | null }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValor}>{valor || "-"}</Text>
    </View>
  );
}

export function SaveButton({
  label,
  loading,
  onPress,
}: {
  label: string;
  loading: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={[styles.botaoSalvar, loading && { opacity: 0.7 }]}
      onPress={onPress}
      disabled={loading}
    >
      {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.botaoSalvarTexto}>{label}</Text>}
    </TouchableOpacity>
  );
}

export function SectionHeader({
  title,
  editing,
  empty,
  onEdit,
  onCancel,
}: {
  title: string;
  editing: boolean;
  empty?: boolean;
  onEdit: () => void;
  onCancel: () => void;
}) {
  return (
    <View style={styles.secaoHeader}>
      <Text style={styles.secaoTitulo}>{title}</Text>
      {!editing ? (
        <TouchableOpacity onPress={onEdit}>
          <Text style={styles.editarTexto}>{empty ? "Cadastrar" : "Editar"}</Text>
        </TouchableOpacity>
      ) : (
        <TouchableOpacity onPress={onCancel}>
          <Text style={[styles.editarTexto, { color: CORES.erro }]}>Cancelar</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}
