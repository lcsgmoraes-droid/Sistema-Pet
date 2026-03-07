import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useNavigation } from "@react-navigation/native";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { listarPedidos, repetirPedido } from "../../services/shop.service";
import { useCartStore } from "../../store/cart.store";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import { Pedido } from "../../types";
import { formatarDataHora, formatarMoeda } from "../../utils/format";

const STATUS_CONFIG: Record<
  string,
  { cor: string; corTexto: string; label: string; emoji: string; icone: string }
> = {
  pendente: {
    cor: "#FEF3C7",
    corTexto: "#78350F",
    label: "Aguardando pagamento",
    emoji: "⏳",
    icone: "time-outline",
  },
  pago: {
    cor: "#D1FAE5",
    corTexto: "#065F46",
    label: "Pago",
    emoji: "💳",
    icone: "checkmark-circle-outline",
  },
  em_preparo: {
    cor: "#DBEAFE",
    corTexto: "#1E40AF",
    label: "Em preparo",
    emoji: "📦",
    icone: "construct-outline",
  },
  pronto: {
    cor: "#D1FAE5",
    corTexto: "#065F46",
    label: "Pronto para retirada",
    emoji: "🎉",
    icone: "bag-check-outline",
  },
  entregue: {
    cor: "#F3F4F6",
    corTexto: "#374151",
    label: "Entregue",
    emoji: "📬",
    icone: "home-outline",
  },
  aprovado: {
    cor: "#D1FAE5",
    corTexto: "#065F46",
    label: "Confirmado",
    emoji: "✅",
    icone: "checkmark-done-outline",
  },
  cancelado: {
    cor: "#FEE2E2",
    corTexto: "#991B1B",
    label: "Cancelado",
    emoji: "❌",
    icone: "close-circle-outline",
  },
  criado: {
    cor: "#E0E7FF",
    corTexto: "#3730A3",
    label: "Recebido",
    emoji: "🛍️",
    icone: "receipt-outline",
  },
};

const STATUS_ENTREGA: Record<string, { label: string; cor: string }> = {
  pendente: { label: "Despacho pendente", cor: "#F59E0B" },
  em_andamento: { label: "🛵 Entregador a caminho", cor: "#3B82F6" },
  em_rota: { label: "🛵 Em rota", cor: "#3B82F6" },
  entregue: { label: "✅ Entregue", cor: "#10B981" },
};

export default function OrdersScreen() {
  const navigation = useNavigation<any>();
  const { carregar: recarregarCarrinho } = useCartStore();
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [repetindo, setRepetindo] = useState<string | null>(null);

  async function handleRepetirPedido(pedido: Pedido) {
    setRepetindo(pedido.pedido_id);
    try {
      const adicionados = await repetirPedido(pedido);
      await recarregarCarrinho();
      Alert.alert(
        "🛒 Carrinho atualizado",
        `${adicionados} de ${pedido.itens.length} produto(s) foram adicionados ao carrinho.`,
        [
          { text: "Continuar comprando", style: "cancel" },
          {
            text: "Ver carrinho",
            onPress: () => navigation.navigate("Loja", { screen: "Carrinho" }),
          },
        ],
      );
    } catch {
      Alert.alert(
        "Erro",
        "Não foi possível repetir o pedido. Tente novamente.",
      );
    } finally {
      setRepetindo(null);
    }
  }

  useFocusEffect(
    useCallback(() => {
      carregar();
    }, []),
  );

  async function carregar() {
    try {
      const lista = await listarPedidos();
      setPedidos(lista);
    } catch {}
    setCarregando(false);
  }

  async function onRefresh() {
    setRefreshing(true);
    await carregar();
    setRefreshing(false);
  }

  function handleRastrear(pedido: Pedido) {
    navigation.navigate("Rastreio", { pedidoId: pedido.pedido_id });
  }

  function renderPedido({ item }: { item: Pedido }) {
    const cfg = STATUS_CONFIG[item.status] ?? STATUS_CONFIG.pendente;
    const temEntrega = (item as any).tem_entrega;
    const statusEntrega = (item as any).status_entrega;
    const entregaCfg = statusEntrega ? STATUS_ENTREGA[statusEntrega] : null;
    const temPalavraChave =
      item.palavra_chave_retirada && item.status === "pendente";
    const podeRastrear =
      temEntrega &&
      ["aprovado", "em_preparo", "pronto", "pago", "criado"].includes(
        item.status,
      );

    return (
      <View style={styles.card}>
        {/* Cabeçalho */}
        <View style={styles.cardHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.pedidoId}>
              #{item.pedido_id.slice(-8).toUpperCase()}
            </Text>
            <Text style={styles.pedidoData}>
              {formatarDataHora(item.created_at)}
            </Text>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: cfg.cor }]}>
            <Ionicons name={cfg.icone as any} size={13} color={cfg.corTexto} />
            <Text style={[styles.statusTexto, { color: cfg.corTexto }]}>
              {cfg.label}
            </Text>
          </View>
        </View>

        {/* Badge de entrega (quando em rota) */}
        {entregaCfg && (
          <View
            style={[
              styles.entregaBadge,
              { backgroundColor: entregaCfg.cor + "20" },
            ]}
          >
            <Text style={[styles.entregaBadgeText, { color: entregaCfg.cor }]}>
              {entregaCfg.label}
            </Text>
          </View>
        )}

        {/* Itens */}
        <View style={styles.itensList}>
          {item.itens?.slice(0, 3).map((it, idx) => (
            <View key={idx} style={styles.itemLinha}>
              <View style={styles.itemQtdBadge}>
                <Text style={styles.itemQtd}>{it.quantidade}x</Text>
              </View>
              <Text style={styles.itemNome} numberOfLines={1}>
                {it.nome}
              </Text>
            </View>
          ))}
          {(item.itens?.length ?? 0) > 3 && (
            <Text style={styles.itemMais}>
              +{item.itens.length - 3} outros itens
            </Text>
          )}
        </View>

        {/* Palavra-chave retirada */}
        {temPalavraChave && (
          <View style={styles.palavraChaveBox}>
            <Ionicons name="key" size={16} color={CORES.primario} />
            <View>
              <Text style={styles.palavraChaveLabel}>
                Fale no caixa para retirar:
              </Text>
              <Text style={styles.palavraChaveValor}>
                {item.palavra_chave_retirada?.toUpperCase()}
              </Text>
            </View>
          </View>
        )}

        {/* Rodapé */}
        <View style={styles.cardRodape}>
          <View>
            <Text style={styles.totalLabel}>Total</Text>
            <Text style={styles.totalValor}>{formatarMoeda(item.total)}</Text>
          </View>
          <View style={styles.acoes}>
            {podeRastrear && (
              <TouchableOpacity
                style={styles.btnRastrear}
                onPress={() => handleRastrear(item)}
              >
                <Ionicons name="navigate" size={14} color="#fff" />
                <Text style={styles.btnRastrearTexto}>Rastrear</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity
              style={[
                styles.btnRepetir,
                repetindo === item.pedido_id && { opacity: 0.6 },
              ]}
              onPress={() => handleRepetirPedido(item)}
              disabled={repetindo === item.pedido_id}
            >
              {repetindo === item.pedido_id ? (
                <ActivityIndicator size="small" color={CORES.primario} />
              ) : (
                <>
                  <Ionicons
                    name="refresh-outline"
                    size={14}
                    color={CORES.primario}
                  />
                  <Text style={styles.btnRepetirTexto}>Repetir</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </View>
    );
  }

  if (carregando) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color={CORES.primario} />
        <Text style={styles.loadingText}>Carregando pedidos...</Text>
      </View>
    );
  }

  return (
    <FlatList
      data={pedidos}
      keyExtractor={(item) => item.pedido_id}
      renderItem={renderPedido}
      contentContainerStyle={styles.lista}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={CORES.primario}
        />
      }
      ListHeaderComponent={
        pedidos.length > 0 ? (
          <View style={styles.header}>
            <Ionicons name="receipt-outline" size={24} color={CORES.primario} />
            <View>
              <Text style={styles.headerTitulo}>Meus Pedidos</Text>
              <Text style={styles.headerSub}>
                {pedidos.length} {pedidos.length === 1 ? "pedido" : "pedidos"}
              </Text>
            </View>
          </View>
        ) : null
      }
      ListEmptyComponent={
        <View style={styles.vazio}>
          <Text style={styles.vazioEmoji}>🛍️</Text>
          <Text style={styles.vazioTitulo}>Nenhum pedido ainda</Text>
          <Text style={styles.vazioTexto}>
            Seus pedidos aparecerão aqui assim que você finalizar uma compra.
          </Text>
          <TouchableOpacity
            style={styles.btnComprar}
            onPress={() => navigation.navigate("Loja", { screen: "Catalogo" })}
          >
            <Ionicons name="storefront-outline" size={16} color="#fff" />
            <Text style={styles.btnComprarTexto}>Ver produtos</Text>
          </TouchableOpacity>
        </View>
      }
    />
  );
}

const styles = StyleSheet.create({
  loading: { flex: 1, justifyContent: "center", alignItems: "center", gap: 12 },
  loadingText: { fontSize: FONTE.normal, color: CORES.textoSecundario },
  lista: { padding: ESPACO.md, paddingBottom: 40 },

  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    marginBottom: ESPACO.sm,
    paddingBottom: ESPACO.sm,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
  },
  headerTitulo: {
    fontSize: FONTE.grande,
    fontWeight: "700",
    color: CORES.texto,
  },
  headerSub: { fontSize: FONTE.pequena, color: CORES.textoSecundario },

  card: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginBottom: ESPACO.sm,
    ...SOMBRA,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: ESPACO.sm,
  },
  pedidoId: {
    fontSize: FONTE.normal,
    fontWeight: "700",
    color: CORES.texto,
    letterSpacing: 0.5,
  },
  pedidoData: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
    marginTop: 2,
  },
  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: ESPACO.sm,
    paddingVertical: 4,
    borderRadius: RAIO.circulo,
    gap: 4,
    maxWidth: 180,
  },
  statusTexto: { fontSize: 11, fontWeight: "600" },

  entregaBadge: {
    borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: 5,
    marginBottom: ESPACO.sm,
    alignSelf: "flex-start",
  },
  entregaBadgeText: { fontSize: FONTE.pequena, fontWeight: "700" },

  itensList: { marginBottom: ESPACO.sm, gap: 4 },
  itemLinha: { flexDirection: "row", alignItems: "center", gap: 8 },
  itemQtdBadge: {
    backgroundColor: CORES.fundo,
    borderRadius: RAIO.sm,
    paddingHorizontal: 6,
    paddingVertical: 2,
    minWidth: 32,
    alignItems: "center",
  },
  itemQtd: { fontSize: 11, fontWeight: "700", color: CORES.primario },
  itemNome: { fontSize: FONTE.normal, color: CORES.textoSecundario, flex: 1 },
  itemMais: {
    fontSize: FONTE.pequena,
    color: CORES.textoClaro,
    marginTop: 2,
    marginLeft: 40,
  },

  palavraChaveBox: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: CORES.primarioClaro,
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
    marginBottom: ESPACO.sm,
    gap: ESPACO.sm,
  },
  palavraChaveLabel: { fontSize: 11, color: CORES.primario },
  palavraChaveValor: {
    fontSize: FONTE.grande,
    fontWeight: "800",
    color: CORES.primario,
    letterSpacing: 2,
  },

  cardRodape: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderTopWidth: 1,
    borderTopColor: CORES.borda,
    paddingTop: ESPACO.sm,
    marginTop: ESPACO.xs,
  },
  totalLabel: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  totalValor: { fontSize: FONTE.grande, fontWeight: "800", color: CORES.texto },
  acoes: { flexDirection: "row", gap: 8 },
  btnRastrear: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm - 2,
    backgroundColor: CORES.primario,
    borderRadius: RAIO.circulo,
  },
  btnRastrearTexto: {
    fontSize: FONTE.pequena,
    color: "#fff",
    fontWeight: "700",
  },
  btnRepetir: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm - 2,
    borderWidth: 1.5,
    borderColor: CORES.primario,
    borderRadius: RAIO.circulo,
  },
  btnRepetirTexto: {
    fontSize: FONTE.pequena,
    color: CORES.primario,
    fontWeight: "600",
  },

  vazio: {
    alignItems: "center",
    paddingTop: 80,
    paddingHorizontal: 40,
    gap: 12,
  },
  vazioEmoji: { fontSize: 64 },
  vazioTitulo: {
    fontSize: FONTE.grande,
    fontWeight: "700",
    color: CORES.texto,
  },
  vazioTexto: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    textAlign: "center",
    lineHeight: 22,
  },
  btnComprar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: CORES.primario,
    paddingHorizontal: ESPACO.lg,
    paddingVertical: ESPACO.sm + 2,
    borderRadius: RAIO.circulo,
    marginTop: 8,
  },
  btnComprarTexto: { fontSize: FONTE.normal, color: "#fff", fontWeight: "700" },
});
