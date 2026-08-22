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
  View,
} from "react-native";

import api from "../../services/api";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import { formatarMoeda } from "../../utils/format";

type ContaCrediario = {
  id: number;
  venda_id?: number | null;
  descricao: string;
  valor_original: number;
  valor_recebido: number;
  saldo: number;
  data_vencimento: string;
  status: string;
};

export default function CrediarioScreen() {
  const [contas, setContas] = useState<ContaCrediario[]>([]);
  const [resumo, setResumo] = useState({ em_aberto: 0, vencido: 0 });
  const [carregando, setCarregando] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      const response = await api.get("/checkout/crediario");
      setContas(Array.isArray(response.data?.contas) ? response.data.contas : []);
      setResumo({
        em_aberto: Number(response.data?.resumo?.em_aberto ?? 0),
        vencido: Number(response.data?.resumo?.vencido ?? 0),
      });
      setErro(null);
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      setErro(typeof detail === "string" ? detail : "Nao foi possivel carregar o crediario.");
      throw error;
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      setCarregando(true);
      carregar()
        .catch(() => undefined)
        .finally(() => setCarregando(false));
    }, [carregar]),
  );

  if (carregando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator size="large" color={CORES.primario} />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.conteudo}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={async () => {
            setRefreshing(true);
            try {
              await carregar();
            } catch {
              Alert.alert("Erro", "Nao foi possivel atualizar o crediario.");
            } finally {
              setRefreshing(false);
            }
          }}
        />
      }
    >
      <View style={styles.resumoLinha}>
        <View style={styles.resumoCard}>
          <Text style={styles.resumoLabel}>Em aberto</Text>
          <Text style={styles.resumoValor}>{formatarMoeda(resumo.em_aberto)}</Text>
        </View>
        <View style={[styles.resumoCard, resumo.vencido > 0 && styles.resumoVencido]}>
          <Text style={styles.resumoLabel}>Vencido</Text>
          <Text style={[styles.resumoValor, resumo.vencido > 0 && { color: CORES.erro }]}>
            {formatarMoeda(resumo.vencido)}
          </Text>
        </View>
      </View>

      {erro ? <Text style={styles.erro}>{erro}</Text> : null}

      {contas.map((conta) => {
        const encerrada = [
          "recebido",
          "pago",
          "cancelado",
          "cancelada",
          "estornado",
          "estornada",
        ].includes(conta.status);
        const aberta = !encerrada && conta.saldo > 0;
        const statusLabel =
          conta.status === "vencido"
            ? "Vencido"
            : aberta
              ? "Em aberto"
              : ["cancelado", "cancelada", "estornado", "estornada"].includes(conta.status)
                ? "Cancelado"
                : "Pago";
        return (
          <View key={conta.id} style={styles.card}>
            <View style={styles.cardHeader}>
              <View style={{ flex: 1 }}>
                <Text style={styles.descricao}>{conta.descricao}</Text>
                <Text style={styles.data}>
                  Vencimento: {conta.data_vencimento.split("-").reverse().join("/")}
                </Text>
              </View>
              <View
                style={[
                  styles.badge,
                  conta.status === "vencido"
                    ? styles.badgeVencido
                    : aberta
                      ? styles.badgeAberto
                      : styles.badgePago,
                ]}
              >
                <Text style={styles.badgeTexto}>{statusLabel}</Text>
              </View>
            </View>
            <View style={styles.valoresLinha}>
              <Text style={styles.valorLabel}>Valor {formatarMoeda(conta.valor_original)}</Text>
              <Text style={styles.saldo}>Saldo {formatarMoeda(conta.saldo)}</Text>
            </View>
          </View>
        );
      })}

      {contas.length === 0 && !erro ? (
        <View style={styles.vazio}>
          <Ionicons name="checkmark-circle-outline" size={58} color={CORES.sucesso} />
          <Text style={styles.vazioTitulo}>Nenhuma compra no crediario</Text>
          <Text style={styles.vazioTexto}>
            Quando houver uma compra, o vencimento e a situacao aparecerao aqui.
          </Text>
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  conteudo: { padding: ESPACO.md, gap: ESPACO.sm, paddingBottom: ESPACO.xxl },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center" },
  resumoLinha: { flexDirection: "row", gap: ESPACO.sm, marginBottom: ESPACO.sm },
  resumoCard: {
    flex: 1,
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    ...SOMBRA,
  },
  resumoVencido: { borderColor: "#FCA5A5", backgroundColor: "#FEF2F2" },
  resumoLabel: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  resumoValor: { fontSize: FONTE.grande, fontWeight: "900", color: CORES.texto, marginTop: 4 },
  card: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
  },
  cardHeader: { flexDirection: "row", gap: ESPACO.sm, alignItems: "flex-start" },
  descricao: { fontWeight: "800", color: CORES.texto },
  data: { color: CORES.textoSecundario, marginTop: 4, fontSize: FONTE.pequena },
  badge: { paddingHorizontal: ESPACO.sm, paddingVertical: 4, borderRadius: RAIO.circulo },
  badgeAberto: { backgroundColor: "#FEF3C7" },
  badgeVencido: { backgroundColor: "#FEE2E2" },
  badgePago: { backgroundColor: "#DCFCE7" },
  badgeTexto: { fontSize: 11, fontWeight: "800", color: CORES.texto },
  valoresLinha: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: ESPACO.md,
    paddingTop: ESPACO.sm,
    borderTopWidth: 1,
    borderTopColor: CORES.borda,
  },
  valorLabel: { color: CORES.textoSecundario },
  saldo: { color: CORES.primario, fontWeight: "900" },
  erro: { color: CORES.erro, textAlign: "center", fontWeight: "700", padding: ESPACO.sm },
  vazio: { alignItems: "center", padding: ESPACO.xxl, gap: ESPACO.sm },
  vazioTitulo: { fontSize: FONTE.grande, fontWeight: "900", color: CORES.texto },
  vazioTexto: { color: CORES.textoSecundario, textAlign: "center", lineHeight: 20 },
});
