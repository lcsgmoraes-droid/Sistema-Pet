import { useFocusEffect } from "@react-navigation/native";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { listarAgendamentosVet, VetAgendamento } from "../../services/vet.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

function formatHora(value?: string | null) {
  if (!value) return "--:--";
  return new Date(value).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export default function VetAgendaScreen() {
  const [itens, setItens] = useState<VetAgendamento[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const carregar = useCallback(async (mostrarErro = true) => {
    try {
      setItens(await listarAgendamentosVet());
    } catch {
      if (mostrarErro) Alert.alert("Erro", "Nao foi possivel carregar a agenda.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { carregar(false); }, [carregar]));

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={CORES.primario} size="large" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); carregar(); }} />}
    >
      <Text style={styles.title}>Agenda de hoje</Text>
      {itens.map((item) => (
        <View key={item.id} style={styles.card}>
          <View style={styles.row}>
            <Text style={styles.time}>{formatHora(item.data_hora)}</Text>
            <Text style={[styles.badge, item.tipo === "retorno" && styles.badgeReturn]}>
              {item.tipo || "consulta"}
            </Text>
          </View>
          <Text style={styles.pet}>{item.pet_nome || `Pet #${item.pet_id}`}</Text>
          <Text style={styles.text}>Tutor: {item.cliente_nome || "nao informado"}</Text>
          <Text style={styles.text}>Local: {item.consultorio_nome || "sem consultorio"}</Text>
          <Text style={styles.text}>Motivo: {item.motivo || "sem motivo informado"}</Text>
          <Text style={styles.status}>{item.status || "agendado"}</Text>
        </View>
      ))}
      {!itens.length && <Text style={styles.empty}>Nenhum agendamento encontrado para hoje.</Text>}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.md, gap: ESPACO.md },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: CORES.fundo },
  title: { fontSize: FONTE.titulo, color: CORES.texto, fontWeight: "800" },
  card: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderLeftWidth: 4,
    borderLeftColor: CORES.primario,
    ...SOMBRA,
  },
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: ESPACO.sm },
  time: { fontSize: FONTE.grande, color: CORES.primario, fontWeight: "800" },
  badge: {
    backgroundColor: CORES.primarioClaro,
    color: CORES.primario,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.xs,
    borderRadius: RAIO.circulo,
    overflow: "hidden",
    fontWeight: "800",
    textTransform: "capitalize",
  },
  badgeReturn: { backgroundColor: "#ecfdf5", color: CORES.sucesso },
  pet: { fontSize: FONTE.grande, color: CORES.texto, fontWeight: "800", marginBottom: ESPACO.xs },
  text: { color: CORES.textoSecundario, fontSize: FONTE.normal, marginTop: 2 },
  status: { color: CORES.texto, fontSize: FONTE.pequena, fontWeight: "800", marginTop: ESPACO.sm },
  empty: { color: CORES.textoSecundario, textAlign: "center", marginTop: ESPACO.xl },
});

