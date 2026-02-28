import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { listarPedidos, repetirPedido } from '../../services/shop.service';
import { useCartStore } from '../../store/cart.store';
import { Pedido } from '../../types';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { formatarMoeda, formatarDataHora } from '../../utils/format';

const STATUS_CONFIG: Record<string, { cor: string; corTexto: string; label: string; emoji: string }> = {
  pendente: { cor: '#FEF3C7', corTexto: '#92400E', label: 'Pendente', emoji: '⏳' },
  pago: { cor: '#D1FAE5', corTexto: '#065F46', label: 'Pago', emoji: '✅' },
  em_preparo: { cor: '#DBEAFE', corTexto: '#1E40AF', label: 'Em preparo', emoji: '📦' },
  pronto: { cor: '#D1FAE5', corTexto: '#065F46', label: 'Pronto', emoji: '🎉' },
  entregue: { cor: '#F3F4F6', corTexto: '#374151', label: 'Entregue', emoji: '📬' },
  cancelado: { cor: '#FEE2E2', corTexto: '#991B1B', label: 'Cancelado', emoji: '❌' },
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
        '🛒 Carrinho atualizado',
        `${adicionados} de ${pedido.itens.length} produto(s) foram adicionados ao carrinho.`,
        [
          { text: 'Continuar comprando', style: 'cancel' },
          {
            text: 'Ver carrinho',
            onPress: () => navigation.navigate('Loja', { screen: 'Carrinho' })
          },
        ]
      );
    } catch {
      Alert.alert('Erro', 'Não foi possível repetir o pedido. Tente novamente.');
    } finally {
      setRepetindo(null);
    }
  }

  useFocusEffect(
    useCallback(() => {
      carregar();
    }, [])
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

  function renderPedido({ item }: { item: Pedido }) {
    const cfg = STATUS_CONFIG[item.status] ?? STATUS_CONFIG.pendente;
    const temPalavraChave = item.palavra_chave_retirada;

    return (
      <View style={styles.card}>
        {/* Cabeçalho */}
        <View style={styles.cardHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.pedidoId}>#{item.pedido_id.slice(-8).toUpperCase()}</Text>
            <Text style={styles.pedidoData}>{formatarDataHora(item.created_at)}</Text>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: cfg.cor }]}>
            <Text style={{ fontSize: 12 }}>{cfg.emoji}</Text>
            <Text style={[styles.statusTexto, { color: cfg.corTexto }]}>{cfg.label}</Text>
          </View>
        </View>

        {/* Itens */}
        <View style={styles.itensList}>
          {item.itens?.slice(0, 3).map((it, idx) => (
            <Text key={idx} style={styles.itemTexto} numberOfLines={1}>
              {it.quantidade}x {it.nome}
            </Text>
          ))}
          {(item.itens?.length ?? 0) > 3 && (
            <Text style={styles.itemMais}>+{item.itens.length - 3} outros</Text>
          )}
        </View>

        {/* Palavra-chave */}
        {temPalavraChave && item.status === 'pendente' && (
          <View style={styles.palavraChaveBox}>
            <Ionicons name="key-outline" size={16} color={CORES.primario} />
            <Text style={styles.palavraChaveLabel}>Palavra-chave: </Text>
            <Text style={styles.palavraChaveValor}>
              {item.palavra_chave_retirada?.toUpperCase()}
            </Text>
          </View>
        )}

        {/* Total e botão repetir */}
        <View style={styles.cardRodape}>
          <View>
            <Text style={styles.totalLabel}>Total</Text>
            <Text style={styles.totalValor}>{formatarMoeda(item.total)}</Text>
          </View>
          <TouchableOpacity
            style={[styles.btnRepetir, repetindo === item.pedido_id && { opacity: 0.6 }]}
            onPress={() => handleRepetirPedido(item)}
            disabled={repetindo === item.pedido_id}
          >
            {repetindo === item.pedido_id
              ? <ActivityIndicator size="small" color={CORES.primario} />
              : <>
                  <Ionicons name="refresh-outline" size={14} color={CORES.primario} />
                  <Text style={styles.btnRepetirTexto}>Repetir</Text>
                </>
            }
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  if (carregando) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color={CORES.primario} />
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
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={CORES.primario} />
      }
      ListEmptyComponent={
        <View style={styles.vazio}>
          <Text style={styles.vazioEmoji}>📦</Text>
          <Text style={styles.vazioTitulo}>Nenhum pedido ainda</Text>
          <Text style={styles.vazioTexto}>Seus pedidos aparecerão aqui.</Text>
        </View>
      }
    />
  );
}

const styles = StyleSheet.create({
  loading: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  lista: { padding: ESPACO.md },
  card: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginBottom: ESPACO.sm,
    ...SOMBRA,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: ESPACO.sm },
  pedidoId: { fontSize: FONTE.normal, fontWeight: 'bold', color: CORES.texto },
  pedidoData: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: ESPACO.sm,
    paddingVertical: 4,
    borderRadius: RAIO.circulo,
    gap: 4,
  },
  statusTexto: { fontSize: FONTE.pequena, fontWeight: '600' },
  itensList: { marginBottom: ESPACO.sm },
  itemTexto: { fontSize: FONTE.normal, color: CORES.textoSecundario },
  itemMais: { fontSize: FONTE.pequena, color: CORES.textoClaro, marginTop: 2 },
  palavraChaveBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: CORES.primarioClaro,
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
    marginBottom: ESPACO.sm,
    gap: 4,
  },
  palavraChaveLabel: { fontSize: FONTE.normal, color: CORES.primario },
  palavraChaveValor: { fontSize: FONTE.normal, fontWeight: 'bold', color: CORES.primario },
  cardRodape: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: CORES.borda,
    paddingTop: ESPACO.sm,
    marginTop: ESPACO.xs,
  },
  totalLabel: { fontSize: FONTE.normal, color: CORES.textoSecundario },
  totalValor: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto },
  btnRepetir: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm - 2,
    borderWidth: 1,
    borderColor: CORES.primario,
    borderRadius: RAIO.circulo,
  },
  btnRepetirTexto: { fontSize: FONTE.pequena, color: CORES.primario, fontWeight: '600' },
  vazio: { alignItems: 'center', paddingTop: 80, gap: 12 },
  vazioEmoji: { fontSize: 60 },
  vazioTitulo: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto },
  vazioTexto: { fontSize: FONTE.normal, color: CORES.textoSecundario },
});
