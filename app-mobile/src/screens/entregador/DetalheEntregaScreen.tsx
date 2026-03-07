import { RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import React, { useCallback, useEffect, useState } from 'react';
import {
    ActivityIndicator,
    Alert,
    Linking,
    ScrollView,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from 'react-native';
import api from '../../services/api';
import { EntregadorStackParamList } from '../../types/entregadorNavigation';

// ─── Tipos ───────────────────────────────────────────────────────────────────

interface Parada {
  id: number;
  ordem: number;
  endereco: string;
  status: string; // pendente | entregue | nao_entregue
  cliente_nome?: string;
  cliente_telefone?: string;
  cliente_celular?: string;
  observacoes?: string;
  data_entrega?: string;
}

interface Rota {
  id: number;
  numero: string;
  status: string;
  paradas: Parada[];
}

type RouteProps = RouteProp<EntregadorStackParamList, 'DetalheEntrega'>;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function abrirMapa(endereco: string) {
  const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(endereco)}`;
  Linking.openURL(url).catch(() =>
    Alert.alert('Erro', 'Não foi possível abrir o mapa.')
  );
}

function ligar(telefone?: string | null) {
  if (!telefone) return;
  const digits = telefone.replaceAll(/\D/g, '');
  Linking.openURL(`tel:${digits}`).catch(() =>
    Alert.alert('Erro', 'Não foi possível ligar.')
  );
}

const STATUS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  pendente:      { label: 'Pendente',       color: '#92400e', bg: '#fef3c7' },
  entregue:      { label: 'Entregue ✓',     color: '#065f46', bg: '#d1fae5' },
  nao_entregue:  { label: 'Não entregue ✗', color: '#7f1d1d', bg: '#fee2e2' },
};

// ─── Componente ──────────────────────────────────────────────────────────────

export default function DetalheEntregaScreen() {
  const navigation = useNavigation();
  const route = useRoute<RouteProps>();
  const { rotaId, numero } = route.params;

  const [rota, setRota] = useState<Rota | null>(null);
  const [loading, setLoading] = useState(true);
  const [processando, setProcessando] = useState<number | null>(null); // parada id em processamento

  const carregar = useCallback(async () => {
    try {
      const { data } = await api.get<Rota>(`/rotas-entrega/${rotaId}`);
      let r: Rota = data;
      if (r.paradas) {
        r = { ...r, paradas: [...r.paradas].sort((a, b) => a.ordem - b.ordem) };
      }
      setRota(r);
    } catch {
      Alert.alert('Erro', 'Não foi possível carregar a rota.');
    } finally {
      setLoading(false);
    }
  }, [rotaId]);

  useEffect(() => {
    navigation.setOptions({ title: `Rota #${numero}` });
    carregar();
  }, [carregar, navigation, numero]);

  // ── Ações nas paradas ─────────────────────────────────────────────────────

  async function marcarEntregue(paradaId: number) {
    setProcessando(paradaId);
    try {
      await api.post(`/rotas-entrega/${rotaId}/paradas/${paradaId}/marcar-entregue`, {});
      await carregar();
    } catch {
      Alert.alert('Erro', 'Não foi possível marcar como entregue.');
    } finally {
      setProcessando(null);
    }
  }

  async function marcarNaoEntregue(paradaId: number) {
    Alert.prompt(
      'Motivo',
      'Descreva o motivo da não entrega (opcional):',
      async (motivo) => {
        setProcessando(paradaId);
        try {
          await api.post(`/rotas-entrega/${rotaId}/paradas/${paradaId}/nao-entregue`, {
            motivo: motivo || '',
          });
          await carregar();
        } catch {
          Alert.alert('Erro', 'Não foi possível registrar a ocorrência.');
        } finally {
          setProcessando(null);
        }
      },
      'plain-text',
      '',
    );
  }

  async function iniciarRota() {
    try {
      await api.post(`/rotas-entrega/${rotaId}/iniciar`, {});
      await carregar();
    } catch {
      Alert.alert('Erro', 'Não foi possível iniciar a rota.');
    }
  }

  // ── Render parada ─────────────────────────────────────────────────────────

  function renderParada(parada: Parada) {
    const badge = STATUS_BADGE[parada.status] ?? { label: parada.status, color: '#374151', bg: '#f3f4f6' };
    const emProcessamento = processando === parada.id;

    return (
      <View key={parada.id} style={styles.paradaCard}>
        {/* Cabeçalho */}
        <View style={styles.paradaHeader}>
          <View style={styles.ordemCircle}>
            <Text style={styles.ordemText}>{parada.ordem}</Text>
          </View>
          <View style={styles.paradaInfo}>
            <Text style={styles.paradaCliente} numberOfLines={1}>
              {parada.cliente_nome ?? 'Cliente'}
            </Text>
            <Text style={styles.paradaEndereco} numberOfLines={2}>
              {parada.endereco}
            </Text>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: badge.bg }]}>
            <Text style={[styles.statusBadgeText, { color: badge.color }]}>{badge.label}</Text>
          </View>
        </View>

        {/* Observações (se houver) */}
        {!!parada.observacoes && (
          <Text style={styles.observacoes}>📝 {parada.observacoes}</Text>
        )}

        {/* Botões de ação */}
        <View style={styles.paradaBotoes}>
          <TouchableOpacity
            style={styles.btnMapa}
            onPress={() => abrirMapa(parada.endereco)}
          >
            <Text style={styles.btnMapaText}>📍 Navegar</Text>
          </TouchableOpacity>

          {parada.cliente_telefone || parada.cliente_celular ? (
            <TouchableOpacity
              style={styles.btnLigar}
              onPress={() => ligar(parada.cliente_celular ?? parada.cliente_telefone)}
            >
              <Text style={styles.btnLigarText}>📞 Ligar</Text>
            </TouchableOpacity>
          ) : null}
        </View>

        {/* Ações de entrega — só mostrar se ainda estiver pendente */}
        {parada.status === 'pendente' && (
          <View style={styles.paradaAcoes}>
            {emProcessamento ? (
              <ActivityIndicator color="#2563eb" />
            ) : (
              <>
                <TouchableOpacity
                  style={styles.btnEntregue}
                  onPress={() => marcarEntregue(parada.id)}
                >
                  <Text style={styles.btnEntregueText}>✅ Entregue</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.btnNaoEntregue}
                  onPress={() => marcarNaoEntregue(parada.id)}
                >
                  <Text style={styles.btnNaoEntregueText}>❌ Não entregue</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        )}
      </View>
    );
  }

  // ── Tela ──────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    );
  }

  if (!rota) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Rota não encontrada.</Text>
      </View>
    );
  }

  const pendentes = rota.paradas.filter(p => p.status === 'pendente').length;
  const entregues = rota.paradas.filter(p => p.status === 'entregue').length;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Resumo */}
      <View style={styles.resumo}>
        <View style={styles.resumoItem}>
          <Text style={styles.resumoValor}>{rota.paradas.length}</Text>
          <Text style={styles.resumoLabel}>Total</Text>
        </View>
        <View style={styles.resumoItem}>
          <Text style={[styles.resumoValor, { color: '#f59e0b' }]}>{pendentes}</Text>
          <Text style={styles.resumoLabel}>Pendentes</Text>
        </View>
        <View style={styles.resumoItem}>
          <Text style={[styles.resumoValor, { color: '#10b981' }]}>{entregues}</Text>
          <Text style={styles.resumoLabel}>Entregues</Text>
        </View>
      </View>

      {/* Botão iniciar rota (só se pendente) */}
      {rota.status === 'pendente' && (
        <TouchableOpacity style={styles.btnIniciar} onPress={iniciarRota}>
          <Text style={styles.btnIniciarText}>▶  Iniciar Rota</Text>
        </TouchableOpacity>
      )}

      {/* Lista de paradas */}
      {rota.paradas.map(renderParada)}
    </ScrollView>
  );
}

// ─── Estilos ─────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorText: { color: '#ef4444', fontSize: 16 },

  // Resumo
  resumo: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    justifyContent: 'space-around',
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 1 },
    elevation: 1,
  },
  resumoItem: { alignItems: 'center' },
  resumoValor: { fontSize: 22, fontWeight: '700', color: '#111827' },
  resumoLabel: { fontSize: 12, color: '#6b7280', marginTop: 2 },

  // Botão iniciar
  btnIniciar: {
    backgroundColor: '#2563eb',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    marginBottom: 16,
  },
  btnIniciarText: { color: '#fff', fontSize: 16, fontWeight: '700' },

  // Card de parada
  paradaCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 1 },
    elevation: 1,
  },
  paradaHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 10 },
  ordemCircle: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#2563eb',
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
    marginTop: 2,
  },
  ordemText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  paradaInfo: { flex: 1 },
  paradaCliente: { fontSize: 15, fontWeight: '600', color: '#111827' },
  paradaEndereco: { fontSize: 13, color: '#6b7280', marginTop: 2 },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 20,
    flexShrink: 0,
  },
  statusBadgeText: { fontSize: 11, fontWeight: '600' },

  observacoes: { fontSize: 13, color: '#374151', marginBottom: 8, fontStyle: 'italic' },

  // Botões de ação (mapa + ligar)
  paradaBotoes: { flexDirection: 'row', gap: 8, marginBottom: 10 },
  btnMapa: {
    flex: 1,
    backgroundColor: '#eff6ff',
    borderRadius: 8,
    padding: 10,
    alignItems: 'center',
  },
  btnMapaText: { color: '#2563eb', fontWeight: '600', fontSize: 13 },
  btnLigar: {
    flex: 1,
    backgroundColor: '#f0fdf4',
    borderRadius: 8,
    padding: 10,
    alignItems: 'center',
  },
  btnLigarText: { color: '#16a34a', fontWeight: '600', fontSize: 13 },

  // Ações de entrega
  paradaAcoes: { flexDirection: 'row', gap: 8 },
  btnEntregue: {
    flex: 1,
    backgroundColor: '#10b981',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
  },
  btnEntregueText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  btnNaoEntregue: {
    flex: 1,
    backgroundColor: '#ef4444',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
  },
  btnNaoEntregueText: { color: '#fff', fontWeight: '700', fontSize: 14 },
});
