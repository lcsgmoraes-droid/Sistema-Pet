import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useNavigation } from "@react-navigation/native";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { listarPets, obterStatusPush } from "../../services/pets.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import { Pet, PushStatus, VetFocusSection } from "../../types";

const sectionLabels: Record<VetFocusSection, string> = {
  vacinas: "Carteirinha de vacinas",
  exames: "Exames e resultados",
  consultas: "Consultas veterinarias",
};

const sectionSubtitles: Record<VetFocusSection, string> = {
  vacinas: "Vacinas aplicadas, pendentes e atrasadas por pet.",
  exames: "Resultados, anexos e historico de exames.",
  consultas: "Atendimentos clinicos e historico veterinario.",
};

export default function VeterinarioScreen() {
  const navigation = useNavigation<any>();
  const [pets, setPets] = useState<Pet[]>([]);
  const [pushStatus, setPushStatus] = useState<PushStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const [petsRes, pushRes] = await Promise.allSettled([
        listarPets(),
        obterStatusPush(),
      ]);

      setPets(petsRes.status === "fulfilled" ? petsRes.value : []);
      setPushStatus(pushRes.status === "fulfilled" ? pushRes.value : null);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      carregar();
    }, [carregar])
  );

  async function onRefresh() {
    setRefreshing(true);
    await carregar();
    setRefreshing(false);
  }

  function abrirAreaVet(section: VetFocusSection) {
    if (!pets.length) {
      navigation.navigate("FormPet");
      return;
    }

    if (pets.length === 1) {
      navigation.navigate("DetalhePet", {
        pet: pets[0],
        focusSection: section,
      });
      return;
    }

    navigation.navigate("ListaPets", { focusSection: section });
  }

  function nomePetAgendamento(petId: number) {
    return pets.find((pet) => pet.id === petId)?.nome || `Pet #${petId}`;
  }

  function formatarAgenda(data?: string | null) {
    if (!data) return "Horario a confirmar";
    return new Date(data).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
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
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={CORES.primario}
        />
      }
    >
      <View style={styles.hero}>
        <View style={styles.heroIcon}>
          <Ionicons name="medkit-outline" size={28} color="#fff" />
        </View>
        <Text style={styles.heroTitle}>Central Veterinaria</Text>
        <Text style={styles.heroText}>
          Vacinas, exames, consultas e agenda clinica em uma area separada do perfil da conta.
        </Text>
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Saude do pet</Text>
          <Text style={styles.sectionBadge}>{pets.length ? "Ativo" : "Cadastre um pet"}</Text>
        </View>

        {(Object.keys(sectionLabels) as VetFocusSection[]).map((section) => (
          <ActionCard
            key={section}
            icon={section === "vacinas" ? "fitness-outline" : section === "exames" ? "document-text-outline" : "medical-outline"}
            title={sectionLabels[section]}
            subtitle={
              pets.length
                ? sectionSubtitles[section]
                : "Cadastre um pet para liberar esta area no app."
            }
            action={pets.length ? "Abrir" : "Cadastrar pet"}
            onPress={() => abrirAreaVet(section)}
          />
        ))}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Proximos atendimentos</Text>
        {pushStatus?.proximos_agendamentos?.length ? (
          pushStatus.proximos_agendamentos.map((agendamento) => (
            <View key={agendamento.id} style={styles.appointmentItem}>
              <View style={styles.appointmentIcon}>
                <Ionicons name="calendar-outline" size={17} color={CORES.primario} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.appointmentTitle}>
                  {agendamento.tipo || "Atendimento"} - {nomePetAgendamento(agendamento.pet_id)}
                </Text>
                <Text style={styles.appointmentSubtitle}>
                  {formatarAgenda(agendamento.data_hora)}
                </Text>
              </View>
              <Text style={styles.appointmentStatus}>
                {agendamento.status || "agendado"}
              </Text>
            </View>
          ))
        ) : (
          <Text style={styles.supportText}>
            Nenhuma consulta futura confirmada no momento.
          </Text>
        )}
      </View>

      <View style={{ height: ESPACO.xxl }} />
    </ScrollView>
  );
}

function ActionCard({
  icon,
  title,
  subtitle,
  action,
  onPress,
  tint = CORES.primario,
  background = "#EFF6FF",
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle: string;
  action: string;
  onPress: () => void;
  tint?: string;
  background?: string;
}) {
  return (
    <TouchableOpacity style={styles.actionCard} onPress={onPress} activeOpacity={0.85}>
      <View style={[styles.actionIcon, { backgroundColor: background }]}>
        <Ionicons name={icon} size={22} color={tint} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.actionTitle}>{title}</Text>
        <Text style={styles.actionSubtitle}>{subtitle}</Text>
      </View>
      <View style={[styles.actionPill, { backgroundColor: background }]}>
        <Text style={[styles.actionPillText, { color: tint }]}>{action}</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.lg },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  hero: {
    padding: ESPACO.lg,
    borderRadius: RAIO.lg,
    marginBottom: ESPACO.lg,
    backgroundColor: CORES.primario,
    ...SOMBRA,
  },
  heroIcon: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: ESPACO.md,
    backgroundColor: "rgba(255,255,255,0.2)",
  },
  heroTitle: { color: "#fff", fontSize: FONTE.titulo, fontWeight: "800" },
  heroText: {
    color: "rgba(255,255,255,0.86)",
    fontSize: FONTE.normal,
    lineHeight: 20,
    marginTop: 6,
  },
  section: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.lg,
    padding: ESPACO.lg,
    marginBottom: ESPACO.lg,
    ...SOMBRA,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: ESPACO.sm,
  },
  sectionTitle: {
    color: CORES.texto,
    fontSize: FONTE.grande,
    fontWeight: "800",
    marginBottom: ESPACO.sm,
  },
  sectionBadge: {
    color: CORES.primario,
    fontSize: FONTE.pequena,
    fontWeight: "800",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: RAIO.circulo,
    backgroundColor: "#EFF6FF",
    overflow: "hidden",
  },
  actionCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    paddingVertical: ESPACO.md,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
  },
  actionIcon: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
  },
  actionTitle: { color: CORES.texto, fontSize: FONTE.normal, fontWeight: "800" },
  actionSubtitle: {
    color: CORES.textoSecundario,
    fontSize: FONTE.pequena,
    lineHeight: 18,
    marginTop: 2,
  },
  actionPill: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: RAIO.circulo,
  },
  actionPillText: { fontSize: FONTE.pequena, fontWeight: "800" },
  appointmentItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    padding: ESPACO.sm,
    marginTop: ESPACO.sm,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    backgroundColor: "#FAFAFA",
  },
  appointmentIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EFF6FF",
  },
  appointmentTitle: { color: CORES.texto, fontSize: FONTE.normal, fontWeight: "800" },
  appointmentSubtitle: { color: CORES.textoSecundario, fontSize: FONTE.pequena, marginTop: 2 },
  appointmentStatus: {
    color: CORES.primario,
    fontSize: FONTE.pequena,
    fontWeight: "800",
    textTransform: "capitalize",
  },
  supportText: {
    color: CORES.textoSecundario,
    fontSize: FONTE.normal,
    lineHeight: 20,
  },
});
