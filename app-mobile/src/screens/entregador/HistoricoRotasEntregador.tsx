import React, { useMemo, useState } from "react";
import {
  FlatList,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { formatarDataHora, formatarMoeda } from "../../utils/format";

interface ParadaHistorico {
  id: number;
  ordem: number;
  venda_id: number;
  numero_venda?: string;
  cliente_nome?: string;
  endereco: string;
  status: string;
  valor_venda?: number;
  taxa_entrega?: number;
  data_entrega?: string;
}

export interface RotaHistorico {
  id: number;
  numero: string;
  status: string;
  created_at: string;
  data_inicio?: string;
  data_conclusao?: string;
  duracao_minutos?: number;
  total_entregas?: number;
  entregas_concluidas?: number;
  distancia_real?: number;
  distancia_total_km_real?: number;
  distancia_prevista?: number;
  valor_total_vendas?: number;
  taxa_total_entregas?: number;
  paradas: ParadaHistorico[];
}

type Periodo = 7 | 30 | 90 | 0;
type Ordenacao = "recentes" | "antigas" | "mais_entregas" | "maior_distancia";

interface Props {
  rotas: RotaHistorico[];
  refreshing: boolean;
  onRefresh: () => void;
  onOpen: (rota: RotaHistorico) => void;
}

const PERIODOS: Array<{ valor: Periodo; label: string }> = [
  { valor: 7, label: "7 dias" },
  { valor: 30, label: "30 dias" },
  { valor: 90, label: "90 dias" },
  { valor: 0, label: "Todas" },
];

const ORDENACOES: Array<{ valor: Ordenacao; label: string }> = [
  { valor: "recentes", label: "Recentes" },
  { valor: "antigas", label: "Antigas" },
  { valor: "mais_entregas", label: "Mais entregas" },
  { valor: "maior_distancia", label: "Maior distância" },
];

function quantidadeEntregas(rota: RotaHistorico) {
  return Number(rota.total_entregas) || rota.paradas?.length || 0;
}

function distanciaRota(rota: RotaHistorico) {
  return Number(
    rota.distancia_real ||
      rota.distancia_total_km_real ||
      rota.distancia_prevista ||
      0,
  );
}

function textoPesquisavel(rota: RotaHistorico) {
  return [
    rota.numero,
    ...rota.paradas.flatMap((parada) => [
      parada.numero_venda,
      parada.venda_id,
      parada.cliente_nome,
      parada.endereco,
    ]),
  ]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase("pt-BR");
}

function duracaoLabel(minutos?: number) {
  if (minutos == null || minutos < 0) return "Não informada";
  if (minutos < 60) return `${Math.round(minutos)} min`;
  const horas = Math.floor(minutos / 60);
  const restante = Math.round(minutos % 60);
  return restante ? `${horas}h ${restante}min` : `${horas}h`;
}

export function HistoricoRotasEntregador({
  rotas,
  refreshing,
  onRefresh,
  onOpen,
}: Props) {
  const [periodo, setPeriodo] = useState<Periodo>(30);
  const [ordenacao, setOrdenacao] = useState<Ordenacao>("recentes");
  const [busca, setBusca] = useState("");

  const rotasFiltradas = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase("pt-BR");
    const limite = new Date();
    if (periodo) limite.setDate(limite.getDate() - periodo);

    return rotas
      .filter((rota) => {
        const data = new Date(rota.data_conclusao || rota.created_at);
        const dentroPeriodo =
          !periodo || (!Number.isNaN(data.getTime()) && data >= limite);
        return (
          dentroPeriodo && (!termo || textoPesquisavel(rota).includes(termo))
        );
      })
      .sort((a, b) => {
        if (ordenacao === "mais_entregas") {
          return quantidadeEntregas(b) - quantidadeEntregas(a);
        }
        if (ordenacao === "maior_distancia")
          return distanciaRota(b) - distanciaRota(a);
        const dataA = new Date(a.data_conclusao || a.created_at).getTime() || 0;
        const dataB = new Date(b.data_conclusao || b.created_at).getTime() || 0;
        return ordenacao === "antigas" ? dataA - dataB : dataB - dataA;
      });
  }, [busca, ordenacao, periodo, rotas]);

  const totais = useMemo(
    () =>
      rotasFiltradas.reduce(
        (acc, rota) => ({
          entregas: acc.entregas + quantidadeEntregas(rota),
          distancia: acc.distancia + distanciaRota(rota),
          vendas: acc.vendas + Number(rota.valor_total_vendas || 0),
        }),
        { entregas: 0, distancia: 0, vendas: 0 },
      ),
    [rotasFiltradas],
  );

  const filtros = (
    <View style={styles.filtrosWrap}>
      <TextInput
        value={busca}
        onChangeText={setBusca}
        placeholder="Buscar rota, venda, cliente ou endereço"
        placeholderTextColor="#94a3b8"
        style={styles.busca}
      />
      <Text style={styles.filtroTitulo}>Período</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.chips}
      >
        {PERIODOS.map((item) => (
          <TouchableOpacity
            key={item.valor}
            style={[styles.chip, periodo === item.valor && styles.chipAtivo]}
            onPress={() => setPeriodo(item.valor)}
          >
            <Text
              style={[
                styles.chipTexto,
                periodo === item.valor && styles.chipTextoAtivo,
              ]}
            >
              {item.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
      <Text style={styles.filtroTitulo}>Ordenar</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.chips}
      >
        {ORDENACOES.map((item) => (
          <TouchableOpacity
            key={item.valor}
            style={[styles.chip, ordenacao === item.valor && styles.chipAtivo]}
            onPress={() => setOrdenacao(item.valor)}
          >
            <Text
              style={[
                styles.chipTexto,
                ordenacao === item.valor && styles.chipTextoAtivo,
              ]}
            >
              {item.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
      <View style={styles.resumo}>
        <Text style={styles.resumoDestaque}>{rotasFiltradas.length} rotas</Text>
        <Text style={styles.resumoTexto}>{totais.entregas} entregas</Text>
        <Text style={styles.resumoTexto}>{totais.distancia.toFixed(1)} km</Text>
        <Text style={styles.resumoTexto}>
          {formatarMoeda(totais.vendas)} em vendas
        </Text>
      </View>
    </View>
  );

  return (
    <FlatList
      data={rotasFiltradas}
      keyExtractor={(item) => String(item.id)}
      contentContainerStyle={
        rotasFiltradas.length ? styles.lista : styles.vazia
      }
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
      ListHeaderComponent={filtros}
      renderItem={({ item }) => {
        const quantidade = quantidadeEntregas(item);
        const distancia = distanciaRota(item);
        return (
          <TouchableOpacity
            style={styles.card}
            activeOpacity={0.78}
            onPress={() => onOpen(item)}
          >
            <View style={styles.cardHeader}>
              <View style={{ flex: 1 }}>
                <Text style={styles.cardNumero}>{item.numero}</Text>
                <Text style={styles.cardData}>
                  {formatarDataHora(item.data_conclusao)}
                </Text>
              </View>
              <View style={styles.badge}>
                <Text style={styles.badgeTexto}>Concluída</Text>
              </View>
            </View>
            <View style={styles.metricas}>
              <Text style={styles.metrica}>{quantidade} entregas</Text>
              <Text style={styles.metrica}>{distancia.toFixed(1)} km</Text>
              <Text style={styles.metrica}>
                {duracaoLabel(item.duracao_minutos)}
              </Text>
              <Text style={styles.metrica}>
                {formatarMoeda(item.valor_total_vendas)}
              </Text>
            </View>
            {item.paradas.slice(0, 2).map((parada) => (
              <View key={parada.id} style={styles.parada}>
                <Text style={styles.paradaTitulo} numberOfLines={1}>
                  {parada.ordem}. {parada.cliente_nome || "Cliente"} ·{" "}
                  {parada.numero_venda || `Venda ${parada.venda_id}`}
                </Text>
                <Text style={styles.paradaDetalhe} numberOfLines={1}>
                  {parada.endereco}
                </Text>
                <Text style={styles.paradaValor}>
                  {formatarMoeda(parada.valor_venda)} · entregue{" "}
                  {formatarDataHora(parada.data_entrega)}
                </Text>
              </View>
            ))}
            {quantidade > 2 && (
              <Text style={styles.mais}>+{quantidade - 2} entregas</Text>
            )}
          </TouchableOpacity>
        );
      }}
      ListEmptyComponent={
        <View style={styles.emptyContent}>
          <Text style={styles.emptyIcon}>📜</Text>
          <Text style={styles.emptyTitle}>Nenhuma rota concluída</Text>
          <Text style={styles.emptySubtitle}>
            Ajuste os filtros ou puxe para atualizar.
          </Text>
        </View>
      }
    />
  );
}

const styles = StyleSheet.create({
  lista: { padding: 14, gap: 12 },
  vazia: { flexGrow: 1, padding: 14 },
  filtrosWrap: { marginBottom: 12, gap: 7 },
  busca: {
    borderWidth: 1,
    borderColor: "#cbd5e1",
    backgroundColor: "#fff",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#0f172a",
  },
  filtroTitulo: {
    color: "#475569",
    fontSize: 12,
    fontWeight: "700",
    marginTop: 2,
  },
  chips: { gap: 7, paddingRight: 14 },
  chip: {
    borderWidth: 1,
    borderColor: "#cbd5e1",
    borderRadius: 999,
    paddingHorizontal: 11,
    paddingVertical: 6,
    backgroundColor: "#fff",
  },
  chipAtivo: { backgroundColor: "#1d4ed8", borderColor: "#1d4ed8" },
  chipTexto: { color: "#475569", fontSize: 12, fontWeight: "600" },
  chipTextoAtivo: { color: "#fff" },
  resumo: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 9,
    backgroundColor: "#eff6ff",
    borderRadius: 9,
    padding: 10,
    marginTop: 3,
  },
  resumoDestaque: { color: "#1d4ed8", fontWeight: "800", fontSize: 12 },
  resumoTexto: { color: "#475569", fontSize: 12 },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", gap: 8 },
  cardNumero: { color: "#0f172a", fontSize: 16, fontWeight: "800" },
  cardData: { color: "#64748b", fontSize: 12, marginTop: 2 },
  badge: {
    backgroundColor: "#dcfce7",
    borderRadius: 999,
    paddingHorizontal: 9,
    paddingVertical: 4,
  },
  badgeTexto: { color: "#166534", fontSize: 11, fontWeight: "800" },
  metricas: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 7,
    marginVertical: 10,
  },
  metrica: {
    color: "#334155",
    backgroundColor: "#f1f5f9",
    borderRadius: 6,
    padding: 5,
    fontSize: 11,
  },
  parada: {
    borderTopWidth: 1,
    borderTopColor: "#e2e8f0",
    paddingTop: 8,
    marginTop: 6,
  },
  paradaTitulo: { color: "#1e3a8a", fontWeight: "700", fontSize: 12 },
  paradaDetalhe: { color: "#64748b", fontSize: 11, marginTop: 2 },
  paradaValor: { color: "#166534", fontSize: 11, marginTop: 2 },
  mais: { color: "#64748b", fontSize: 12, fontWeight: "600", marginTop: 8 },
  emptyContent: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
  },
  emptyIcon: { fontSize: 44 },
  emptyTitle: {
    color: "#0f172a",
    fontSize: 17,
    fontWeight: "700",
    marginTop: 8,
  },
  emptySubtitle: {
    color: "#64748b",
    fontSize: 13,
    textAlign: "center",
    marginTop: 4,
  },
});
