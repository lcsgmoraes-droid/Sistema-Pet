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
  const [rotas, setRotas] = useState<Rota[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const { data } = await api.get<Rota[]>('/ecommerce/entregador/minhas-rotas');
      setRotas(data);
    } catch {
      Alert.alert('Erro', 'Não foi possível carregar as rotas. Tente novamente.');
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
    <FlatList
      data={rotas}
      keyExtractor={item => String(item.id)}
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
  );
}

// ─── Estilos ─────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  list: {
    padding: 16,
    gap: 12,
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
