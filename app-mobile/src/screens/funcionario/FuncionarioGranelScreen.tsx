import { Ionicons } from "@expo/vector-icons";
import { CameraView, useCameraPermissions } from "expo-camera";
import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  Vibration,
  View,
} from "react-native";

import {
  buscarProdutoGranelPorBarcode,
  buscarProdutosGranelFuncionario,
  converterGranelFuncionario,
  FuncionarioGranelProduto,
  obterConfigGranelFuncionario,
} from "../../services/funcionarioGranel.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

function mensagemErro(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  return typeof detail === "string" && detail.trim() ? detail : fallback;
}

function formatarQuantidade(valor: number) {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(valor || 0);
}

export default function FuncionarioGranelScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [bipagemObrigatoria, setBipagemObrigatoria] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [scannerAberto, setScannerAberto] = useState(false);
  const [scanAtivo, setScanAtivo] = useState(true);
  const [origem, setOrigem] = useState<FuncionarioGranelProduto | null>(null);
  const [granel, setGranel] = useState<FuncionarioGranelProduto | null>(null);
  const [barcodeOrigem, setBarcodeOrigem] = useState<string | null>(null);
  const [barcodeGranel, setBarcodeGranel] = useState<string | null>(null);
  const [quantidade, setQuantidade] = useState("1");
  const [observacao, setObservacao] = useState("");
  const [busca, setBusca] = useState("");
  const [sugestoes, setSugestoes] = useState<FuncionarioGranelProduto[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const ultimoCodigo = useRef("");

  useEffect(() => {
    obterConfigGranelFuncionario()
      .then((config) => setBipagemObrigatoria(config.bipagem_obrigatoria))
      .catch((error) =>
        Alert.alert("Erro", mensagemErro(error, "Nao foi possivel abrir o granel.")),
      )
      .finally(() => setCarregando(false));
  }, []);

  useEffect(() => {
    if (scannerAberto && !permission?.granted) requestPermission();
  }, [scannerAberto, permission?.granted, requestPermission]);

  function etapaAtual(): "origem" | "granel" {
    return origem ? "granel" : "origem";
  }

  function selecionar(item: FuncionarioGranelProduto) {
    if (!origem) {
      setOrigem(item);
      setGranel(null);
      setBarcodeOrigem(null);
      setBarcodeGranel(null);
    } else {
      setGranel(item);
      setBarcodeGranel(null);
    }
    setBusca("");
    setSugestoes([]);
  }

  async function onBarcodeScanned({ data }: { data: string }) {
    if (!scanAtivo || buscando || data === ultimoCodigo.current) return;
    ultimoCodigo.current = data;
    setScanAtivo(false);
    setBuscando(true);
    Vibration.vibrate(70);
    const etapa = etapaAtual();
    try {
      const produto = await buscarProdutoGranelPorBarcode(data, etapa, origem?.id);
      if (etapa === "origem") {
        setOrigem(produto);
        setGranel(null);
        setBarcodeOrigem(data);
        setBarcodeGranel(null);
        Alert.alert("Produto fechado conferido", "Agora bipe o produto a granel vinculado.");
      } else {
        setGranel(produto);
        setBarcodeGranel(data);
        setScannerAberto(false);
        Alert.alert("Tudo certo", "O produto a granel corresponde ao produto fechado.");
      }
    } catch (error: any) {
      Vibration.vibrate([0, 90, 60, 130]);
      Alert.alert("Conferencia", mensagemErro(error, "Nao foi possivel conferir o produto."));
    } finally {
      ultimoCodigo.current = "";
      setScanAtivo(true);
      setBuscando(false);
    }
  }

  async function buscarManual() {
    if (busca.trim().length < 2) return;
    setBuscando(true);
    try {
      setSugestoes(await buscarProdutosGranelFuncionario(busca, etapaAtual(), origem?.id));
    } catch (error: any) {
      Alert.alert("Erro", mensagemErro(error, "Nao foi possivel buscar os produtos."));
    } finally {
      setBuscando(false);
    }
  }

  function limpar() {
    setOrigem(null);
    setGranel(null);
    setBarcodeOrigem(null);
    setBarcodeGranel(null);
    setQuantidade("1");
    setObservacao("");
    setBusca("");
    setSugestoes([]);
  }

  async function lancar() {
    if (!origem || !granel) {
      Alert.alert("Produtos pendentes", "Informe o produto fechado e o produto a granel.");
      return;
    }
    const quantidadeNumero = Number(quantidade.replace(",", "."));
    if (!Number.isFinite(quantidadeNumero) || quantidadeNumero <= 0) {
      Alert.alert("Quantidade invalida", "Informe quantas embalagens foram abertas.");
      return;
    }
    setSalvando(true);
    try {
      const resultado = await converterGranelFuncionario({
        produto_origem_id: origem.id,
        produto_granel_id: granel.id,
        quantidade_pacotes: quantidadeNumero,
        produto_origem_barcode: barcodeOrigem,
        produto_granel_barcode: barcodeGranel,
        observacao: observacao.trim() || null,
      });
      Alert.alert(
        "Granel lancado",
        `${formatarQuantidade(resultado.quantidade_granel_kg)} kg adicionados a ${resultado.produto_granel_nome}.`,
      );
      limpar();
    } catch (error: any) {
      Alert.alert(
        "Nao foi possivel lancar",
        mensagemErro(error, "Confira os dados e tente novamente."),
      );
    } finally {
      setSalvando(false);
    }
  }

  if (carregando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={CORES.sucesso} />
      </View>
    );
  }

  if (scannerAberto) {
    if (!permission?.granted) {
      return (
        <View style={styles.centrado}>
          <Ionicons name="camera-outline" size={44} color={CORES.sucesso} />
          <Text style={styles.titulo}>Permitir camera</Text>
          <TouchableOpacity style={styles.botaoPrimario} onPress={() => requestPermission()}>
            <Text style={styles.botaoPrimarioTexto}>Permitir</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setScannerAberto(false)}>
            <Text>Voltar</Text>
          </TouchableOpacity>
        </View>
      );
    }
    return (
      <View style={styles.scannerContainer}>
        <CameraView
          style={StyleSheet.absoluteFill}
          facing="back"
          onBarcodeScanned={scanAtivo ? onBarcodeScanned : undefined}
          barcodeScannerSettings={{
            barcodeTypes: ["ean13", "ean8", "upc_a", "upc_e", "code128", "code39", "qr"],
          }}
        />
        <View style={styles.scannerOverlay}>
          <TouchableOpacity style={styles.fecharScanner} onPress={() => setScannerAberto(false)}>
            <Ionicons name="close" size={28} color="#fff" />
          </TouchableOpacity>
          <View style={styles.frameScan} />
          <Text style={styles.scannerTexto}>
            {buscando
              ? "Conferindo..."
              : origem
                ? "Bipe o produto a granel"
                : "Bipe o produto fechado"}
          </Text>
        </View>
      </View>
    );
  }

  const kgPrevistos =
    Number(quantidade.replace(",", ".") || 0) * Number(origem?.peso_embalagem || 0);
  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.conteudo}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.aviso}>
        <Ionicons
          name={bipagemObrigatoria ? "lock-closed-outline" : "scan-outline"}
          size={22}
          color={CORES.primario}
        />
        <Text style={styles.avisoTexto}>
          {bipagemObrigatoria
            ? "A empresa exige a bipagem do produto fechado e do produto a granel vinculado."
            : "Voce pode bipar os produtos ou usar a busca manual."}
        </Text>
      </View>

      <View style={styles.etapas}>
        <ProdutoCard titulo="1. Produto fechado" produto={origem} onLimpar={limpar} />
        <ProdutoCard
          titulo="2. Produto a granel"
          produto={granel}
          onLimpar={() => {
            setGranel(null);
            setBarcodeGranel(null);
          }}
        />
      </View>

      <TouchableOpacity style={styles.botaoScanner} onPress={() => setScannerAberto(true)}>
        <Ionicons name="barcode-outline" size={22} color="#fff" />
        <Text style={styles.botaoPrimarioTexto}>
          {origem ? "Bipar produto a granel" : "Bipar produto fechado"}
        </Text>
      </TouchableOpacity>

      {!bipagemObrigatoria && (
        <View>
          <Text style={styles.label}>
            Busca manual de {origem ? "produto a granel vinculado" : "produto fechado"}
          </Text>
          <View style={styles.buscaLinha}>
            <TextInput
              style={styles.input}
              value={busca}
              onChangeText={setBusca}
              placeholder="Nome ou codigo"
            />
            <TouchableOpacity style={styles.botaoBusca} onPress={buscarManual}>
              {buscando ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Ionicons name="search" size={20} color="#fff" />
              )}
            </TouchableOpacity>
          </View>
          {sugestoes.map((item) => (
            <TouchableOpacity
              key={item.id}
              style={styles.sugestao}
              onPress={() => selecionar(item)}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.sugestaoNome}>{item.nome}</Text>
                <Text style={styles.muted}>{item.codigo}</Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
            </TouchableOpacity>
          ))}
        </View>
      )}

      <View style={styles.card}>
        <Text style={styles.label}>Embalagens abertas</Text>
        <TextInput
          style={styles.inputInteiro}
          value={quantidade}
          onChangeText={setQuantidade}
          keyboardType="decimal-pad"
        />
        <Text style={styles.previsao}>Entrada prevista: {formatarQuantidade(kgPrevistos)} kg</Text>
        <Text style={styles.label}>Observacao (opcional)</Text>
        <TextInput
          style={[styles.inputInteiro, styles.observacao]}
          value={observacao}
          onChangeText={setObservacao}
          multiline
        />
      </View>

      <TouchableOpacity
        style={[styles.botaoPrimario, (!origem || !granel) && styles.desabilitado]}
        onPress={lancar}
        disabled={salvando || !origem || !granel}
      >
        {salvando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Ionicons name="checkmark-circle-outline" size={22} color="#fff" />
        )}
        <Text style={styles.botaoPrimarioTexto}>Confirmar lancamento</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

function ProdutoCard({
  titulo,
  produto,
  onLimpar,
}: {
  titulo: string;
  produto: FuncionarioGranelProduto | null;
  onLimpar: () => void;
}) {
  return (
    <View style={[styles.card, produto && styles.cardOk]}>
      <Text style={styles.cardTitulo}>{titulo}</Text>
      {produto ? (
        <View style={styles.produtoLinha}>
          <Ionicons name="checkmark-circle" size={24} color={CORES.sucesso} />
          <View style={{ flex: 1 }}>
            <Text style={styles.produtoNome}>{produto.nome}</Text>
            <Text style={styles.muted}>{produto.codigo}</Text>
          </View>
          <TouchableOpacity onPress={onLimpar}>
            <Ionicons name="close-circle-outline" size={22} color={CORES.textoSecundario} />
          </TouchableOpacity>
        </View>
      ) : (
        <Text style={styles.muted}>Ainda nao informado</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  conteudo: { padding: ESPACO.md, gap: ESPACO.md, paddingBottom: ESPACO.xxl },
  centrado: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: ESPACO.md,
    padding: ESPACO.lg,
  },
  titulo: { fontSize: FONTE.titulo, fontWeight: "800", color: CORES.texto },
  aviso: {
    flexDirection: "row",
    gap: ESPACO.sm,
    backgroundColor: CORES.primarioClaro,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
  },
  avisoTexto: { flex: 1, color: CORES.primarioEscuro, fontWeight: "700", lineHeight: 20 },
  etapas: { gap: ESPACO.sm },
  card: {
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    ...SOMBRA,
  },
  cardOk: { borderColor: "#86EFAC", backgroundColor: "#F0FDF4" },
  cardTitulo: {
    fontSize: FONTE.media,
    fontWeight: "900",
    color: CORES.texto,
    marginBottom: ESPACO.sm,
  },
  produtoLinha: { flexDirection: "row", alignItems: "center", gap: ESPACO.sm },
  produtoNome: { fontWeight: "800", color: CORES.texto },
  muted: { color: CORES.textoSecundario, marginTop: 2 },
  botaoScanner: {
    minHeight: 52,
    borderRadius: RAIO.md,
    backgroundColor: CORES.sucesso,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
  },
  botaoPrimario: {
    minHeight: 52,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primario,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
    paddingHorizontal: ESPACO.md,
  },
  botaoPrimarioTexto: { color: "#fff", fontWeight: "900", fontSize: FONTE.media },
  desabilitado: { opacity: 0.45 },
  label: { fontWeight: "800", color: CORES.texto, marginBottom: ESPACO.xs, marginTop: ESPACO.sm },
  buscaLinha: { flexDirection: "row", gap: ESPACO.sm },
  input: {
    flex: 1,
    minHeight: 48,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    backgroundColor: "#fff",
    paddingHorizontal: ESPACO.md,
  },
  inputInteiro: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    backgroundColor: "#fff",
    paddingHorizontal: ESPACO.md,
  },
  observacao: { minHeight: 72, textAlignVertical: "top", paddingTop: ESPACO.sm },
  botaoBusca: {
    width: 50,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primario,
    alignItems: "center",
    justifyContent: "center",
  },
  sugestao: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    borderBottomWidth: 1,
    borderColor: CORES.borda,
    padding: ESPACO.md,
  },
  sugestaoNome: { fontWeight: "800", color: CORES.texto },
  previsao: { color: CORES.sucesso, fontWeight: "800", marginTop: ESPACO.sm },
  scannerContainer: { flex: 1, backgroundColor: "#000" },
  scannerOverlay: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(0,0,0,0.18)",
  },
  fecharScanner: {
    position: "absolute",
    right: ESPACO.lg,
    top: ESPACO.xxl,
    width: 44,
    height: 44,
    borderRadius: RAIO.circulo,
    backgroundColor: "rgba(0,0,0,0.55)",
    alignItems: "center",
    justifyContent: "center",
  },
  frameScan: {
    width: "78%",
    height: 190,
    borderWidth: 3,
    borderColor: "#fff",
    borderRadius: RAIO.md,
  },
  scannerTexto: {
    color: "#fff",
    backgroundColor: "rgba(0,0,0,0.65)",
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    borderRadius: RAIO.md,
    marginTop: ESPACO.lg,
    fontWeight: "900",
  },
});
