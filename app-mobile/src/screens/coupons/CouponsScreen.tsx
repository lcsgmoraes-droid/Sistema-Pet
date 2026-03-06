import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  TouchableOpacity,
  Clipboard,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import api from '../../services/api';
import { CORES } from '../../theme';

interface Cupom {
  codigo: string;
  tipo_desconto: string;
  valor_desconto: number;
  desconto_formatado: string;
  valor_minimo_pedido: number | null;
  valid_until: string | null;
  expirado: boolean;
}

export default function CouponsScreen() {
  const [cupons, setCupons] = useState<Cupom[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [copiado, setCopiado] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      const { data } = await api.get<Cupom[]>('/ecommerce/auth/meus-cupons');
      setCupons(data);
    } catch {
      setCupons([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const copiar = (codigo: string) => {
    Clipboard.setString(codigo);
    setCopiado(codigo);
    setTimeout(() => setCopiado(null), 2000);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={CORES.primario} />
      </View>
    );
  }

  if (cupons.length === 0) {
    return (
      <View style={styles.center}>
        <Ionicons name="ticket-outline" size={64} color={CORES.textoClaro} />
        <Text style={styles.vazio}>Você ainda não tem cupons</Text>
        <Text style={styles.vazioSub}>
          Participe de promoções e acumule benefícios!
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={cupons}
      keyExtractor={(item) => item.codigo}
      contentContainerStyle={styles.lista}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            carregar();
          }}
          colors={[CORES.primario]}
        />
      }
      renderItem={({ item }) => (
        <View style={[styles.card, item.expirado && styles.cardExpirado]}>
          <View style={styles.cardTopo}>
            <TouchableOpacity
              style={styles.codigoContainer}
              onPress={() => !item.expirado && copiar(item.codigo)}
              activeOpacity={item.expirado ? 1 : 0.7}
            >
              <Text style={styles.codigo}>{item.codigo}</Text>
              {!item.expirado && (
                <Ionicons
                  name={copiado === item.codigo ? 'checkmark' : 'copy-outline'}
                  size={16}
                  color={copiado === item.codigo ? CORES.sucesso : CORES.primario}
                  style={{ marginLeft: 6 }}
                />
              )}
            </TouchableOpacity>
            <View
              style={[
                styles.badge,
                item.expirado ? styles.badgeExpirado : styles.badgeAtivo,
              ]}
            >
              <Text
                style={[
                  styles.badgeTexto,
                  item.expirado
                    ? styles.badgeTextoExpirado
                    : styles.badgeTextoAtivo,
                ]}
              >
                {item.expirado ? 'Expirado' : 'Ativo'}
              </Text>
            </View>
          </View>

          <Text style={styles.desconto}>{item.desconto_formatado} de desconto</Text>

          {item.valor_minimo_pedido !== null && item.valor_minimo_pedido > 0 && (
            <Text style={styles.info}>
              Pedido mínimo: R$ {item.valor_minimo_pedido.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            </Text>
          )}

          {item.valid_until && (
            <Text style={[styles.info, item.expirado && styles.infoExpirado]}>
              Válido até {new Date(item.valid_until).toLocaleDateString('pt-BR')}
            </Text>
          )}

          {copiado === item.codigo && (
            <Text style={styles.copiouTexto}>Código copiado!</Text>
          )}
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
    backgroundColor: CORES.fundo,
  },
  vazio: {
    marginTop: 16,
    fontSize: 16,
    fontWeight: '600',
    color: CORES.texto,
    textAlign: 'center',
  },
  vazioSub: {
    marginTop: 8,
    fontSize: 13,
    color: CORES.textoClaro,
    textAlign: 'center',
  },
  lista: {
    padding: 16,
    gap: 12,
    backgroundColor: CORES.fundo,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
    borderLeftWidth: 4,
    borderLeftColor: CORES.primario,
  },
  cardExpirado: {
    borderLeftColor: CORES.textoClaro,
    opacity: 0.7,
  },
  cardTopo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  codigoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  codigo: {
    fontSize: 20,
    fontWeight: 'bold',
    letterSpacing: 2,
    color: CORES.primario,
    fontVariant: ['tabular-nums'] as any,
  },
  badge: {
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  badgeAtivo: {
    backgroundColor: '#e8f5e9',
  },
  badgeExpirado: {
    backgroundColor: '#f5f5f5',
  },
  badgeTexto: {
    fontSize: 11,
    fontWeight: '600',
  },
  badgeTextoAtivo: {
    color: '#2e7d32',
  },
  badgeTextoExpirado: {
    color: CORES.textoClaro,
  },
  desconto: {
    fontSize: 15,
    fontWeight: '600',
    color: CORES.texto,
    marginBottom: 4,
  },
  info: {
    fontSize: 12,
    color: CORES.textoClaro,
    marginTop: 2,
  },
  infoExpirado: {
    color: '#e57373',
  },
  copiouTexto: {
    marginTop: 8,
    fontSize: 12,
    color: CORES.sucesso ?? '#2e7d32',
    fontWeight: '600',
  },
});
