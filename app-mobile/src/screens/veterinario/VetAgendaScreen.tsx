import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import {
  criarAgendamentoVet,
  listarAgendamentosVet,
  listarConsultoriosVet,
  listarPetsVet,
  VetAgendamento,
  VetConsultorio,
  VetPetResumo,
} from "../../services/vet.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

const MIN_CARACTERES_BUSCA_PET = 2;
const DIAS_SEMANA = ["D", "S", "T", "Q", "Q", "S", "S"];

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

function dateFromIso(value?: string | null) {
  const [yearRaw, monthRaw, dayRaw] = String(value || "").split("-").map(Number);
  const year = Number.isFinite(yearRaw) ? yearRaw : NaN;
  const month = Number.isFinite(monthRaw) ? monthRaw - 1 : NaN;
  const day = Number.isFinite(dayRaw) ? dayRaw : NaN;
  const parsed = new Date(year, month, day);
  if (
    !Number.isFinite(year) ||
    !Number.isFinite(month) ||
    !Number.isFinite(day) ||
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month ||
    parsed.getDate() !== day
  ) {
    return new Date();
  }
  return parsed;
}

function formatarDataIsoParaBr(value?: string | null) {
  const date = dateFromIso(value);
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
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

function gerarCalendarioDias(mesReferenciaIso: string, selecionadaIso: string) {
  const mesReferencia = dateFromIso(mesReferenciaIso);
  const selecionada = dateFromIso(selecionadaIso);
  const hojeIso = isoDate(new Date());
  const inicioMes = new Date(mesReferencia.getFullYear(), mesReferencia.getMonth(), 1);
  const inicioGrade = addDays(inicioMes, -inicioMes.getDay());

  return Array.from({ length: 42 }, (_, index) => {
    const data = addDays(inicioGrade, index);
    const dataIso = isoDate(data);
    return {
      key: dataIso,
      data: dataIso,
      dia: data.getDate(),
      foraMes: data.getMonth() !== mesReferencia.getMonth(),
      selecionado: data.toDateString() === selecionada.toDateString(),
      hoje: dataIso === hojeIso,
    };
  });
}

function mesAnoCalendario(value: string) {
  return dateFromIso(value).toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
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

function dataDoAgendamento(item: VetAgendamento) {
  if (!item.data_hora) return "";
  return isoDate(new Date(item.data_hora));
}

function horaDoAgendamento(item: VetAgendamento) {
  return formatHora(item.data_hora);
}

function mensagemErroApi(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return fallback;
}

function formInicialAgendamento(data = isoDate(new Date()), hora = "08:00") {
  return {
    pet_id: "",
    data,
    hora,
    consultorio_id: "",
    motivo: "",
    duracao_minutos: "30",
  };
}

function dataReferenciaModal(date: Date) {
  return isoDate(date);
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
  const [pets, setPets] = useState<VetPetResumo[]>([]);
  const [consultorios, setConsultorios] = useState<VetConsultorio[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modo, setModo] = useState<AgendaModo>("dia");
  const [referencia, setReferencia] = useState(() => new Date());
  const [modalAberto, setModalAberto] = useState(false);
  const [buscaPet, setBuscaPet] = useState("");
  const [salvandoNovo, setSalvandoNovo] = useState(false);
  const [carregandoApoios, setCarregandoApoios] = useState(false);
  const [form, setForm] = useState(() => formInicialAgendamento());
  const [calendarioAberto, setCalendarioAberto] = useState(false);
  const [calendarioReferencia, setCalendarioReferencia] = useState(() => formInicialAgendamento().data);

  const periodo = useMemo(() => periodoAgenda(modo, referencia), [modo, referencia]);
  const horariosBase = useMemo(() => gerarHorariosBase(), []);
  const calendarioDias = useMemo(
    () => gerarCalendarioDias(calendarioReferencia, form.data),
    [calendarioReferencia, form.data],
  );

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

  const horariosOcupados = useMemo(() => {
    const ocupados = new Set<string>();
    itens.forEach((item) => {
      if (dataDoAgendamento(item) === form.data) {
        const hora = horaDoAgendamento(item);
        if (hora) ocupados.add(hora);
      }
    });
    return ocupados;
  }, [form.data, itens]);

  const petsFiltrados = useMemo(() => {
    const termo = buscaPet.trim().toLowerCase();
    if (termo.length < MIN_CARACTERES_BUSCA_PET) return [];
    return pets
      .filter((pet) => {
        const texto = [
          pet.nome,
          pet.codigo,
          pet.raca,
          pet.cliente_nome,
          pet.cliente_telefone,
          pet.cliente_celular,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return texto.includes(termo);
      })
      .slice(0, 30);
  }, [buscaPet, pets]);

  const carregar = useCallback(async (mostrarErro = true) => {
    try {
      setItens(await listarAgendamentosVet(periodo.params));
    } catch (error) {
      if (mostrarErro) Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel carregar a agenda."));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [periodo.params]);

  useFocusEffect(useCallback(() => { carregar(false); }, [carregar]));

  function sugerirHorarioLivre(data: string) {
    const ocupados = new Set(
      itens
        .filter((item) => dataDoAgendamento(item) === data)
        .map(horaDoAgendamento)
        .filter(Boolean),
    );
    return horariosBase.find((horario) => !ocupados.has(horario)) || horariosBase[0] || "08:00";
  }

  async function carregarApoiosAgendamento() {
    setCarregandoApoios(true);
    try {
      const [petsDisponiveis, consultoriosDisponiveis] = await Promise.all([
        listarPetsVet(),
        listarConsultoriosVet(),
      ]);
      setPets(petsDisponiveis);
      setConsultorios(consultoriosDisponiveis);
    } catch (error) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel carregar pets e consultorios."));
    } finally {
      setCarregandoApoios(false);
    }
  }

  function abrirModalAgendamento() {
    const data = dataReferenciaModal(referencia);
    setBuscaPet("");
    setForm(formInicialAgendamento(data, sugerirHorarioLivre(data)));
    setCalendarioAberto(false);
    setCalendarioReferencia(data);
    setModalAberto(true);
    carregarApoiosAgendamento();
  }

  function atualizarCampo(campo: keyof ReturnType<typeof formInicialAgendamento>, valor: string) {
    setForm((atual) => {
      if (campo !== "data") return { ...atual, [campo]: valor };
      return { ...atual, data: valor, hora: sugerirHorarioLivre(valor) };
    });
  }

  function abrirCalendario() {
    setCalendarioReferencia(form.data || isoDate(new Date()));
    setCalendarioAberto(true);
  }

  function navegarMesCalendario(delta: number) {
    setCalendarioReferencia((atual) => isoDate(addMonths(dateFromIso(atual), delta)));
  }

  function selecionarDataCalendario(data: string) {
    atualizarCampo("data", data);
    setCalendarioReferencia(data);
    setCalendarioAberto(false);
  }

  async function salvarAgendamento() {
    const petId = Number(form.pet_id);
    const duracao = Number(form.duracao_minutos);

    if (!petId) {
      Alert.alert("Pet", "Selecione o pet para agendar a consulta.");
      return;
    }
    if (!form.data || !form.hora) {
      Alert.alert("Data e horario", "Informe data e horario da consulta.");
      return;
    }
    if (!Number.isFinite(duracao) || duracao < 5) {
      Alert.alert("Duracao", "Informe a duracao em minutos.");
      return;
    }

    setSalvandoNovo(true);
    try {
      await criarAgendamentoVet({
        pet_id: petId,
        data_hora: `${form.data}T${form.hora}`,
        duracao_minutos: duracao,
        tipo: "consulta",
        motivo: form.motivo.trim() || null,
        consultorio_id: form.consultorio_id ? Number(form.consultorio_id) : null,
      });

      const dataSelecionada = new Date(`${form.data}T12:00:00`);
      setModo("dia");
      setReferencia(dataSelecionada);
      setItens(await listarAgendamentosVet({ data: form.data }));
      setModalAberto(false);
    } catch (error) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel agendar a consulta."));
    } finally {
      setSalvandoNovo(false);
      setLoading(false);
    }
  }

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
    <>
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); carregar(); }} />}
      >
      <View style={styles.headerRow}>
        <Text style={styles.title}>Agenda veterinaria</Text>
        <TouchableOpacity style={styles.newButton} onPress={abrirModalAgendamento}>
          <Text style={styles.newButtonText}>Nova consulta</Text>
        </TouchableOpacity>
      </View>

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

      <Modal visible={modalAberto} animationType="slide" transparent onRequestClose={() => setModalAberto(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <ScrollView contentContainerStyle={styles.modalContent}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>Agendar consulta</Text>
                <TouchableOpacity onPress={() => setModalAberto(false)}>
                  <Text style={styles.closeText}>Fechar</Text>
                </TouchableOpacity>
              </View>

              <Text style={styles.label}>Buscar pet</Text>
              <TextInput
                value={buscaPet}
                onChangeText={setBuscaPet}
                placeholder="Digite nome, codigo, tutor ou telefone"
                placeholderTextColor={CORES.textoSecundario}
                style={styles.input}
              />

              <View style={styles.petList}>
                {carregandoApoios && <Text style={styles.emptyInline}>Carregando pets...</Text>}
                {!carregandoApoios && buscaPet.trim().length < MIN_CARACTERES_BUSCA_PET && (
                  <Text style={styles.emptyInline}>Digite pelo menos 2 caracteres para buscar o pet.</Text>
                )}
                {!carregandoApoios && petsFiltrados.map((pet) => {
                  const ativo = String(pet.id) === form.pet_id;
                  return (
                    <TouchableOpacity
                      key={pet.id}
                      style={[styles.petOption, ativo && styles.petOptionActive]}
                      onPress={() => atualizarCampo("pet_id", String(pet.id))}
                    >
                      <Text style={[styles.petOptionTitle, ativo && styles.petOptionTitleActive]}>
                        {pet.nome || `Pet #${pet.id}`}
                      </Text>
                      <Text style={styles.petOptionText}>
                        {[pet.cliente_nome, pet.raca || pet.especie, pet.codigo].filter(Boolean).join(" | ") || "Sem detalhes"}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
                {!carregandoApoios && buscaPet.trim().length >= MIN_CARACTERES_BUSCA_PET && !petsFiltrados.length && (
                  <Text style={styles.emptyInline}>Nenhum pet encontrado.</Text>
                )}
              </View>

              <Text style={styles.label}>Consultorio</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsRow}>
                <TouchableOpacity
                  style={[styles.chip, !form.consultorio_id && styles.chipActive]}
                  onPress={() => atualizarCampo("consultorio_id", "")}
                >
                  <Text style={[styles.chipText, !form.consultorio_id && styles.chipTextActive]}>Sem sala</Text>
                </TouchableOpacity>
                {consultorios.map((consultorio) => {
                  const ativo = String(consultorio.id) === form.consultorio_id;
                  return (
                    <TouchableOpacity
                      key={consultorio.id}
                      style={[styles.chip, ativo && styles.chipActive]}
                      onPress={() => atualizarCampo("consultorio_id", String(consultorio.id))}
                    >
                      <Text style={[styles.chipText, ativo && styles.chipTextActive]}>{consultorio.nome}</Text>
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>

              <Text style={styles.label}>Data</Text>
              <TouchableOpacity style={styles.dateInputWrap} onPress={abrirCalendario} activeOpacity={0.85}>
                <TextInput
                  value={formatarDataIsoParaBr(form.data)}
                  placeholder="dd/mm/aaaa"
                  placeholderTextColor={CORES.textoSecundario}
                  style={styles.dateInputText}
                  editable={false}
                  pointerEvents="none"
                />
                <Ionicons name="calendar-outline" size={20} color={CORES.primario} />
              </TouchableOpacity>

              {calendarioAberto && (
                <View style={styles.calendarCard}>
                  <View style={styles.calendarHeader}>
                    <TouchableOpacity style={styles.calendarNavButton} onPress={() => navegarMesCalendario(-1)}>
                      <Ionicons name="chevron-back" size={20} color={CORES.primario} />
                    </TouchableOpacity>
                    <Text style={styles.calendarTitle}>{mesAnoCalendario(calendarioReferencia)}</Text>
                    <TouchableOpacity style={styles.calendarNavButton} onPress={() => navegarMesCalendario(1)}>
                      <Ionicons name="chevron-forward" size={20} color={CORES.primario} />
                    </TouchableOpacity>
                  </View>
                  <View style={styles.calendarWeekRow}>
                    {DIAS_SEMANA.map((dia, index) => (
                      <Text key={`${dia}-${index}`} style={styles.calendarWeekText}>{dia}</Text>
                    ))}
                  </View>
                  <View style={styles.calendarGrid}>
                    {calendarioDias.map((dia) => (
                      <TouchableOpacity
                        key={dia.key}
                        style={[
                          styles.calendarDay,
                          dia.foraMes && styles.calendarDayOutside,
                          dia.hoje && styles.calendarDayToday,
                          dia.selecionado && styles.calendarDaySelected,
                        ]}
                        onPress={() => selecionarDataCalendario(dia.data)}
                      >
                        <Text
                          style={[
                            styles.calendarDayText,
                            dia.foraMes && styles.calendarDayOutsideText,
                            dia.selecionado && styles.calendarDaySelectedText,
                          ]}
                        >
                          {dia.dia}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                  <TouchableOpacity
                    style={styles.calendarTodayButton}
                    onPress={() => selecionarDataCalendario(isoDate(new Date()))}
                  >
                    <Text style={styles.calendarTodayText}>Hoje</Text>
                  </TouchableOpacity>
                </View>
              )}

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

              <View style={styles.twoColumns}>
                <View style={styles.flexField}>
                  <Text style={styles.label}>Duracao</Text>
                  <TextInput
                    value={form.duracao_minutos}
                    onChangeText={(value) => atualizarCampo("duracao_minutos", value)}
                    keyboardType="number-pad"
                    placeholder="30"
                    placeholderTextColor={CORES.textoSecundario}
                    style={styles.input}
                  />
                </View>
                <View style={styles.flexField}>
                  <Text style={styles.label}>Tipo</Text>
                  <View style={styles.readonlyField}>
                    <Text style={styles.readonlyText}>Consulta</Text>
                  </View>
                </View>
              </View>

              <Text style={styles.label}>Motivo</Text>
              <TextInput
                value={form.motivo}
                onChangeText={(value) => atualizarCampo("motivo", value)}
                placeholder="Ex: retorno, avaliacao, vacina..."
                placeholderTextColor={CORES.textoSecundario}
                style={[styles.input, styles.textArea]}
                multiline
              />

              <TouchableOpacity
                style={[styles.saveButton, (salvandoNovo || carregandoApoios) && styles.disabledButton]}
                onPress={salvarAgendamento}
                disabled={salvandoNovo || carregandoApoios}
              >
                <Text style={styles.saveButtonText}>{salvandoNovo ? "Salvando..." : "Agendar consulta"}</Text>
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
  dateInputWrap: {
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    paddingRight: ESPACO.md,
    flexDirection: "row",
    alignItems: "center",
  },
  dateInputText: {
    flex: 1,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    color: CORES.texto,
    fontWeight: "800",
  },
  calendarCard: {
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
    gap: ESPACO.sm,
  },
  calendarHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  calendarNavButton: {
    width: 36,
    height: 36,
    borderRadius: RAIO.sm,
    borderWidth: 1,
    borderColor: CORES.borda,
    alignItems: "center",
    justifyContent: "center",
  },
  calendarTitle: {
    color: CORES.texto,
    fontWeight: "900",
    textTransform: "capitalize",
  },
  calendarWeekRow: {
    flexDirection: "row",
  },
  calendarWeekText: {
    width: `${100 / 7}%`,
    textAlign: "center",
    color: CORES.textoSecundario,
    fontWeight: "900",
    fontSize: FONTE.pequena,
  },
  calendarGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  calendarDay: {
    width: `${100 / 7}%`,
    aspectRatio: 1,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: RAIO.sm,
    borderWidth: 1,
    borderColor: "transparent",
  },
  calendarDayOutside: { opacity: 0.45 },
  calendarDayToday: { borderColor: CORES.primario },
  calendarDaySelected: { backgroundColor: CORES.primario, borderColor: CORES.primario },
  calendarDayText: { color: CORES.texto, fontWeight: "800" },
  calendarDayOutsideText: { color: CORES.textoSecundario },
  calendarDaySelectedText: { color: "#FFFFFF" },
  calendarTodayButton: {
    alignSelf: "flex-start",
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.xs,
  },
  calendarTodayText: { color: CORES.primario, fontWeight: "900" },
  textArea: { minHeight: 76, textAlignVertical: "top" },
  petList: { gap: ESPACO.xs },
  petOption: {
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
  },
  petOptionActive: { borderColor: CORES.primario, backgroundColor: CORES.primarioClaro },
  petOptionTitle: { color: CORES.texto, fontWeight: "900" },
  petOptionTitleActive: { color: CORES.primario },
  petOptionText: { color: CORES.textoSecundario, fontSize: FONTE.pequena, marginTop: 2 },
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
  readonlyField: {
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
  },
  readonlyText: { color: CORES.texto, fontWeight: "800" },
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

