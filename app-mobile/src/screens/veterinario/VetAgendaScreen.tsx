import { useFocusEffect } from "@react-navigation/native";
import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
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

function formatData(value?: string | null) {
  if (!value) return "Sem data";
  return new Date(value).toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
  });
}

function isoDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(date: Date, days: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function addMonths(date: Date, months: number) {
  const next = new Date(date);
  next.setMonth(next.getMonth() + months);
  return next;
}

function startOfWeek(date: Date) {
  return addDays(date, -date.getDay());
}

function endOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

type AgendaModo = "dia" | "semana" | "mes";

function periodoAgenda(modo: AgendaModo, referencia: Date) {
  if (modo === "dia") {
    return {
      params: { data: isoDate(referencia) },
      titulo: referencia.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" }),
    };
  }

  if (modo === "semana") {
    const inicio = startOfWeek(referencia);
    const fim = addDays(inicio, 6);
    return {
      params: { data_inicio: isoDate(inicio), data_fim: isoDate(fim) },
      titulo: `${inicio.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })} - ${fim.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })}`,
    };
  }

  const inicio = new Date(referencia.getFullYear(), referencia.getMonth(), 1);
  const fim = endOfMonth(referencia);
  return {
    params: { data_inicio: isoDate(inicio), data_fim: isoDate(fim) },
    titulo: referencia.toLocaleDateString("pt-BR", { month: "long", year: "numeric" }),
  };
}

export default function VetAgendaScreen() {
  const [itens, setItens] = useState<VetAgendamento[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modo, setModo] = useState<AgendaModo>("dia");
  const [referencia, setReferencia] = useState(() => new Date());

  const periodo = useMemo(() => periodoAgenda(modo, referencia), [modo, referencia]);

  const grupos = useMemo(() => {
    const mapa = new Map<string, VetAgendamento[]>();
    itens.forEach((item) => {
      const chave = item.data_hora ? isoDate(new Date(item.data_hora)) : "sem-data";
      const atuais = mapa.get(chave) || [];
      atuais.push(item);
      mapa.set(chave, atuais);
    });
    return Array.from(mapa.entries()).map(([data, agenda]) => ({ data, agenda }));
  }, [itens]);

  const carregar = useCallback(async (mostrarErro = true) => {
    try {
      setItens(await listarAgendamentosVet(periodo.params));
    } catch {
      if (mostrarErro) Alert.alert("Erro", "Nao foi possivel carregar a agenda.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [periodo.params]);

  useFocusEffect(useCallback(() => { carregar(false); }, [carregar]));

  function navegar(delta: number) {
    setLoading(true);
    setReferencia((atual) => {
      if (modo === "mes") return addMonths(atual, delta);
      return addDays(atual, modo === "semana" ? delta * 7 : delta);
    });
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
      <Text style={styles.title}>Agenda veterinaria</Text>

      <View style={styles.segment}>
        {(["dia", "semana", "mes"] as AgendaModo[]).map((item) => (
          <Pressable
            key={item}
            onPress={() => {
              setLoading(true);
              setModo(item);
            }}
            style={[styles.segmentButton, modo === item && styles.segmentButtonActive]}
          >
            <Text style={[styles.segmentText, modo === item && styles.segmentTextActive]}>
              {item === "dia" ? "Dia" : item === "semana" ? "Semana" : "Mes"}
            </Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.navRow}>
        <Pressable onPress={() => navegar(-1)} style={styles.navButton}>
          <Text style={styles.navText}>Anterior</Text>
        </Pressable>
        <Text style={styles.periodTitle}>{periodo.titulo}</Text>
        <Pressable onPress={() => navegar(1)} style={styles.navButton}>
          <Text style={styles.navText}>Proximo</Text>
        </Pressable>
      </View>

      {grupos.map((grupo) => (
        <View key={grupo.data} style={styles.dayGroup}>
          <Text style={styles.dayTitle}>{formatData(grupo.agenda[0]?.data_hora)}</Text>
          {grupo.agenda.map((item) => (
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
        </View>
      ))}
      {!itens.length && <Text style={styles.empty}>Nenhum agendamento encontrado neste periodo.</Text>}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.md, gap: ESPACO.md },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: CORES.fundo },
  title: { fontSize: FONTE.titulo, color: CORES.texto, fontWeight: "800" },
  segment: {
    flexDirection: "row",
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: 4,
    ...SOMBRA,
  },
  segmentButton: { flex: 1, alignItems: "center", paddingVertical: ESPACO.sm, borderRadius: RAIO.sm },
  segmentButtonActive: { backgroundColor: CORES.primario },
  segmentText: { color: CORES.textoSecundario, fontWeight: "800" },
  segmentTextActive: { color: "#FFFFFF" },
  navRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: ESPACO.sm,
  },
  navButton: {
    borderWidth: 1,
    borderColor: CORES.borda,
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.sm,
  },
  navText: { color: CORES.primario, fontWeight: "800", fontSize: FONTE.pequena },
  periodTitle: { flex: 1, textAlign: "center", color: CORES.texto, fontWeight: "800", textTransform: "capitalize" },
  dayGroup: { gap: ESPACO.sm },
  dayTitle: { color: CORES.textoSecundario, fontWeight: "800", textTransform: "capitalize" },
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

