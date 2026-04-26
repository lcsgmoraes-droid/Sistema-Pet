import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
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
import {
  avaliarBanhoTosaAtendimento,
  listarStatusBanhoTosa,
} from "../../services/banhoTosa.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import { BanhoTosaStatusItem } from "../../types";
import { formatarDataHora, formatarMoeda } from "../../utils/format";

const statusCores: Record<string, { bg: string; fg: string }> = {
  agendado: { bg: "#E0F2FE", fg: "#075985" },
  confirmado: { bg: "#DCFCE7", fg: "#166534" },
  chegou: { bg: "#FEF3C7", fg: "#92400E" },
  em_banho: { bg: "#DBEAFE", fg: "#1D4ED8" },
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

  async function carregar() {
    try {
      const response = await listarStatusBanhoTosa();
      setItens(response.itens || []);
    } catch {
      setItens([]);
    } finally {
      setLoading(false);
    }
  }

  useFocusEffect(useCallback(() => { carregar(); }, []));

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

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={CORES.primario} />
      </View>
    );
  }

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
