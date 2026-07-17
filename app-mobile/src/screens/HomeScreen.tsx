import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import React, { useCallback, useEffect, useState } from 'react';
import {
  Image,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import HeaderProfileActions from '../components/HeaderProfileActions';
import { listarNotificacoesApp } from '../services/appNotifications.service';
import { listarProdutos } from '../services/shop.service';
import { useAuthStore } from '../store/auth.store';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../theme';
import { Produto } from '../types';
import { formatarMoeda } from '../utils/format';
import { navigateToLogin, useRequireAuth } from '../hooks/useRequireAuth';

type HomeIconFamily = 'ionicons' | 'material-community' | 'food-bag-bone';
type HomeIconName =
  | React.ComponentProps<typeof Ionicons>['name']
  | React.ComponentProps<typeof MaterialCommunityIcons>['name']
  | 'food-bag-bone';

export default function HomeScreen() {
  const { user, isAuthenticated } = useAuthStore();
  const navigation = useNavigation<any>();
  const requireAuth = useRequireAuth(navigation);
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [unreadNotifications, setUnreadNotifications] = useState(0);

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

  const carregarNotificacoesNaoLidas = useCallback(async () => {
    if (!isAuthenticated) {
      setUnreadNotifications(0);
      return;
    }
    try {
      const response = await listarNotificacoesApp();
      setUnreadNotifications(Math.max(0, Number(response.unread_count ?? 0)));
    } catch {
      setUnreadNotifications(0);
    }
  }, [isAuthenticated]);

  useFocusEffect(
    useCallback(() => {
      void carregarNotificacoesNaoLidas();
    }, [carregarNotificacoesNaoLidas]),
  );

  async function onRefresh() {
    setRefreshing(true);
    await Promise.all([
      carregar(),
      isAuthenticated ? carregarNotificacoesNaoLidas() : Promise.resolve(),
    ]);
    setRefreshing(false);
  }

  function abrirVeterinario() {
    requireAuth(
      () => navigation.navigate('Pets', { screen: 'Veterinario' }),
      'Faca login para acessar os servicos do seu pet.',
    );
  }

  const primeiroNome = user?.nome?.split(' ')[0];
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
          <Text style={styles.saudacao}>{primeiroNome ? `Ola, ${primeiroNome}!` : 'Ola!'}</Text>
          <Text style={styles.subSaudacao}>
            {isAuthenticated ? 'Bem-vindo ao pet shop' : 'Explore os produtos da loja'}
          </Text>
        </View>
        <View style={styles.headerActions}>
          {isAuthenticated ? <>
            <View style={styles.headerTopActions}>
            <TouchableOpacity
              style={styles.pontosCard}
              onPress={() => navigation.navigate('Beneficios')}
            >
              <Ionicons name="trophy" size={16} color={CORES.pontos} />
              <Text style={styles.pontosTexto}>{pontos} pts</Text>
            </TouchableOpacity>
            <TouchableOpacity
              accessibilityLabel="Abrir notificacoes"
              style={styles.notificacoesButton}
              onPress={() => navigation.navigate('Notificacoes')}
            >
              <Ionicons name="notifications-outline" size={18} color={CORES.primario} />
              {unreadNotifications > 0 ? (
                <View style={styles.notificacoesBadge}>
                  <Text style={styles.notificacoesBadgeText}>
                    {unreadNotifications > 99 ? '99+' : unreadNotifications}
                  </Text>
                </View>
              ) : null}
            </TouchableOpacity>
            </View>
            <HeaderProfileActions
              color={CORES.primario}
              logoutContextLabel="cliente"
              showLogout={false}
            />
          </> : (
            <TouchableOpacity
              style={styles.loginButton}
              onPress={() => navigateToLogin(navigation)}
            >
              <Ionicons name="log-in-outline" size={18} color="#fff" />
              <Text style={styles.loginButtonText}>Entrar</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      <TouchableOpacity
        style={styles.scannerCardCompacto}
        onPress={() =>
          requireAuth(
            () => navigation.navigate('Loja', { screen: 'BarcodeScanner' }),
            'Faca login para usar o leitor e comprar sem fila.',
          )
        }
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
            iconFamily="material-community"
            iconName="dog"
            label="Cães"
            cor="#E0F2FE"
            corTexto="#0369A1"
            onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}
          />
          <CategoriaPetChip
            iconFamily="material-community"
            iconName="cat"
            label="Gatos"
            cor="#FAE8FF"
            corTexto="#86198F"
            onPress={() => navigation.navigate('Loja', { screen: 'Catalogo' })}
          />
          <CategoriaPetChip
            iconFamily="food-bag-bone"
            iconName="food-bag-bone"
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
            iconFamily="material-community"
            iconName="stethoscope"
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
            onPress={() =>
              requireAuth(
                () => navigation.navigate('Pets', { screen: 'CalculadoraRacao' }),
                'Faca login para calcular a racao dos seus pets.',
              )
            }
          />
          <Atalho
            iconName="cut-outline"
            titulo="Banho & Tosa"
            cor="#ECFEFF"
            corTexto="#0E7490"
            onPress={() =>
              requireAuth(
                () => navigation.navigate('Pets', { screen: 'BanhoTosa' }),
                'Faca login para acessar os servicos do seu pet.',
              )
            }
          />
          <Atalho
            iconName="receipt-outline"
            titulo="Pedidos"
            cor="#FDF4FF"
            corTexto="#9333EA"
            onPress={() =>
              requireAuth(
                () => navigation.navigate('Pedidos'),
                'Faca login para consultar seus pedidos.',
              )
            }
          />
          <Atalho
            iconName="gift-outline"
            titulo="Benefícios"
            cor="#FEF3C7"
            corTexto="#92400E"
            onPress={() =>
              requireAuth(
                () => navigation.navigate('Beneficios'),
                'Faca login para consultar seus beneficios.',
              )
            }
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
  iconFamily,
  iconName,
  titulo,
  cor,
  corTexto,
  onPress,
}: {
  iconFamily?: HomeIconFamily;
  iconName: HomeIconName;
  titulo: string;
  cor: string;
  corTexto: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={[styles.atalho, { backgroundColor: cor }]} onPress={onPress}>
      <HomeIcon family={iconFamily} name={iconName} size={22} color={corTexto} />
      <Text style={[styles.atalhoTexto, { color: corTexto }]}>{titulo}</Text>
    </TouchableOpacity>
  );
}

function CategoriaPetChip({
  iconFamily,
  iconName,
  label,
  cor,
  corTexto,
  onPress,
}: {
  iconFamily?: HomeIconFamily;
  iconName: HomeIconName;
  label: string;
  cor: string;
  corTexto: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={[styles.petChip, { backgroundColor: cor }]} onPress={onPress}>
      <HomeIcon
        family={iconFamily}
        name={iconName}
        size={22}
        color={corTexto}
        style={styles.petChipIconDiscreto}
      />
      <Text style={[styles.petChipTexto, { color: corTexto }]}>{label}</Text>
    </TouchableOpacity>
  );
}

function HomeIcon({
  family = 'ionicons',
  name,
  size,
  color,
  style,
}: {
  family?: HomeIconFamily;
  name: HomeIconName;
  size: number;
  color: string;
  style?: object;
}) {
  if (family === 'food-bag-bone') {
    return <RacaoFoodBagIcon size={size} color={color} style={style} />;
  }

  if (family === 'material-community') {
    return (
      <MaterialCommunityIcons
        name={name as React.ComponentProps<typeof MaterialCommunityIcons>['name']}
        size={size}
        color={color}
        style={style}
      />
    );
  }

  return (
    <Ionicons
      name={name as React.ComponentProps<typeof Ionicons>['name']}
      size={size}
      color={color}
      style={style}
    />
  );
}

function RacaoFoodBagIcon({
  size,
  color,
  style,
}: {
  size: number;
  color: string;
  style?: object;
}) {
  const largura = size + 10;
  const altura = size + 8;
  const boneSize = Math.max(12, Math.round(size * 0.62));

  return (
    <View style={[styles.racaoChipIcon, { width: largura, height: altura }, style]}>
      <Svg width={largura} height={altura} viewBox="0 0 32 30">
        <Path
          d="M8.2 11.2C8.2 8 10.7 5.8 13.5 6C14.4 3.8 17.6 3.8 18.5 6C21.3 5.8 23.8 8 23.8 11.2"
          fill="none"
          stroke={color}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2.4}
        />
        <Circle cx={12.8} cy={8.9} r={0.9} fill={color} />
        <Circle cx={16} cy={7.8} r={0.9} fill={color} />
        <Circle cx={19.2} cy={8.9} r={0.9} fill={color} />
        <Path
          d="M4.8 12.4H27.2"
          fill="none"
          stroke={color}
          strokeLinecap="round"
          strokeWidth={2.8}
        />
        <Path
          d="M6.2 13.8L4.9 27H27.1L25.8 13.8"
          fill="none"
          stroke={color}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2.3}
        />
      </Svg>
      <MaterialCommunityIcons
        name="bone"
        size={boneSize}
        color={color}
        style={[
          styles.racaoChipBagBoneIcon,
          {
            left: Math.round(size * 0.36),
            top: Math.round(size * 0.58),
          },
        ]}
      />
    </View>
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
  headerTopActions: { flexDirection: 'row', alignItems: 'center', gap: ESPACO.xs },
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
  loginButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.xs,
    backgroundColor: CORES.primario,
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
  },
  loginButtonText: { color: '#fff', fontSize: FONTE.normal, fontWeight: '700' },
  notificacoesButton: {
    width: 36,
    height: 36,
    borderRadius: RAIO.circulo,
    borderWidth: 1,
    borderColor: CORES.borda,
    backgroundColor: CORES.superficie,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  notificacoesBadge: {
    position: 'absolute',
    top: -5,
    right: -5,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: CORES.superficie,
    backgroundColor: '#DC2626',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  notificacoesBadgeText: {
    color: '#fff',
    fontSize: 9,
    fontWeight: '900',
  },
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
    justifyContent: 'center',
    gap: ESPACO.xs,
  },
  petChipTexto: {
    fontSize: FONTE.normal,
    fontWeight: '800',
  },
  petChipIconDiscreto: {
    opacity: 0.94,
  },
  racaoChipIcon: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  racaoChipBagBoneIcon: {
    position: 'absolute',
    transform: [{ rotate: '-32deg' }],
  },
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
