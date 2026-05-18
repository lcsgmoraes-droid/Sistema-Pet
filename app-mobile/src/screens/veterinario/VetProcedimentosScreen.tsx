import { useFocusEffect } from "@react-navigation/native";
import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import {
  concluirProcedimentoVet,
  criarProcedimentoAgendaVet,
  listarInternacoesVet,
  listarProcedimentosVet,
  VetInternacao,
  VetProcedimentoAgenda,
} from "../../services/vet.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

function formatHora(value?: string | null) {
  if (!value) return "--:--";
  return new Date(value).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function isoDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function gerarHorariosBase() {
  const horarios: string[] = [];
  for (let hora = 8; hora <= 18; hora += 1) {
    for (let minuto = 0; minuto < 60; minuto += 30) {
      if (hora === 18 && minuto > 0) continue;
      horarios.push(`${String(hora).padStart(2, "0")}:${String(minuto).padStart(2, "0")}`);
    }
  }
  return horarios;
}

function dataDoProcedimento(item: VetProcedimentoAgenda) {
  const value = item.horario_agendado || item.horario;
  if (!value) return "";
  return isoDate(new Date(value));
}

function horaDoProcedimento(item: VetProcedimentoAgenda) {
  const value = item.horario_agendado || item.horario;
  if (!value) return "";
  return formatHora(value);
}

function parseQuantidade(value: string) {
  const texto = value.trim().replace(",", ".");
  if (!texto) return null;
  const parsed = Number(texto);
  return Number.isFinite(parsed) ? parsed : null;
}

function mensagemErroApi(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return fallback;
}

function formInicial(internacaoId = "") {
  return {
    internacao_id: internacaoId,
    data: isoDate(new Date()),
    hora: "08:00",
    medicamento: "",
    dose: "",
    via: "",
    quantidade_prevista: "",
    unidade_quantidade: "",
    observacoes_agenda: "",
  };
}

export default function VetProcedimentosScreen() {
  const [itens, setItens] = useState<VetProcedimentoAgenda[]>([]);
  const [internacoes, setInternacoes] = useState<VetInternacao[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [concluindoId, setConcluindoId] = useState<number | null>(null);
  const [modalAberto, setModalAberto] = useState(false);
  const [salvandoNovo, setSalvandoNovo] = useState(false);
  const [form, setForm] = useState(() => formInicial());

  const horariosBase = useMemo(() => gerarHorariosBase(), []);
  const horariosOcupados = useMemo(() => {
    const ocupados = new Set<string>();
    itens.forEach((item) => {
      if (dataDoProcedimento(item) === form.data) {
        const hora = horaDoProcedimento(item);
        if (hora) ocupados.add(hora);
      }
    });
    return ocupados;
  }, [form.data, itens]);

  const carregar = useCallback(async (mostrarErro = true) => {
    try {
      const [procedimentos, internacoesAtivas] = await Promise.all([
        listarProcedimentosVet(),
        listarInternacoesVet(),
      ]);
      setItens(procedimentos);
      setInternacoes(internacoesAtivas);
    } catch (error) {
      if (mostrarErro) Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel carregar os procedimentos."));
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
          } catch (error) {
            Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel concluir este cuidado."));
          } finally {
            setConcluindoId(null);
          }
        },
      },
    ]);
  }

  function sugerirHorarioLivre(data: string) {
    const ocupados = new Set(
      itens
        .filter((item) => dataDoProcedimento(item) === data)
        .map(horaDoProcedimento)
        .filter(Boolean),
    );
    return horariosBase.find((horario) => !ocupados.has(horario)) || horariosBase[0] || "08:00";
  }

  function abrirModalAgendamento() {
    const primeiraInternacao = internacoes[0]?.id ? String(internacoes[0].id) : "";
    const data = isoDate(new Date());
    setForm({
      ...formInicial(primeiraInternacao),
      data,
      hora: sugerirHorarioLivre(data),
    });
    setModalAberto(true);
  }

  function atualizarCampo(campo: keyof ReturnType<typeof formInicial>, valor: string) {
    setForm((atual) => {
      if (campo !== "data") return { ...atual, [campo]: valor };
      return { ...atual, data: valor, hora: sugerirHorarioLivre(valor) };
    });
  }

  async function salvarAgendamento() {
    if (!form.internacao_id) {
      Alert.alert("Internacao", "Selecione um internado para agendar o cuidado.");
      return;
    }
    if (!form.data || !form.hora || !form.medicamento.trim()) {
      Alert.alert("Campos obrigatorios", "Informe data, horario e medicamento/procedimento.");
      return;
    }

    const quantidade = parseQuantidade(form.quantidade_prevista);
    setSalvandoNovo(true);
    try {
      await criarProcedimentoAgendaVet(Number(form.internacao_id), {
        horario_agendado: `${form.data}T${form.hora}`,
        medicamento: form.medicamento.trim(),
        dose: form.dose.trim() || null,
        via: form.via.trim() || null,
        quantidade_prevista: quantidade,
        unidade_quantidade: form.unidade_quantidade.trim() || null,
        lembrete_min: 30,
        observacoes_agenda: form.observacoes_agenda.trim() || null,
      });
      setModalAberto(false);
      await carregar(false);
    } catch (error) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel agendar este cuidado."));
    } finally {
      setSalvandoNovo(false);
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
    <>
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); carregar(); }} />}
      >
        <View style={styles.headerRow}>
          <Text style={styles.title}>Procedimentos e remedios</Text>
          <TouchableOpacity style={styles.newButton} onPress={abrirModalAgendamento}>
            <Text style={styles.newButtonText}>Agendar</Text>
          </TouchableOpacity>
        </View>
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

      <Modal visible={modalAberto} animationType="slide" transparent onRequestClose={() => setModalAberto(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <ScrollView contentContainerStyle={styles.modalContent}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>Agendar cuidado</Text>
                <TouchableOpacity onPress={() => setModalAberto(false)}>
                  <Text style={styles.closeText}>Fechar</Text>
                </TouchableOpacity>
              </View>

              <Text style={styles.label}>Internado</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsRow}>
                {internacoes.map((internacao) => {
                  const ativo = String(internacao.id) === form.internacao_id;
                  return (
                    <TouchableOpacity
                      key={internacao.id}
                      style={[styles.chip, ativo && styles.chipActive]}
                      onPress={() => atualizarCampo("internacao_id", String(internacao.id))}
                    >
                      <Text style={[styles.chipText, ativo && styles.chipTextActive]}>
                        {internacao.pet_nome || `Pet #${internacao.pet_id}`}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
                {!internacoes.length && <Text style={styles.emptyInline}>Nenhuma internacao ativa.</Text>}
              </ScrollView>

              <Text style={styles.label}>Data</Text>
              <TextInput
                value={form.data}
                onChangeText={(value) => atualizarCampo("data", value)}
                placeholder="AAAA-MM-DD"
                style={styles.input}
              />

              <Text style={styles.label}>Horario</Text>
              <View style={styles.slotsGrid}>
                {horariosBase.map((horario) => {
                  const ocupado = horariosOcupados.has(horario);
                  const selecionado = form.hora === horario;
                  return (
                    <TouchableOpacity
                      key={horario}
                      style={[
                        styles.slot,
                        ocupado ? styles.slotOcupado : styles.slotLivre,
                        selecionado && styles.slotSelecionado,
                      ]}
                      onPress={() => atualizarCampo("hora", horario)}
                    >
                      <Text style={styles.slotText}>{horario}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
              <View style={styles.legendRow}>
                <Text style={styles.legendLivre}>Livre</Text>
                <Text style={styles.legendOcupado}>Marcado</Text>
              </View>

              <Text style={styles.label}>Medicamento ou procedimento</Text>
              <TextInput
                value={form.medicamento}
                onChangeText={(value) => atualizarCampo("medicamento", value)}
                placeholder="Ex: Dipirona, curativo, glicemia..."
                style={styles.input}
              />

              <Text style={styles.label}>Dose / orientacao</Text>
              <TextInput
                value={form.dose}
                onChangeText={(value) => atualizarCampo("dose", value)}
                placeholder="Ex: 1 gota/kg a cada 12h"
                style={styles.input}
              />

              <View style={styles.twoColumns}>
                <View style={styles.flexField}>
                  <Text style={styles.label}>Quantidade</Text>
                  <TextInput
                    value={form.quantidade_prevista}
                    onChangeText={(value) => atualizarCampo("quantidade_prevista", value)}
                    keyboardType="decimal-pad"
                    placeholder="1"
                    style={styles.input}
                  />
                </View>
                <View style={styles.flexField}>
                  <Text style={styles.label}>Unidade</Text>
                  <TextInput
                    value={form.unidade_quantidade}
                    onChangeText={(value) => atualizarCampo("unidade_quantidade", value)}
                    placeholder="mL, comp, un"
                    style={styles.input}
                  />
                </View>
              </View>

              <Text style={styles.label}>Via</Text>
              <TextInput
                value={form.via}
                onChangeText={(value) => atualizarCampo("via", value)}
                placeholder="VO, SC, IV..."
                style={styles.input}
              />

              <Text style={styles.label}>Observacoes</Text>
              <TextInput
                value={form.observacoes_agenda}
                onChangeText={(value) => atualizarCampo("observacoes_agenda", value)}
                placeholder="Observacao para a equipe"
                style={[styles.input, styles.textArea]}
                multiline
              />

              <TouchableOpacity
                style={[styles.saveButton, salvandoNovo && styles.disabledButton]}
                onPress={salvarAgendamento}
                disabled={salvandoNovo}
              >
                <Text style={styles.saveButtonText}>{salvandoNovo ? "Salvando..." : "Adicionar na agenda"}</Text>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.md, gap: ESPACO.md },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: CORES.fundo },
  title: { fontSize: FONTE.titulo, color: CORES.texto, fontWeight: "800" },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: ESPACO.sm },
  newButton: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
  },
  newButtonText: { color: "#fff", fontWeight: "800" },
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
  emptyInline: { color: CORES.textoSecundario, paddingVertical: ESPACO.sm },
  modalOverlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(15,23,42,0.45)",
  },
  modalCard: {
    maxHeight: "92%",
    backgroundColor: CORES.fundo,
    borderTopLeftRadius: RAIO.lg,
    borderTopRightRadius: RAIO.lg,
  },
  modalContent: { padding: ESPACO.md, gap: ESPACO.sm, paddingBottom: ESPACO.xl },
  modalHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  modalTitle: { color: CORES.texto, fontSize: FONTE.titulo, fontWeight: "900" },
  closeText: { color: CORES.primario, fontWeight: "800" },
  label: { color: CORES.textoSecundario, fontWeight: "800", fontSize: FONTE.pequena, marginTop: ESPACO.xs },
  input: {
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    color: CORES.texto,
  },
  textArea: { minHeight: 76, textAlignVertical: "top" },
  chipsRow: { gap: ESPACO.sm, paddingVertical: ESPACO.xs },
  chip: {
    borderWidth: 1,
    borderColor: CORES.borda,
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
  },
  chipActive: { borderColor: CORES.primario, backgroundColor: CORES.primarioClaro },
  chipText: { color: CORES.textoSecundario, fontWeight: "800" },
  chipTextActive: { color: CORES.primario },
  slotsGrid: { flexDirection: "row", flexWrap: "wrap", gap: ESPACO.xs },
  slot: {
    minWidth: 64,
    borderRadius: RAIO.sm,
    paddingVertical: ESPACO.sm,
    paddingHorizontal: ESPACO.sm,
    alignItems: "center",
    borderWidth: 2,
  },
  slotLivre: { backgroundColor: "#DCFCE7", borderColor: "#DCFCE7" },
  slotOcupado: { backgroundColor: "#FEF3C7", borderColor: "#FEF3C7" },
  slotSelecionado: { borderColor: CORES.primario },
  slotText: { color: CORES.texto, fontWeight: "900" },
  legendRow: { flexDirection: "row", gap: ESPACO.sm, marginBottom: ESPACO.xs },
  legendLivre: { color: "#15803D", fontWeight: "800", fontSize: FONTE.pequena },
  legendOcupado: { color: "#A16207", fontWeight: "800", fontSize: FONTE.pequena },
  twoColumns: { flexDirection: "row", gap: ESPACO.sm },
  flexField: { flex: 1 },
  saveButton: {
    backgroundColor: CORES.sucesso,
    borderRadius: RAIO.sm,
    paddingVertical: ESPACO.md,
    alignItems: "center",
    marginTop: ESPACO.md,
  },
  disabledButton: { opacity: 0.65 },
  saveButtonText: { color: "#fff", fontWeight: "900" },
});
