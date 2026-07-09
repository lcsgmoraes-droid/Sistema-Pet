import { Ionicons } from '@expo/vector-icons';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { buscarProdutoPorId } from '../../services/shop.service';
import { useCartStore } from '../../store/cart.store';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { Produto } from '../../types';
import { formatarMoeda } from '../../utils/format';
import { resolveProductDetailParams } from '../../utils/productDetailRoute';

export default function ProductDetailScreen({ route, navigation }: any) {
  const { produtoId, produtoParam } = resolveProductDetailParams<Produto>(route.params);
  const [produto, setProduto] = useState<Produto | undefined>(produtoParam);
  const [carregandoProduto, setCarregandoProduto] = useState(!produtoParam && !!produtoId);
  const [erroProduto, setErroProduto] = useState(false);
  const [imagemAberta, setImagemAberta] = useState(false);
  const { adicionar } = useCartStore();
  const produtoExibido =
    produto && (!produtoId || Number(produto.id) === produtoId) ? produto : undefined;

  React.useEffect(() => {
    let active = true;
    if (produtoParam) {
      setProduto(produtoParam);
      setCarregandoProduto(false);
      setErroProduto(false);
      return () => {
        active = false;
      };
    }
    if (!produtoId) {
      setProduto(undefined);
      setCarregandoProduto(false);
      setErroProduto(true);
      return () => {
        active = false;
      };
    }

    setProduto(undefined);
    setCarregandoProduto(true);
    setErroProduto(false);
    buscarProdutoPorId(produtoId)
      .then((produtoEncontrado) => {
        if (active) setProduto(produtoEncontrado);
      })
      .catch(() => {
        if (active) setErroProduto(true);
      })
      .finally(() => {
        if (active) setCarregandoProduto(false);
      });

    return () => {
      active = false;
    };
  }, [produtoParam, produtoId]);

  if (carregandoProduto || (produtoId && produto && Number(produto.id) !== produtoId)) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={CORES.primario} size="large" />
      </View>
    );
  }

  if (!produtoExibido) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyText}>
          {erroProduto ? 'Produto nao encontrado.' : 'Produto indisponivel.'}
        </Text>
      </View>
    );
  }

  const temOferta = !!produtoExibido.promocao_ativa && !!produtoExibido.preco_promocional;
  const precoFinal = temOferta ? Number(produtoExibido.preco_promocional) : Number(produtoExibido.preco || 0);
  const precoOriginal = Number(produtoExibido.preco_original ?? produtoExibido.preco ?? 0);

  async function adicionarProduto() {
    if (!produtoExibido) return;
    try {
      await adicionar(produtoExibido, 1);
      Alert.alert('Adicionado', 'Produto enviado para o carrinho.', [
        { text: 'Continuar comprando' },
        { text: 'Ver carrinho', onPress: () => navigation.navigate('Carrinho') },
      ]);
    } catch {
      Alert.alert('Erro', 'Nao foi possivel adicionar ao carrinho.');
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <TouchableOpacity
        style={styles.imageBox}
        activeOpacity={produtoExibido.foto_url ? 0.9 : 1}
        onPress={() => produtoExibido.foto_url && setImagemAberta(true)}
      >
        {produtoExibido.foto_url ? (
          <Image source={{ uri: produtoExibido.foto_url }} style={styles.image} resizeMode="contain" />
        ) : (
          <View style={styles.placeholder}>
            <Ionicons name="image-outline" size={54} color={CORES.textoClaro} />
          </View>
        )}
        {produtoExibido.foto_url ? (
          <View style={styles.expandBadge}>
            <Ionicons name="expand-outline" size={16} color="#fff" />
            <Text style={styles.expandText}>Ampliar</Text>
          </View>
        ) : null}
      </TouchableOpacity>

      <View style={styles.card}>
        {temOferta ? (
          <View style={styles.offerBadge}>
            <Ionicons name="pricetag" size={14} color="#fff" />
            <Text style={styles.offerText}>Oferta</Text>
          </View>
        ) : null}
        <Text style={styles.nome}>{produtoExibido.nome}</Text>
        {produtoExibido.codigo ? <Text style={styles.meta}>SKU: {produtoExibido.codigo}</Text> : null}
        {produtoExibido.codigo_barras ? <Text style={styles.meta}>Codigo de barras: {produtoExibido.codigo_barras}</Text> : null}

        <View style={styles.priceRow}>
          {temOferta ? <Text style={styles.priceOld}>{formatarMoeda(precoOriginal)}</Text> : null}
          <Text style={styles.price}>{formatarMoeda(precoFinal)}</Text>
        </View>

        {produtoExibido.descricao ? <Text style={styles.description}>{produtoExibido.descricao}</Text> : null}

        <TouchableOpacity style={styles.addButton} onPress={adicionarProduto}>
          <Ionicons name="cart" size={18} color="#fff" />
          <Text style={styles.addButtonText}>Adicionar ao carrinho</Text>
        </TouchableOpacity>
      </View>

      <Modal visible={imagemAberta} transparent animationType="fade" onRequestClose={() => setImagemAberta(false)}>
        <View style={styles.modalOverlay}>
          <TouchableOpacity style={styles.modalClose} onPress={() => setImagemAberta(false)}>
            <Ionicons name="close" size={28} color="#fff" />
          </TouchableOpacity>
          {produtoExibido.foto_url ? (
            <Image source={{ uri: produtoExibido.foto_url }} style={styles.modalImage} resizeMode="contain" />
          ) : null}
        </View>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.lg, paddingBottom: 120 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: CORES.fundo },
  emptyText: { color: CORES.textoSecundario },
  imageBox: {
    height: 300,
    borderRadius: RAIO.lg,
    backgroundColor: CORES.superficie,
    overflow: 'hidden',
    ...SOMBRA,
  },
  image: { width: '100%', height: '100%' },
  placeholder: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  expandBadge: {
    position: 'absolute',
    right: ESPACO.md,
    bottom: ESPACO.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(15,23,42,0.78)',
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.md,
    paddingVertical: 8,
  },
  expandText: { color: '#fff', fontWeight: '700', fontSize: FONTE.pequena },
  card: { marginTop: ESPACO.lg, padding: ESPACO.lg, borderRadius: RAIO.lg, backgroundColor: CORES.superficie, ...SOMBRA },
  offerBadge: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: '#DC2626',
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: 6,
    marginBottom: ESPACO.sm,
  },
  offerText: { color: '#fff', fontWeight: '800', fontSize: FONTE.pequena },
  nome: { fontSize: FONTE.titulo, fontWeight: '800', color: CORES.texto },
  meta: { marginTop: 4, color: CORES.textoSecundario, fontSize: FONTE.pequena },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', gap: ESPACO.sm, marginTop: ESPACO.md },
  priceOld: { color: CORES.textoClaro, textDecorationLine: 'line-through', fontSize: FONTE.normal },
  price: { color: CORES.primario, fontWeight: '900', fontSize: FONTE.titulo },
  description: { color: CORES.textoSecundario, lineHeight: 21, marginTop: ESPACO.md },
  addButton: {
    marginTop: ESPACO.lg,
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  addButtonText: { color: '#fff', fontWeight: '800', fontSize: FONTE.media },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.92)', alignItems: 'center', justifyContent: 'center' },
  modalClose: { position: 'absolute', top: 52, right: 22, zIndex: 2, padding: 8 },
  modalImage: { width: '94%', height: '82%' },
});
