import { useFocusEffect } from "@react-navigation/native";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { concluirProcedimentoVet, listarProcedimentosVet, VetProcedimentoAgenda } from "../../services/vet.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

function formatHora(value?: string | null) {
  if (!value) return "--:--";
  return new Date(value).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export default function VetProcedimentosScreen() {
  const [itens, setItens] = useState<VetProcedimentoAgenda[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [concluindoId, setConcluindoId] = useState<number | null>(null);

  const carregar = useCallback(async (mostrarErro = true) => {
    try {
      setItens(await listarProcedimentosVet());
    } catch {
      if (mostrarErro) Alert.alert("Erro", "Nao foi possivel carregar os procedimentos.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { carregar(false); }, [carregar]));

  function confirmarConcluir(item: VetProcedimentoAgenda) {
    Alert.alert("Marcar como feito", `Confirmar ${item.medicamento} para ${item.pet_nome}?`, [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Confirmar",
        onPress: async () => {
          try {
            setConcluindoId(item.id);
            await concluirProcedimentoVet(item.id);
            await carregar(false);
          } catch {
            Alert.alert("Erro", "Nao foi possivel concluir este cuidado.");
          } finally {
            setConcluindoId(null);
          }
        },
      },
    ]);
  }

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
      <Text style={styles.title}>Procedimentos e remedios</Text>
      {itens.map((item) => (
        <View key={item.id} style={styles.card}>
          <View style={styles.row}>
            <Text style={styles.time}>{formatHora(item.horario_agendado || item.horario)}</Text>
            <Text style={styles.status}>{item.status || "agendado"}</Text>
          </View>
          <Text style={styles.med}>{item.medicamento}</Text>
          <Text style={styles.text}>{item.pet_nome} - {item.baia || "Sem baia"}</Text>
          <Text style={styles.text}>{[item.dose, item.via].filter(Boolean).join(" | ") || "Sem dose/via informada"}</Text>
          {!!item.observacoes && <Text style={styles.note}>{item.observacoes}</Text>}
          <TouchableOpacity
            style={styles.action}
            onPress={() => confirmarConcluir(item)}
            disabled={concluindoId === item.id}
          >
            <Text style={styles.actionText}>
              {concluindoId === item.id ? "Confirmando..." : "Marcar como feito"}
            </Text>
          </TouchableOpacity>
        </View>
      ))}
      {!itens.length && <Text style={styles.empty}>Nenhum procedimento pendente.</Text>}
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
    borderLeftColor: CORES.aviso,
    ...SOMBRA,
  },
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: ESPACO.sm },
  time: { color: CORES.aviso, fontSize: FONTE.grande, fontWeight: "800" },
  status: {
    color: CORES.textoSecundario,
    backgroundColor: "#f3f4f6",
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.xs,
    borderRadius: RAIO.circulo,
    overflow: "hidden",
    fontWeight: "800",
  },
  med: { color: CORES.texto, fontSize: FONTE.grande, fontWeight: "800" },
  text: { color: CORES.textoSecundario, fontSize: FONTE.normal, marginTop: 4 },
  note: { color: CORES.texto, fontSize: FONTE.normal, marginTop: ESPACO.sm },
  action: {
    backgroundColor: CORES.sucesso,
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
    alignItems: "center",
    marginTop: ESPACO.md,
  },
  actionText: { color: "#fff", fontWeight: "800" },
  empty: { color: CORES.textoSecundario, textAlign: "center", marginTop: ESPACO.xl },
});
