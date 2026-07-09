import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import React, { useCallback, useState } from 'react';
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
import {
  AppNotification,
  limparNotificacoesApp,
  listarNotificacoesApp,
  markNotificationAsRead,
} from '../../services/appNotifications.service';
import { CORES, ESPACO, FONTE, RAIO } from '../../theme';
import {
  appointmentNotificationTarget,
  stockNotificationToProductId,
} from '../../utils/notificationNavigation';

export default function NotificationsScreen({ navigation }: any) {
  const [items, setItems] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [clearing, setClearing] = useState(false);

  const carregar = useCallback(async () => {
    const response = await listarNotificacoesApp();
    setItems(response.items);
    setUnreadCount(response.unread_count);
  }, []);

  useFocusEffect(
    useCallback(() => {
      let active = true;
      setLoading(true);
      carregar()
        .catch(() => {
          if (active) setItems([]);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
      return () => {
        active = false;
      };
    }, [carregar]),
  );

  async function onRefresh() {
    setRefreshing(true);
    try {
      await carregar();
    } finally {
      setRefreshing(false);
    }
  }

  async function abrirNotificacao(item: AppNotification) {
    try {
      await markNotificationAsRead(item.id);
      setItems((atuais) =>
        atuais.map((notificacao) =>
          notificacao.id === item.id
            ? { ...notificacao, read_at: new Date().toISOString(), is_read: true }
            : notificacao,
        ),
      );
      setUnreadCount((count) => Math.max(0, count - (item.read_at ? 0 : 1)));
    } catch {
      // A navegacao ainda pode seguir; a leitura sincroniza na proxima abertura.
    }

    const produtoId = stockNotificationToProductId(item.data);
    if (produtoId) {
      navigation.navigate('Loja', {
        screen: 'DetalhesProduto',
        params: { produtoId },
      });
      return;
    }

    const appointmentTarget = appointmentNotificationTarget(item.data);
    if (appointmentTarget) {
      navigation.navigate(appointmentTarget.route, appointmentTarget.params);
    }
  }

  function confirmarLimpeza() {
    if (items.length === 0 || clearing) return;
    Alert.alert(
      'Limpar notificacoes',
      'Deseja limpar todas as notificacoes desta lista?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Limpar',
          style: 'destructive',
          onPress: limparLista,
        },
      ],
    );
  }

  async function limparLista() {
    setClearing(true);
    try {
      await limparNotificacoesApp();
      setItems([]);
      setUnreadCount(0);
    } catch {
      Alert.alert('Notificacoes', 'Nao foi possivel limpar agora.');
    } finally {
      setClearing(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={CORES.primario} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.summaryRow}>
        <View style={styles.summaryText}>
          <Text style={styles.summaryTitle}>Notificacoes</Text>
          <Text style={styles.summarySubtitle}>
            {unreadCount > 0 ? `${unreadCount} nao lida(s)` : 'Tudo em dia'}
          </Text>
        </View>
        {items.length > 0 ? (
          <TouchableOpacity
            style={[styles.clearButton, clearing && styles.clearButtonDisabled]}
            onPress={confirmarLimpeza}
            disabled={clearing}
          >
            {clearing ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Ionicons name="trash-outline" size={17} color="#fff" />
            )}
            <Text style={styles.clearButtonText}>Limpar</Text>
          </TouchableOpacity>
        ) : null}
      </View>

      <FlatList
        data={items}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={items.length ? styles.list : styles.emptyList}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={CORES.primario}
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="notifications-outline" size={34} color={CORES.textoClaro} />
            <Text style={styles.emptyTitle}>Nenhuma notificacao</Text>
            <Text style={styles.emptyText}>
              Quando houver novidades, elas aparecem aqui.
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.item, !item.read_at && styles.itemUnread]}
            activeOpacity={0.82}
            onPress={() => abrirNotificacao(item)}
          >
            <View style={styles.iconBox}>
              <Ionicons
                name={
                  item.source === 'stock_waitlist'
                    ? 'cube-outline'
                    : item.source === 'appointment_reminder'
                      ? 'calendar-outline'
                      : 'notifications-outline'
                }
                size={20}
                color={CORES.primario}
              />
            </View>
            <View style={styles.itemText}>
              <View style={styles.itemTitleRow}>
                <Text style={styles.itemTitle} numberOfLines={2}>
                  {item.title}
                </Text>
                {!item.read_at ? <View style={styles.unreadDot} /> : null}
              </View>
              <Text style={styles.itemBody} numberOfLines={3}>
                {item.body}
              </Text>
              <Text style={styles.itemDate}>{formatarData(item.created_at)}</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

function formatarData(value?: string | null): string {
  if (!value) return '';
  const data = new Date(value);
  if (Number.isNaN(data.getTime())) return '';
  return data.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: CORES.fundo,
  },
  summaryRow: {
    paddingHorizontal: ESPACO.lg,
    paddingVertical: ESPACO.md,
    backgroundColor: CORES.superficie,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.md,
  },
  summaryText: { flex: 1, minWidth: 0 },
  summaryTitle: { fontSize: FONTE.grande, fontWeight: '800', color: CORES.texto },
  summarySubtitle: {
    marginTop: 2,
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
  },
  clearButton: {
    minHeight: 38,
    paddingHorizontal: ESPACO.md,
    borderRadius: RAIO.md,
    backgroundColor: CORES.erro,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: ESPACO.xs,
  },
  clearButtonDisabled: { opacity: 0.72 },
  clearButtonText: { color: '#fff', fontWeight: '800', fontSize: FONTE.normal },
  list: { padding: ESPACO.md, gap: ESPACO.sm },
  emptyList: { flexGrow: 1, padding: ESPACO.lg },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: ESPACO.lg,
  },
  emptyTitle: {
    marginTop: ESPACO.sm,
    fontSize: FONTE.grande,
    fontWeight: '800',
    color: CORES.texto,
  },
  emptyText: {
    marginTop: ESPACO.xs,
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    textAlign: 'center',
  },
  item: {
    minHeight: 92,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    backgroundColor: CORES.superficie,
    padding: ESPACO.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.sm,
  },
  itemUnread: { borderColor: CORES.primario },
  iconBox: {
    width: 40,
    height: 40,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primarioClaro,
    alignItems: 'center',
    justifyContent: 'center',
  },
  itemText: { flex: 1, minWidth: 0 },
  itemTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.xs,
  },
  itemTitle: { flex: 1, fontSize: FONTE.media, fontWeight: '800', color: CORES.texto },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: CORES.primario,
  },
  itemBody: {
    marginTop: 4,
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    lineHeight: 19,
  },
  itemDate: {
    marginTop: 6,
    fontSize: FONTE.pequena,
    color: CORES.textoClaro,
  },
});
