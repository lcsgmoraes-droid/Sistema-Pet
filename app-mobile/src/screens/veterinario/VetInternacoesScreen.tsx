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
import { listarInternacoesVet, VetInternacao } from "../../services/vet.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

function formatDataHora(value?: string | null) {
  if (!value) return "--";
  return new Date(value).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export default function VetInternacoesScreen() {
  const [itens, setItens] = useState<VetInternacao[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const carregar = useCallback(async (mostrarErro = true) => {
    try {
      setItens(await listarInternacoesVet());
    } catch {
      if (mostrarErro) Alert.alert("Erro", "Nao foi possivel carregar internacoes.");
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
      <Text style={styles.title}>Internados</Text>
      {itens.map((item) => (
        <View key={item.id} style={styles.card}>
          <View style={styles.row}>
            <Text style={styles.pet}>{item.pet_nome}</Text>
            <Text style={styles.bed}>{item.baia || "Sem baia"}</Text>
          </View>
          <Text style={styles.text}>Entrada: {formatDataHora(item.data_entrada)}</Text>
          <Text style={styles.text}>Motivo: {item.motivo || "sem motivo informado"}</Text>
          {!!item.observacoes && <Text style={styles.note}>{item.observacoes}</Text>}
        </View>
      ))}
      {!itens.length && <Text style={styles.empty}>Nenhum pet internado agora.</Text>}
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
    ...SOMBRA,
  },
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: ESPACO.sm },
  pet: { fontSize: FONTE.grande, color: CORES.texto, fontWeight: "800", flex: 1 },
  bed: {
    backgroundColor: "#f3e8ff",
    color: "#7e22ce",
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.xs,
    borderRadius: RAIO.circulo,
    overflow: "hidden",
    fontWeight: "800",
  },
  text: { color: CORES.textoSecundario, fontSize: FONTE.normal, marginTop: 4 },
  note: { color: CORES.texto, fontSize: FONTE.normal, marginTop: ESPACO.sm },
  empty: { color: CORES.textoSecundario, textAlign: "center", marginTop: ESPACO.xl },
});

