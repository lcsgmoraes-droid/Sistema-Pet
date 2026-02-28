import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { useWishlistStore } from '../../store/wishlist.store';
import { useCartStore } from '../../store/cart.store';
import { listarProdutos } from '../../services/shop.service';
import { Produto } from '../../types';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { formatarMoeda } from '../../utils/format';

export default function WishlistScreen() {
  const navigation = useNavigation<any>();
  const { ids, carregar: carregarWishlist, toggle } = useWishlistStore();
  const { adicionar } = useCartStore();
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [adicionando, setAdicionando] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useFocusEffect(
    useCallback(() => {
      carregarFavoritos();
    }, [ids])
  );

  async function carregarFavoritos() {
    setCarregando(true);
    try {
      await carregarWishlist();
      if (ids.length === 0) {
        setProdutos([]);
        return;
      }
      const { produtos: todos } = await listarProdutos();
      setProdutos(todos.filter((p) => ids.includes(p.id)));
    } catch {}
    setCarregando(false);
  }

  async function onRefresh() {
    setRefreshing(true);
    await carregarFavoritos();
    setRefreshing(false);
  }

  async function handleAdicionarCarrinho(produto: Produto) {
    setAdicionando(produto.id);
    try {
      await adicionar(produto, 1);
      navigation.navigate('Loja', { screen: 'Carrinho' });
    } catch {
      // silencioso
    } finally {
      setAdicionando(null);
    }
  }

  function renderItem({ item }: { item: Produto }) {
    const disponivel = (item.estoque_ecommerce ?? item.estoque ?? 0) > 0;
    return (
      <View style={styles.card}>
        {/* Foto */}
        <View style={styles.fotoBox}>
          {item.foto_url ? (
            <Image source={{ uri: item.foto_url }} style={styles.foto} resizeMode="contain" />
          ) : (
            <View style={[styles.foto, styles.fotoPlaceholder]}>
              <Text style={{ fontSize: 32 }}>🛍️</Text>
            </View>
          )}
          {/* Botão remover dos favoritos */}
          <TouchableOpacity
            style={styles.btnCoracao}
            onPress={() => toggle(item.id)}
          >
            <Ionicons name="heart" size={20} color={CORES.secundario} />
          </TouchableOpacity>
        </View>

        {/* Info */}
        <View style={styles.info}>
          <Text style={styles.nome} numberOfLines={2}>{item.nome}</Text>
          {item.marca_nome && (
            <Text style={styles.marca}>{item.marca_nome}</Text>
          )}
          <View style={styles.precoRow}>
            {item.promocao_ativa && item.preco_promocional ? (
              <>
                <Text style={styles.precoOriginal}>{formatarMoeda(item.preco)}</Text>
                <Text style={styles.precoPromo}>{formatarMoeda(item.preco_promocional)}</Text>
              </>
            ) : (
              <Text style={styles.preco}>{formatarMoeda(item.preco)}</Text>
            )}
          </View>

          {disponivel ? (
            <TouchableOpacity
              style={[styles.btnCarrinho, adicionando === item.id && { opacity: 0.7 }]}
              onPress={() => handleAdicionarCarrinho(item)}
              disabled={adicionando === item.id}
            >
              {adicionando === item.id ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <>
                  <Ionicons name="cart-outline" size={16} color="#fff" />
                  <Text style={styles.btnCarrinhoTexto}>Adicionar</Text>
                </>
              )}
            </TouchableOpacity>
          ) : (
            <View style={styles.indisponivel}>
              <Text style={styles.indisponivelTexto}>Indisponível</Text>
            </View>
          )}
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
      data={produtos}
      keyExtractor={(item) => String(item.id)}
      renderItem={renderItem}
      numColumns={2}
      contentContainerStyle={styles.lista}
      columnWrapperStyle={styles.row}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={CORES.primario} />
      }
      ListEmptyComponent={
        <View style={styles.vazio}>
          <Ionicons name="heart-outline" size={64} color={CORES.borda} />
          <Text style={styles.vazioTitulo}>Nenhum favorito ainda</Text>
          <Text style={styles.vazioTexto}>
            Toque no ❤️ em qualquer produto para salvá-lo aqui.
          </Text>
          <TouchableOpacity
            style={styles.btnVerLoja}
            onPress={() => navigation.navigate('Loja')}
          >
            <Text style={styles.btnVerLojaTexto}>Ver produtos</Text>
          </TouchableOpacity>
        </View>
      }
    />
  );
}

const styles = StyleSheet.create({
  loading: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  lista: { padding: ESPACO.sm, paddingBottom: ESPACO.xl },
  row: { gap: ESPACO.sm },
  card: {
    flex: 1,
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    marginBottom: ESPACO.sm,
    overflow: 'hidden',
    ...SOMBRA,
  },
  fotoBox: {
    position: 'relative',
    backgroundColor: '#F9FAFB',
    height: 130,
    alignItems: 'center',
    justifyContent: 'center',
  },
  foto: { width: '100%', height: 130 },
  fotoPlaceholder: { justifyContent: 'center', alignItems: 'center' },
  btnCoracao: {
    position: 'absolute',
    top: 6,
    right: 6,
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  info: { padding: ESPACO.sm },
  nome: { fontSize: FONTE.pequena, fontWeight: '600', color: CORES.texto, marginBottom: 2 },
  marca: { fontSize: FONTE.pequena - 1, color: CORES.textoClaro, marginBottom: ESPACO.xs },
  precoRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: ESPACO.sm },
  preco: { fontSize: FONTE.normal, fontWeight: 'bold', color: CORES.texto },
  precoOriginal: { fontSize: FONTE.pequena, color: CORES.textoClaro, textDecorationLine: 'line-through' },
  precoPromo: { fontSize: FONTE.normal, fontWeight: 'bold', color: CORES.sucesso },
  btnCarrinho: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    backgroundColor: CORES.primario,
    borderRadius: RAIO.sm,
    paddingVertical: 6,
  },
  btnCarrinhoTexto: { fontSize: FONTE.pequena, color: '#fff', fontWeight: '600' },
  indisponivel: {
    backgroundColor: '#F3F4F6',
    borderRadius: RAIO.sm,
    paddingVertical: 6,
    alignItems: 'center',
  },
  indisponivelTexto: { fontSize: FONTE.pequena, color: CORES.textoClaro },
  vazio: { alignItems: 'center', paddingTop: 80, paddingHorizontal: ESPACO.xl, gap: ESPACO.md },
  vazioTitulo: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto },
  vazioTexto: { fontSize: FONTE.normal, color: CORES.textoSecundario, textAlign: 'center' },
  btnVerLoja: {
    backgroundColor: CORES.primario,
    paddingHorizontal: ESPACO.xl,
    paddingVertical: ESPACO.md - 2,
    borderRadius: RAIO.md,
    marginTop: ESPACO.sm,
  },
  btnVerLojaTexto: { color: '#fff', fontWeight: 'bold', fontSize: FONTE.normal },
});
