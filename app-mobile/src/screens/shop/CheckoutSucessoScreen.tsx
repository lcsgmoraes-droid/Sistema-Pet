import React, { useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Share,
  Vibration,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { Pedido } from '../../types';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { formatarMoeda, formatarDataHora } from '../../utils/format';
import { useCartStore } from '../../store/cart.store';

interface Props {
  route: { params: { pedido: Pedido } };
}

export default function CheckoutSucessoScreen({ route }: Props) {
  const { pedido } = route.params;
  const navigation = useNavigation<any>();
  const { limpar } = useCartStore();

  useEffect(() => {
    // Vibrar para feedback positivo
    Vibration.vibrate([0, 100, 100, 100]);
    // Limpar carrinho local
    limpar().catch(() => {});
  }, []);

  const isEntrega = pedido.tipo_retirada === 'entrega';
  const isTerceiro = pedido.tipo_retirada === 'terceiro';

  async function compartilhar() {
    const msg = isEntrega
      ? `🐾 Comprei no PetShop App!\n` +
        `Pedido: ${pedido.pedido_id.slice(-8).toUpperCase()}\n` +
        `Entrega em: ${pedido.endereco_entrega || 'a combinar'}\n` +
        `Total: ${formatarMoeda(pedido.total)}`
      : `🐾 Comprei no PetShop App!\n` +
        `Pedido: ${pedido.pedido_id.slice(-8).toUpperCase()}\n` +
        `Palavra-chave: ${pedido.palavra_chave_retirada?.toUpperCase()}\n` +
        `Total: ${formatarMoeda(pedido.total)}`;
    await Share.share({ message: msg });
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Sucesso */}
      <View style={styles.iconeSucesso}>
        <Ionicons name="checkmark-circle" size={80} color={CORES.sucesso} />
      </View>

      <Text style={styles.titulo}>Pedido confirmado! 🎉</Text>
      <Text style={styles.subtitulo}>
        {isEntrega
          ? 'Seu pedido foi registrado. Entraremos em contato para combinar a entrega!'
          : 'Agora é só ir ao caixa, falar a palavra-chave e pronto!'}
      </Text>

      {/* Card de entrega */}
      {isEntrega ? (
        <View style={[styles.palavraChaveCard, { backgroundColor: CORES.sucesso }]}>
          <Text style={styles.palavraChaveLabel}>📦 Entrega solicitada</Text>
          <Text style={[styles.palavraChave, { fontSize: 18, letterSpacing: 0 }]}>
            {pedido.endereco_entrega || 'Endereço a confirmar'}
          </Text>
          <Text style={styles.palavraChaveInstrucao}>
            Pedido #{pedido.pedido_id.slice(-8).toUpperCase()}
          </Text>
        </View>
      ) : (
        /* Palavra-chave — destaque principal (retirada) */
        <View style={styles.palavraChaveCard}>
          <Text style={styles.palavraChaveLabel}>
            {isTerceiro ? '🔑 Senha de retirada (terceiro)' : 'Sua palavra-chave'}
          </Text>
          <Text style={styles.palavraChave}>
            {pedido.palavra_chave_retirada?.toUpperCase() ?? 'AGUARDANDO'}
          </Text>
          <Text style={styles.palavraChaveInstrucao}>
            {isTerceiro
              ? 'Compartilhe esta senha com a pessoa que vai retirar ✅'
              : 'Fale esta palavra no caixa para liberar sua saída ✅'}
          </Text>
        </View>
      )}

      {/* Resumo do pedido */}
      <View style={styles.resumoCard}>
        <Text style={styles.resumoTitulo}>Resumo do pedido</Text>

        <View style={styles.resumoRow}>
          <Text style={styles.resumoLabel}>Pedido</Text>
          <Text style={styles.resumoValor}>#{pedido.pedido_id.slice(-8).toUpperCase()}</Text>
        </View>
        <View style={styles.resumoRow}>
          <Text style={styles.resumoLabel}>Data</Text>
          <Text style={styles.resumoValor}>{formatarDataHora(pedido.created_at)}</Text>
        </View>
        <View style={styles.resumoRow}>
          <Text style={styles.resumoLabel}>Status</Text>
          <View style={styles.badge}>
            <Text style={styles.badgeTexto}>Pendente</Text>
          </View>
        </View>

        {/* Itens */}
        <View style={styles.itensSection}>
          <Text style={styles.itensTitulo}>Produtos</Text>
          {pedido.itens?.map((item, idx) => (
            <View key={idx} style={styles.itemRow}>
              <Text style={styles.itemNome} numberOfLines={1}>
                {item.quantidade}x {item.nome}
              </Text>
              <Text style={styles.itemSubtotal}>{formatarMoeda(item.subtotal)}</Text>
            </View>
          ))}
        </View>

        <View style={[styles.resumoRow, styles.totalRow]}>
          <Text style={styles.totalLabel}>Total</Text>
          <Text style={styles.totalValor}>{formatarMoeda(pedido.total)}</Text>
        </View>
      </View>

      {/* Instruções */}
      <View style={styles.instrucoes}>
        {isEntrega ? (
          <>
            <InstrucaoItem numero={1} texto="Pedido registrado com sucesso" />
            <InstrucaoItem numero={2} texto="Aguarde o contato da loja para combinar a entrega" />
            <InstrucaoItem numero={3} texto="Pague ao receber ou conforme combinado" />
          </>
        ) : (
          <>
            <InstrucaoItem numero={1} texto="Vá ao caixa da loja" />
            <InstrucaoItem numero={2} texto={`Fale a palavra "${pedido.palavra_chave_retirada?.toUpperCase()}"`} />
            <InstrucaoItem numero={3} texto="O funcionário confirma e você sai!" />
          </>
        )}
      </View>

      {/* Ações */}
      <TouchableOpacity style={styles.botaoCompartilhar} onPress={compartilhar}>
        <Ionicons name="share-outline" size={18} color={CORES.primario} />
        <Text style={styles.botaoCompartilharTexto}>Compartilhar comprovante</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.botaoInicio}
        onPress={() => navigation.navigate('Catalogo')}
      >
        <Text style={styles.botaoInicioTexto}>Continuar comprando</Text>
      </TouchableOpacity>

      <View style={{ height: ESPACO.xxl }} />
    </ScrollView>
  );
}

function InstrucaoItem({ numero, texto }: { numero: number; texto: string }) {
  return (
    <View style={styles.instrucaoItem}>
      <View style={styles.instrucaoNumero}>
        <Text style={styles.instrucaoNumeroTexto}>{numero}</Text>
      </View>
      <Text style={styles.instrucaoTexto}>{texto}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.lg, alignItems: 'center' },
  iconeSucesso: { marginTop: ESPACO.xl, marginBottom: ESPACO.md },
  titulo: {
    fontSize: FONTE.titulo,
    fontWeight: 'bold',
    color: CORES.texto,
    textAlign: 'center',
  },
  subtitulo: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    textAlign: 'center',
    marginTop: ESPACO.xs,
    marginBottom: ESPACO.lg,
  },
  palavraChaveCard: {
    width: '100%',
    backgroundColor: CORES.primario,
    borderRadius: RAIO.lg,
    padding: ESPACO.xl,
    alignItems: 'center',
    marginBottom: ESPACO.lg,
    ...SOMBRA,
  },
  palavraChaveLabel: {
    fontSize: FONTE.normal,
    color: 'rgba(255,255,255,0.8)',
    marginBottom: ESPACO.sm,
  },
  palavraChave: {
    fontSize: 42,
    fontWeight: 'bold',
    color: '#fff',
    letterSpacing: 2,
    textAlign: 'center',
  },
  palavraChaveInstrucao: {
    fontSize: FONTE.normal,
    color: 'rgba(255,255,255,0.9)',
    marginTop: ESPACO.md,
    textAlign: 'center',
  },
  resumoCard: {
    width: '100%',
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.lg,
    padding: ESPACO.lg,
    marginBottom: ESPACO.lg,
    ...SOMBRA,
  },
  resumoTitulo: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto, marginBottom: ESPACO.md },
  resumoRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: ESPACO.sm },
  resumoLabel: { fontSize: FONTE.normal, color: CORES.textoSecundario },
  resumoValor: { fontSize: FONTE.normal, fontWeight: '600', color: CORES.texto },
  badge: {
    backgroundColor: '#FEF3C7',
    paddingHorizontal: ESPACO.sm,
    paddingVertical: 2,
    borderRadius: RAIO.circulo,
  },
  badgeTexto: { fontSize: FONTE.pequena, color: '#92400E', fontWeight: '600' },
  itensSection: {
    borderTopWidth: 1,
    borderTopColor: CORES.borda,
    paddingTop: ESPACO.sm,
    marginTop: ESPACO.sm,
    marginBottom: ESPACO.sm,
  },
  itensTitulo: { fontSize: FONTE.normal, fontWeight: '600', color: CORES.textoSecundario, marginBottom: ESPACO.xs },
  itemRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  itemNome: { fontSize: FONTE.normal, color: CORES.texto, flex: 1 },
  itemSubtotal: { fontSize: FONTE.normal, fontWeight: '600', color: CORES.texto },
  totalRow: { borderTopWidth: 1, borderTopColor: CORES.borda, paddingTop: ESPACO.sm, marginTop: ESPACO.xs },
  totalLabel: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto },
  totalValor: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.primario },
  instrucoes: { width: '100%', marginBottom: ESPACO.lg },
  instrucaoItem: { flexDirection: 'row', alignItems: 'center', marginBottom: ESPACO.sm, gap: ESPACO.md },
  instrucaoNumero: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: CORES.sucesso,
    justifyContent: 'center',
    alignItems: 'center',
  },
  instrucaoNumeroTexto: { color: '#fff', fontWeight: 'bold', fontSize: FONTE.normal },
  instrucaoTexto: { fontSize: FONTE.normal, color: CORES.texto, flex: 1 },
  botaoCompartilhar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.sm,
    paddingVertical: ESPACO.md,
    paddingHorizontal: ESPACO.xl,
    borderWidth: 1,
    borderColor: CORES.primario,
    borderRadius: RAIO.md,
    marginBottom: ESPACO.sm,
    width: '100%',
    justifyContent: 'center',
  },
  botaoCompartilharTexto: { color: CORES.primario, fontWeight: '600', fontSize: FONTE.normal },
  botaoInicio: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.md,
    width: '100%',
    alignItems: 'center',
  },
  botaoInicioTexto: { color: '#fff', fontWeight: 'bold', fontSize: FONTE.media },
});
