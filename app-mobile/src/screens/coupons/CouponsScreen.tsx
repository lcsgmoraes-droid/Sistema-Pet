import { Ionicons } from '@expo/vector-icons';
import * as Clipboard from 'expo-clipboard';
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Modal,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import QRCode from 'react-native-qrcode-svg';
import api from '../../services/api';
import { CORES } from '../../theme';

interface CupomApi {
  id?: number;
  code?: string;
  codigo?: string;
  coupon_type?: string;
  tipo_desconto?: string;
  discount_value?: number | null;
  valor_desconto?: number | null;
  discount_percent?: number | null;
  desconto_formatado?: string;
  min_purchase_value?: number | null;
  valor_minimo_pedido?: number | null;
  valid_until: string | null;
  expirado: boolean;
}

interface Cupom {
  id: string;
  codigo: string;
  desconto_formatado: string;
  valor_minimo_pedido: number | null;
  valid_until: string | null;
  expirado: boolean;
}

function brl(valor: number): string {
  return valor.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function normalizarCupom(item: CupomApi): Cupom | null {
  const codigo = String(item.code || item.codigo || '').trim();
  if (!codigo) return null;

  let desconto = item.desconto_formatado;
  if (!desconto) {
    if (item.discount_percent != null) {
      desconto = `${item.discount_percent}% de desconto`;
    } else if (item.discount_value != null) {
      desconto = `R$ ${brl(Number(item.discount_value || 0))} de desconto`;
    } else if (item.valor_desconto != null) {
      desconto = `R$ ${brl(Number(item.valor_desconto || 0))} de desconto`;
    } else {
      desconto = 'Beneficio especial';
    }
  }

  return {
    id: String(item.id ?? codigo),
    codigo,
    desconto_formatado: desconto,
    valor_minimo_pedido: item.min_purchase_value ?? item.valor_minimo_pedido ?? null,
    valid_until: item.valid_until ?? null,
    expirado: Boolean(item.expirado),
  };
}

export default function CouponsScreen() {
  const [cupons, setCupons] = useState<Cupom[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [copiado, setCopiado] = useState<string | null>(null);
  const [qrModal, setQrModal] = useState<string | null>(null); // codigo do cupom cujo QR está aberto

  const carregar = useCallback(async () => {
    try {
      const { data } = await api.get<CupomApi[]>('/ecommerce/auth/meus-cupons');
      setCupons((Array.isArray(data) ? data : []).map(normalizarCupom).filter(Boolean) as Cupom[]);
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

  const copiar = async (codigo: string) => {
    await Clipboard.setStringAsync(codigo);
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
    <>
    <FlatList
      data={cupons}
      keyExtractor={(item) => item.id}
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

          <Text style={styles.desconto}>{item.desconto_formatado}</Text>

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

          {!item.expirado && (
            <TouchableOpacity
              style={styles.qrBtn}
              onPress={() => setQrModal(item.codigo)}
              activeOpacity={0.7}
            >
              <Ionicons name="qr-code-outline" size={14} color={CORES.primario} />
              <Text style={styles.qrBtnTexto}>Mostrar QR Code</Text>
            </TouchableOpacity>
          )}
        </View>
      )}
    />

    {/* Modal QR Code */}
    <Modal
      visible={!!qrModal}
      transparent
      animationType="fade"
      onRequestClose={() => setQrModal(null)}
    >
      <TouchableOpacity
        style={styles.qrOverlay}
        activeOpacity={1}
        onPress={() => setQrModal(null)}
      >
        <View style={styles.qrContainer}>
          <Text style={styles.qrTitulo}>QR Code do Cupom</Text>
          {qrModal && (
            <>
              <QRCode
                value={qrModal}
                size={200}
                color="#1a1a2e"
                backgroundColor="#ffffff"
              />
              <Text style={styles.qrCodigo}>{qrModal}</Text>
            </>
          )}
          <Text style={styles.qrDica}>
            Mostre este QR Code no caixa para usar o cupom
          </Text>
          <TouchableOpacity
            style={styles.qrFechar}
            onPress={() => setQrModal(null)}
          >
            <Text style={styles.qrFecharTexto}>Fechar</Text>
          </TouchableOpacity>
        </View>
      </TouchableOpacity>
    </Modal>
    </>
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
  qrBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 10,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: CORES.primario,
    alignSelf: 'flex-start',
  },
  qrBtnTexto: {
    fontSize: 12,
    color: CORES.primario,
    fontWeight: '600',
  },
  qrOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  qrContainer: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 28,
    alignItems: 'center',
    width: '100%',
    maxWidth: 320,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 12,
    elevation: 8,
  },
  qrTitulo: {
    fontSize: 16,
    fontWeight: '700',
    color: CORES.texto,
    marginBottom: 20,
  },
  qrCodigo: {
    marginTop: 16,
    fontSize: 22,
    fontWeight: 'bold',
    letterSpacing: 3,
    color: CORES.primario,
  },
  qrDica: {
    marginTop: 12,
    fontSize: 12,
    color: CORES.textoClaro,
    textAlign: 'center',
    lineHeight: 18,
  },
  qrFechar: {
    marginTop: 20,
    paddingVertical: 10,
    paddingHorizontal: 32,
    backgroundColor: CORES.primario,
    borderRadius: 12,
  },
  qrFecharTexto: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 14,
  },
});
