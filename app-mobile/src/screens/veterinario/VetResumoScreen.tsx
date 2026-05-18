import { Ionicons } from "@expo/vector-icons";
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
import { obterResumoVet, VetResumo } from "../../services/vet.service";
import { sincronizarLembretesVet } from "../../services/vetNotifications.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

function formatHora(value?: string | null) {
  if (!value) return "--:--";
  return new Date(value).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export default function VetResumoScreen() {
  const [resumo, setResumo] = useState<VetResumo | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lembretes, setLembretes] = useState(0);

  const carregar = useCallback(async (mostrarErro = true) => {
    try {
      const data = await obterResumoVet();
      setResumo(data);
      sincronizarLembretesVet(data)
        .then(setLembretes)
        .catch(() => setLembretes(0));
    } catch {
      if (mostrarErro) {
        Alert.alert("Erro", "Nao foi possivel carregar o resumo veterinario.");
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      carregar(false);
    }, [carregar]),
  );

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
      <View style={styles.hero}>
        <Text style={styles.kicker}>Central veterinaria</Text>
        <Text style={styles.title}>{resumo?.veterinario.nome || "Veterinario"}</Text>
        <Text style={styles.subtitle}>{resumo?.veterinario.crmv ? `CRMV ${resumo.veterinario.crmv}` : "Rotina clinica do dia"}</Text>
        <Text style={styles.subtitle}>{lembretes} lembrete(s) sincronizado(s) no celular</Text>
      </View>

      <View style={styles.metrics}>
        <Metric icon="calendar-outline" label="Agenda" value={resumo?.agendamentos_hoje.length ?? 0} />
        <Metric icon="bed-outline" label="Internados" value={resumo?.internacoes_ativas.length ?? 0} />
        <Metric icon="alarm-outline" label="Lembretes" value={resumo?.procedimentos_pendentes.length ?? 0} />
      </View>

      <Section title="Proximas consultas">
        {(resumo?.agendamentos_hoje || []).slice(0, 4).map((item) => (
          <View key={item.id} style={styles.item}>
            <Text style={styles.time}>{formatHora(item.data_hora)}</Text>
            <View style={styles.itemBody}>
              <Text style={styles.itemTitle}>{item.pet_nome || `Pet #${item.pet_id}`}</Text>
              <Text style={styles.itemText}>{item.cliente_nome || "Tutor nao informado"}</Text>
              <Text style={styles.itemText}>{item.tipo || "consulta"} - {item.status || "agendado"}</Text>
            </View>
          </View>
        ))}
        {(!resumo?.agendamentos_hoje.length) && <Empty text="Nenhuma consulta para hoje." />}
      </Section>

      <Section title="Cuidados pendentes">
        {(resumo?.procedimentos_pendentes || []).slice(0, 4).map((item) => (
          <View key={item.id} style={styles.item}>
            <Text style={styles.time}>{formatHora(item.horario_agendado || item.horario)}</Text>
            <View style={styles.itemBody}>
              <Text style={styles.itemTitle}>{item.medicamento}</Text>
              <Text style={styles.itemText}>{item.pet_nome} - {item.baia || "Sem baia"}</Text>
              <Text style={styles.itemText}>{[item.dose, item.via].filter(Boolean).join(" | ")}</Text>
            </View>
          </View>
        ))}
        {(!resumo?.procedimentos_pendentes.length) && <Empty text="Nenhum cuidado pendente nas proximas horas." />}
      </Section>
    </ScrollView>
  );
}

function Metric({ icon, label, value }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: number }) {
  return (
    <View style={styles.metric}>
      <Ionicons name={icon} size={20} color={CORES.primario} />
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function Empty({ text }: { text: string }) {
  return <Text style={styles.empty}>{text}</Text>;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.md, gap: ESPACO.md },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: CORES.fundo },
  hero: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    padding: ESPACO.lg,
  },
  kicker: { color: "#bfdbfe", fontSize: FONTE.pequena, fontWeight: "700", textTransform: "uppercase" },
  title: { color: "#fff", fontSize: FONTE.titulo, fontWeight: "800", marginTop: ESPACO.xs },
  subtitle: { color: "#dbeafe", fontSize: FONTE.normal, marginTop: ESPACO.xs },
  metrics: { flexDirection: "row", gap: ESPACO.sm },
  metric: {
    flex: 1,
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    alignItems: "center",
    ...SOMBRA,
  },
  metricValue: { fontSize: FONTE.titulo, fontWeight: "800", color: CORES.texto, marginTop: ESPACO.xs },
  metricLabel: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  section: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    ...SOMBRA,
  },
  sectionTitle: { fontSize: FONTE.media, color: CORES.texto, fontWeight: "800", marginBottom: ESPACO.sm },
  item: { flexDirection: "row", paddingVertical: ESPACO.sm, borderTopWidth: 1, borderTopColor: CORES.borda },
  time: { width: 58, color: CORES.primario, fontWeight: "800" },
  itemBody: { flex: 1 },
  itemTitle: { color: CORES.texto, fontSize: FONTE.normal, fontWeight: "800" },
  itemText: { color: CORES.textoSecundario, fontSize: FONTE.pequena, marginTop: 2 },
  empty: { color: CORES.textoSecundario, paddingVertical: ESPACO.md },
});
