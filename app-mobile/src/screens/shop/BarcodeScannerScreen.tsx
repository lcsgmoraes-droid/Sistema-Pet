import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Vibration,
  ActivityIndicator,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useIsFocused } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { buscarProdutoPorBarcode } from '../../services/shop.service';
import { useCartStore } from '../../store/cart.store';
import { Produto } from '../../types';
import { CORES, ESPACO, FONTE, RAIO } from '../../theme';
import { formatarMoeda } from '../../utils/format';

export default function BarcodeScannerScreen({ navigation }: any) {
  const isFocused = useIsFocused();
  const [permission, requestPermission] = useCameraPermissions();
  const [scanAtivo, setScanAtivo] = useState(true);
  const [buscando, setBuscando] = useState(false);
  const [produtoEncontrado, setProdutoEncontrado] = useState<Produto | null>(null);
  const ultimoScan = useRef<string>('');
  const { adicionar } = useCartStore();

  useEffect(() => {
    if (!permission?.granted) {
      requestPermission();
    }
  }, []);

  async function onBarcodeScanned({ data }: { data: string }) {
    if (!scanAtivo || buscando || data === ultimoScan.current) return;

    ultimoScan.current = data;
    setScanAtivo(false);
    setBuscando(true);
    Vibration.vibrate(100);

    try {
      const produto = await buscarProdutoPorBarcode(data);
      if (produto) {
        setProdutoEncontrado(produto);
      } else {
        Alert.alert(
          'Produto não encontrado',
          `Código ${data} não está no nosso catálogo.`,
          [
            {
              text: 'Escanear outro',
              onPress: () => {
                ultimoScan.current = '';
                setScanAtivo(true);
              },
            },
          ]
        );
      }
    } catch {
      Alert.alert('Erro', 'Não foi possível buscar o produto.', [
        { text: 'Tentar novamente', onPress: () => { ultimoScan.current = ''; setScanAtivo(true); } },
      ]);
    } finally {
      setBuscando(false);
    }
  }

  async function adicionarAoCarrinho() {
    if (!produtoEncontrado) return;
    try {
      await adicionar(produtoEncontrado, 1);
      Alert.alert(
        '✅ Adicionado!',
        `${produtoEncontrado.nome} foi ao carrinho.`,
        [
          { text: 'Escanear mais', onPress: () => { setProdutoEncontrado(null); ultimoScan.current = ''; setScanAtivo(true); } },
          { text: 'Ver carrinho', onPress: () => navigation.navigate('Carrinho') },
        ]
      );
    } catch {
      Alert.alert('Erro', 'Não foi possível adicionar ao carrinho.');
    }
  }

  if (!permission) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator size="large" color={CORES.primario} />
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.semPermissao}>
        <Text style={styles.semPermissaoEmoji}>📷</Text>
        <Text style={styles.semPermissaoTitulo}>Precisamos da câmera</Text>
        <Text style={styles.semPermissaoTexto}>
          Para escanear códigos de barras dos produtos, precisamos de permissão para usar a câmera.
        </Text>
        <TouchableOpacity style={styles.botaoPermissao} onPress={requestPermission}>
          <Text style={styles.botaoPermissaoTexto}>Permitir câmera</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.linkVoltar}>Voltar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!isFocused) {
    return <View style={styles.container} />;
  }

  return (
    <View style={styles.container}>
      <CameraView
        style={styles.camera}
        facing="back"
        onBarcodeScanned={scanAtivo ? onBarcodeScanned : undefined}
        barcodeScannerSettings={{
          barcodeTypes: [
            'ean13', 'ean8', 'upc_a', 'upc_e',
            'code128', 'code39', 'qr',
          ],
        }}
      >
        {/* Overlay */}
        <View style={styles.overlay}>
          {/* Botão fechar */}
          <TouchableOpacity style={styles.fechar} onPress={() => navigation.goBack()}>
            <Ionicons name="close" size={28} color="#fff" />
          </TouchableOpacity>

          {/* Área de scan */}
          <View style={styles.areaCenter}>
            <View style={styles.frameScan}>
              {/* Cantos do frame */}
              <View style={[styles.canto, styles.cantoTopLeft]} />
              <View style={[styles.canto, styles.cantoTopRight]} />
              <View style={[styles.canto, styles.cantoBottomLeft]} />
              <View style={[styles.canto, styles.cantoBottomRight]} />
            </View>
            <Text style={styles.instrucao}>
              {buscando
                ? 'Buscando produto...'
                : 'Aponte para o código de barras do produto'}
            </Text>
          </View>

          {/* Loading */}
          {buscando && (
            <View style={styles.loadingOverlay}>
              <ActivityIndicator size="large" color="#fff" />
            </View>
          )}
        </View>
      </CameraView>

      {/* Card do produto encontrado */}
      {produtoEncontrado && (
        <View style={styles.produtoCard}>
          <View style={styles.produtoInfo}>
            <Text style={styles.produtoNome} numberOfLines={2}>{produtoEncontrado.nome}</Text>
            <Text style={styles.produtoPreco}>
              {formatarMoeda(
                produtoEncontrado.promocao_ativa && produtoEncontrado.preco_promocional
                  ? produtoEncontrado.preco_promocional
                  : produtoEncontrado.preco
              )}
            </Text>
          </View>
          <View style={styles.produtoAcoes}>
            <TouchableOpacity
              style={styles.botaoEscanear}
              onPress={() => {
                setProdutoEncontrado(null);
                ultimoScan.current = '';
                setScanAtivo(true);
              }}
            >
              <Ionicons name="scan-outline" size={18} color={CORES.primario} />
            </TouchableOpacity>
            <TouchableOpacity style={styles.botaoAdicionar} onPress={adicionarAoCarrinho}>
              <Ionicons name="cart" size={18} color="#fff" />
              <Text style={styles.botaoAdicionarTexto}>Adicionar</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  camera: { flex: 1 },
  overlay: { flex: 1 },
  fechar: {
    position: 'absolute',
    top: 50,
    right: 20,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 20,
    padding: 8,
    zIndex: 10,
  },
  areaCenter: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  frameScan: {
    width: 260,
    height: 180,
    position: 'relative',
    marginBottom: 20,
  },
  canto: {
    position: 'absolute',
    width: 30,
    height: 30,
    borderColor: '#fff',
    borderWidth: 3,
  },
  cantoTopLeft: { top: 0, left: 0, borderRightWidth: 0, borderBottomWidth: 0 },
  cantoTopRight: { top: 0, right: 0, borderLeftWidth: 0, borderBottomWidth: 0 },
  cantoBottomLeft: { bottom: 0, left: 0, borderRightWidth: 0, borderTopWidth: 0 },
  cantoBottomRight: { bottom: 0, right: 0, borderLeftWidth: 0, borderTopWidth: 0 },
  instrucao: {
    color: '#fff',
    fontSize: FONTE.normal,
    textAlign: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: RAIO.circulo,
  },
  loadingOverlay: {
    position: 'absolute',
    inset: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  produtoCard: {
    backgroundColor: CORES.superficie,
    padding: ESPACO.lg,
    flexDirection: 'row',
    alignItems: 'center',
    borderTopLeftRadius: RAIO.lg,
    borderTopRightRadius: RAIO.lg,
    gap: ESPACO.md,
  },
  produtoInfo: { flex: 1 },
  produtoNome: { fontSize: FONTE.normal, fontWeight: '600', color: CORES.texto },
  produtoPreco: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.primario, marginTop: 4 },
  produtoAcoes: { flexDirection: 'row', gap: ESPACO.sm, alignItems: 'center' },
  botaoEscanear: {
    width: 42,
    height: 42,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.primario,
    justifyContent: 'center',
    alignItems: 'center',
  },
  botaoAdicionar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm + 4,
    gap: 6,
  },
  botaoAdicionarTexto: { color: '#fff', fontWeight: 'bold', fontSize: FONTE.normal },
  // Sem permissão
  semPermissao: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: ESPACO.xl,
    backgroundColor: CORES.fundo,
  },
  semPermissaoEmoji: { fontSize: 60, marginBottom: ESPACO.md },
  semPermissaoTitulo: { fontSize: FONTE.titulo, fontWeight: 'bold', color: CORES.texto, marginBottom: ESPACO.sm },
  semPermissaoTexto: { fontSize: FONTE.normal, color: CORES.textoSecundario, textAlign: 'center', marginBottom: ESPACO.xl },
  botaoPermissao: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.xl,
    paddingVertical: ESPACO.md,
    marginBottom: ESPACO.md,
  },
  botaoPermissaoTexto: { color: '#fff', fontSize: FONTE.media, fontWeight: 'bold' },
  linkVoltar: { color: CORES.primario, fontSize: FONTE.normal },
});
