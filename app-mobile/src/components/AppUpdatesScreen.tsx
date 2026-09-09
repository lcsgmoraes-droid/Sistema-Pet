import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { ActivityIndicator, Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAppUpdatesContext } from "./AppUpdatesProvider";

export default function AppUpdatesScreen({ onClose }: { onClose: () => void }) {
  const update = useAppUpdatesContext();

  if (!update.enabled) return null;

  const confirmarAplicacao = () => {
    Alert.alert("Aplicar atualização?", "O app será reiniciado. Salve qualquer alteração em andamento antes de continuar.", [
      { text: "Agora não", style: "cancel" },
      { text: "Reiniciar e aplicar", onPress: () => { void update.aplicar(); } },
    ]);
  };

  return (
    <SafeAreaView style={styles.tela}>
      <View style={styles.cabecalho}>
        <Text style={styles.titulo}>Atualizações do app</Text>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Fechar atualizações" disabled={update.reiniciando} onPress={onClose} style={styles.fechar}>
          <Ionicons name="close" size={26} color="#0f172a" />
        </TouchableOpacity>
      </View>
      <ScrollView contentContainerStyle={styles.conteudo}>
        <View style={styles.card}>
          {update.ocupado && <ActivityIndicator color="#0f766e" size="large" />}
          <Text accessibilityLiveRegion="polite" style={styles.status}>{update.status}</Text>
          <Text style={styles.descricao}>{update.pronto
            ? "A atualização já foi baixada. Você pode aplicá-la quando terminar o que está fazendo."
            : "O CorePet busca novidades ao abrir e ao voltar para o app. Você também pode verificar por aqui."}</Text>
          {update.erro && <Text accessibilityRole="alert" style={styles.erro}>{update.erro}</Text>}
          <TouchableOpacity accessibilityRole="button" disabled={update.ocupado} onPress={update.pronto ? confirmarAplicacao : () => { void update.verificar(true); }} style={[styles.botao, update.ocupado && styles.desabilitado]}>
            <Text style={styles.textoBotao}>{update.pronto ? "Aplicar atualização" : "Verificar agora"}</Text>
          </TouchableOpacity>
          {update.pronto && <TouchableOpacity accessibilityRole="button" disabled={update.reiniciando} onPress={onClose} style={styles.adiar}><Text style={styles.textoAtalho}>Continuar trabalhando</Text></TouchableOpacity>}
        </View>
        <View style={styles.card}>
          <Text style={styles.subtitulo}>Versão em uso</Text>
          <Text style={styles.descricao}>{update.versao.runtimeVersion ?? "—"}{update.versao.createdAt ? ` · ${update.versao.createdAt.toLocaleString("pt-BR")}` : ""}</Text>
          <Text style={styles.suporte}>Identificação para suporte</Text>
          <Text selectable style={styles.identificacao}>{update.versao.updateId ?? "Versão instalada pela loja"}</Text>
          <Text style={styles.suporte}>Canal: {update.versao.channel ?? "—"}{update.versao.isEmbeddedLaunch ? " · versão da loja" : ""}</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  textoAtalho: { color: "#0f766e", fontWeight: "700", fontSize: 13, flexShrink: 1 },
  tela: { flex: 1, backgroundColor: "#f8fafc" },
  cabecalho: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff" },
  titulo: { fontSize: 21, fontWeight: "800", color: "#0f172a", flex: 1 },
  fechar: { minWidth: 44, minHeight: 44, alignItems: "center", justifyContent: "center" },
  conteudo: { padding: 20, gap: 18 },
  card: { padding: 20, gap: 14, borderRadius: 16, backgroundColor: "#fff", borderWidth: 1, borderColor: "#e2e8f0" },
  status: { color: "#0f172a", fontWeight: "800", fontSize: 22 },
  descricao: { color: "#475569", fontSize: 15, lineHeight: 23 },
  erro: { color: "#b91c1c", fontSize: 15, lineHeight: 22 },
  botao: { backgroundColor: "#0f766e", padding: 16, borderRadius: 10, alignItems: "center" },
  textoBotao: { color: "#fff", fontWeight: "800", fontSize: 16 },
  desabilitado: { opacity: 0.55 },
  adiar: { minHeight: 44, justifyContent: "center", alignItems: "center" },
  subtitulo: { color: "#0f172a", fontSize: 17, fontWeight: "700" },
  suporte: { color: "#64748b", fontSize: 12 },
  identificacao: { color: "#475569", fontSize: 12 },
});
