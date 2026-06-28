import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import React, { useEffect, useState } from 'react';
import {
  Image,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import HeaderProfileActions from '../components/HeaderProfileActions';
import { listarProdutos } from '../services/shop.service';
import { useAuthStore } from '../store/auth.store';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../theme';
import { Produto } from '../types';
import { formatarMoeda } from '../utils/format';

export default function HomeScreen() {
  const { user } = useAuthStore();
  const navigation = useNavigation<any>();
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  async function carregar() {
    try {
      const { produtos: prods } = await listarProdutos({ pagina: 1 });
      setProdutos((prods ?? []).slice(0, 6));
    } catch {
      setProdutos([]);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  async function onRefresh() {
    setRefreshing(true);
    await carregar();
    setRefreshing(false);
  }

  function abrirVeterinario() {
    navigation.navigate('Pets', { screen: 'Veterinario' });
  }

  const primeiroNome = user?.nome?.split(' ')[0] || 'Cliente';
  const pontos = user?.pontos ?? 0;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={CORES.primario}
        />
      }
    >
      <View style={styles.header}>
        <View style={styles.headerText}>
          <Text style={styles.saudacao}>Ola, {primeiroNome}!</Text>
          <Text style={styles.subSaudacao}>Bem-vindo ao pet shop</Text>
        </View>
        <View style={styles.headerActions}>
          <TouchableOpacity
            style={styles.pontosCard}
            onPress={() => navigation.navigate('Beneficios')}
          >
            <Ionicons name="trophy" size={16} color={CORES.pontos} />
            <Text style={styles.pontosTexto}>{pontos} pts</Text>
          </TouchableOpacity>
          <HeaderProfileActions
            color={CORES.primario}
            logoutContextLabel="cliente"
            showLogout={false}
          />
        </View>
      </View>

      <TouchableOpacity
        style={styles.scannerCardCompacto}
        onPress={() => navigation.navigate('Loja', { screen: 'BarcodeScanner' })}
        activeOpacity={0.85}
      >
        <View style={styles.scannerIconBox}>
          <Ionicons name="barcode-outline" size={24} color={CORES.primario} />
        </View>
        <View style={styles.scannerInfo}>
          <Text style={styles.scannerTitulo}>Comprar sem fila</Text>
          <Text style={styles.scannerTexto}>
            Escaneie produtos na prateleira.
          </Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color={CORES.textoClaro} />
      </TouchableOpacity>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitulo}>Comprar por pet</Text>
          <TouchableOpacity onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}>
            <Text style={styles.verTodos}>Ver loja</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.petChips}>
          <CategoriaPetChip
            iconName="paw-outline"
            label="Cães"
            cor="#E0F2FE"
            corTexto="#0369A1"
            onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}
          />
          <CategoriaPetChip
            iconName="sparkles-outline"
            label="Gatos"
            cor="#FAE8FF"
            corTexto="#86198F"
            onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}
          />
          <CategoriaPetChip
            iconName="nutrition-outline"
            label="Rações"
            cor="#DCFCE7"
            corTexto="#166534"
            onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}
          />
          <CategoriaPetChip
            iconName="pricetag-outline"
            label="Ofertas"
            cor="#FEF3C7"
            corTexto="#92400E"
            onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}
          />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitulo}>Acesso rapido</Text>
        <View style={styles.atalhos}>
          <Atalho
            iconName="storefront-outline"
            titulo="Loja"
            cor="#EFF6FF"
            corTexto={CORES.primario}
            onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}
          />
          <Atalho
            iconName="medical-outline"
            titulo="Veterinário"
            cor="#EEF2FF"
            corTexto="#4338CA"
            onPress={abrirVeterinario}
          />
          <Atalho
            iconName="calculator-outline"
            titulo="Calculadora"
            cor="#F0FDF4"
            corTexto={CORES.sucesso}
            onPress={() => navigation.navigate('Pets', { screen: 'CalculadoraRacao' })}
          />
          <Atalho
            iconName="cut-outline"
            titulo="Banho & Tosa"
            cor="#ECFEFF"
            corTexto="#0E7490"
            onPress={() => navigation.navigate('Pets', { screen: 'BanhoTosa' })}
          />
          <Atalho
            iconName="receipt-outline"
            titulo="Pedidos"
            cor="#FDF4FF"
            corTexto="#9333EA"
            onPress={() => navigation.navigate('Pedidos')}
          />
          <Atalho
            iconName="gift-outline"
            titulo="Benefícios"
            cor="#FEF3C7"
            corTexto="#92400E"
            onPress={() => navigation.navigate('Beneficios')}
          />
        </View>
      </View>

      {produtos.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitulo}>Destaques</Text>
            <TouchableOpacity onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}>
              <Text style={styles.verTodos}>Ver todos</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.produtosGrid}>
            {produtos.map((produto) => (
              <ProdutoCard
                key={produto.id}
                produto={produto}
                onPress={() => navigation.navigate('Loja', { screen: 'DetalhesProduto', params: { produto } })}
              />
            ))}
          </View>
        </View>
      )}

      <View style={{ height: ESPACO.xxl }} />
    </ScrollView>
  );
}

function Atalho({
  iconName,
  titulo,
  cor,
  corTexto,
  onPress,
}: {
  iconName: React.ComponentProps<typeof Ionicons>['name'];
  titulo: string;
  cor: string;
  corTexto: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={[styles.atalho, { backgroundColor: cor }]} onPress={onPress}>
      <Ionicons name={iconName} size={22} color={corTexto} />
      <Text style={[styles.atalhoTexto, { color: corTexto }]}>{titulo}</Text>
    </TouchableOpacity>
  );
}

function CategoriaPetChip({
  iconName,
  label,
  cor,
  corTexto,
  onPress,
}: {
  iconName: React.ComponentProps<typeof Ionicons>['name'];
  label: string;
  cor: string;
  corTexto: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={[styles.petChip, { backgroundColor: cor }]} onPress={onPress}>
      <Ionicons name={iconName} size={18} color={corTexto} />
      <Text style={[styles.petChipTexto, { color: corTexto }]}>{label}</Text>
    </TouchableOpacity>
  );
}

function ProdutoCard({ produto, onPress }: { produto: Produto; onPress: () => void }) {
  const preco =
    produto.promocao_ativa && produto.preco_promocional
      ? produto.preco_promocional
      : produto.preco;
  const temOferta = !!produto.promocao_ativa && !!produto.preco_promocional;

  return (
    <TouchableOpacity style={styles.produtoCard} onPress={onPress}>
      {produto.foto_url ? (
        <Image source={{ uri: produto.foto_url }} style={styles.produtoFoto} resizeMode="contain" />
      ) : (
        <View style={[styles.produtoFoto, styles.produtoFotoPlaceholder]}>
          <Ionicons name="bag-handle-outline" size={28} color={CORES.primario} />
        </View>
      )}
      {temOferta ? (
        <View style={styles.produtoOfertaBadge}>
          <Text style={styles.produtoOfertaTexto}>Oferta</Text>
        </View>
      ) : null}
      <Text style={styles.produtoNome} numberOfLines={2}>
        {produto.nome}
      </Text>
      <View style={styles.produtoPrecoRow}>
        {temOferta ? <Text style={styles.produtoPrecoOriginal}>{formatarMoeda(produto.preco)}</Text> : null}
        <Text style={styles.produtoPreco}>{formatarMoeda(preco)}</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: ESPACO.lg,
    paddingTop: ESPACO.xl,
    backgroundColor: CORES.superficie,
    gap: ESPACO.md,
  },
  headerText: { flex: 1 },
  headerActions: { alignItems: 'flex-end', gap: ESPACO.xs },
  saudacao: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto },
  subSaudacao: { fontSize: FONTE.normal, color: CORES.textoSecundario, marginTop: 2 },
  pontosCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF8E1',
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.xs + 2,
    gap: 4,
  },
  pontosTexto: { fontSize: FONTE.normal, fontWeight: 'bold', color: '#92400E' },
  scannerCardCompacto: {
    marginHorizontal: ESPACO.lg,
    marginTop: ESPACO.lg,
    marginBottom: ESPACO.md,
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: CORES.borda,
    ...SOMBRA,
  },
  scannerIconBox: {
    width: 42,
    height: 42,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primarioClaro,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: ESPACO.sm,
  },
  scannerInfo: { flex: 1, minWidth: 0, paddingRight: ESPACO.sm },
  scannerTitulo: { fontSize: FONTE.normal, fontWeight: '800', color: CORES.texto, marginBottom: 2 },
  scannerTexto: { fontSize: FONTE.pequena, color: CORES.textoSecundario, lineHeight: 16 },
  section: { paddingHorizontal: ESPACO.lg, marginBottom: ESPACO.lg },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: ESPACO.sm,
  },
  sectionTitulo: {
    fontSize: FONTE.grande,
    fontWeight: 'bold',
    color: CORES.texto,
    marginBottom: ESPACO.sm,
  },
  verTodos: { fontSize: FONTE.normal, color: CORES.primario, fontWeight: '500' },
  petChips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: ESPACO.sm,
  },
  petChip: {
    width: '48%',
    minHeight: 48,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.xs,
  },
  petChipTexto: { fontSize: FONTE.normal, fontWeight: '800' },
  atalhos: { flexDirection: 'row', flexWrap: 'wrap', gap: ESPACO.sm },
  atalho: {
    width: '31%',
    borderRadius: RAIO.md,
    minHeight: 78,
    paddingHorizontal: ESPACO.xs,
    paddingVertical: ESPACO.sm,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  atalhoTexto: { fontSize: FONTE.pequena, fontWeight: '700', textAlign: 'center' },
  produtosGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: ESPACO.sm,
  },
  produtoCard: {
    width: '48%',
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    overflow: 'hidden',
    ...SOMBRA,
  },
  produtoFoto: { width: '100%', height: 120 },
  produtoOfertaBadge: {
    position: 'absolute',
    top: 8,
    left: 8,
    backgroundColor: '#DC2626',
    borderRadius: RAIO.circulo,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  produtoOfertaTexto: { color: '#fff', fontSize: 10, fontWeight: '900' },
  produtoFotoPlaceholder: {
    backgroundColor: CORES.primarioClaro,
    justifyContent: 'center',
    alignItems: 'center',
  },
  produtoNome: {
    fontSize: FONTE.pequena,
    fontWeight: '500',
    color: CORES.texto,
    padding: ESPACO.sm,
    paddingBottom: 2,
  },
  produtoPrecoRow: { padding: ESPACO.sm, paddingTop: 2 },
  produtoPrecoOriginal: {
    fontSize: FONTE.pequena,
    color: CORES.textoClaro,
    textDecorationLine: 'line-through',
  },
  produtoPreco: {
    fontSize: FONTE.normal,
    fontWeight: 'bold',
    color: CORES.primario,
  },
});
