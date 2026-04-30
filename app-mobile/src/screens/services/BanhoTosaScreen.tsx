import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  ActivityIndicator,
  Linking,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import * as Clipboard from "expo-clipboard";
import {
  avaliarBanhoTosaAtendimento,
  listarCalendarioBanhoTosa,
  listarStatusBanhoTosa,
} from "../../services/banhoTosa.service";
import { listarPets } from "../../services/pets.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import { BanhoTosaCalendarioDia, BanhoTosaCalendarioResponse, BanhoTosaStatusItem, Pet } from "../../types";
import { formatarDataHora, formatarMoeda } from "../../utils/format";

const statusCores: Record<string, { bg: string; fg: string }> = {
  agendado: { bg: "#E0F2FE", fg: "#075985" },
  confirmado: { bg: "#DCFCE7", fg: "#166534" },
  chegou: { bg: "#FEF3C7", fg: "#92400E" },
  em_banho: { bg: "#DBEAFE", fg: "#1D4ED8" },
  em_secagem: { bg: "#FCE7F3", fg: "#BE185D" },
  secagem: { bg: "#FCE7F3", fg: "#BE185D" },
  em_tosa: { bg: "#EDE9FE", fg: "#6D28D9" },
  pronto: { bg: "#D1FAE5", fg: "#047857" },
  entregue: { bg: "#F3F4F6", fg: "#374151" },
};

export default function BanhoTosaScreen() {
  const [itens, setItens] = useState<BanhoTosaStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [avaliandoId, setAvaliandoId] = useState<number | null>(null);
  const [calendario, setCalendario] = useState<BanhoTosaCalendarioResponse | null>(null);
  const [pets, setPets] = useState<Pet[]>([]);
  const [servicoId, setServicoId] = useState<number | null>(null);
  const [petId, setPetId] = useState<number | null>(null);
  const [dataSelecionada, setDataSelecionada] = useState<string | null>(null);
  const [agendaAberta, setAgendaAberta] = useState(true);
  const [servicoListaAberta, setServicoListaAberta] = useState(false);

  async function carregar() {
    try {
      const response = await listarStatusBanhoTosa();
      setItens(response.itens || []);
    } catch {
      setItens([]);
    }

    try {
      const [calendarioResponse, petsResponse] = await Promise.all([
        listarCalendarioBanhoTosa(),
        listarPets().catch(() => []),
      ]);
      setCalendario(calendarioResponse);
      setPets(petsResponse);
      if (!servicoId && calendarioResponse.servicos?.[0]?.id) setServicoId(calendarioResponse.servicos[0].id);
      if (!petId && petsResponse?.[0]?.id) setPetId(petsResponse[0].id);
      const primeiroDia = calendarioResponse.dias?.find((dia) => dia.funciona)?.data || calendarioResponse.dias?.[0]?.data || null;
      setDataSelecionada((atual) => (
        atual && calendarioResponse.dias?.some((dia) => dia.data === atual) ? atual : primeiroDia
      ));
    } catch {
      setCalendario(null);
    } finally {
      setLoading(false);
    }
  }

  useFocusEffect(useCallback(() => { carregar(); }, []));

  useEffect(() => {
    if (!calendario?.dias?.length) return;
    if (dataSelecionada && calendario.dias.some((dia) => dia.data === dataSelecionada)) return;
    setDataSelecionada(calendario.dias.find((dia) => dia.funciona)?.data || calendario.dias[0].data);
  }, [calendario?.dias, dataSelecionada]);

  async function onRefresh() {
    setRefreshing(true);
    await carregar();
    setRefreshing(false);
  }

  async function avaliar(item: BanhoTosaStatusItem, nota: number) {
    if (!item.atendimento_id) return;
    setAvaliandoId(item.atendimento_id);
    try {
      await avaliarBanhoTosaAtendimento(item.atendimento_id, nota);
      await carregar();
    } finally {
      setAvaliandoId(null);
    }
  }

  async function pedirAgendamento(data: string, horario: string) {
    const servico = calendario?.servicos.find((item) => item.id === servicoId);
    const pet = pets.find((item) => item.id === petId);
    if (!servico) {
      Alert.alert("Escolha o servico", "Selecione o servico antes de pedir o horario.");
      return;
    }
    if (!pet) {
      Alert.alert("Escolha o pet", "Selecione o pet antes de pedir o horario.");
      return;
    }
    const mensagem = `Ola! Gostaria de marcar ${servico.nome} para o pet ${pet.nome} no dia ${formatarDataCurta(data)} as ${horario}.`;
    await abrirWhatsappLoja(mensagem);
  }

  async function abrirWhatsappLoja(mensagem?: string) {
    const whatsapp = limparWhatsapp(calendario?.whatsapp);
    if (!whatsapp) {
      Alert.alert("WhatsApp nao configurado", "A loja ainda nao cadastrou o WhatsApp de agendamento.");
      return;
    }
    const texto = mensagem || "Ola! Gostaria de falar sobre banho e tosa.";
    await Clipboard.setStringAsync(texto);
    const numero = whatsapp.startsWith("55") ? whatsapp : `55${whatsapp}`;
    const url = `https://wa.me/${numero}?text=${encodeURIComponent(texto)}`;
    const podeAbrir = await Linking.canOpenURL(url);
    if (podeAbrir) {
      Linking.openURL(url);
    } else {
      Alert.alert("Mensagem copiada", "Cole a mensagem no WhatsApp da loja para solicitar o agendamento.");
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={CORES.primario} />
      </View>
    );
  }

  const servicoSelecionado = calendario?.servicos.find((item) => item.id === servicoId);
  const diaSelecionado =
    calendario?.dias.find((dia) => dia.data === dataSelecionada) ||
    calendario?.dias.find((dia) => dia.funciona) ||
    calendario?.dias[0];
  const whatsappFormatado = formatarWhatsapp(calendario?.whatsapp);

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={CORES.primario} />}
    >
      <View style={styles.hero}>
        <View style={styles.heroIcon}>
          <Ionicons name="sparkles-outline" size={26} color="#fff" />
        </View>
        <Text style={styles.heroTitle}>Banho & Tosa</Text>
        <Text style={styles.heroText}>
          Acompanhe agendamentos, andamento do atendimento e avalie quando seu pet for entregue.
        </Text>
      </View>

      {calendario ? (
        calendario.visivel ? (
          <View style={styles.calendarCard}>
            <TouchableOpacity
              style={styles.calendarHeader}
              activeOpacity={0.82}
              onPress={() => setAgendaAberta((atual) => !atual)}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.sectionTitle}>Agenda disponivel</Text>
                <Text style={styles.sectionTextCompact}>
                  {agendaAberta
                    ? "Escolha dia, horario, servico e pet para falar com a loja."
                    : "Toque para abrir os horarios e pedir agendamento pelo WhatsApp."}
                </Text>
              </View>
              <View style={styles.calendarToggle}>
                <Text style={styles.calendarToggleText}>{agendaAberta ? "Minimizar" : "Ver horarios"}</Text>
                <Ionicons name={agendaAberta ? "chevron-up" : "chevron-down"} size={18} color={CORES.primario} />
              </View>
            </TouchableOpacity>

            {agendaAberta && (
              <>
                <TouchableOpacity style={styles.whatsappBox} onPress={() => abrirWhatsappLoja()} activeOpacity={0.86}>
                  <Ionicons name="logo-whatsapp" size={20} color="#16A34A" />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.whatsappLabel}>WhatsApp da loja</Text>
                    <Text style={styles.whatsappNumero}>{whatsappFormatado || "Nao configurado"}</Text>
                  </View>
                  <Text style={styles.whatsappAction}>Abrir</Text>
                </TouchableOpacity>

                <Text style={styles.selectorLabel}>Servico</Text>
                <TouchableOpacity
                  style={styles.dropdownButton}
                  onPress={() => setServicoListaAberta((atual) => !atual)}
                  activeOpacity={0.86}
                >
                  <Text style={styles.dropdownText}>{servicoSelecionado?.nome || "Selecione o servico"}</Text>
                  <Ionicons name={servicoListaAberta ? "chevron-up" : "chevron-down"} size={18} color={CORES.textoSecundario} />
                </TouchableOpacity>
                {servicoListaAberta && (
                  <View style={styles.dropdownList}>
                    {calendario.servicos.map((servico) => (
                      <TouchableOpacity
                        key={servico.id}
                        style={styles.dropdownItem}
                        onPress={() => {
                          setServicoId(servico.id);
                          setServicoListaAberta(false);
                        }}
                      >
                        <Text style={[styles.dropdownItemText, servicoId === servico.id && styles.dropdownItemTextActive]}>
                          {servico.nome}
                        </Text>
                        {servicoId === servico.id && <Ionicons name="checkmark-circle" size={18} color={CORES.primario} />}
                      </TouchableOpacity>
                    ))}
                  </View>
                )}

                <Text style={styles.selectorLabel}>Pet</Text>
                <View style={styles.petGrid}>
                  {pets.map((pet) => (
                    <TouchableOpacity
                      key={pet.id}
                      style={[styles.chip, petId === pet.id && styles.chipActive]}
                      onPress={() => setPetId(pet.id)}
                    >
                      <Text style={[styles.chipText, petId === pet.id && styles.chipTextActive]}>{pet.nome}</Text>
                    </TouchableOpacity>
                  ))}
                </View>

                <Text style={styles.selectorLabel}>Calendario</Text>
                <View style={styles.daysGrid}>
                  {calendario.dias.map((dia) => {
                    const selecionado = dia.data === diaSelecionado?.data;
                    const livres = contarSlotsLivres(dia);
                    return (
                      <TouchableOpacity
                        key={dia.data}
                        style={[
                          styles.dayMini,
                          selecionado && styles.dayMiniActive,
                          !dia.funciona && styles.dayMiniClosed,
                        ]}
                        onPress={() => setDataSelecionada(dia.data)}
                      >
                        <Text style={[styles.dayWeek, selecionado && styles.dayMiniTextActive]}>
                          {formatarDiaSemana(dia.data)}
                        </Text>
                        <Text style={[styles.dayNumber, selecionado && styles.dayMiniTextActive]}>
                          {formatarDiaMes(dia.data)}
                        </Text>
                        <Text style={[styles.dayAvailability, selecionado && styles.dayMiniTextActive]}>
                          {!dia.funciona ? "Fechado" : `${livres} livre${livres === 1 ? "" : "s"}`}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>

                {diaSelecionado ? (
                  <View style={styles.dayBox}>
                    <Text style={styles.dayTitle}>{formatarDataCurta(diaSelecionado.data)}</Text>
                    {!diaSelecionado.funciona ? (
                      <Text style={styles.dayClosed}>Loja fechada neste dia</Text>
                    ) : (
                      <View style={styles.slotsGrid}>
                        {diaSelecionado.slots.map((slot) => {
                          const disponivel = slot.status === "disponivel";
                          return (
                            <TouchableOpacity
                              key={`${diaSelecionado.data}-${slot.horario_inicio}`}
                              disabled={!disponivel}
                              style={[styles.slot, !disponivel && styles.slotBusy]}
                              onPress={() => pedirAgendamento(diaSelecionado.data, slot.horario_inicio)}
                            >
                              <Text style={[styles.slotText, !disponivel && styles.slotTextBusy]}>{slot.horario_inicio}</Text>
                              <Text style={[styles.slotSub, !disponivel && styles.slotTextBusy]}>
                                {disponivel ? "Livre" : "Ocupado"}
                              </Text>
                            </TouchableOpacity>
                          );
                        })}
                      </View>
                    )}
                  </View>
                ) : null}
              </>
            )}
          </View>
        ) : (
          <View style={styles.calendarCard}>
            <Text style={styles.sectionTitle}>Agenda do banho e tosa</Text>
            <Text style={styles.sectionText}>
              A loja ainda nao liberou a visualizacao dos horarios no app. Quando ativar o calendario no ERP, os horarios livres e ocupados aparecem aqui.
            </Text>
          </View>
        )
      ) : null}

      {itens.length === 0 ? (
        <View style={styles.empty}>
          <Ionicons name="calendar-outline" size={38} color={CORES.textoClaro} />
          <Text style={styles.emptyTitle}>Nenhum atendimento em aberto</Text>
          <Text style={styles.emptyText}>
            Quando a loja agendar ou receber seu pet, o status aparece aqui.
          </Text>
        </View>
      ) : (
        itens.map((item) => (
          <StatusCard
            key={`${item.tipo}-${item.atendimento_id || item.agendamento_id}`}
            item={item}
            avaliando={avaliandoId === item.atendimento_id}
            onAvaliar={avaliar}
          />
        ))
      )}
      <View style={{ height: ESPACO.xxl }} />
    </ScrollView>
  );
}

function StatusCard({
  item,
  avaliando,
  onAvaliar,
}: {
  item: BanhoTosaStatusItem;
  avaliando: boolean;
  onAvaliar: (item: BanhoTosaStatusItem, nota: number) => void;
}) {
  const cores = statusCores[item.status] || { bg: "#F3F4F6", fg: "#374151" };
  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={{ flex: 1 }}>
          <Text style={styles.petNome}>{item.pet_nome || "Seu pet"}</Text>
          <Text style={styles.dataTexto}>{formatarDataHora(item.data_hora_inicio || item.checkin_em)}</Text>
        </View>
        <View style={[styles.badge, { backgroundColor: cores.bg }]}>
          <Text style={[styles.badgeText, { color: cores.fg }]}>{item.status_label}</Text>
        </View>
      </View>

      <View style={styles.progressWrap}>
        <View style={[styles.progressFill, { width: `${Math.min(item.progresso_percentual || 0, 100)}%` }]} />
      </View>
      <Text style={styles.etapaTexto}>{item.etapa_atual || item.status_label}</Text>

      {item.servicos?.length > 0 && (
        <View style={styles.servicos}>
          {item.servicos.map((servico, index) => (
            <Text key={`${servico.nome}-${index}`} style={styles.servicoTexto}>
              {servico.quantidade > 1 ? `${servico.quantidade}x ` : ""}{servico.nome}
            </Text>
          ))}
        </View>
      )}

      <View style={styles.footer}>
        <Text style={styles.valor}>{formatarMoeda(Number(item.valor_previsto || 0))}</Text>
        {item.avaliacao ? (
          <Text style={styles.avaliado}>Avaliado: NPS {item.avaliacao.nota_nps}</Text>
        ) : null}
      </View>

      {item.pode_avaliar && (
        <View style={styles.npsBox}>
          <Text style={styles.npsTitle}>Como foi a experiencia?</Text>
          <View style={styles.npsGrid}>
            {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((nota) => (
              <TouchableOpacity
                key={nota}
                disabled={avaliando}
                style={styles.npsButton}
                onPress={() => onAvaliar(item, nota)}
              >
                <Text style={styles.npsButtonText}>{nota}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}
    </View>
  );
}

function formatarDataCurta(dataIso: string): string {
  const [ano, mes, dia] = String(dataIso || "").split("-");
  if (!ano || !mes || !dia) return dataIso;
  return `${dia}/${mes}/${ano}`;
}

function parseDataLocal(dataIso: string): Date | null {
  const [ano, mes, dia] = String(dataIso || "").split("-").map(Number);
  if (!ano || !mes || !dia) return null;
  return new Date(ano, mes - 1, dia);
}

function formatarDiaSemana(dataIso: string): string {
  const data = parseDataLocal(dataIso);
  if (!data) return "--";
  return data.toLocaleDateString("pt-BR", { weekday: "short" }).replace(".", "");
}

function formatarDiaMes(dataIso: string): string {
  const data = parseDataLocal(dataIso);
  if (!data) return "--";
  return String(data.getDate()).padStart(2, "0");
}

function contarSlotsLivres(dia: BanhoTosaCalendarioDia): number {
  if (!dia.funciona) return 0;
  return dia.slots.filter((slot) => slot.status === "disponivel").length;
}

function limparWhatsapp(valor?: string | null): string {
  return String(valor || "").replace(/\D/g, "");
}

function formatarWhatsapp(valor?: string | null): string {
  let numero = limparWhatsapp(valor);
  if (numero.startsWith("55") && numero.length > 11) {
    numero = numero.slice(2);
  }
  if (numero.length === 11) {
    return `(${numero.slice(0, 2)}) ${numero.slice(2, 7)}-${numero.slice(7)}`;
  }
  if (numero.length === 10) {
    return `(${numero.slice(0, 2)}) ${numero.slice(2, 6)}-${numero.slice(6)}`;
  }
  return numero;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  hero: {
    margin: ESPACO.lg,
    padding: ESPACO.lg,
    borderRadius: RAIO.lg,
    backgroundColor: CORES.primario,
    ...SOMBRA,
  },
  heroIcon: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: ESPACO.sm,
  },
  heroTitle: { color: "#fff", fontSize: FONTE.titulo, fontWeight: "bold" },
  heroText: { color: "rgba(255,255,255,0.85)", marginTop: 6, fontSize: FONTE.normal },
  calendarCard: { marginHorizontal: ESPACO.lg, marginBottom: ESPACO.md, padding: ESPACO.lg, borderRadius: RAIO.lg, backgroundColor: CORES.superficie, ...SOMBRA },
  calendarHeader: { flexDirection: "row", alignItems: "center", gap: ESPACO.sm },
  calendarToggle: { flexDirection: "row", alignItems: "center", gap: 4, borderRadius: RAIO.circulo, backgroundColor: "#EFF6FF", paddingHorizontal: ESPACO.sm, paddingVertical: 8 },
  calendarToggleText: { color: CORES.primario, fontSize: FONTE.pequena, fontWeight: "800" },
  sectionTitle: { fontSize: FONTE.grande, color: CORES.texto, fontWeight: "bold" },
  sectionText: { color: CORES.textoSecundario, marginTop: 4, marginBottom: ESPACO.md },
  sectionTextCompact: { color: CORES.textoSecundario, marginTop: 4 },
  whatsappBox: { flexDirection: "row", alignItems: "center", gap: ESPACO.sm, marginTop: ESPACO.md, padding: ESPACO.sm, borderRadius: RAIO.md, backgroundColor: "#F0FDF4", borderWidth: 1, borderColor: "#BBF7D0" },
  whatsappLabel: { color: "#166534", fontSize: FONTE.pequena, fontWeight: "800" },
  whatsappNumero: { marginTop: 2, color: "#14532D", fontWeight: "900" },
  whatsappAction: { color: "#16A34A", fontWeight: "900" },
  selectorLabel: { color: CORES.texto, fontWeight: "700", marginTop: ESPACO.sm, marginBottom: ESPACO.xs },
  dropdownButton: { minHeight: 48, borderRadius: RAIO.md, borderWidth: 1, borderColor: CORES.borda, backgroundColor: CORES.fundo, paddingHorizontal: ESPACO.md, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  dropdownText: { color: CORES.texto, fontWeight: "800", flex: 1 },
  dropdownList: { marginTop: 6, borderRadius: RAIO.md, borderWidth: 1, borderColor: CORES.borda, backgroundColor: "#FFFFFF", overflow: "hidden" },
  dropdownItem: { minHeight: 44, flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: ESPACO.md, borderBottomWidth: 1, borderBottomColor: "#F1F5F9" },
  dropdownItemText: { color: CORES.textoSecundario, fontWeight: "700" },
  dropdownItemTextActive: { color: CORES.primario },
  petGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chipsRow: { gap: 8, paddingRight: ESPACO.lg },
  chip: { borderWidth: 1, borderColor: CORES.borda, borderRadius: RAIO.circulo, paddingHorizontal: ESPACO.md, paddingVertical: 8, backgroundColor: CORES.fundo },
  chipActive: { backgroundColor: CORES.primario, borderColor: CORES.primario },
  chipText: { color: CORES.textoSecundario, fontWeight: "700" },
  chipTextActive: { color: "#fff" },
  daysGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  dayMini: { width: "22.8%", minHeight: 76, borderRadius: RAIO.md, borderWidth: 1, borderColor: CORES.borda, backgroundColor: "#FFFFFF", alignItems: "center", justifyContent: "center", padding: 6 },
  dayMiniActive: { backgroundColor: CORES.primario, borderColor: CORES.primario },
  dayMiniClosed: { backgroundColor: "#F8FAFC" },
  dayWeek: { color: CORES.textoSecundario, fontSize: 10, fontWeight: "900", textTransform: "uppercase" },
  dayNumber: { marginTop: 3, color: CORES.texto, fontSize: 20, fontWeight: "900" },
  dayAvailability: { marginTop: 2, color: CORES.textoClaro, fontSize: 9, fontWeight: "800", textAlign: "center" },
  dayMiniTextActive: { color: "#FFFFFF" },
  dayBox: { marginTop: ESPACO.md, borderTopWidth: 1, borderTopColor: CORES.borda, paddingTop: ESPACO.md },
  dayTitle: { color: CORES.texto, fontWeight: "800", marginBottom: ESPACO.sm },
  dayClosed: { color: CORES.textoClaro },
  slotsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  slot: { minWidth: 74, borderRadius: RAIO.md, backgroundColor: "#ECFDF5", borderWidth: 1, borderColor: "#A7F3D0", paddingVertical: 8, alignItems: "center" },
  slotBusy: { backgroundColor: "#F3F4F6", borderColor: CORES.borda },
  slotText: { color: "#047857", fontWeight: "900" },
  slotSub: { color: "#047857", fontSize: FONTE.pequena, marginTop: 2 },
  slotTextBusy: { color: CORES.textoClaro },
  empty: { margin: ESPACO.lg, padding: ESPACO.xl, alignItems: "center", backgroundColor: CORES.superficie, borderRadius: RAIO.lg },
  emptyTitle: { marginTop: ESPACO.sm, fontSize: FONTE.grande, fontWeight: "bold", color: CORES.texto },
  emptyText: { marginTop: 4, color: CORES.textoSecundario, textAlign: "center" },
  card: { marginHorizontal: ESPACO.lg, marginBottom: ESPACO.md, padding: ESPACO.lg, borderRadius: RAIO.lg, backgroundColor: CORES.superficie, ...SOMBRA },
  cardHeader: { flexDirection: "row", alignItems: "flex-start", gap: ESPACO.sm },
  petNome: { fontSize: FONTE.grande, fontWeight: "bold", color: CORES.texto },
  dataTexto: { marginTop: 2, color: CORES.textoSecundario, fontSize: FONTE.pequena },
  badge: { borderRadius: RAIO.circulo, paddingHorizontal: ESPACO.sm, paddingVertical: 6 },
  badgeText: { fontSize: FONTE.pequena, fontWeight: "bold" },
  progressWrap: { height: 8, borderRadius: 8, backgroundColor: "#E5E7EB", overflow: "hidden", marginTop: ESPACO.md },
  progressFill: { height: 8, borderRadius: 8, backgroundColor: CORES.secundario },
  etapaTexto: { marginTop: ESPACO.sm, color: CORES.texto, fontWeight: "600" },
  servicos: { marginTop: ESPACO.sm, gap: 4 },
  servicoTexto: { color: CORES.textoSecundario },
  footer: { marginTop: ESPACO.md, flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  valor: { color: CORES.primario, fontWeight: "bold" },
  avaliado: { color: CORES.sucesso, fontWeight: "600", fontSize: FONTE.pequena },
  npsBox: { marginTop: ESPACO.md, paddingTop: ESPACO.md, borderTopWidth: 1, borderTopColor: CORES.borda },
  npsTitle: { color: CORES.texto, fontWeight: "bold", marginBottom: ESPACO.sm },
  npsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  npsButton: { minWidth: 34, height: 34, borderRadius: 17, alignItems: "center", justifyContent: "center", backgroundColor: "#EEF2FF" },
  npsButtonText: { color: CORES.primario, fontWeight: "bold" },
});
