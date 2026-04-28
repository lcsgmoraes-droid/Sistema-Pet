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
        <View>
          <Text style={styles.saudacao}>Ola, {primeiroNome}!</Text>
          <Text style={styles.subSaudacao}>Bem-vindo ao pet shop</Text>
        </View>
        <TouchableOpacity
          style={styles.pontosCard}
          onPress={() => navigation.navigate('Beneficios')}
        >
          <Ionicons name="trophy" size={16} color={CORES.pontos} />
          <Text style={styles.pontosTexto}>{pontos} pts</Text>
        </TouchableOpacity>
      </View>

      <TouchableOpacity
        style={styles.scannerCard}
        onPress={() => navigation.navigate('Loja', { screen: 'BarcodeScanner' })}
        activeOpacity={0.85}
      >
        <View style={styles.scannerInfo}>
          <Text style={styles.scannerTitulo}>Comprar sem fila</Text>
          <Text style={styles.scannerTexto}>
            Escaneie produtos na prateleira, monte seu carrinho e acompanhe os beneficios disponiveis.
          </Text>
        </View>
        <Ionicons name="barcode-outline" size={48} color="rgba(255,255,255,0.7)" />
      </TouchableOpacity>

      <View style={styles.section}>
        <Text style={styles.sectionTitulo}>Acesso rapido</Text>
        <View style={styles.atalhos}>
          <Atalho
            iconText="Loja"
            titulo="Produtos"
            cor="#EFF6FF"
            corTexto={CORES.primario}
            onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}
          />
          <Atalho
            iconText="VET"
            titulo="Veterinario"
            cor="#EEF2FF"
            corTexto="#4338CA"
            onPress={abrirVeterinario}
          />
          <Atalho
            iconText="Calc"
            titulo="Calculadora"
            cor="#F0FDF4"
            corTexto={CORES.sucesso}
            onPress={() => navigation.navigate('Pets', { screen: 'CalculadoraRacao' })}
          />
          <Atalho
            iconText="BT"
            titulo="Banho & Tosa"
            cor="#ECFEFF"
            corTexto="#0E7490"
            onPress={() => navigation.navigate('Pets', { screen: 'BanhoTosa' })}
          />
          <Atalho
            iconText="Ped"
            titulo="Pedidos"
            cor="#FDF4FF"
            corTexto="#9333EA"
            onPress={() => navigation.navigate('Pedidos')}
          />
          <Atalho
            iconText="Pts"
            titulo="Beneficios"
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
                onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}
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
  iconText,
  titulo,
  cor,
  corTexto,
  onPress,
}: {
  iconText: string;
  titulo: string;
  cor: string;
  corTexto: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={[styles.atalho, { backgroundColor: cor }]} onPress={onPress}>
      <Text style={[styles.atalhoIcon, { color: corTexto }]}>{iconText}</Text>
      <Text style={[styles.atalhoTexto, { color: corTexto }]}>{titulo}</Text>
    </TouchableOpacity>
  );
}

function ProdutoCard({ produto, onPress }: { produto: Produto; onPress: () => void }) {
  const preco =
    produto.promocao_ativa && produto.preco_promocional
      ? produto.preco_promocional
      : produto.preco;

  return (
    <TouchableOpacity style={styles.produtoCard} onPress={onPress}>
      {produto.foto_url ? (
        <Image source={{ uri: produto.foto_url }} style={styles.produtoFoto} resizeMode="contain" />
      ) : (
        <View style={[styles.produtoFoto, styles.produtoFotoPlaceholder]}>
          <Ionicons name="bag-handle-outline" size={28} color={CORES.primario} />
        </View>
      )}
      <Text style={styles.produtoNome} numberOfLines={2}>
        {produto.nome}
      </Text>
      <Text style={styles.produtoPreco}>{formatarMoeda(preco)}</Text>
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
  },
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
  scannerCard: {
    margin: ESPACO.lg,
    backgroundColor: CORES.primario,
    borderRadius: RAIO.lg,
    padding: ESPACO.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    ...SOMBRA,
  },
  scannerInfo: { flex: 1, paddingRight: ESPACO.md },
  scannerTitulo: { fontSize: FONTE.grande, fontWeight: 'bold', color: '#fff', marginBottom: 6 },
  scannerTexto: { fontSize: FONTE.pequena, color: 'rgba(255,255,255,0.85)', lineHeight: 18 },
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
  atalhos: { flexDirection: 'row', flexWrap: 'wrap', gap: ESPACO.sm },
  atalho: {
    width: '31%',
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.md,
    alignItems: 'center',
    gap: 4,
  },
  atalhoIcon: { fontSize: 13, fontWeight: '900', letterSpacing: 0.3 },
  atalhoTexto: { fontSize: FONTE.pequena, fontWeight: '600' },
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
  produtoPreco: {
    fontSize: FONTE.normal,
    fontWeight: 'bold',
    color: CORES.primario,
    padding: ESPACO.sm,
    paddingTop: 2,
  },
});
