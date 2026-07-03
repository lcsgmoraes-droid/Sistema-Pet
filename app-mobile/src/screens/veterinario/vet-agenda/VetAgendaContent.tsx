import React from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { CORES } from "../../../theme";
import { vetAgendaStyles as styles } from "./VetAgendaStyles";
import {
  AgendaModo,
  formatData,
  formatHora,
  VetAgendaGroup,
} from "./VetAgendaUtils";

type VetAgendaContentProps = {
  loading: boolean;
  refreshing: boolean;
  modo: AgendaModo;
  periodoTitulo: string;
  grupos: VetAgendaGroup[];
  totalItens: number;
  onRefresh: () => void;
  onOpenAppointment: () => void;
  onChangeModo: (modo: AgendaModo) => void;
  onNavigate: (delta: number) => void;
};

export function VetAgendaContent({
  loading,
  refreshing,
  modo,
  periodoTitulo,
  grupos,
  totalItens,
  onRefresh,
  onOpenAppointment,
  onChangeModo,
  onNavigate,
}: VetAgendaContentProps) {
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
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.headerRow}>
        <Text style={styles.title}>Agenda veterinaria</Text>
        <TouchableOpacity style={styles.newButton} onPress={onOpenAppointment}>
          <Text style={styles.newButtonText}>Nova consulta</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.segment}>
        {(["dia", "semana", "mes"] as AgendaModo[]).map((item) => (
          <Pressable
            key={item}
            onPress={() => onChangeModo(item)}
            style={[
              styles.segmentButton,
              modo === item && styles.segmentButtonActive,
            ]}
          >
            <Text
              style={[
                styles.segmentText,
                modo === item && styles.segmentTextActive,
              ]}
            >
              {item === "dia" ? "Dia" : item === "semana" ? "Semana" : "Mes"}
            </Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.navRow}>
        <Pressable onPress={() => onNavigate(-1)} style={styles.navButton}>
          <Text style={styles.navText}>Anterior</Text>
        </Pressable>
        <Text style={styles.periodTitle}>{periodoTitulo}</Text>
        <Pressable onPress={() => onNavigate(1)} style={styles.navButton}>
          <Text style={styles.navText}>Proximo</Text>
        </Pressable>
      </View>

      {grupos.map((grupo) => (
        <View key={grupo.data} style={styles.dayGroup}>
          <Text style={styles.dayTitle}>
            {formatData(grupo.agenda[0]?.data_hora)}
          </Text>
          {grupo.agenda.map((item) => (
            <View key={item.id} style={styles.card}>
              <View style={styles.row}>
                <Text style={styles.time}>{formatHora(item.data_hora)}</Text>
                <Text
                  style={[
                    styles.badge,
                    item.tipo === "retorno" && styles.badgeReturn,
                  ]}
                >
                  {item.tipo || "consulta"}
                </Text>
              </View>
              <Text style={styles.pet}>
                {item.pet_nome || `Pet #${item.pet_id}`}
              </Text>
              <Text style={styles.text}>
                Tutor: {item.cliente_nome || "nao informado"}
              </Text>
              <Text style={styles.text}>
                Local: {item.consultorio_nome || "sem consultorio"}
              </Text>
              <Text style={styles.text}>
                Motivo: {item.motivo || "sem motivo informado"}
              </Text>
              <Text style={styles.status}>{item.status || "agendado"}</Text>
            </View>
          ))}
        </View>
      ))}

      {!totalItens && (
        <Text style={styles.empty}>
          Nenhum agendamento encontrado neste periodo.
        </Text>
      )}
    </ScrollView>
  );
}
