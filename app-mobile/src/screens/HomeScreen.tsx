import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  RefreshControl,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../store/auth.store';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../theme';
import { listarProdutos } from '../services/shop.service';
import { listarPets } from '../services/pets.service';
import { Produto, Pet } from '../types';
import { formatarMoeda } from '../utils/format';

export default function HomeScreen() {
  const { user } = useAuthStore();
  const navigation = useNavigation<any>();
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [pets, setPets] = useState<Pet[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  async function carregar() {
    try {
      const [{ produtos: prods }, meusPets] = await Promise.all([
        listarProdutos({ pagina: 1 }),
        listarPets(),
      ]);
      setProdutos((prods ?? []).slice(0, 6)); // destaques
      setPets(meusPets ?? []);
    } catch {}
  }

  useEffect(() => { carregar(); }, []);

  async function onRefresh() {
    setRefreshing(true);
    await carregar();
    setRefreshing(false);
  }

  const primeiroNome = user?.nome?.split(' ')[0] || 'Cliente';
  const pontos = user?.pontos ?? 0;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={CORES.primario} />}
    >
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.saudacao}>Olá, {primeiroNome}! 👋</Text>
          <Text style={styles.subSaudacao}>Bem-vindo ao pet shop</Text>
        </View>
        <TouchableOpacity
          style={styles.pontosCard}
          onPress={() => navigation.navigate('Perfil')}
        >
          <Ionicons name="trophy" size={16} color={CORES.pontos} />
          <Text style={styles.pontosTexto}>{pontos} pts</Text>
        </TouchableOpacity>
      </View>

      {/* Ação rápida: escanear produto */}
      <TouchableOpacity
        style={styles.scannerCard}
        onPress={() => navigation.navigate('Loja', { screen: 'BarcodeScanner' })}
        activeOpacity={0.85}
      >
        <View style={styles.scannerInfo}>
          <Text style={styles.scannerTitulo}>📷 Comprar sem fila</Text>
          <Text style={styles.scannerTexto}>
            Escaneie os produtos na prateleira, pague pelo app e retire na saída com uma palavra-chave.
          </Text>
        </View>
        <Ionicons name="barcode-outline" size={48} color="rgba(255,255,255,0.7)" />
      </TouchableOpacity>

      {/* Atalhos */}
      <View style={styles.section}>
        <Text style={styles.sectionTitulo}>Acesso rápido</Text>
        <View style={styles.atalhos}>
          <Atalho
            emoji="🛍️"
            titulo="Produtos"
            cor="#EFF6FF"
            corTexto={CORES.primario}
            onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}
          />
          <Atalho
            emoji="🐾"
            titulo="Meus Pets"
            cor="#FFF7ED"
            corTexto={CORES.secundario}
            onPress={() => navigation.navigate('Pets')}
          />
          <Atalho
            emoji="🥣"
            titulo="Calculadora"
            cor="#F0FDF4"
            corTexto={CORES.sucesso}
            onPress={() => navigation.navigate('Pets', { screen: 'CalculadoraRacao' })}
          />
          <Atalho
            emoji="📦"
            titulo="Pedidos"
            cor="#FDF4FF"
            corTexto="#9333EA"
            onPress={() => navigation.navigate('Pedidos')}
          />
        </View>
      </View>

      {/* Pets cadastrados */}
      {pets.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitulo}>Meus pets</Text>
            <TouchableOpacity onPress={() => navigation.navigate('Pets')}>
              <Text style={styles.verTodos}>Ver todos</Text>
            </TouchableOpacity>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {pets.map((pet) => (
              <TouchableOpacity
                key={pet.id}
                style={styles.petCard}
                onPress={() => navigation.navigate('Pets', { screen: 'FormPet', params: { pet } })}
              >
                {pet.foto_url ? (
                  <Image source={{ uri: pet.foto_url }} style={styles.petFoto} />
                ) : (
                  <View style={[styles.petFoto, styles.petFotoPlaceholder]}>
                    <Text style={{ fontSize: 28 }}>
                      {pet.especie === 'gato' ? '🐱' : pet.especie === 'cão' ? '🐶' : '🐾'}
                    </Text>
                  </View>
                )}
                <Text style={styles.petNome} numberOfLines={1}>{pet.nome}</Text>
                <Text style={styles.petEspecie}>{pet.especie}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Destaques */}
      {produtos.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitulo}>Destaques</Text>
            <TouchableOpacity onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}>
              <Text style={styles.verTodos}>Ver todos</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.produtosGrid}>
            {produtos.map((p) => (
              <ProdutoCard
                key={p.id}
                produto={p}
                onPress={() =>
                  navigation.navigate('Loja', {
                    screen: 'Catalogo',
                  })
                }
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
  emoji,
  titulo,
  cor,
  corTexto,
  onPress,
}: {
  emoji: string;
  titulo: string;
  cor: string;
  corTexto: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={[styles.atalho, { backgroundColor: cor }]} onPress={onPress}>
      <Text style={styles.atalhoEmoji}>{emoji}</Text>
      <Text style={[styles.atalhoTexto, { color: corTexto }]}>{titulo}</Text>
    </TouchableOpacity>
  );
}

function ProdutoCard({ produto, onPress }: { produto: Produto; onPress: () => void }) {
  const preco = produto.promocao_ativa && produto.preco_promocional
    ? produto.preco_promocional
    : produto.preco;
  return (
    <TouchableOpacity style={styles.produtoCard} onPress={onPress}>
      {produto.foto_url ? (
        <Image source={{ uri: produto.foto_url }} style={styles.produtoFoto} resizeMode="contain" />
      ) : (
        <View style={[styles.produtoFoto, styles.produtoFotoPlaceholder]}>
          <Text style={{ fontSize: 24 }}>🛍️</Text>
        </View>
      )}
      <Text style={styles.produtoNome} numberOfLines={2}>{produto.nome}</Text>
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
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: ESPACO.sm },
  sectionTitulo: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto, marginBottom: ESPACO.sm },
  verTodos: { fontSize: FONTE.normal, color: CORES.primario, fontWeight: '500' },
  atalhos: { flexDirection: 'row', gap: ESPACO.sm },
  atalho: {
    flex: 1,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.md,
    alignItems: 'center',
    gap: 4,
  },
  atalhoEmoji: { fontSize: 22 },
  atalhoTexto: { fontSize: FONTE.pequena, fontWeight: '600' },
  petCard: {
    width: 90,
    marginRight: ESPACO.sm,
    alignItems: 'center',
  },
  petFoto: {
    width: 70,
    height: 70,
    borderRadius: 35,
    marginBottom: 6,
  },
  petFotoPlaceholder: {
    backgroundColor: CORES.primarioClaro,
    justifyContent: 'center',
    alignItems: 'center',
  },
  petNome: { fontSize: FONTE.pequena, fontWeight: '600', color: CORES.texto, textAlign: 'center' },
  petEspecie: { fontSize: FONTE.pequena - 1, color: CORES.textoSecundario },
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
