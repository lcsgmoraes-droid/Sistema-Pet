import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import React, { useCallback, useEffect, useState } from 'react';
import {
    ActivityIndicator,
    Alert,
    FlatList,
    RefreshControl,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from 'react-native';
import api from '../../services/api';
import { EntregadorStackParamList } from '../../types/entregadorNavigation';

// ─── Tipos ───────────────────────────────────────────────────────────────────

interface ParadaResumo {
  id: number;
  ordem: number;
  endereco: string;
  status: string; // pendente | entregue | nao_entregue
  cliente_nome?: string;
}

interface Rota {
  id: number;
  numero: string;
  status: string; // pendente | em_rota | em_andamento | concluida
  created_at: string;
  paradas: ParadaResumo[];
}

interface EntregaAberta {
  id: number;
  numero_venda: string;
  cliente_nome: string;
  endereco_entrega: string;
  ordem_otimizada?: number | null;
  total: number;
  taxa_entrega: number;
}

type Nav = NativeStackNavigationProp<EntregadorStackParamList, 'MinhasRotas'>;

// ─── Helpers ─────────────────────────────────────────────────────────────────

const BADGE: Record<string, { label: string; color: string }> = {
  pendente:     { label: 'Pendente',     color: '#f59e0b' },
  em_rota:      { label: 'Em rota',      color: '#3b82f6' },
  em_andamento: { label: 'Em andamento', color: '#3b82f6' },
  concluida:    { label: 'Concluída',    color: '#10b981' },
};

function badgeFor(status: string) {
  return BADGE[status] ?? { label: status, color: '#6b7280' };
}

// ─── Componente ──────────────────────────────────────────────────────────────

export default function RotasDoEntregadorScreen() {
  const navigation = useNavigation<Nav>();
  const [aba, setAba] = useState<'abertas' | 'rotas'>('abertas');

  const [entregasAbertas, setEntregasAbertas] = useState<EntregaAberta[]>([]);
  const [selecionadas, setSelecionadas] = useState<number[]>([]);
  const [otimizando, setOtimizando] = useState(false);
  const [criandoRota, setCriandoRota] = useState(false);

  const [rotas, setRotas] = useState<Rota[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const [rotasRes, abertasRes] = await Promise.all([
        api.get<Rota[]>('/ecommerce/entregador/minhas-rotas'),
        api.get<EntregaAberta[]>('/ecommerce/entregador/entregas-abertas'),
      ]);
      setRotas(rotasRes.data || []);
      setEntregasAbertas(abertasRes.data || []);
    } catch {
      Alert.alert('Erro', 'Não foi possível carregar as entregas. Tente novamente.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    carregar();
  }, [carregar]);

  function toggleEntrega(vendaId: number) {
    setSelecionadas((prev) =>
      prev.includes(vendaId) ? prev.filter((id) => id !== vendaId) : [...prev, vendaId],
    );
  }

  async function otimizarSelecionadas() {
    if (selecionadas.length === 0) {
      Alert.alert('Atenção', 'Selecione ao menos uma entrega para otimizar.');
      return;
    }
    setOtimizando(true);
    try {
      await api.post('/ecommerce/entregador/entregas-abertas/otimizar-selecionadas', {
        venda_ids: selecionadas,
      });
      Alert.alert('Sucesso', 'Ordem das entregas otimizada com sucesso.');
      await carregar();
    } catch {
      Alert.alert('Erro', 'Não foi possível otimizar as entregas selecionadas.');
    } finally {
      setOtimizando(false);
    }
  }

  async function criarRotaSelecionadas() {
    if (selecionadas.length === 0) {
      Alert.alert('Atenção', 'Selecione ao menos uma entrega para criar a rota.');
      return;
    }

    const confirmarCriacao = async () => {
      setCriandoRota(true);
      try {
        const response = await api.post<Rota>('/ecommerce/entregador/rotas', { venda_ids: selecionadas });
        const novaRota = response.data;
        setSelecionadas([]);
        setAba('rotas');
        await carregar();
        if (novaRota?.id && novaRota?.numero) {
          Alert.alert(
            'Rota criada',
            'Agora inicie a rota na próxima tela para começar as entregas.',
            [
              {
                text: 'Abrir rota',
                onPress: () => {
                  navigation.navigate('DetalheEntrega', {
                    rotaId: novaRota.id,
                    numero: novaRota.numero,
                  });
                },
              },
              { text: 'Depois', style: 'cancel' },
            ],
          );
        } else {
          Alert.alert('Sucesso', 'Rota criada com sucesso. Abra a rota e toque em "Iniciar Rota".');
        }
      } catch {
        Alert.alert('Erro', 'Não foi possível criar a rota agora.');
      } finally {
        setCriandoRota(false);
      }
    };

    Alert.alert(
      'Criar rota',
      `Criar rota com ${selecionadas.length} entrega(s) selecionada(s)?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Criar rota',
          onPress: () => {
            void confirmarCriacao();
          },
        },
      ],
    );
  }

  // ── Render item ────────────────────────────────────────────────────────────

  const renderRota = ({ item }: { item: Rota }) => {
    const badge = badgeFor(item.status);
    const total = item.paradas.length;
    const entregues = item.paradas.filter(p => p.status === 'entregue').length;
    const data = new Date(item.created_at).toLocaleDateString('pt-BR');

    return (
      <TouchableOpacity
        style={styles.card}
        activeOpacity={0.75}
        onPress={() => navigation.navigate('DetalheEntrega', { rotaId: item.id, numero: item.numero })}
      >
        <View style={styles.cardHeader}>
          <Text style={styles.cardNumero}>Rota #{item.numero}</Text>
          <View style={[styles.badge, { backgroundColor: badge.color }]}>
            <Text style={styles.badgeText}>{badge.label}</Text>
          </View>
        </View>

        <Text style={styles.cardData}>{data}</Text>

        <View style={styles.cardFooter}>
          <Text style={styles.cardParadas}>
            {total} {total === 1 ? 'parada' : 'paradas'}
          </Text>
          {total > 0 && (
            <Text style={styles.cardProgresso}>
              {entregues}/{total} entregues
            </Text>
          )}
        </View>

        {item.paradas.slice(0, 3).map(p => (
          <Text key={p.id} style={styles.cardParadaItem} numberOfLines={1}>
            {p.ordem}. {p.cliente_nome ?? 'Cliente'} — {p.endereco}
          </Text>
        ))}
        {total > 3 && (
          <Text style={styles.cardMais}>+{total - 3} mais…</Text>
        )}
      </TouchableOpacity>
    );
  };

  const renderEntregaAberta = ({ item }: { item: EntregaAberta }) => {
    const selecionada = selecionadas.includes(item.id);
    return (
      <TouchableOpacity
        style={[styles.card, selecionada && styles.cardSelecionado]}
        onPress={() => toggleEntrega(item.id)}
        activeOpacity={0.8}
      >
        <View style={styles.cardHeader}>
          <Text style={styles.cardNumero}>Venda #{item.numero_venda}</Text>
          <View style={[styles.checkbox, selecionada && styles.checkboxAtivo]}>
            <Text style={styles.checkboxTexto}>{selecionada ? '✓' : ''}</Text>
          </View>
        </View>
        <Text style={styles.cardCliente}>{item.cliente_nome}</Text>
        <Text style={styles.cardParadaItem} numberOfLines={2}>
          📍 {item.endereco_entrega}
        </Text>
        <Text style={styles.cardData}>
          Total: R$ {Number(item.total || 0).toFixed(2)}
          {item.ordem_otimizada ? ` • Ordem otimizada: ${item.ordem_otimizada}` : ''}
        </Text>
      </TouchableOpacity>
    );
  };

  // ── Tela ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2563eb" />
        <Text style={styles.loadingText}>Carregando rotas…</Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      <View style={styles.tabsWrap}>
        <TouchableOpacity
          style={[styles.tabBtn, aba === 'abertas' && styles.tabBtnAtivo]}
          onPress={() => setAba('abertas')}
        >
          <Text style={[styles.tabText, aba === 'abertas' && styles.tabTextAtivo]}>
            📦 Entregas em Aberto
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tabBtn, aba === 'rotas' && styles.tabBtnAtivo]}
          onPress={() => setAba('rotas')}
        >
          <Text style={[styles.tabText, aba === 'rotas' && styles.tabTextAtivo]}>
            🚚 Rotas de Entrega
          </Text>
        </TouchableOpacity>
      </View>

      {aba === 'abertas' && (
        <>
          <View style={styles.actionsBar}>
            <TouchableOpacity
              style={[styles.actionBtn, (otimizando || criandoRota) && styles.actionBtnDisabled]}
              disabled={otimizando || criandoRota}
              onPress={otimizarSelecionadas}
            >
              <Text style={styles.actionBtnText}>
                {otimizando ? 'Otimizando...' : '🗺️ Otimizar Selecionadas'}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.actionBtnPrimary, (otimizando || criandoRota) && styles.actionBtnDisabled]}
              disabled={otimizando || criandoRota}
              onPress={criarRotaSelecionadas}
            >
              <Text style={styles.actionBtnPrimaryText}>
                {criandoRota ? 'Criando...' : `✅ Criar Rota (${selecionadas.length})`}
              </Text>
            </TouchableOpacity>
          </View>

          <FlatList
            data={entregasAbertas}
            keyExtractor={(item) => String(item.id)}
            renderItem={renderEntregaAberta}
            contentContainerStyle={entregasAbertas.length === 0 ? styles.emptyContainer : styles.list}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
            ListEmptyComponent={
              <View style={styles.center}>
                <Text style={styles.emptyIcon}>📦</Text>
                <Text style={styles.emptyTitle}>Nenhuma entrega em aberto</Text>
                <Text style={styles.emptySubtitle}>Puxe para baixo para atualizar</Text>
              </View>
            }
          />
        </>
      )}

      {aba === 'rotas' && (
        <FlatList
          data={rotas}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderRota}
          contentContainerStyle={rotas.length === 0 ? styles.emptyContainer : styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          ListEmptyComponent={
            <View style={styles.center}>
              <Text style={styles.emptyIcon}>🚚</Text>
              <Text style={styles.emptyTitle}>Nenhuma rota para hoje</Text>
              <Text style={styles.emptySubtitle}>Puxe para baixo para atualizar</Text>
            </View>
          }
        />
      )}
    </View>
  );
}

// ─── Estilos ─────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  list: {
    padding: 16,
    gap: 12,
  },
  tabsWrap: {
    flexDirection: 'row',
    padding: 10,
    gap: 8,
    backgroundColor: '#eef2ff',
  },
  tabBtn: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#c7d2fe',
    paddingVertical: 10,
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  tabBtnAtivo: {
    backgroundColor: '#1d4ed8',
    borderColor: '#1d4ed8',
  },
  tabText: {
    color: '#1e3a8a',
    fontSize: 13,
    fontWeight: '600',
  },
  tabTextAtivo: {
    color: '#fff',
  },
  actionsBar: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 12,
    paddingTop: 8,
  },
  actionBtn: {
    flex: 1,
    backgroundColor: '#0f766e',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  actionBtnPrimary: {
    flex: 1,
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  actionBtnDisabled: {
    opacity: 0.6,
  },
  actionBtnText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '700',
  },
  actionBtnPrimaryText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '700',
  },
  emptyContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },
  loadingText: {
    marginTop: 12,
    color: '#6b7280',
    fontSize: 14,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 8,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 4,
  },
  // Card
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
    marginBottom: 12,
  },
  cardSelecionado: {
    borderWidth: 2,
    borderColor: '#2563eb',
    backgroundColor: '#eff6ff',
  },
  cardCliente: {
    fontSize: 14,
    color: '#111827',
    fontWeight: '600',
    marginBottom: 4,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderWidth: 1,
    borderColor: '#9ca3af',
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
  },
  checkboxAtivo: {
    backgroundColor: '#2563eb',
    borderColor: '#2563eb',
  },
  checkboxTexto: {
    color: '#fff',
    fontWeight: '700',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  cardNumero: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 20,
  },
  badgeText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  cardData: {
    fontSize: 13,
    color: '#6b7280',
    marginBottom: 8,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  cardParadas: {
    fontSize: 14,
    color: '#374151',
    fontWeight: '500',
  },
  cardProgresso: {
    fontSize: 14,
    color: '#2563eb',
    fontWeight: '500',
  },
  cardParadaItem: {
    fontSize: 13,
    color: '#6b7280',
    marginTop: 2,
  },
  cardMais: {
    fontSize: 13,
    color: '#9ca3af',
    marginTop: 4,
  },
});
