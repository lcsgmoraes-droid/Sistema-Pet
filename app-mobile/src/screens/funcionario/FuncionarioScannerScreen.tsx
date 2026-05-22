import { Ionicons } from "@expo/vector-icons";
import { useIsFocused } from "@react-navigation/native";
import { CameraView, useCameraPermissions } from "expo-camera";
import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  Vibration,
  View,
} from "react-native";
import { buscarProdutoPorBarcodeFuncionario } from "../../services/funcionario.service";
import { useFuncionarioPdvStore } from "../../store/funcionarioPdv.store";
import { CORES, ESPACO, FONTE, RAIO } from "../../theme";
import { Produto } from "../../types";
import { formatarMoeda } from "../../utils/format";

function mensagemErroApi(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return fallback;
}

function formatarMoedaScanner(valor: number | null | undefined) {
  return formatarMoeda(valor).replace(/\s+/g, "\u00A0");
}

export default function FuncionarioScannerScreen({ navigation }: any) {
  const isFocused = useIsFocused();
  const [permission, requestPermission] = useCameraPermissions();
  const [scanAtivo, setScanAtivo] = useState(true);
  const [buscando, setBuscando] = useState(false);
  const [produtoEncontrado, setProdutoEncontrado] = useState<Produto | null>(null);
  const ultimoScan = useRef("");
  const { adicionarProduto } = useFuncionarioPdvStore();
  const produtoSemEstoque = !!produtoEncontrado && Number(produtoEncontrado.estoque ?? 0) <= 0;

  useEffect(() => {
    if (!permission?.granted) {
      requestPermission();
    }
  }, [permission?.granted, requestPermission]);

  async function onBarcodeScanned({ data }: { data: string }) {
    if (!scanAtivo || buscando || data === ultimoScan.current) return;

    ultimoScan.current = data;
    setScanAtivo(false);
    setBuscando(true);
    Vibration.vibrate(100);

    try {
      const produto = await buscarProdutoPorBarcodeFuncionario(data);
      if (produto) {
        setProdutoEncontrado(produto);
      } else {
        Alert.alert("Produto nao encontrado", `Codigo ${data} nao foi localizado.`, [
          {
            text: "Escanear outro",
            onPress: () => {
              ultimoScan.current = "";
              setScanAtivo(true);
            },
          },
        ]);
      }
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar o produto."), [
        { text: "Tentar novamente", onPress: () => { ultimoScan.current = ""; setScanAtivo(true); } },
      ]);
    } finally {
      setBuscando(false);
    }
  }

  function adicionarAoCarrinho() {
    if (!produtoEncontrado) return;
    if (Number(produtoEncontrado.estoque ?? 0) <= 0) {
      Alert.alert("Sem estoque", "Este produto esta sem estoque disponivel.");
      return;
    }
    try {
      adicionarProduto(produtoEncontrado, 1);
      Alert.alert("Adicionado", `${produtoEncontrado.nome} foi ao carrinho PDV.`, [
        { text: "Escanear mais", onPress: () => { setProdutoEncontrado(null); ultimoScan.current = ""; setScanAtivo(true); } },
        { text: "Ver carrinho", onPress: () => navigation.navigate("FuncionarioCarrinho") },
      ]);
    } catch (error: any) {
      Alert.alert("Estoque", error?.message || "Nao foi possivel adicionar ao carrinho.");
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
        <Ionicons name="camera-outline" size={56} color={CORES.primario} />
        <Text style={styles.semPermissaoTitulo}>Permitir camera</Text>
        <Text style={styles.semPermissaoTexto}>A camera e necessaria para ler codigo de barras.</Text>
        <TouchableOpacity style={styles.botaoPermissao} onPress={requestPermission}>
          <Text style={styles.botaoPermissaoTexto}>Permitir</Text>
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
          barcodeTypes: ["ean13", "ean8", "upc_a", "upc_e", "code128", "code39", "qr"],
        }}
      >
        <View style={styles.overlay}>
          <TouchableOpacity style={styles.fechar} onPress={() => navigation.goBack()}>
            <Ionicons name="close" size={28} color="#fff" />
          </TouchableOpacity>

          <View style={styles.areaCenter}>
            <View style={styles.frameScan}>
              <View style={[styles.canto, styles.cantoTopLeft]} />
              <View style={[styles.canto, styles.cantoTopRight]} />
              <View style={[styles.canto, styles.cantoBottomLeft]} />
              <View style={[styles.canto, styles.cantoBottomRight]} />
            </View>
            <Text style={styles.instrucao}>
              {buscando ? "Buscando produto..." : "Aponte para o codigo de barras"}
            </Text>
          </View>

          {buscando && (
            <View style={styles.loadingOverlay}>
              <ActivityIndicator size="large" color="#fff" />
            </View>
          )}
        </View>
      </CameraView>

      {produtoEncontrado && (
        <View style={styles.produtoCard}>
          <View style={styles.produtoResumoRow}>
            <View style={styles.produtoImagemWrap}>
              {produtoEncontrado.foto_url ? (
                <Image source={{ uri: produtoEncontrado.foto_url }} style={styles.produtoImagem} resizeMode="contain" />
              ) : (
                <View style={[styles.produtoImagem, styles.produtoImagemPlaceholder]}>
                  <Ionicons name="image-outline" size={24} color={CORES.textoClaro} />
                </View>
              )}
            </View>
            <View style={styles.produtoInfo}>
              <Text style={styles.produtoNome} numberOfLines={2}>{produtoEncontrado.nome}</Text>
              <Text style={[styles.produtoEstoque, produtoSemEstoque && styles.produtoEstoqueIndisponivel]}>
                {produtoSemEstoque ? "Sem estoque" : `Estoque: ${produtoEncontrado.estoque ?? "-"}`}
              </Text>
            </View>
            <TouchableOpacity
              style={styles.botaoEscanear}
              onPress={() => {
                setProdutoEncontrado(null);
                ultimoScan.current = "";
                setScanAtivo(true);
              }}
            >
              <Ionicons name="scan-outline" size={18} color={CORES.primario} />
            </TouchableOpacity>
          </View>

          <View style={styles.produtoCompraRow}>
            <View style={styles.produtoPrecoWrap}>
              {produtoEncontrado.promocao_ativa && produtoEncontrado.preco_promocional ? (
                <Text style={styles.produtoPrecoOriginal} numberOfLines={1}>
                  {formatarMoedaScanner(produtoEncontrado.preco)}
                </Text>
              ) : null}
              <Text style={styles.produtoPreco} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.75}>
                {formatarMoedaScanner(
                  produtoEncontrado.promocao_ativa && produtoEncontrado.preco_promocional
                    ? produtoEncontrado.preco_promocional
                    : produtoEncontrado.preco,
                )}
              </Text>
            </View>
            <TouchableOpacity
              style={[styles.botaoAdicionar, produtoSemEstoque && styles.botaoAdicionarDesabilitado]}
              onPress={adicionarAoCarrinho}
              disabled={produtoSemEstoque}
            >
              <Ionicons name="cart" size={18} color="#fff" />
              <Text style={styles.botaoAdicionarTexto}>{produtoSemEstoque ? "Sem estoque" : "Adicionar"}</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  centrado: { flex: 1, justifyContent: "center", alignItems: "center" },
  camera: { flex: 1 },
  overlay: { flex: 1 },
  fechar: {
    position: "absolute",
    top: 50,
    right: 20,
    backgroundColor: "rgba(0,0,0,0.5)",
    borderRadius: 20,
    padding: 8,
    zIndex: 10,
  },
  areaCenter: { flex: 1, justifyContent: "center", alignItems: "center" },
  frameScan: { width: 260, height: 180, position: "relative", marginBottom: 20 },
  canto: { position: "absolute", width: 30, height: 30, borderColor: "#fff", borderWidth: 3 },
  cantoTopLeft: { top: 0, left: 0, borderRightWidth: 0, borderBottomWidth: 0 },
  cantoTopRight: { top: 0, right: 0, borderLeftWidth: 0, borderBottomWidth: 0 },
  cantoBottomLeft: { bottom: 0, left: 0, borderRightWidth: 0, borderTopWidth: 0 },
  cantoBottomRight: { bottom: 0, right: 0, borderLeftWidth: 0, borderTopWidth: 0 },
  instrucao: {
    color: "#fff",
    fontSize: FONTE.normal,
    textAlign: "center",
    backgroundColor: "rgba(0,0,0,0.5)",
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: RAIO.circulo,
  },
  loadingOverlay: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(0,0,0,0.4)",
  },
  produtoCard: {
    backgroundColor: CORES.superficie,
    padding: ESPACO.lg,
    borderTopLeftRadius: RAIO.lg,
    borderTopRightRadius: RAIO.lg,
    gap: ESPACO.md,
  },
  produtoResumoRow: { flexDirection: "row", alignItems: "center", gap: ESPACO.md },
  produtoImagemWrap: { width: 72, height: 72, borderRadius: RAIO.md, overflow: "hidden", backgroundColor: CORES.fundo },
  produtoImagem: { width: "100%", height: "100%" },
  produtoImagemPlaceholder: { alignItems: "center", justifyContent: "center" },
  produtoInfo: { flex: 1, minWidth: 0 },
  produtoNome: { fontSize: FONTE.normal, fontWeight: "800", color: CORES.texto },
  produtoEstoque: { fontSize: FONTE.pequena, color: CORES.sucesso, fontWeight: "700", marginTop: 4 },
  produtoEstoqueIndisponivel: { color: CORES.erro },
  produtoCompraRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: ESPACO.md },
  produtoPrecoWrap: { flexShrink: 1, minWidth: 88, maxWidth: 120, paddingRight: ESPACO.xs },
  produtoPrecoOriginal: { fontSize: FONTE.pequena, color: CORES.textoClaro, textDecorationLine: "line-through", marginBottom: 2 },
  produtoPreco: { fontSize: FONTE.grande, fontWeight: "900", color: CORES.primario },
  botaoEscanear: {
    width: 42,
    height: 42,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.primario,
    justifyContent: "center",
    alignItems: "center",
  },
  botaoAdicionar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm + 4,
    gap: 6,
    minWidth: 128,
  },
  botaoAdicionarDesabilitado: { backgroundColor: CORES.textoClaro },
  botaoAdicionarTexto: { color: "#fff", fontWeight: "800", fontSize: FONTE.normal },
  semPermissao: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: ESPACO.xl,
    backgroundColor: CORES.fundo,
  },
  semPermissaoTitulo: { fontSize: FONTE.titulo, fontWeight: "800", color: CORES.texto, marginTop: ESPACO.md },
  semPermissaoTexto: { fontSize: FONTE.normal, color: CORES.textoSecundario, textAlign: "center", marginTop: ESPACO.sm, marginBottom: ESPACO.xl },
  botaoPermissao: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.xl,
    paddingVertical: ESPACO.md,
    marginBottom: ESPACO.md,
  },
  botaoPermissaoTexto: { color: "#fff", fontSize: FONTE.media, fontWeight: "800" },
  linkVoltar: { color: CORES.primario, fontSize: FONTE.normal },
});
