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
  Modal,
  ScrollView,
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
  { value: 'prontos', label: 'Relevância' },
  { value: 'nome', label: 'A-Z' },
  { value: 'menor_preco', label: 'Menor preço' },
  { value: 'maior_preco', label: 'Maior preço' },
];

type EspecieFiltro = 'todos' | 'cao' | 'gato';
type PesoPetFiltro = 'todos' | 'ate3' | 'ate10' | 'ate15' | 'acima15';

type CatalogoFiltros = {
  especie: EspecieFiltro;
  pesoPet: PesoPetFiltro;
  marca: string;
};

const FILTROS_PADRAO: CatalogoFiltros = {
  especie: 'todos',
  pesoPet: 'todos',
  marca: '',
};

const ESPECIE_OPTIONS: Array<{ value: EspecieFiltro; label: string }> = [
  { value: 'todos', label: 'Todos' },
  { value: 'cao', label: 'Cão' },
  { value: 'gato', label: 'Gato' },
];

const PESO_PET_OPTIONS: Array<{ value: PesoPetFiltro; label: string }> = [
  { value: 'todos', label: 'Todos' },
  { value: 'ate3', label: 'Até 3 kg' },
  { value: 'ate10', label: 'Até 10 kg' },
  { value: 'ate15', label: 'Até 15 kg' },
  { value: 'acima15', label: 'Acima de 15 kg' },
];

function normalizarTexto(value: string | null | undefined): string {
  return (value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

function textoProduto(produto: Produto): string {
  return normalizarTexto(
    [produto.nome, produto.categoria_nome, produto.marca_nome, produto.descricao]
      .filter(Boolean)
      .join(' ')
  );
}

function combinaEspecie(texto: string, especie: EspecieFiltro): boolean {
  if (especie === 'todos') return true;

  const termosCao = /\b(cao|caes|canin|cachorro|dog|puppy)\b/;
  const termosGato = /\b(gato|gatos|felin|cat|kitten)\b/;

  if (especie === 'cao') {
    if (termosCao.test(texto)) return true;
    return !termosGato.test(texto);
  }

  if (termosGato.test(texto)) return true;
  return !termosCao.test(texto);
}

function combinaPesoPet(texto: string, pesoPet: PesoPetFiltro): boolean {
  if (pesoPet === 'todos') return true;
  if (pesoPet === 'ate3') return !/\b(grande|gigante|large|15\s?kg|20\s?kg)\b/.test(texto);
  if (pesoPet === 'ate10') return !/\b(gigante|giant|20\s?kg|25\s?kg)\b/.test(texto);
  if (pesoPet === 'ate15') return !/\b(gigante|giant|25\s?kg)\b/.test(texto);
  return !/\b(mini|toy|filhote|pequeno|small)\b/.test(texto);
}

function aplicarFiltrosCatalogo(produto: Produto, filtros: CatalogoFiltros): boolean {
  const texto = textoProduto(produto);

  if (filtros.marca && produto.marca_nome !== filtros.marca) return false;
  if (!combinaEspecie(texto, filtros.especie)) return false;
  if (!combinaPesoPet(texto, filtros.pesoPet)) return false;

  return true;
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
  const [modalFiltrosVisivel, setModalFiltrosVisivel] = useState(false);
  const [filtros, setFiltros] = useState<CatalogoFiltros>(FILTROS_PADRAO);
  const [ordenacao, setOrdenacao] = useState<CatalogOrder>('prontos');

  const ordenacaoLabel = useMemo(
    () => ORDER_OPTIONS.find((item) => item.value === ordenacao)?.label ?? 'Relevância',
    [ordenacao]
  );

  const marcasDisponiveis = useMemo(
    () =>
      Array.from(
        new Set(
          produtos
            .map((produto) => produto.marca_nome?.trim())
            .filter((marca): marca is string => !!marca)
        )
      ).sort((a, b) => a.localeCompare(b)),
    [produtos]
  );

  const produtosFiltrados = useMemo(
    () => produtos.filter((produto) => aplicarFiltrosCatalogo(produto, filtros)),
    [filtros, produtos]
  );

  const filtrosAtivos = useMemo(
    () =>
      Number(filtros.especie !== FILTROS_PADRAO.especie) +
      Number(filtros.pesoPet !== FILTROS_PADRAO.pesoPet) +
      Number(!!filtros.marca),
    [filtros]
  );

  const carregar = useCallback(
    async (pg: number, q: string) => {
      if (pg === 1) setCarregando(true);

      try {
        const { produtos: novos, total: totalRecebido } = await listarProdutos({
          pagina: pg,
          busca: q || undefined,
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
    [ordenacao]
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

  function limparFiltros() {
    setFiltros(FILTROS_PADRAO);
  }

  function selecionarFiltro<K extends keyof CatalogoFiltros>(campo: K, valor: CatalogoFiltros[K]) {
    setFiltros((atuais) => ({ ...atuais, [campo]: valor }));
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
                ? `Disponível: ${estoqueDisponivel}`
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
          style={[styles.botaoScanner, filtrosAtivos > 0 && styles.botaoFiltroAtivo]}
          onPress={() => setModalFiltrosVisivel(true)}
        >
          <Ionicons
            name="funnel-outline"
            size={22}
            color={filtrosAtivos > 0 ? '#fff' : CORES.primario}
          />
          {filtrosAtivos > 0 && (
            <View style={styles.badge}>
              <Text style={styles.badgeNum}>{filtrosAtivos}</Text>
            </View>
          )}
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

      <View style={styles.resumoContainer}>
        <Text style={styles.resumoCatalogo}>
          {filtrosAtivos > 0
            ? `${produtosFiltrados.length} produto(s) filtrado(s)`
            : `Mostrando ${produtos.length} de ${total || produtos.length} produtos`}
        </Text>
        <Text style={styles.ordenacaoResumo}>{ordenacaoLabel}</Text>
      </View>

      {carregando && pagina === 1 ? (
        <View style={styles.loading}>
          <ActivityIndicator size="large" color={CORES.primario} />
        </View>
      ) : (
        <FlatList
          data={produtosFiltrados}
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

      <Modal
        visible={modalFiltrosVisivel}
        transparent
        animationType="slide"
        onRequestClose={() => setModalFiltrosVisivel(false)}
      >
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <View>
                <Text style={styles.modalTitulo}>Filtros</Text>
                <Text style={styles.modalSubtitulo}>Encontre produtos por perfil do pet.</Text>
              </View>
              <TouchableOpacity onPress={() => setModalFiltrosVisivel(false)} style={styles.modalFechar}>
                <Ionicons name="close" size={22} color={CORES.texto} />
              </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.modalConteudo}>
              <FiltroSecao titulo="Espécie">
                {ESPECIE_OPTIONS.map((item) => (
                  <OpcaoFiltro
                    key={item.value}
                    label={item.label}
                    selecionado={filtros.especie === item.value}
                    onPress={() => selecionarFiltro('especie', item.value)}
                  />
                ))}
              </FiltroSecao>

              <FiltroSecao titulo="Peso do pet">
                {PESO_PET_OPTIONS.map((item) => (
                  <OpcaoFiltro
                    key={item.value}
                    label={item.label}
                    selecionado={filtros.pesoPet === item.value}
                    onPress={() => selecionarFiltro('pesoPet', item.value)}
                  />
                ))}
              </FiltroSecao>

              <FiltroSecao titulo="Marca">
                <OpcaoFiltro
                  label="Todas"
                  selecionado={!filtros.marca}
                  onPress={() => selecionarFiltro('marca', '')}
                />
                {marcasDisponiveis.map((marca) => (
                  <OpcaoFiltro
                    key={marca}
                    label={marca}
                    selecionado={filtros.marca === marca}
                    onPress={() => selecionarFiltro('marca', marca)}
                  />
                ))}
              </FiltroSecao>

              <FiltroSecao titulo="Ordenar por">
                {ORDER_OPTIONS.map((item) => (
                  <OpcaoFiltro
                    key={item.value}
                    label={item.label}
                    selecionado={ordenacao === item.value}
                    onPress={() => setOrdenacao(item.value)}
                  />
                ))}
              </FiltroSecao>
            </ScrollView>

            <View style={styles.modalAcoes}>
              <TouchableOpacity style={styles.botaoLimpar} onPress={limparFiltros}>
                <Text style={styles.botaoLimparTexto}>Limpar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.botaoAplicar} onPress={() => setModalFiltrosVisivel(false)}>
                <Text style={styles.botaoAplicarTexto}>Aplicar filtros</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

function FiltroSecao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <View style={styles.filtroSecao}>
      <Text style={styles.filtroSecaoTitulo}>{titulo}</Text>
      <View style={styles.filtroOpcoes}>{children}</View>
    </View>
  );
}

function OpcaoFiltro({
  label,
  selecionado,
  onPress,
}: {
  label: string;
  selecionado: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={[styles.filtroChip, selecionado && styles.filtroChipAtivo]}
      onPress={onPress}
    >
      <Text style={[styles.filtroChipTexto, selecionado && styles.filtroChipTextoAtivo]}>
        {label}
      </Text>
    </TouchableOpacity>
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
  botaoFiltroAtivo: {
    backgroundColor: CORES.primario,
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
  resumoContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: ESPACO.sm,
    paddingHorizontal: ESPACO.md,
    paddingBottom: ESPACO.sm,
    backgroundColor: CORES.superficie,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
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
  ordenacaoResumo: {
    fontSize: 12,
    color: CORES.primario,
    fontWeight: '700',
  },
  modalBackdrop: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(17, 24, 39, 0.45)',
  },
  modalCard: {
    maxHeight: '88%',
    backgroundColor: CORES.superficie,
    borderTopLeftRadius: RAIO.lg,
    borderTopRightRadius: RAIO.lg,
    paddingTop: ESPACO.md,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: ESPACO.lg,
    paddingBottom: ESPACO.md,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
  },
  modalTitulo: {
    fontSize: FONTE.grande,
    fontWeight: '800',
    color: CORES.texto,
  },
  modalSubtitulo: {
    marginTop: 2,
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
  },
  modalFechar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: CORES.fundo,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalConteudo: {
    padding: ESPACO.lg,
    paddingBottom: ESPACO.md,
    gap: ESPACO.lg,
  },
  filtroSecao: {
    gap: ESPACO.sm,
  },
  filtroSecaoTitulo: {
    fontSize: FONTE.normal,
    fontWeight: '800',
    color: CORES.texto,
  },
  filtroOpcoes: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: ESPACO.xs,
  },
  modalAcoes: {
    flexDirection: 'row',
    gap: ESPACO.sm,
    padding: ESPACO.lg,
    paddingTop: ESPACO.md,
    borderTopWidth: 1,
    borderTopColor: CORES.borda,
  },
  botaoLimpar: {
    flex: 1,
    minHeight: 44,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    justifyContent: 'center',
    alignItems: 'center',
  },
  botaoLimparTexto: {
    color: CORES.textoSecundario,
    fontWeight: '800',
  },
  botaoAplicar: {
    flex: 1.4,
    minHeight: 44,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primario,
    justifyContent: 'center',
    alignItems: 'center',
  },
  botaoAplicarTexto: {
    color: '#fff',
    fontWeight: '800',
  },
  lista: { padding: ESPACO.sm, paddingBottom: ESPACO.lg },
  colunaPar: { justifyContent: 'space-between', paddingHorizontal: ESPACO.xs, alignItems: 'stretch' },
  card: {
    width: '48%',
    minHeight: 316,
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
  cardInfo: { padding: ESPACO.sm, flex: 1 },
  produtoNome: {
    fontSize: FONTE.normal,
    fontWeight: '600',
    color: CORES.texto,
    marginBottom: 2,
    lineHeight: 18,
    minHeight: 36,
  },
  categoriaTexto: { fontSize: 10, color: CORES.textoClaro, marginBottom: 1 },
  skuTexto: { fontSize: 10, color: CORES.textoClaro, marginBottom: 2 },
  estoqueTexto: { fontSize: 10, color: '#10B981', fontWeight: '500', marginBottom: 4, minHeight: 14 },
  estoqueZero: { color: '#D97706' },
  precoRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: ESPACO.sm, minHeight: 22 },
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
    minHeight: 36,
    marginTop: 'auto',
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
    minHeight: 36,
    marginTop: 'auto',
  },
  botaoAvisemeTexto: { color: '#D97706', fontSize: 10, fontWeight: '600' },
  loading: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  vazio: { alignItems: 'center', paddingTop: 60, gap: 8 },
  vazioTexto: { fontSize: FONTE.grande, fontWeight: '600', color: CORES.textoSecundario },
  vazioSubtexto: { fontSize: FONTE.normal, color: CORES.textoClaro, textAlign: 'center' },
});
