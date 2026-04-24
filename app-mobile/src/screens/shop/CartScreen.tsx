import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Image,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  Modal,
  ScrollView as RNScrollView,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { useCartStore } from '../../store/cart.store';
import { useAuthStore } from '../../store/auth.store';
import { finalizarCheckoutAppLoja } from '../../services/shop.service';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { formatarMoeda } from '../../utils/format';

export default function CartScreen() {
  const navigation = useNavigation<any>();
  const { itens, subtotal, carregar, atualizar, remover, limpar } = useCartStore();
  const { user } = useAuthStore();
  const [finalizando, setFinalizando] = useState(false);

  // Forma de pagamento online
  const [pagamentoTipo, setPagamentoTipo] = useState<'pix' | 'debito' | 'credito' | ''>('');
  const [pagamentoBandeira, setPagamentoBandeira] = useState<string>('Visa');
  const [pagamentoParcelas, setPagamentoParcelas] = useState<number>(1);

  // Modo de recebimento
  const [modo, setModo] = useState<'retirada' | 'entrega'>('retirada');
  const [tipoRetirada, setTipoRetirada] = useState<'proprio' | 'terceiro'>('proprio');
  const [isDrive, setIsDrive] = useState(false); // Drive-thru: cliente aguarda no carro

  // Endereço: salvo (do perfil) ou outro
  const enderecoSalvo = user?.cidade
    ? `${user?.endereco ?? ''}${user?.numero ? ', ' + user.numero : ''} - ${user?.bairro ?? ''} - ${user?.cidade}/${user?.estado ?? ''}`
    : null;
  const [usarEnderecoSalvo, setUsarEnderecoSalvo] = useState(true);

  // Modal endereço outro
  const [modalEnderecoAberto, setModalEnderecoAberto] = useState(false);
  const [cep, setCep] = useState(user?.cep ?? '');
  const [rua, setRua] = useState(user?.endereco ?? '');
  const [numero, setNumero] = useState(user?.numero ?? '');
  const [complemento, setComplemento] = useState('');
  const [bairro, setBairro] = useState(user?.bairro ?? '');
  const [cidade, setCidade] = useState(user?.cidade ?? '');
  const [estado, setEstado] = useState(user?.estado ?? '');
  const [buscandoCep, setBuscandoCep] = useState(false);

  useEffect(() => {
    carregar();
  }, []);

  async function buscarCep(value: string) {
    const numeros = value.replace(/\D/g, '');
    // Formatar como 00000-000
    if (numeros.length <= 5) {
      setCep(numeros);
    } else {
      setCep(numeros.slice(0, 5) + '-' + numeros.slice(5, 8));
    }
    if (numeros.length === 8) {
      setBuscandoCep(true);
      try {
        const resp = await fetch(`https://viacep.com.br/ws/${numeros}/json/`);
        const data = await resp.json();
        if (!data.erro) {
          setRua(data.logradouro ?? '');
          setBairro(data.bairro ?? '');
          setCidade(data.localidade ?? '');
          setEstado(data.uf ?? '');
        }
      } catch {
        // ignora erro silenciosamente
      } finally {
        setBuscandoCep(false);
      }
    }
  }

  function getEnderecoEntrega(): string {
    if (usarEnderecoSalvo && enderecoSalvo) {
      return enderecoSalvo;
    }
    return `${rua}, ${numero}${complemento ? ' ' + complemento : ''} - ${bairro} - ${cidade}/${estado} - CEP: ${cep}`;
  }

  async function handleFinalizar() {
    if (itens.length === 0) {
      Alert.alert('Carrinho vazio', 'Adicione produtos antes de finalizar.');
      return;
    }

    if (modo === 'entrega') {
      if (!usarEnderecoSalvo && (!rua.trim() || !cidade.trim())) {
        Alert.alert('Endereço incompleto', 'Preencha pelo menos a rua e a cidade para entrega.');
        return;
      }
      if (usarEnderecoSalvo && !enderecoSalvo) {
        Alert.alert('Sem endereço', 'Nenhum endereço salvo no perfil. Preencha o endereço de entrega.');
        setUsarEnderecoSalvo(false);
        return;
      }
    }

    if (!pagamentoTipo) {
      Alert.alert('Forma de pagamento', 'Escolha PIX, debito ou credito para continuar.');
      return;
    }

    const enderecoFormatado = modo === 'entrega' ? getEnderecoEntrega() : undefined;
    const modoLabel = modo === 'retirada'
      ? tipoRetirada === 'terceiro'
        ? 'Retirada por terceiro (senha será gerada)'
        : (isDrive ? 'Drive-thru (aguardar no carro)' : 'Retirada na loja por mim')
      : `Entrega em: ${enderecoFormatado}`;

    function buildPagLabel(): string {
      if (pagamentoTipo === 'pix') return 'PIX';
      if (pagamentoTipo === 'debito') return `Débito ${pagamentoBandeira}`;
      if (pagamentoTipo === 'credito') return `Crédito ${pagamentoBandeira} ${pagamentoParcelas}x`;
      return '';
    }
    const pagLabel = pagamentoTipo ? `\n💳 Pagamento: ${buildPagLabel()}` : '';

    Alert.alert(
      'Ir para pagamento',
      `Total: ${formatarMoeda(subtotal)}\n\n${modoLabel}${pagLabel}\n\nO carrinho ainda nao e pedido. O pedido so sera liberado apos aprovacao do pagamento online.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Continuar',
          onPress: async () => {
            setFinalizando(true);
            try {
              const pedido = await finalizarCheckoutAppLoja({
                cidade: user?.cidade || 'loja',
                modo,
                tipoRetirada,
                isDrive: isDrive && modo === 'retirada' && tipoRetirada === 'proprio',
                endereco: enderecoFormatado,
                formaPagamentoNome: buildPagLabel() || undefined,
              });
              // Limpar o carrinho após o pedido ser feito com sucesso
              await limpar();
              navigation.navigate('CheckoutSucesso', { pedido });
            } catch (err: any) {
              Alert.alert(
                'Erro ao finalizar',
                err?.response?.data?.detail || 'Tente novamente.'
              );
            } finally {
              setFinalizando(false);
            }
          },
        },
      ]
    );
  }

  function renderItem({ item }: { item: any }) {
    return (
      <View style={styles.item}>
        {item.foto_url ? (
          <Image source={{ uri: item.foto_url }} style={styles.itemFoto} resizeMode="cover" />
        ) : (
          <View style={[styles.itemFoto, styles.itemFotoPlaceholder]}>
            <Text style={{ fontSize: 22 }}>🛍️</Text>
          </View>
        )}
        <View style={styles.itemInfo}>
          <Text style={styles.itemNome} numberOfLines={2}>{item.nome}</Text>
          <Text style={styles.itemPreco}>{formatarMoeda(item.preco_unitario)} / un</Text>
        </View>
        <View style={styles.itemControles}>
          <TouchableOpacity
            style={styles.controleBtn}
            onPress={async () => {
              try {
                if (item.quantidade <= 1) {
                  await remover(item.produto_id);
                } else {
                  await atualizar(item.produto_id, item.quantidade - 1);
                }
              } catch {
                Alert.alert('Erro', 'Não foi possível atualizar o item.');
              }
            }}
          >
            <Ionicons name={item.quantidade <= 1 ? 'trash-outline' : 'remove'} size={18} color={item.quantidade <= 1 ? CORES.erro : CORES.texto} />
          </TouchableOpacity>
          <Text style={styles.qtd}>{item.quantidade}</Text>
          <TouchableOpacity
            style={styles.controleBtn}
            onPress={async () => {
              try {
                await atualizar(item.produto_id, item.quantidade + 1);
              } catch {
                Alert.alert('Erro', 'Não foi possível atualizar o item.');
              }
            }}
          >
            <Ionicons name="add" size={18} color={CORES.texto} />
          </TouchableOpacity>
        </View>
        <Text style={styles.itemSubtotal}>{formatarMoeda(item.subtotal)}</Text>
      </View>
    );
  }

  if (itens.length === 0) {
    return (
      <View style={styles.vazio}>
        <Text style={styles.vazioEmoji}>🛒</Text>
        <Text style={styles.vazioTitulo}>Carrinho vazio</Text>
        <Text style={styles.vazioTexto}>
          Adicione produtos pelo catálogo ou escanear o código de barras.
        </Text>
        <TouchableOpacity
          style={styles.botaoScanner}
          onPress={() => navigation.navigate('BarcodeScanner')}
        >
          <Ionicons name="barcode-outline" size={20} color="#fff" />
          <Text style={styles.botaoScannerTexto}>Escanear produto</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.botaoCatalogo}
          onPress={() => navigation.navigate('Catalogo')}
        >
          <Text style={styles.botaoCatalogoTexto}>Ver catálogo</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <FlatList
        style={{ flex: 1 }}
        data={itens}
        keyExtractor={(item) => String(item.produto_id)}
        renderItem={renderItem}
        contentContainerStyle={styles.lista}
        keyboardShouldPersistTaps="handled"
        ListHeaderComponent={
          <TouchableOpacity
            style={styles.btnLimpar}
            onPress={() =>
              Alert.alert('Limpar carrinho', 'Deseja remover todos os produtos?', [
                { text: 'Cancelar', style: 'cancel' },
                { text: 'Limpar', style: 'destructive', onPress: async () => { try { await limpar(); } catch { Alert.alert('Erro', 'Não foi possível limpar o carrinho.'); } } },
              ])
            }
          >
            <Text style={styles.btnLimparTexto}>Limpar carrinho</Text>
          </TouchableOpacity>
        }
        ListFooterComponent={
          <View style={styles.opcaoEntrega}>
            <Text style={styles.secaoTitulo}>Forma de recebimento</Text>

            {/* Seleção retirada / entrega */}
            <View style={styles.modoRow}>
              <TouchableOpacity
                style={[styles.modoBotao, modo === 'retirada' && styles.modoBotaoAtivo]}
                onPress={() => setModo('retirada')}
              >
                <Ionicons name="storefront-outline" size={18} color={modo === 'retirada' ? '#fff' : CORES.texto} />
                <Text style={[styles.modoTexto, modo === 'retirada' && styles.modoTextoAtivo]}>
                  Retirar na loja
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modoBotao, modo === 'entrega' && styles.modoBotaoAtivo]}
                onPress={() => setModo('entrega')}
              >
                <Ionicons name="bicycle-outline" size={18} color={modo === 'entrega' ? '#fff' : CORES.texto} />
                <Text style={[styles.modoTexto, modo === 'entrega' && styles.modoTextoAtivo]}>
                  Entrega
                </Text>
              </TouchableOpacity>
            </View>

            {/* Quem vai retirar (só para retirada) */}
            {modo === 'retirada' && (
              <View style={styles.subSecao}>
                <Text style={styles.subSecaoTitulo}>Quem vai retirar?</Text>
                <TouchableOpacity
                  style={[styles.opcaoBotao, tipoRetirada === 'proprio' && styles.opcaoBotaoAtivo]}
                  onPress={() => setTipoRetirada('proprio')}
                >
                  <Text style={[styles.opcaoTexto, tipoRetirada === 'proprio' && styles.opcaoTextoAtivo]}>
                    🙋 Eu mesmo(a) vou retirar
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.opcaoBotao, tipoRetirada === 'terceiro' && styles.opcaoBotaoAtivo]}
                  onPress={() => setTipoRetirada('terceiro')}
                >
                  <Text style={[styles.opcaoTexto, tipoRetirada === 'terceiro' && styles.opcaoTextoAtivo]}>
                    👥 Outra pessoa vai retirar por mim
                  </Text>
                </TouchableOpacity>
                {tipoRetirada === 'terceiro' && (
                  <View style={styles.aviso}>
                    <Text style={styles.avisoTexto}>
                      🔑 Uma senha secreta será gerada após confirmar. Compartilhe com a pessoa que irá retirar.
                    </Text>
                  </View>
                )}
                {/* Drive-thru: apenas quando o próprio cliente vai retirar */}
                {tipoRetirada === 'proprio' && (
                  <TouchableOpacity
                    style={[styles.opcaoBotao, isDrive && styles.opcaoBotaoAtivo]}
                    onPress={() => setIsDrive(prev => !prev)}
                  >
                    <Text style={[styles.opcaoTexto, isDrive && styles.opcaoTextoAtivo]}>
                      🚗 {isDrive ? '✅ Vou aguardar no carro (Drive-thru)' : 'Vou aguardar no carro (Drive-thru)'}
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
            )}

            {/* Endereço (só para entrega) */}
            {modo === 'entrega' && (
              <View style={styles.subSecao}>
                <Text style={styles.subSecaoTitulo}>Endereço de entrega</Text>

                {enderecoSalvo ? (
                  <>
                    {/* Opção 1: Usar endereço salvo */}
                    <TouchableOpacity
                      style={[styles.opcaoBotao, usarEnderecoSalvo && styles.opcaoBotaoAtivo]}
                      onPress={() => setUsarEnderecoSalvo(true)}
                    >
                      <Text style={[styles.opcaoTexto, usarEnderecoSalvo && styles.opcaoTextoAtivo]}>
                        🏠 Entregar no meu endereço cadastrado
                      </Text>
                      {usarEnderecoSalvo && (
                        <Text style={styles.enderecoSalvoTexto}>{enderecoSalvo}</Text>
                      )}
                    </TouchableOpacity>

                    {/* Opção 2: Outro endereço */}
                    <TouchableOpacity
                      style={[styles.opcaoBotao, !usarEnderecoSalvo && styles.opcaoBotaoAtivo]}
                      onPress={() => { setUsarEnderecoSalvo(false); setModalEnderecoAberto(true); }}
                    >
                      <Text style={[styles.opcaoTexto, !usarEnderecoSalvo && styles.opcaoTextoAtivo]}>
                        📍 Entregar em outro endereço
                      </Text>
                      {!usarEnderecoSalvo && rua ? (
                        <Text style={styles.enderecoSalvoTexto}>{getEnderecoEntrega()}</Text>
                      ) : null}
                    </TouchableOpacity>

                    {/* Botão editar caso outro endereço já selecionado */}
                    {!usarEnderecoSalvo && (
                      <TouchableOpacity
                        style={styles.btnEditar}
                        onPress={() => setModalEnderecoAberto(true)}
                      >
                        <Ionicons name="pencil-outline" size={14} color={CORES.primario} />
                        <Text style={styles.btnEditarTexto}>Editar endereço</Text>
                      </TouchableOpacity>
                    )}
                  </>
                ) : (
                  /* Sem endereço salvo: Abrir modal direto */
                  <TouchableOpacity
                    style={styles.opcaoBotao}
                    onPress={() => setModalEnderecoAberto(true)}
                  >
                    <Ionicons name="add-circle-outline" size={18} color={CORES.primario} />
                    <Text style={[styles.opcaoTexto, { color: CORES.primario }]}>
                      {rua ? getEnderecoEntrega() : 'Preencher endereço de entrega'}
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
            )}

            {/* Forma de pagamento */}
            <View style={styles.subSecao}>
              <Text style={styles.subSecaoTitulo}>💳 Forma de pagamento</Text>
              <Text style={styles.pagamentoAviso}>
                O carrinho ainda nao e pedido. O pedido so sera liberado apos aprovacao do pagamento online.
              </Text>
              <View style={styles.modoRow}>
                {(['pix', 'debito', 'credito'] as const).map((tipo) => (
                  <TouchableOpacity
                    key={tipo}
                    style={[styles.pagBotao, pagamentoTipo === tipo && styles.pagBotaoAtivo]}
                    onPress={() => setPagamentoTipo(tipo)}
                  >
                    <Text style={styles.pagBotaoIcon}>
                      {tipo === 'pix' ? '📱' : '💳'}
                    </Text>
                    <Text style={[styles.pagBotaoTexto, pagamentoTipo === tipo && styles.pagBotaoTextoAtivo]}>
                      {tipo === 'pix' ? 'PIX' : tipo === 'debito' ? 'Débito' : 'Crédito'}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
              {(pagamentoTipo === 'debito' || pagamentoTipo === 'credito') && (
                <View style={{ marginTop: 8 }}>
                  <Text style={styles.pagLabel}>Bandeira</Text>
                  <View style={styles.modoRow}>
                    {['Visa', 'Mastercard', 'Elo', 'Outra'].map((b) => (
                      <TouchableOpacity
                        key={b}
                        style={[styles.bandeiraBotao, pagamentoBandeira === b && styles.bandeiraBotaoAtivo]}
                        onPress={() => setPagamentoBandeira(b)}
                      >
                        <Text style={[styles.bandeiraTexto, pagamentoBandeira === b && styles.bandeiraTextoAtivo]}>{b}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              )}

              {pagamentoTipo === 'credito' && (
                <View style={{ marginTop: 8 }}>
                  <Text style={styles.pagLabel}>Parcelas</Text>
                  <View style={styles.modoRow}>
                    {[1, 2, 3].map((p) => (
                      <TouchableOpacity
                        key={p}
                        style={[styles.bandeiraBotao, pagamentoParcelas === p && styles.bandeiraBotaoAtivo]}
                        onPress={() => setPagamentoParcelas(p)}
                      >
                        <Text style={[styles.bandeiraTexto, pagamentoParcelas === p && styles.bandeiraTextoAtivo]}>{p}x</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              )}
            </View>
          </View>
        }
      />

      {/* Resumo e finalizar */}
      <View style={styles.rodape}>
        <View style={styles.resumo}>
          <Text style={styles.resumoLabel}>Total</Text>
          <Text style={styles.resumoTotal}>{formatarMoeda(subtotal)}</Text>
        </View>

        <TouchableOpacity
          style={[styles.botaoFinalizar, finalizando && styles.botaoDesativado]}
          onPress={handleFinalizar}
          disabled={finalizando}
        >
          {finalizando ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name="checkmark-circle" size={20} color="#fff" />
              <Text style={styles.botaoFinalizarTexto}>Ir para pagamento</Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      {/* Modal de endereço */}
      <Modal
        visible={modalEnderecoAberto}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setModalEnderecoAberto(false)}
      >
        <KeyboardAvoidingView
          style={{ flex: 1, backgroundColor: CORES.fundo }}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitulo}>Endereço de entrega</Text>
            <TouchableOpacity onPress={() => setModalEnderecoAberto(false)}>
              <Ionicons name="close" size={24} color={CORES.texto} />
            </TouchableOpacity>
          </View>

          <RNScrollView contentContainerStyle={styles.modalConteudo} keyboardShouldPersistTaps="handled">
            {/* CEP com busca automática */}
            <Text style={styles.modalLabel}>CEP</Text>
            <View style={styles.cepRow}>
              <TextInput
                style={[styles.modalInput, { flex: 1 }]}
                placeholder="00000-000"
                placeholderTextColor={CORES.textoClaro}
                keyboardType="numeric"
                value={cep}
                onChangeText={buscarCep}
                maxLength={9}
              />
              {buscandoCep && (
                <ActivityIndicator size="small" color={CORES.primario} style={{ marginLeft: 8 }} />
              )}
            </View>

            <Text style={styles.modalLabel}>Rua / Avenida *</Text>
            <TextInput style={styles.modalInput} placeholder="Ex: Rua das Flores" placeholderTextColor={CORES.textoClaro} value={rua} onChangeText={setRua} />

            <View style={styles.modalRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.modalLabel}>Número</Text>
                <TextInput style={styles.modalInput} placeholder="123" placeholderTextColor={CORES.textoClaro} keyboardType="numeric" value={numero} onChangeText={setNumero} />
              </View>
              <View style={{ flex: 2, marginLeft: ESPACO.sm }}>
                <Text style={styles.modalLabel}>Complemento</Text>
                <TextInput style={styles.modalInput} placeholder="Apto 42" placeholderTextColor={CORES.textoClaro} value={complemento} onChangeText={setComplemento} />
              </View>
            </View>

            <Text style={styles.modalLabel}>Bairro</Text>
            <TextInput style={styles.modalInput} placeholder="Bairro" placeholderTextColor={CORES.textoClaro} value={bairro} onChangeText={setBairro} />

            <View style={styles.modalRow}>
              <View style={{ flex: 2 }}>
                <Text style={styles.modalLabel}>Cidade *</Text>
                <TextInput style={styles.modalInput} placeholder="São Paulo" placeholderTextColor={CORES.textoClaro} value={cidade} onChangeText={setCidade} />
              </View>
              <View style={{ flex: 1, marginLeft: ESPACO.sm }}>
                <Text style={styles.modalLabel}>UF</Text>
                <TextInput style={styles.modalInput} placeholder="SP" placeholderTextColor={CORES.textoClaro} autoCapitalize="characters" maxLength={2} value={estado} onChangeText={setEstado} />
              </View>
            </View>

            <TouchableOpacity
              style={styles.modalBotao}
              onPress={() => {
                if (!rua.trim() || !cidade.trim()) {
                  Alert.alert('Campos obrigatórios', 'Preencha pelo menos a rua e a cidade.');
                  return;
                }
                setUsarEnderecoSalvo(false);
                setModalEnderecoAberto(false);
              }}
            >
              <Text style={styles.modalBotaoTexto}>Usar este endereço</Text>
            </TouchableOpacity>
          </RNScrollView>
        </KeyboardAvoidingView>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  lista: { padding: ESPACO.md, paddingBottom: 0 },
  item: {
    flexDirection: 'row',
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.sm,
    marginBottom: ESPACO.sm,
    alignItems: 'center',
    gap: ESPACO.sm,
    ...SOMBRA,
  },
  itemFoto: { width: 55, height: 55, borderRadius: RAIO.sm },
  itemFotoPlaceholder: {
    backgroundColor: CORES.primarioClaro,
    justifyContent: 'center',
    alignItems: 'center',
  },
  itemInfo: { flex: 1 },
  itemNome: { fontSize: FONTE.normal, fontWeight: '500', color: CORES.texto },
  itemPreco: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  itemControles: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.xs,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: 6,
  },
  controleBtn: { padding: 6 },
  qtd: { fontSize: FONTE.normal, fontWeight: 'bold', color: CORES.texto, minWidth: 20, textAlign: 'center' },
  itemSubtotal: { fontSize: FONTE.normal, fontWeight: 'bold', color: CORES.primario, minWidth: 60, textAlign: 'right' },

  // Seção de entrega/retirada
  opcaoEntrega: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginTop: ESPACO.sm,
    marginBottom: ESPACO.md,
    ...SOMBRA,
  },
  secaoTitulo: { fontSize: FONTE.normal, fontWeight: '700', color: CORES.texto, marginBottom: ESPACO.sm },
  modoRow: { flexDirection: 'row', gap: ESPACO.sm, marginBottom: ESPACO.sm },
  modoBotao: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: ESPACO.xs,
    paddingVertical: ESPACO.sm + 2,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    backgroundColor: CORES.fundo,
  },
  modoBotaoAtivo: { backgroundColor: CORES.primario, borderColor: CORES.primario },
  modoTexto: { fontSize: FONTE.pequena, fontWeight: '600', color: CORES.texto },
  modoTextoAtivo: { color: '#fff' },
  subSecao: { marginTop: ESPACO.sm },
  subSecaoTitulo: { fontSize: FONTE.pequena, fontWeight: '600', color: CORES.textoSecundario, marginBottom: ESPACO.xs },
  opcaoBotao: {
    paddingVertical: ESPACO.sm,
    paddingHorizontal: ESPACO.md,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    marginBottom: ESPACO.xs,
  },
  opcaoBotaoAtivo: { borderColor: CORES.primario, backgroundColor: CORES.primarioClaro },
  opcaoTexto: { fontSize: FONTE.normal, color: CORES.texto },
  opcaoTextoAtivo: { color: CORES.primario, fontWeight: '600' },
  aviso: {
    backgroundColor: '#FFF7ED',
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
    borderWidth: 1,
    borderColor: '#FED7AA',
    marginTop: ESPACO.xs,
  },
  avisoTexto: { fontSize: FONTE.pequena, color: '#92400E' },
  campo: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.xs + 4,
    fontSize: FONTE.normal,
    color: CORES.texto,
    backgroundColor: CORES.fundo,
    marginBottom: ESPACO.xs,
  },
  campoRow: { flexDirection: 'row', gap: ESPACO.xs },
  enderecoSalvoTexto: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
    marginTop: 4,
  },
  btnEditar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: ESPACO.xs,
    alignSelf: 'flex-end',
  },
  btnEditarTexto: { fontSize: FONTE.pequena, color: CORES.primario },

  // Modal endereço
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: ESPACO.lg,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
    backgroundColor: CORES.superficie,
  },
  modalTitulo: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto },
  modalConteudo: { padding: ESPACO.lg },
  modalLabel: { fontSize: FONTE.pequena, fontWeight: '600', color: CORES.textoSecundario, marginBottom: 4 },
  modalInput: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm + 2,
    fontSize: FONTE.normal,
    color: CORES.texto,
    backgroundColor: CORES.fundo,
    marginBottom: ESPACO.md,
  },
  modalRow: { flexDirection: 'row', marginBottom: 0 },
  cepRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 0 },
  modalBotao: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.md,
    alignItems: 'center',
    marginTop: ESPACO.lg,
  },
  modalBotaoTexto: { color: '#fff', fontSize: FONTE.media, fontWeight: 'bold' },

  // Rodapé
  rodape: {
    backgroundColor: CORES.superficie,
    padding: ESPACO.lg,
    borderTopWidth: 1,
    borderTopColor: CORES.borda,
    ...SOMBRA,
  },
  resumo: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: ESPACO.md },
  resumoLabel: { fontSize: FONTE.media, color: CORES.textoSecundario },
  resumoTotal: { fontSize: FONTE.titulo, fontWeight: 'bold', color: CORES.texto },
  botaoFinalizar: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.md,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: ESPACO.sm,
  },
  botaoDesativado: { opacity: 0.7 },
  botaoFinalizarTexto: { color: '#fff', fontSize: FONTE.media, fontWeight: 'bold' },
  btnLimpar: { alignSelf: 'flex-end', marginBottom: ESPACO.sm },
  btnLimparTexto: { color: CORES.erro, fontSize: FONTE.pequena },
  vazio: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: ESPACO.xl },
  vazioEmoji: { fontSize: 60, marginBottom: ESPACO.md },
  vazioTitulo: { fontSize: FONTE.titulo, fontWeight: 'bold', color: CORES.texto, marginBottom: ESPACO.sm },
  vazioTexto: { fontSize: FONTE.normal, color: CORES.textoSecundario, textAlign: 'center', marginBottom: ESPACO.xl },
  botaoScanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.xl,
    paddingVertical: ESPACO.md,
    gap: ESPACO.sm,
    marginBottom: ESPACO.sm,
  },
  botaoScannerTexto: { color: '#fff', fontWeight: 'bold', fontSize: FONTE.normal },
  botaoCatalogo: { padding: ESPACO.sm },
  botaoCatalogoTexto: { color: CORES.primario, fontSize: FONTE.normal },

  // Pagamento simplificado
  pagamentoAviso: {
    fontSize: FONTE.pequena,
    color: '#92400E',
    backgroundColor: '#FFF7ED',
    borderColor: '#FED7AA',
    borderWidth: 1,
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
    marginBottom: ESPACO.sm,
  },
  pagBotao: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: ESPACO.sm + 2,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    backgroundColor: CORES.fundo,
  },
  pagBotaoAtivo: { backgroundColor: CORES.primario, borderColor: CORES.primario },
  pagBotaoIcon: { fontSize: 18, marginBottom: 2 },
  pagBotaoTexto: { fontSize: FONTE.pequena, fontWeight: '600', color: CORES.texto },
  pagBotaoTextoAtivo: { color: '#fff' },
  pagLabel: { fontSize: FONTE.pequena, fontWeight: '600', color: CORES.textoSecundario, marginBottom: 4 },
  bandeiraBotao: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: ESPACO.xs + 4,
    borderRadius: RAIO.sm,
    borderWidth: 1,
    borderColor: CORES.borda,
    backgroundColor: CORES.fundo,
  },
  bandeiraBotaoAtivo: { backgroundColor: CORES.primarioClaro, borderColor: CORES.primario },
  bandeiraTexto: { fontSize: FONTE.pequena, color: CORES.texto },
  bandeiraTextoAtivo: { color: CORES.primario, fontWeight: '700' },
});
