import { Ionicons } from "@expo/vector-icons";
import { useIsFocused } from "@react-navigation/native";
import { CameraView, useCameraPermissions } from "expo-camera";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  Vibration,
  View,
} from "react-native";
import {
  buscarProdutoFuncionarioPorBarcode,
  buscarProdutosFuncionario,
  registrarBalancoFuncionario,
} from "../../services/funcionarioEstoque.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import { FuncionarioProdutoEstoque } from "../../types";
import { formatarMoeda } from "../../utils/format";

type HistoricoBalancoSessao = {
  id: string;
  produtoNome: string;
  codigo?: string | null;
  estoqueAnterior: number;
  estoqueNovo: number;
  diferenca: number;
  tipoMovimentacao?: "entrada" | "saida" | null;
  quantidadeMovimentada: number;
  mensagem: string;
};

function mensagemErroApi(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return fallback;
}

function parseNumero(valor: string): number | null {
  const normalizado = valor.replace(/\./g, "").replace(",", ".").trim();
  if (!normalizado) return null;
  const numero = Number(normalizado);
  return Number.isFinite(numero) ? numero : null;
}

function formatarQuantidade(valor: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor ?? 0));
}

export default function FuncionarioBalancoScreen() {
  const isFocused = useIsFocused();
  const [permission, requestPermission] = useCameraPermissions();
  const [scannerAberto, setScannerAberto] = useState(false);
  const [scanAtivo, setScanAtivo] = useState(true);
  const [buscando, setBuscando] = useState(false);
  const [buscaManual, setBuscaManual] = useState("");
  const [sugestoes, setSugestoes] = useState<FuncionarioProdutoEstoque[]>([]);
  const [produto, setProduto] = useState<FuncionarioProdutoEstoque | null>(null);
  const [saldoFinal, setSaldoFinal] = useState("");
  const [numeroLote, setNumeroLote] = useState("");
  const [dataValidade, setDataValidade] = useState("");
  const [observacao, setObservacao] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [ultimoResultado, setUltimoResultado] = useState<string | null>(null);
  const [historicoSessao, setHistoricoSessao] = useState<HistoricoBalancoSessao[]>([]);
  const ultimoScan = useRef("");

  useEffect(() => {
    if (scannerAberto && !permission?.granted) {
      requestPermission();
    }
  }, [scannerAberto, permission?.granted, requestPermission]);

  const saldoFinalNumero = useMemo(() => parseNumero(saldoFinal), [saldoFinal]);
  const diferenca = useMemo(() => {
    if (!produto || saldoFinalNumero == null) return null;
    return saldoFinalNumero - Number(produto.estoque_atual ?? 0);
  }, [produto, saldoFinalNumero]);

  function selecionarProduto(item: FuncionarioProdutoEstoque) {
    setProduto(item);
    setSaldoFinal(String(item.estoque_atual ?? 0).replace(".", ","));
    setSugestoes([]);
    setBuscaManual("");
    setUltimoResultado(null);
  }

  async function onBarcodeScanned({ data }: { data: string }) {
    if (!scanAtivo || buscando || data === ultimoScan.current) return;
    ultimoScan.current = data;
    setScanAtivo(false);
    setBuscando(true);
    Vibration.vibrate(80);

    try {
      const encontrado = await buscarProdutoFuncionarioPorBarcode(data);
      if (!encontrado) {
        Alert.alert("Nao encontrado", `Codigo ${data} nao encontrado no ERP.`, [
          {
            text: "Escanear outro",
            onPress: () => {
              ultimoScan.current = "";
              setScanAtivo(true);
            },
          },
        ]);
        return;
      }
      selecionarProduto(encontrado);
      setScannerAberto(false);
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar o produto."));
    } finally {
      setBuscando(false);
    }
  }

  async function buscarManual() {
    const termo = buscaManual.trim();
    if (termo.length < 2) return;
    setBuscando(true);
    try {
      setSugestoes(await buscarProdutosFuncionario(termo));
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar no ERP."));
    } finally {
      setBuscando(false);
    }
  }

  async function registrar() {
    if (!produto) {
      Alert.alert("Produto obrigatorio", "Escaneie ou busque um produto antes de registrar.");
      return;
    }
    if (produto.permite_balanco === false) {
      Alert.alert("Produto nao permitido", produto.aviso || "Este produto nao aceita balanco direto.");
      return;
    }
    if (saldoFinalNumero == null || saldoFinalNumero < 0) {
      Alert.alert("Saldo invalido", "Informe o saldo final contado.");
      return;
    }

    setSalvando(true);
    try {
      const resposta = await registrarBalancoFuncionario({
        produto_id: produto.id,
        saldo_final: saldoFinalNumero,
        numero_lote: numeroLote.trim() || null,
        data_validade: dataValidade.trim() || null,
        observacao: observacao.trim() || null,
      });
      setProduto(resposta.produto);
      setSaldoFinal(String(resposta.estoque_novo).replace(".", ","));
      setNumeroLote("");
      setDataValidade("");
      setObservacao("");
      setUltimoResultado(resposta.mensagem);
      setHistoricoSessao((atual) => [
        {
          id: String(resposta.movimentacao_id ?? `sem-mov-${Date.now()}`),
          produtoNome: resposta.produto.nome,
          codigo: resposta.produto.codigo,
          estoqueAnterior: resposta.estoque_anterior,
          estoqueNovo: resposta.estoque_novo,
          diferenca: resposta.diferenca,
          tipoMovimentacao: resposta.tipo_movimentacao,
          quantidadeMovimentada: resposta.quantidade_movimentada,
          mensagem: resposta.mensagem,
        },
        ...atual,
      ].slice(0, 10));
      Alert.alert("Balanco registrado", resposta.mensagem);
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel registrar o balanco."));
    } finally {
      setSalvando(false);
    }
  }

  if (scannerAberto && permission && !permission.granted) {
    return (
      <View style={styles.centrado}>
        <Ionicons name="camera-outline" size={42} color={CORES.primario} />
        <Text style={styles.tituloPermissao}>Permitir camera</Text>
        <TouchableOpacity style={styles.botaoPrimario} onPress={requestPermission}>
          <Text style={styles.botaoPrimarioTexto}>Permitir</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (scannerAberto && isFocused) {
    return (
      <View style={styles.scannerContainer}>
        <CameraView
          style={styles.camera}
          facing="back"
          onBarcodeScanned={scanAtivo ? onBarcodeScanned : undefined}
          barcodeScannerSettings={{
            barcodeTypes: ["ean13", "ean8", "upc_a", "upc_e", "code128", "code39", "qr"],
          }}
        >
          <View style={styles.scannerOverlay}>
            <TouchableOpacity style={styles.fecharScanner} onPress={() => setScannerAberto(false)}>
              <Ionicons name="close" size={28} color="#fff" />
            </TouchableOpacity>
            <View style={styles.frameScan} />
            <Text style={styles.scannerTexto}>{buscando ? "Buscando no ERP..." : "Aponte para o codigo de barras"}</Text>
            {!scanAtivo ? (
              <TouchableOpacity
                style={styles.botaoScanner}
                onPress={() => {
                  ultimoScan.current = "";
                  setScanAtivo(true);
                }}
              >
                <Ionicons name="scan-outline" size={18} color="#fff" />
                <Text style={styles.botaoScannerTexto}>Escanear novamente</Text>
              </TouchableOpacity>
            ) : null}
          </View>
        </CameraView>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={styles.conteudo} keyboardShouldPersistTaps="handled">
        <View style={styles.headerCard}>
          <View style={styles.headerIcone}>
            <Ionicons name="barcode-outline" size={24} color={CORES.sucesso} />
          </View>
          <View style={styles.headerTexto}>
            <Text style={styles.titulo}>Balanco por camera</Text>
            <Text style={styles.subtitulo}>O ERP e a fonte da verdade. Informe o saldo final contado.</Text>
          </View>
        </View>

        <View style={styles.card}>
          <TouchableOpacity
            style={styles.botaoScan}
            onPress={() => {
              ultimoScan.current = "";
              setScanAtivo(true);
              setScannerAberto(true);
            }}
          >
            <Ionicons name="camera" size={20} color="#fff" />
            <Text style={styles.botaoScanTexto}>Ler codigo de barras</Text>
          </TouchableOpacity>

          <View style={styles.buscaLinha}>
            <TextInput
              value={buscaManual}
              onChangeText={setBuscaManual}
              placeholder="Buscar por nome, SKU ou codigo"
              style={styles.inputBusca}
              returnKeyType="search"
              onSubmitEditing={buscarManual}
            />
            <TouchableOpacity style={styles.botaoBusca} onPress={buscarManual} disabled={buscando}>
              {buscando ? <ActivityIndicator color="#fff" /> : <Ionicons name="search" size={20} color="#fff" />}
            </TouchableOpacity>
          </View>

          {sugestoes.map((item) => (
            <TouchableOpacity key={item.id} style={styles.sugestao} onPress={() => selecionarProduto(item)}>
              <View style={{ flex: 1 }}>
                <Text style={styles.sugestaoNome} numberOfLines={2}>{item.nome}</Text>
                <Text style={styles.sugestaoMeta}>SKU {item.codigo || "-"} | Estoque {formatarQuantidade(item.estoque_atual)}</Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
            </TouchableOpacity>
          ))}
        </View>

        {produto ? (
          <View style={styles.card}>
            <View style={styles.produtoCabecalho}>
              <View style={{ flex: 1 }}>
                <Text style={styles.produtoNome}>{produto.nome}</Text>
                <Text style={styles.produtoMeta}>SKU {produto.codigo || "-"} | {produto.unidade || "UN"}</Text>
              </View>
              <TouchableOpacity style={styles.botaoLimpar} onPress={() => setProduto(null)}>
                <Ionicons name="close" size={18} color={CORES.erro} />
              </TouchableOpacity>
            </View>

            {produto.aviso ? (
              <View style={styles.aviso}>
                <Ionicons name="alert-circle-outline" size={18} color={CORES.aviso} />
                <Text style={styles.avisoTexto}>{produto.aviso}</Text>
              </View>
            ) : null}

            <View style={styles.metricas}>
              <View style={styles.metrica}>
                <Text style={styles.metricaLabel}>Preco venda</Text>
                <Text style={styles.metricaValor}>{formatarMoeda(produto.preco_venda)}</Text>
              </View>
              <View style={styles.metrica}>
                <Text style={styles.metricaLabel}>Estoque ERP</Text>
                <Text style={styles.metricaValor}>{formatarQuantidade(produto.estoque_atual)}</Text>
              </View>
            </View>

            <Text style={styles.label}>Saldo final contado</Text>
            <TextInput
              value={saldoFinal}
              onChangeText={setSaldoFinal}
              placeholder="Ex: 12"
              keyboardType="decimal-pad"
              style={styles.input}
            />

            <View style={styles.diferencaBox}>
              <Text style={styles.diferencaLabel}>Movimentacao calculada</Text>
              <Text style={[styles.diferencaValor, (diferenca ?? 0) < 0 && styles.diferencaNegativa]}>
                {diferenca == null
                  ? "Informe o saldo"
                  : diferenca > 0
                    ? `Entrada de ${formatarQuantidade(diferenca)}`
                    : diferenca < 0
                      ? `Saida de ${formatarQuantidade(Math.abs(diferenca))}`
                      : "Sem alteracao"}
              </Text>
            </View>

            <Text style={styles.label}>Lote</Text>
            <TextInput
              value={numeroLote}
              onChangeText={setNumeroLote}
              placeholder="Opcional"
              style={styles.input}
              autoCapitalize="characters"
            />

            <Text style={styles.label}>Validade</Text>
            <TextInput
              value={dataValidade}
              onChangeText={setDataValidade}
              placeholder="DD/MM/AAAA ou AAAA-MM-DD"
              style={styles.input}
            />

            <Text style={styles.label}>Observacao</Text>
            <TextInput
              value={observacao}
              onChangeText={setObservacao}
              placeholder="Opcional"
              style={[styles.input, styles.inputMultilinha]}
              multiline
            />

            <TouchableOpacity
              style={[styles.botaoSalvar, (salvando || produto.permite_balanco === false) && styles.botaoDesabilitado]}
              onPress={registrar}
              disabled={salvando || produto.permite_balanco === false}
            >
              {salvando ? <ActivityIndicator color="#fff" /> : <Ionicons name="checkmark-circle" size={20} color="#fff" />}
              <Text style={styles.botaoSalvarTexto}>Registrar balanco</Text>
            </TouchableOpacity>
          </View>
        ) : null}

        {ultimoResultado ? (
          <View style={styles.resultado}>
            <Ionicons name="checkmark-circle-outline" size={18} color={CORES.sucesso} />
            <Text style={styles.resultadoTexto}>{ultimoResultado}</Text>
          </View>
        ) : null}

        {historicoSessao.length ? (
          <View style={styles.card}>
            <Text style={styles.secaoTitulo}>Lancamentos da sessao</Text>
            {historicoSessao.map((item) => (
              <View key={item.id} style={styles.historicoItem}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.historicoProduto} numberOfLines={2}>
                    {item.produtoNome}
                  </Text>
                  <Text style={styles.historicoMeta}>
                    SKU {item.codigo || "-"} | Saldo {formatarQuantidade(item.estoqueAnterior)} para {formatarQuantidade(item.estoqueNovo)}
                  </Text>
                  <Text style={styles.historicoMensagem} numberOfLines={2}>
                    {item.mensagem}
                  </Text>
                </View>
                <View style={styles.historicoResumo}>
                  <Text style={[
                    styles.historicoBadge,
                    item.tipoMovimentacao === "saida" && styles.historicoBadgeSaida,
                    !item.tipoMovimentacao && styles.historicoBadgeNeutro,
                  ]}>
                    {item.tipoMovimentacao === "entrada"
                      ? "Entrada"
                      : item.tipoMovimentacao === "saida"
                        ? "Saida"
                        : "Sem mov."}
                  </Text>
                  <Text style={[styles.historicoDiferenca, item.diferenca < 0 && styles.diferencaNegativa]}>
                    {item.diferenca > 0
                      ? `+${formatarQuantidade(item.quantidadeMovimentada)}`
                      : item.diferenca < 0
                        ? `-${formatarQuantidade(item.quantidadeMovimentada)}`
                        : "0"}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  conteudo: { padding: ESPACO.md, gap: ESPACO.md, paddingBottom: ESPACO.xxl },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", padding: ESPACO.lg, backgroundColor: CORES.fundo },
  tituloPermissao: { fontSize: FONTE.titulo, fontWeight: "700", color: CORES.texto, marginVertical: ESPACO.md },
  headerCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    ...SOMBRA,
  },
  headerIcone: {
    width: 48,
    height: 48,
    borderRadius: RAIO.md,
    backgroundColor: "#DCFCE7",
    alignItems: "center",
    justifyContent: "center",
    marginRight: ESPACO.md,
  },
  headerTexto: { flex: 1 },
  titulo: { fontSize: FONTE.titulo, fontWeight: "800", color: CORES.texto },
  subtitulo: { fontSize: FONTE.normal, color: CORES.textoSecundario, marginTop: 2 },
  secaoTitulo: { fontSize: FONTE.grande, fontWeight: "800", color: CORES.texto },
  card: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    gap: ESPACO.sm,
    ...SOMBRA,
  },
  botaoScan: {
    height: 52,
    borderRadius: RAIO.md,
    backgroundColor: CORES.sucesso,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
  },
  botaoScanTexto: { color: "#fff", fontWeight: "800", fontSize: FONTE.media },
  buscaLinha: { flexDirection: "row", gap: ESPACO.sm, marginTop: ESPACO.sm },
  inputBusca: {
    flex: 1,
    height: 48,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    color: CORES.texto,
    fontSize: FONTE.normal,
    backgroundColor: "#fff",
  },
  botaoBusca: {
    width: 52,
    height: 48,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primario,
    alignItems: "center",
    justifyContent: "center",
  },
  sugestao: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginTop: ESPACO.xs,
  },
  sugestaoNome: { fontSize: FONTE.normal, fontWeight: "700", color: CORES.texto },
  sugestaoMeta: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  produtoCabecalho: { flexDirection: "row", alignItems: "flex-start", gap: ESPACO.sm },
  produtoNome: { fontSize: FONTE.grande, fontWeight: "800", color: CORES.texto },
  produtoMeta: { fontSize: FONTE.normal, color: CORES.textoSecundario, marginTop: 2 },
  botaoLimpar: {
    width: 36,
    height: 36,
    borderRadius: RAIO.circulo,
    backgroundColor: "#FEE2E2",
    alignItems: "center",
    justifyContent: "center",
  },
  aviso: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    backgroundColor: "#FFFBEB",
    borderWidth: 1,
    borderColor: "#FDE68A",
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
  },
  avisoTexto: { flex: 1, color: "#92400E", fontSize: FONTE.pequena },
  metricas: { flexDirection: "row", gap: ESPACO.sm },
  metrica: { flex: 1, backgroundColor: CORES.fundo, borderRadius: RAIO.sm, padding: ESPACO.sm },
  metricaLabel: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  metricaValor: { fontSize: FONTE.media, fontWeight: "800", color: CORES.texto, marginTop: 2 },
  label: { fontSize: FONTE.normal, fontWeight: "700", color: CORES.texto, marginTop: ESPACO.xs },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    fontSize: FONTE.media,
    color: CORES.texto,
    backgroundColor: "#fff",
  },
  inputMultilinha: { minHeight: 82, textAlignVertical: "top" },
  diferencaBox: {
    backgroundColor: CORES.primarioClaro,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: "#BFDBFE",
  },
  diferencaLabel: { color: CORES.textoSecundario, fontSize: FONTE.pequena },
  diferencaValor: { color: CORES.sucesso, fontWeight: "900", fontSize: FONTE.grande, marginTop: 2 },
  diferencaNegativa: { color: CORES.erro },
  botaoSalvar: {
    height: 52,
    borderRadius: RAIO.md,
    backgroundColor: CORES.sucesso,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
    marginTop: ESPACO.sm,
  },
  botaoSalvarTexto: { color: "#fff", fontWeight: "800", fontSize: FONTE.media },
  botaoDesabilitado: { opacity: 0.5 },
  resultado: {
    flexDirection: "row",
    gap: ESPACO.sm,
    alignItems: "center",
    backgroundColor: "#ECFDF5",
    borderColor: "#BBF7D0",
    borderWidth: 1,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
  },
  resultadoTexto: { flex: 1, color: "#065F46", fontWeight: "700" },
  historicoItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
  },
  historicoProduto: { fontSize: FONTE.normal, fontWeight: "800", color: CORES.texto },
  historicoMeta: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  historicoMensagem: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 4 },
  historicoResumo: { alignItems: "flex-end", gap: ESPACO.xs },
  historicoBadge: {
    overflow: "hidden",
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: 3,
    backgroundColor: "#DCFCE7",
    color: "#065F46",
    fontSize: FONTE.pequena,
    fontWeight: "800",
  },
  historicoBadgeSaida: { backgroundColor: "#FEE2E2", color: CORES.erro },
  historicoBadgeNeutro: { backgroundColor: "#E5E7EB", color: CORES.textoSecundario },
  historicoDiferenca: { fontSize: FONTE.media, fontWeight: "900", color: CORES.sucesso },
  botaoPrimario: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.lg,
    paddingVertical: ESPACO.md,
  },
  botaoPrimarioTexto: { color: "#fff", fontWeight: "800" },
  scannerContainer: { flex: 1, backgroundColor: "#000" },
  camera: { flex: 1 },
  scannerOverlay: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "rgba(0,0,0,0.25)" },
  fecharScanner: {
    position: "absolute",
    top: 48,
    right: 24,
    width: 44,
    height: 44,
    borderRadius: RAIO.circulo,
    backgroundColor: "rgba(0,0,0,0.5)",
    alignItems: "center",
    justifyContent: "center",
  },
  frameScan: {
    width: 260,
    height: 160,
    borderWidth: 3,
    borderColor: "#fff",
    borderRadius: RAIO.md,
  },
  scannerTexto: { color: "#fff", marginTop: ESPACO.lg, fontSize: FONTE.media, fontWeight: "700" },
  botaoScanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    marginTop: ESPACO.md,
  },
  botaoScannerTexto: { color: "#fff", fontWeight: "800" },
});
