import { useFocusEffect } from "@react-navigation/native";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import {
  listarInternacoesVet,
  obterInternacaoVet,
  VetEvolucaoInternacao,
  VetInternacao,
  VetInternacaoDetalhe,
  VetProcedimentoAgenda,
  VetProcedimentoRealizado,
} from "../../services/vet.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

function formatDataHora(value?: string | null) {
  if (!value) return "--";
  return new Date(value).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function resumoSinais(item: VetEvolucaoInternacao) {
  const partes = [
    item.temperatura ? `${item.temperatura} C` : null,
    item.freq_cardiaca ? `FC ${item.freq_cardiaca}` : null,
    item.freq_respiratoria ? `FR ${item.freq_respiratoria}` : null,
    item.nivel_dor != null ? `Dor ${item.nivel_dor}/10` : null,
    item.peso ? `${item.peso} kg` : null,
  ].filter(Boolean);
  return partes.length ? partes.join(" - ") : "Sem sinais vitais informados";
}

export default function VetInternacoesScreen() {
  const [itens, setItens] = useState<VetInternacao[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [detalhe, setDetalhe] = useState<VetInternacaoDetalhe | null>(null);
  const [loadingDetalhe, setLoadingDetalhe] = useState(false);

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

  async function abrirDetalhe(item: VetInternacao) {
    setLoadingDetalhe(true);
    setDetalhe(null);
    try {
      setDetalhe(await obterInternacaoVet(item.id));
    } catch {
      Alert.alert("Erro", "Nao foi possivel carregar os detalhes da internacao.");
    } finally {
      setLoadingDetalhe(false);
    }
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
      <Text style={styles.title}>Internados</Text>
      {itens.map((item) => (
        <TouchableOpacity key={item.id} style={styles.card} activeOpacity={0.85} onPress={() => abrirDetalhe(item)}>
          <View style={styles.row}>
            <Text style={styles.pet}>{item.pet_nome}</Text>
            <Text style={styles.bed}>{item.baia || "Sem baia"}</Text>
          </View>
          <Text style={styles.text}>Entrada: {formatDataHora(item.data_entrada)}</Text>
          <Text style={styles.text}>Motivo: {item.motivo || "sem motivo informado"}</Text>
          {!!item.observacoes && <Text style={styles.note}>{item.observacoes}</Text>}
          <Text style={styles.openHint}>Toque para ver detalhes</Text>
        </TouchableOpacity>
      ))}
      {!itens.length && <Text style={styles.empty}>Nenhum pet internado agora.</Text>}

      <Modal
        visible={loadingDetalhe || !!detalhe}
        animationType="slide"
        onRequestClose={() => {
          setDetalhe(null);
          setLoadingDetalhe(false);
        }}
      >
        <View style={styles.modalContainer}>
          {loadingDetalhe ? (
            <View style={styles.center}>
              <ActivityIndicator color={CORES.primario} size="large" />
            </View>
          ) : detalhe ? (
            <DetalheInternacao detalhe={detalhe} onClose={() => setDetalhe(null)} />
          ) : null}
        </View>
      </Modal>
    </ScrollView>
  );
}

function DetalheInternacao({ detalhe, onClose }: { detalhe: VetInternacaoDetalhe; onClose: () => void }) {
  return (
    <ScrollView style={styles.modalContainer} contentContainerStyle={styles.modalContent}>
      <View style={styles.modalHeader}>
        <View style={{ flex: 1 }}>
          <Text style={styles.modalTitle}>{detalhe.pet_nome}</Text>
          <Text style={styles.modalSubtitle}>
            {[detalhe.pet_especie, detalhe.pet_raca, detalhe.pet_codigo ? `Cod. ${detalhe.pet_codigo}` : null]
              .filter(Boolean)
              .join(" - ") || "Paciente internado"}
          </Text>
        </View>
        <TouchableOpacity style={styles.closeButton} onPress={onClose}>
          <Text style={styles.closeText}>Fechar</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.detailCard}>
        <Text style={styles.sectionTitle}>Resumo</Text>
        <Text style={styles.text}>Tutor: {detalhe.tutor_nome || "Nao informado"}</Text>
        <Text style={styles.text}>Entrada: {formatDataHora(detalhe.data_entrada)}</Text>
        <Text style={styles.text}>Baia: {detalhe.baia || "Sem baia"}</Text>
        <Text style={styles.text}>Status: {detalhe.status || "internado"}</Text>
        <Text style={styles.text}>Motivo: {detalhe.motivo || "sem motivo informado"}</Text>
        {!!detalhe.observacoes && <Text style={styles.note}>{detalhe.observacoes}</Text>}
      </View>

      <TimelineSection
        title="Agenda de cuidados"
        empty="Nenhum procedimento agendado."
        items={detalhe.procedimentos_agenda}
        renderItem={(item: VetProcedimentoAgenda) => (
          <>
            <Text style={styles.timelineTitle}>{formatDataHora(item.horario_agendado || item.horario)}</Text>
            <Text style={styles.timelineText}>{item.medicamento}</Text>
            <Text style={styles.timelineHint}>
              {[item.dose, item.via, item.unidade_quantidade].filter(Boolean).join(" - ") || "Sem dose/via"}
            </Text>
            <Text style={styles.statusBadge}>{item.status || "agendado"}</Text>
          </>
        )}
      />

      <TimelineSection
        title="Procedimentos realizados"
        empty="Nenhum procedimento realizado ainda."
        items={detalhe.procedimentos_realizados}
        renderItem={(item: VetProcedimentoRealizado) => (
          <>
            <Text style={styles.timelineTitle}>{formatDataHora(item.horario_execucao || item.data_hora)}</Text>
            <Text style={styles.timelineText}>{item.medicamento || "Procedimento"}</Text>
            <Text style={styles.timelineHint}>
              {[item.dose, item.via, item.executado_por].filter(Boolean).join(" - ") || "Sem detalhes adicionais"}
            </Text>
            {!!item.observacao_execucao && <Text style={styles.timelineNote}>{item.observacao_execucao}</Text>}
          </>
        )}
      />

      <TimelineSection
        title="Evolucoes clinicas"
        empty="Nenhuma evolucao registrada ainda."
        items={detalhe.evolucoes}
        renderItem={(item: VetEvolucaoInternacao) => (
          <>
            <Text style={styles.timelineTitle}>{formatDataHora(item.data_hora)}</Text>
            <Text style={styles.timelineText}>{resumoSinais(item)}</Text>
            {!!item.observacoes && <Text style={styles.timelineNote}>{item.observacoes}</Text>}
          </>
        )}
      />
    </ScrollView>
  );
}

function TimelineSection<T>({
  title,
  empty,
  items,
  renderItem,
}: {
  title: string;
  empty: string;
  items: T[];
  renderItem: (item: T) => React.ReactNode;
}) {
  return (
    <View style={styles.detailCard}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {items.length ? (
        items.map((item: any) => (
          <View key={item.id} style={styles.timelineItem}>
            {renderItem(item)}
          </View>
        ))
      ) : (
        <Text style={styles.emptyInline}>{empty}</Text>
      )}
    </View>
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
  openHint: { color: CORES.primario, fontWeight: "800", marginTop: ESPACO.md },
  empty: { color: CORES.textoSecundario, textAlign: "center", marginTop: ESPACO.xl },
  modalContainer: { flex: 1, backgroundColor: CORES.fundo },
  modalContent: { padding: ESPACO.md, gap: ESPACO.md },
  modalHeader: { flexDirection: "row", alignItems: "center", gap: ESPACO.sm, marginTop: ESPACO.md },
  modalTitle: { fontSize: FONTE.titulo, color: CORES.texto, fontWeight: "900" },
  modalSubtitle: { color: CORES.textoSecundario, marginTop: 2 },
  closeButton: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    backgroundColor: "#fff",
  },
  closeText: { color: CORES.texto, fontWeight: "800" },
  detailCard: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    ...SOMBRA,
  },
  sectionTitle: { color: CORES.texto, fontSize: FONTE.grande, fontWeight: "900", marginBottom: ESPACO.sm },
  timelineItem: {
    borderLeftWidth: 3,
    borderLeftColor: CORES.primario,
    paddingLeft: ESPACO.sm,
    paddingVertical: ESPACO.sm,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
  },
  timelineTitle: { color: CORES.texto, fontWeight: "900" },
  timelineText: { color: CORES.texto, marginTop: 3 },
  timelineHint: { color: CORES.textoSecundario, fontSize: FONTE.pequena, marginTop: 2 },
  timelineNote: { color: CORES.textoSecundario, fontSize: FONTE.pequena, marginTop: ESPACO.xs },
  statusBadge: {
    alignSelf: "flex-start",
    backgroundColor: "#eef2ff",
    color: CORES.primario,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: 2,
    borderRadius: RAIO.circulo,
    overflow: "hidden",
    fontWeight: "800",
    marginTop: ESPACO.xs,
  },
  emptyInline: { color: CORES.textoSecundario },
});

