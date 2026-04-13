import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  TextInput,
  RefreshControl,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { CatalogOrder, listarProdutos, registrarAviseme } from '../../services/shop.service';
import { useCartStore } from '../../store/cart.store';
import { useWishlistStore } from '../../store/wishlist.store';
import { useAuthStore } from '../../store/auth.store';
import { Produto } from '../../types';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { formatarMoeda } from '../../utils/format';

const ORDER_OPTIONS: Array<{ value: CatalogOrder; label: string }> = [
  { value: 'prontos', label: 'Mais prontos' },
  { value: 'nome', label: 'A-Z' },
  { value: 'menor_preco', label: 'Menor preço' },
  { value: 'maior_preco', label: 'Maior preço' },
];

function nextCatalogOrder(current: CatalogOrder): CatalogOrder {
  const currentIndex = ORDER_OPTIONS.findIndex((item) => item.value === current);
  const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % ORDER_OPTIONS.length : 0;
  return ORDER_OPTIONS[nextIndex].value;
}

export default function CatalogScreen() {
  const navigation = useNavigation<any>();
  const { adicionar, totalItens } = useCartStore();
  const { ids: wishlistIds, carregar: carregarWishlist, toggle: toggleWishlist } = useWishlistStore();
  const { user } = useAuthStore();
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [busca, setBusca] = useState('');
  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [somenteComEstoque, setSomenteComEstoque] = useState(false);
  const [somenteComImagem, setSomenteComImagem] = useState(false);
  const [ordenacao, setOrdenacao] = useState<CatalogOrder>('prontos');

  const ordenacaoLabel = useMemo(
    () => ORDER_OPTIONS.find((item) => item.value === ordenacao)?.label ?? 'Mais prontos',
    [ordenacao]
  );

  const carregar = useCallback(
    async (pg: number, q: string) => {
      if (pg === 1) setCarregando(true);

      try {
        const { produtos: novos, total: totalRecebido } = await listarProdutos({
          pagina: pg,
          busca: q || undefined,
          somenteComEstoque,
          somenteComImagem,
          ordenacao,
          cacheBust: pg === 1 ? Date.now() : undefined,
        });

        if (pg === 1) {
          setProdutos(novos);
        } else {
          setProdutos((prev) => [...prev, ...novos]);
        }

        setTotal(totalRecebido);
        setPagina(pg);
      } catch {
        if (pg === 1) {
          setProdutos([]);
          setTotal(0);
        }
      } finally {
        setCarregando(false);
      }
    },
    [ordenacao, somenteComEstoque, somenteComImagem]
  );

  useEffect(() => {
    carregarWishlist();
  }, []);

  useEffect(() => {
    carregar(1, busca);
  }, [carregar]);

  async function onRefresh() {
    setRefreshing(true);
    await carregar(1, busca);
    setRefreshing(false);
  }

  function onBusca(texto: string) {
    setBusca(texto);
    if (texto.length === 0 || texto.length >= 2) {
      carregar(1, texto);
    }
  }

  function carregarMais() {
    if (!carregando && produtos.length < total) {
      carregar(pagina + 1, busca);
    }
  }

  function renderProduto({ item }: { item: Produto }) {
    const estoqueDisponivel = Number(item.estoque ?? 0);
    const semEstoque = Number.isFinite(estoqueDisponivel) && estoqueDisponivel <= 0;
    const preco = item.promocao_ativa && item.preco_promocional ? item.preco_promocional : item.preco;
    const temPromocao = item.promocao_ativa && !!item.preco_promocional;
    const naWishlist = wishlistIds.includes(item.id);

    return (
      <View style={[styles.card, semEstoque && styles.cardIndisponivel]}>
        <TouchableOpacity
          style={styles.cardTopo}
          onPress={() => navigation.navigate('DetalhesProduto', { produto: item })}
          activeOpacity={0.85}
        >
          {item.foto_url ? (
            <Image source={{ uri: item.foto_url }} style={styles.foto} resizeMode="contain" />
          ) : (
            <View style={[styles.foto, styles.fotoPlaceholder]}>
              <Ionicons name="image-outline" size={34} color={CORES.textoClaro} />
            </View>
          )}

          {temPromocao && !semEstoque && (
            <View style={styles.badgePromocao}>
              <Text style={styles.badgeTexto}>Oferta</Text>
            </View>
          )}

          {semEstoque && (
            <View style={styles.badgeIndisponivel}>
              <Text style={styles.badgeTexto}>Indisponível</Text>
            </View>
          )}

          <TouchableOpacity
            style={styles.botaoWishlist}
            onPress={() => {
              toggleWishlist(item.id);
            }}
          >
            <Ionicons
              name={naWishlist ? 'heart' : 'heart-outline'}
              size={16}
              color={naWishlist ? '#DC2626' : CORES.primario}
            />
          </TouchableOpacity>
        </TouchableOpacity>

        <View style={styles.cardInfo}>
          <Text style={styles.produtoNome} numberOfLines={2}>
            {item.nome}
          </Text>

          {item.categoria_nome ? <Text style={styles.categoriaTexto}>{item.categoria_nome}</Text> : null}
          {item.codigo ? <Text style={styles.skuTexto}>SKU: {item.codigo}</Text> : null}

          <Text style={[styles.estoqueTexto, semEstoque && styles.estoqueZero]}>
            {semEstoque
              ? 'Volta em breve'
              : Number.isFinite(estoqueDisponivel) && estoqueDisponivel > 0
                ? `Em estoque: ${estoqueDisponivel}`
                : 'Disponível'}
          </Text>

          <View style={styles.precoRow}>
            {temPromocao && <Text style={styles.precoOriginal}>{formatarMoeda(item.preco)}</Text>}
            <Text style={[styles.preco, semEstoque && styles.precoIndisponivel]}>{formatarMoeda(preco)}</Text>
          </View>

          {semEstoque ? (
            <TouchableOpacity
              style={styles.botaoAviseme}
              onPress={async () => {
                if (!user?.email) {
                  Alert.alert(
                    'Entre na sua conta',
                    'Para receber o aviso quando o produto voltar ao estoque, faça login primeiro.',
                    [{ text: 'OK' }]
                  );
                  return;
                }

                try {
                  const res = await registrarAviseme(user.email, item.id, item.nome);
                  Alert.alert('Tudo certo', res.message || 'Você será avisado por e-mail quando o produto voltar.');
                } catch {
                  Alert.alert('Erro', 'Não foi possível registrar o aviso. Tente novamente.');
                }
              }}
            >
              <Ionicons name="notifications-outline" size={14} color="#D97706" />
              <Text style={styles.botaoAvisemeTexto}>Avise-me quando chegar</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={styles.botaoAdicionar}
              onPress={async () => {
                try {
                  await adicionar(item, 1);
                } catch {
                  Alert.alert('Erro', 'Não foi possível adicionar ao carrinho.');
                }
              }}
            >
              <Ionicons name="add" size={16} color="#fff" />
              <Text style={styles.botaoAdicionarTexto}>Adicionar</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.buscaRow}>
        <View style={styles.buscaContainer}>
          <Ionicons name="search-outline" size={18} color={CORES.textoClaro} style={{ marginRight: 6 }} />
          <TextInput
            style={styles.buscaInput}
            placeholder="Buscar produtos..."
            placeholderTextColor={CORES.textoClaro}
            value={busca}
            onChangeText={onBusca}
            returnKeyType="search"
          />
          {busca.length > 0 && (
            <TouchableOpacity onPress={() => onBusca('')}>
              <Ionicons name="close-circle" size={18} color={CORES.textoClaro} />
            </TouchableOpacity>
          )}
        </View>

        <TouchableOpacity style={styles.botaoScanner} onPress={() => navigation.navigate('BarcodeScanner')}>
          <Ionicons name="barcode-outline" size={22} color={CORES.primario} />
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.botaoScanner, { backgroundColor: CORES.primario }]}
          onPress={() => navigation.navigate('Carrinho')}
        >
          <Ionicons name="cart-outline" size={22} color="#fff" />
          {totalItens() > 0 && (
            <View style={styles.badge}>
              <Text style={styles.badgeNum}>{totalItens()}</Text>
            </View>
          )}
        </TouchableOpacity>
      </View>

      <View style={styles.filtrosContainer}>
        <View style={styles.filtrosRow}>
          <TouchableOpacity
            style={[styles.filtroChip, somenteComEstoque && styles.filtroChipAtivo]}
            onPress={() => setSomenteComEstoque((value) => !value)}
          >
            <Text style={[styles.filtroChipTexto, somenteComEstoque && styles.filtroChipTextoAtivo]}>
              Em estoque
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.filtroChip, somenteComImagem && styles.filtroChipAtivo]}
            onPress={() => setSomenteComImagem((value) => !value)}
          >
            <Text style={[styles.filtroChipTexto, somenteComImagem && styles.filtroChipTextoAtivo]}>
              Com foto
            </Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.filtroChip} onPress={() => setOrdenacao((value) => nextCatalogOrder(value))}>
            <Text style={styles.filtroChipTexto}>{ordenacaoLabel}</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.resumoCatalogo}>
          Mostrando {produtos.length} de {total || produtos.length} produtos
        </Text>
      </View>

      {carregando && pagina === 1 ? (
        <View style={styles.loading}>
          <ActivityIndicator size="large" color={CORES.primario} />
        </View>
      ) : (
        <FlatList
          data={produtos}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderProduto}
          numColumns={2}
          columnWrapperStyle={styles.colunaPar}
          contentContainerStyle={styles.lista}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={CORES.primario} />}
          onEndReached={carregarMais}
          onEndReachedThreshold={0.5}
          ListEmptyComponent={
            <View style={styles.vazio}>
              <Ionicons name="search-outline" size={36} color={CORES.textoClaro} />
              <Text style={styles.vazioTexto}>Nenhum produto encontrado.</Text>
              <Text style={styles.vazioSubtexto}>Tente buscar com outro termo ou ajustar os filtros.</Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  buscaRow: {
    flexDirection: 'row',
    gap: ESPACO.sm,
    padding: ESPACO.md,
    paddingBottom: ESPACO.sm,
    backgroundColor: CORES.superficie,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
  },
  buscaContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.sm,
    backgroundColor: CORES.fundo,
  },
  buscaInput: { flex: 1, fontSize: FONTE.normal, color: CORES.texto, paddingVertical: 8 },
  botaoScanner: {
    width: 42,
    height: 42,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.primario,
    justifyContent: 'center',
    alignItems: 'center',
  },
  badge: {
    position: 'absolute',
    top: -4,
    right: -4,
    backgroundColor: CORES.secundario,
    borderRadius: 10,
    minWidth: 16,
    height: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  badgeNum: { color: '#fff', fontSize: 10, fontWeight: 'bold' },
  filtrosContainer: {
    paddingHorizontal: ESPACO.md,
    paddingBottom: ESPACO.sm,
    backgroundColor: CORES.superficie,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
  },
  filtrosRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: ESPACO.xs,
  },
  filtroChip: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#fff',
  },
  filtroChipAtivo: {
    borderColor: '#16A34A',
    backgroundColor: '#F0FDF4',
  },
  filtroChipTexto: {
    fontSize: 12,
    fontWeight: '600',
    color: CORES.textoSecundario,
  },
  filtroChipTextoAtivo: {
    color: '#166534',
  },
  resumoCatalogo: {
    marginTop: ESPACO.xs,
    fontSize: 12,
    color: CORES.textoClaro,
  },
  lista: { padding: ESPACO.sm, paddingBottom: ESPACO.lg },
  colunaPar: { justifyContent: 'space-between', paddingHorizontal: ESPACO.xs },
  card: {
    width: '48%',
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    marginBottom: ESPACO.sm,
    overflow: 'hidden',
    ...SOMBRA,
  },
  cardIndisponivel: { opacity: 0.86 },
  cardTopo: { position: 'relative' },
  foto: { width: '100%', height: 130 },
  fotoPlaceholder: {
    backgroundColor: CORES.primarioClaro,
    justifyContent: 'center',
    alignItems: 'center',
  },
  badgePromocao: {
    position: 'absolute',
    top: 8,
    left: 8,
    backgroundColor: CORES.secundario,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: RAIO.circulo,
  },
  badgeIndisponivel: {
    position: 'absolute',
    top: 8,
    left: 8,
    backgroundColor: '#D97706',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: RAIO.circulo,
  },
  badgeTexto: { color: '#fff', fontSize: FONTE.pequena, fontWeight: 'bold' },
  botaoWishlist: {
    position: 'absolute',
    top: 6,
    right: 6,
    backgroundColor: '#fff',
    borderRadius: 20,
    width: 30,
    height: 30,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.15,
    shadowRadius: 2,
    elevation: 2,
  },
  cardInfo: { padding: ESPACO.sm },
  produtoNome: {
    fontSize: FONTE.normal,
    fontWeight: '600',
    color: CORES.texto,
    marginBottom: 2,
    lineHeight: 18,
  },
  categoriaTexto: { fontSize: 10, color: CORES.textoClaro, marginBottom: 1 },
  skuTexto: { fontSize: 10, color: CORES.textoClaro, marginBottom: 2 },
  estoqueTexto: { fontSize: 10, color: '#10B981', fontWeight: '500', marginBottom: 4 },
  estoqueZero: { color: '#D97706' },
  precoRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: ESPACO.sm },
  precoOriginal: {
    fontSize: FONTE.pequena,
    color: CORES.textoClaro,
    textDecorationLine: 'line-through',
  },
  preco: { fontSize: FONTE.normal, fontWeight: 'bold', color: CORES.primario },
  precoIndisponivel: { color: CORES.textoClaro },
  botaoAdicionar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: CORES.primario,
    borderRadius: RAIO.sm,
    paddingVertical: 7,
    gap: 4,
  },
  botaoAdicionarTexto: { color: '#fff', fontSize: FONTE.pequena, fontWeight: '600' },
  botaoAviseme: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    borderWidth: 1,
    borderColor: '#D97706',
    borderRadius: RAIO.sm,
    paddingVertical: 7,
  },
  botaoAvisemeTexto: { color: '#D97706', fontSize: 10, fontWeight: '600' },
  loading: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  vazio: { alignItems: 'center', paddingTop: 60, gap: 8 },
  vazioTexto: { fontSize: FONTE.grande, fontWeight: '600', color: CORES.textoSecundario },
  vazioSubtexto: { fontSize: FONTE.normal, color: CORES.textoClaro, textAlign: 'center' },
});
