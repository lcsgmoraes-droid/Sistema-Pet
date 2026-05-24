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
  buscarClientesPdv,
  buscarProdutoPdvPorBarcode,
  buscarProdutosPdv,
  finalizarVendaPdv,
  obterCaixaAbertoPdv,
} from "../../services/funcionarioPdv.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import {
  FuncionarioPdvCaixa,
  FuncionarioPdvCliente,
  FuncionarioPdvFormaPagamento,
  FuncionarioPdvProduto,
} from "../../types";
import { formatarMoeda } from "../../utils/format";

type ItemCarrinhoPdv = {
  produto: FuncionarioPdvProduto;
  quantidade: number;
};

const FORMAS_PAGAMENTO: { key: FuncionarioPdvFormaPagamento; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "dinheiro", label: "Dinheiro", icon: "cash-outline" },
  { key: "pix", label: "Pix", icon: "qr-code-outline" },
  { key: "credito", label: "Credito", icon: "card-outline" },
  { key: "debito", label: "Debito", icon: "card-outline" },
];

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

export default function FuncionarioPdvScreen() {
  const isFocused = useIsFocused();
  const [permission, requestPermission] = useCameraPermissions();
  const [scannerAberto, setScannerAberto] = useState(false);
  const [scanAtivo, setScanAtivo] = useState(true);
  const [buscandoProduto, setBuscandoProduto] = useState(false);
  const [buscaManual, setBuscaManual] = useState("");
  const [sugestoes, setSugestoes] = useState<FuncionarioPdvProduto[]>([]);
  const [carrinho, setCarrinho] = useState<ItemCarrinhoPdv[]>([]);
  const [clienteBusca, setClienteBusca] = useState("");
  const [clientesSugestoes, setClientesSugestoes] = useState<FuncionarioPdvCliente[]>([]);
  const [cliente, setCliente] = useState<FuncionarioPdvCliente | null>(null);
  const [formaPagamento, setFormaPagamento] = useState<FuncionarioPdvFormaPagamento>("dinheiro");
  const [valorRecebido, setValorRecebido] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [caixa, setCaixa] = useState<FuncionarioPdvCaixa | null>(null);
  const [carregandoCaixa, setCarregandoCaixa] = useState(false);
  const [finalizando, setFinalizando] = useState(false);
  const ultimoScan = useRef("");

  useEffect(() => {
    if (scannerAberto && !permission?.granted) {
      requestPermission();
    }
  }, [scannerAberto, permission?.granted, requestPermission]);

  useEffect(() => {
    if (!isFocused) return;
    carregarCaixa();
  }, [isFocused]);

  const total = useMemo(
    () =>
      carrinho.reduce(
        (soma, item) => soma + item.quantidade * Number(item.produto.preco_venda ?? 0),
        0,
      ),
    [carrinho],
  );
  const valorRecebidoNumero = useMemo(() => parseNumero(valorRecebido) ?? 0, [valorRecebido]);
  const troco = formaPagamento === "dinheiro" ? Math.max(0, valorRecebidoNumero - total) : 0;
  const totalItens = useMemo(
    () => carrinho.reduce((soma, item) => soma + item.quantidade, 0),
    [carrinho],
  );

  async function carregarCaixa() {
    setCarregandoCaixa(true);
    try {
      setCaixa(await obterCaixaAbertoPdv());
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel consultar o caixa."));
    } finally {
      setCarregandoCaixa(false);
    }
  }

  function adicionarProduto(produto: FuncionarioPdvProduto) {
    if (!produto.vendavel) {
      Alert.alert("Produto nao vendavel", produto.aviso || "Este produto nao pode ser vendido no PDV.");
      return;
    }
    setCarrinho((atual) => {
      const existente = atual.find((item) => item.produto.id === produto.id);
      if (existente) {
        return atual.map((item) =>
          item.produto.id === produto.id ? { ...item, quantidade: item.quantidade + 1 } : item,
        );
      }
      return [...atual, { produto, quantidade: 1 }];
    });
    setSugestoes([]);
    setBuscaManual("");
  }

  function alterarQuantidade(produtoId: number, quantidade: number) {
    if (!Number.isFinite(quantidade) || quantidade <= 0) {
      setCarrinho((atual) => atual.filter((item) => item.produto.id !== produtoId));
      return;
    }
    setCarrinho((atual) =>
      atual.map((item) =>
        item.produto.id === produtoId ? { ...item, quantidade: Math.round(quantidade * 1000) / 1000 } : item,
      ),
    );
  }

  async function onBarcodeScanned({ data }: { data: string }) {
    if (!scanAtivo || buscandoProduto || data === ultimoScan.current) return;
    ultimoScan.current = data;
    setScanAtivo(false);
    setBuscandoProduto(true);
    Vibration.vibrate(80);

    try {
      const produto = await buscarProdutoPdvPorBarcode(data);
      if (!produto) {
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
      adicionarProduto(produto);
      setScannerAberto(false);
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar o produto."));
    } finally {
      setBuscandoProduto(false);
    }
  }

  async function buscarManualProduto() {
    const termo = buscaManual.trim();
    if (termo.length < 2) return;
    setBuscandoProduto(true);
    try {
      setSugestoes(await buscarProdutosPdv(termo));
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar produtos."));
    } finally {
      setBuscandoProduto(false);
    }
  }

  async function buscarCliente() {
    const termo = clienteBusca.trim();
    if (termo.length < 2) return;
    try {
      setClientesSugestoes(await buscarClientesPdv(termo));
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar clientes."));
    }
  }

  async function finalizar() {
    if (!caixa?.aberto) {
      Alert.alert("Caixa fechado", caixa?.mensagem || "Abra um caixa no ERP web antes de vender pelo app.");
      return;
    }
    if (!carrinho.length) {
      Alert.alert("Carrinho vazio", "Adicione ao menos um produto para finalizar.");
      return;
    }
    if (total <= 0) {
      Alert.alert("Total invalido", "O total da venda precisa ser maior que zero.");
      return;
    }
    if (formaPagamento === "dinheiro" && valorRecebidoNumero + 0.01 < total) {
      Alert.alert("Valor recebido", "Informe um valor recebido igual ou maior que o total.");
      return;
    }

    setFinalizando(true);
    try {
      const resposta = await finalizarVendaPdv({
        cliente_id: cliente?.id ?? null,
        itens: carrinho.map((item) => ({
          produto_id: item.produto.id,
          quantidade: item.quantidade,
          preco_unitario: Number(item.produto.preco_venda ?? 0),
        })),
        pagamento: {
          forma_pagamento: formaPagamento,
          valor: Number(total.toFixed(2)),
          valor_recebido: formaPagamento === "dinheiro" ? Number(valorRecebidoNumero.toFixed(2)) : null,
          troco: formaPagamento === "dinheiro" ? Number(troco.toFixed(2)) : null,
        },
        observacoes: observacoes.trim() || null,
      });
      Alert.alert("Venda registrada", `${resposta.numero_venda} - ${formatarMoeda(resposta.total)}`);
      setCarrinho([]);
      setCliente(null);
      setClienteBusca("");
      setClientesSugestoes([]);
      setValorRecebido("");
      setObservacoes("");
      carregarCaixa();
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel finalizar a venda."));
    } finally {
      setFinalizando(false);
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
            <Text style={styles.scannerTexto}>
              {buscandoProduto ? "Buscando no ERP..." : "Aponte para o codigo de barras"}
            </Text>
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
            <Ionicons name="cart-outline" size={24} color={CORES.primario} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.titulo}>PDV rapido</Text>
            <Text style={styles.subtitulo}>Venda simples usando os dados e regras do ERP.</Text>
          </View>
          <TouchableOpacity style={styles.botaoAtualizarCaixa} onPress={carregarCaixa} disabled={carregandoCaixa}>
            {carregandoCaixa ? (
              <ActivityIndicator color={CORES.primario} />
            ) : (
              <Ionicons name="refresh" size={18} color={CORES.primario} />
            )}
          </TouchableOpacity>
        </View>

        <View style={[styles.caixaBox, caixa?.aberto ? styles.caixaAberto : styles.caixaFechado]}>
          <Ionicons
            name={caixa?.aberto ? "checkmark-circle-outline" : "alert-circle-outline"}
            size={20}
            color={caixa?.aberto ? CORES.sucesso : CORES.aviso}
          />
          <Text style={styles.caixaTexto}>
            {caixa?.aberto ? `Caixa #${caixa.numero_caixa ?? caixa.caixa_id} aberto` : caixa?.mensagem || "Consultando caixa..."}
          </Text>
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
              placeholder="Buscar produto no ERP"
              style={styles.inputBusca}
              returnKeyType="search"
              onSubmitEditing={buscarManualProduto}
            />
            <TouchableOpacity style={styles.botaoBusca} onPress={buscarManualProduto} disabled={buscandoProduto}>
              {buscandoProduto ? <ActivityIndicator color="#fff" /> : <Ionicons name="search" size={20} color="#fff" />}
            </TouchableOpacity>
          </View>

          {sugestoes.map((produto) => (
            <TouchableOpacity key={produto.id} style={styles.sugestao} onPress={() => adicionarProduto(produto)}>
              <View style={{ flex: 1 }}>
                <Text style={styles.sugestaoNome} numberOfLines={2}>{produto.nome}</Text>
                <Text style={styles.sugestaoMeta}>
                  SKU {produto.codigo || "-"} | Estoque {formatarQuantidade(produto.estoque_atual)} | {formatarMoeda(produto.preco_venda)}
                </Text>
              </View>
              <Ionicons name="add-circle-outline" size={22} color={CORES.sucesso} />
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.card}>
          <View style={styles.linhaTitulo}>
            <Text style={styles.secaoTitulo}>Carrinho</Text>
            <Text style={styles.badge}>{formatarQuantidade(totalItens)} item(ns)</Text>
          </View>
          {carrinho.length === 0 ? (
            <View style={styles.vazio}>
              <Ionicons name="cube-outline" size={34} color={CORES.textoClaro} />
              <Text style={styles.vazioTexto}>Nenhum produto adicionado</Text>
            </View>
          ) : (
            carrinho.map((item) => (
              <View key={item.produto.id} style={styles.itemCarrinho}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.itemNome} numberOfLines={2}>{item.produto.nome}</Text>
                  <Text style={styles.itemMeta}>{formatarMoeda(item.produto.preco_venda)} un.</Text>
                </View>
                <View style={styles.quantidadeBox}>
                  <TouchableOpacity
                    style={styles.botaoQuantidade}
                    onPress={() => alterarQuantidade(item.produto.id, item.quantidade - 1)}
                  >
                    <Ionicons name="remove" size={16} color={CORES.texto} />
                  </TouchableOpacity>
                  <TextInput
                    value={String(item.quantidade).replace(".", ",")}
                    onChangeText={(valor) => alterarQuantidade(item.produto.id, parseNumero(valor) ?? 0)}
                    keyboardType="decimal-pad"
                    style={styles.inputQuantidade}
                  />
                  <TouchableOpacity
                    style={styles.botaoQuantidade}
                    onPress={() => alterarQuantidade(item.produto.id, item.quantidade + 1)}
                  >
                    <Ionicons name="add" size={16} color={CORES.texto} />
                  </TouchableOpacity>
                </View>
                <Text style={styles.itemSubtotal}>{formatarMoeda(item.quantidade * item.produto.preco_venda)}</Text>
              </View>
            ))
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.secaoTitulo}>Cliente opcional</Text>
          {cliente ? (
            <View style={styles.clienteSelecionado}>
              <View style={{ flex: 1 }}>
                <Text style={styles.clienteNome}>{cliente.nome}</Text>
                <Text style={styles.clienteMeta}>Codigo {cliente.codigo || "-"}</Text>
              </View>
              <TouchableOpacity style={styles.botaoLimpar} onPress={() => setCliente(null)}>
                <Ionicons name="close" size={18} color={CORES.erro} />
              </TouchableOpacity>
            </View>
          ) : (
            <>
              <View style={styles.buscaLinha}>
                <TextInput
                  value={clienteBusca}
                  onChangeText={setClienteBusca}
                  placeholder="Buscar cliente"
                  style={styles.inputBusca}
                  returnKeyType="search"
                  onSubmitEditing={buscarCliente}
                />
                <TouchableOpacity style={styles.botaoBusca} onPress={buscarCliente}>
                  <Ionicons name="search" size={20} color="#fff" />
                </TouchableOpacity>
              </View>
              {clientesSugestoes.map((item) => (
                <TouchableOpacity
                  key={item.id}
                  style={styles.sugestao}
                  onPress={() => {
                    setCliente(item);
                    setClientesSugestoes([]);
                    setClienteBusca("");
                  }}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={styles.sugestaoNome}>{item.nome}</Text>
                    <Text style={styles.sugestaoMeta}>Codigo {item.codigo || "-"} | {item.celular || item.telefone || "-"}</Text>
                  </View>
                  <Ionicons name="person-add-outline" size={20} color={CORES.primario} />
                </TouchableOpacity>
              ))}
            </>
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.secaoTitulo}>Pagamento</Text>
          <View style={styles.formasGrid}>
            {FORMAS_PAGAMENTO.map((forma) => (
              <TouchableOpacity
                key={forma.key}
                style={[styles.formaBotao, formaPagamento === forma.key && styles.formaBotaoAtivo]}
                onPress={() => setFormaPagamento(forma.key)}
              >
                <Ionicons
                  name={forma.icon}
                  size={20}
                  color={formaPagamento === forma.key ? CORES.primario : CORES.textoSecundario}
                />
                <Text style={[styles.formaTexto, formaPagamento === forma.key && styles.formaTextoAtivo]}>
                  {forma.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {formaPagamento === "dinheiro" ? (
            <>
              <Text style={styles.label}>Valor recebido</Text>
              <TextInput
                value={valorRecebido}
                onChangeText={setValorRecebido}
                placeholder="Ex: 100,00"
                keyboardType="decimal-pad"
                style={styles.input}
              />
              <Text style={styles.troco}>Troco: {formatarMoeda(troco)}</Text>
            </>
          ) : null}

          <Text style={styles.label}>Observacao</Text>
          <TextInput
            value={observacoes}
            onChangeText={setObservacoes}
            placeholder="Opcional"
            style={[styles.input, styles.inputMultilinha]}
            multiline
          />
        </View>

        <View style={styles.resumo}>
          <View>
            <Text style={styles.resumoLabel}>Total da venda</Text>
            <Text style={styles.resumoValor}>{formatarMoeda(total)}</Text>
          </View>
          <TouchableOpacity
            style={[styles.botaoFinalizar, (finalizando || !carrinho.length || !caixa?.aberto) && styles.botaoDesabilitado]}
            onPress={finalizar}
            disabled={finalizando || !carrinho.length || !caixa?.aberto}
          >
            {finalizando ? <ActivityIndicator color="#fff" /> : <Ionicons name="checkmark-circle" size={20} color="#fff" />}
            <Text style={styles.botaoFinalizarTexto}>Finalizar</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  conteudo: { padding: ESPACO.md, gap: ESPACO.md, paddingBottom: ESPACO.xxl },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", padding: ESPACO.lg, backgroundColor: CORES.fundo },
  tituloPermissao: { fontSize: FONTE.titulo, fontWeight: "800", color: CORES.texto, marginVertical: ESPACO.md },
  botaoPrimario: {
    height: 48,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primario,
    paddingHorizontal: ESPACO.lg,
    alignItems: "center",
    justifyContent: "center",
  },
  botaoPrimarioTexto: { color: "#fff", fontWeight: "800", fontSize: FONTE.media },
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
    backgroundColor: CORES.primarioClaro,
    alignItems: "center",
    justifyContent: "center",
    marginRight: ESPACO.md,
  },
  titulo: { fontSize: FONTE.titulo, fontWeight: "800", color: CORES.texto },
  subtitulo: { fontSize: FONTE.normal, color: CORES.textoSecundario, marginTop: 2 },
  botaoAtualizarCaixa: {
    width: 40,
    height: 40,
    borderRadius: RAIO.circulo,
    backgroundColor: CORES.primarioClaro,
    alignItems: "center",
    justifyContent: "center",
  },
  caixaBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
  },
  caixaAberto: { backgroundColor: "#ECFDF5", borderColor: "#BBF7D0" },
  caixaFechado: { backgroundColor: "#FFFBEB", borderColor: "#FDE68A" },
  caixaTexto: { flex: 1, color: CORES.texto, fontSize: FONTE.normal, fontWeight: "700" },
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
    backgroundColor: CORES.primario,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
  },
  botaoScanTexto: { color: "#fff", fontWeight: "800", fontSize: FONTE.media },
  buscaLinha: { flexDirection: "row", gap: ESPACO.sm },
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
  sugestaoNome: { fontSize: FONTE.normal, fontWeight: "800", color: CORES.texto },
  sugestaoMeta: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  linhaTitulo: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  secaoTitulo: { fontSize: FONTE.grande, fontWeight: "800", color: CORES.texto },
  badge: {
    backgroundColor: CORES.primarioClaro,
    color: CORES.primario,
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.xs,
    fontWeight: "800",
    overflow: "hidden",
  },
  vazio: { alignItems: "center", paddingVertical: ESPACO.lg },
  vazioTexto: { marginTop: ESPACO.sm, color: CORES.textoSecundario, fontSize: FONTE.normal },
  itemCarrinho: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    borderTopWidth: 1,
    borderTopColor: CORES.borda,
    paddingTop: ESPACO.sm,
  },
  itemNome: { fontSize: FONTE.normal, fontWeight: "800", color: CORES.texto },
  itemMeta: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  quantidadeBox: { flexDirection: "row", alignItems: "center", borderWidth: 1, borderColor: CORES.borda, borderRadius: RAIO.md },
  botaoQuantidade: { width: 34, height: 38, alignItems: "center", justifyContent: "center" },
  inputQuantidade: {
    width: 48,
    height: 38,
    textAlign: "center",
    color: CORES.texto,
    fontWeight: "800",
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: CORES.borda,
  },
  itemSubtotal: { width: 82, textAlign: "right", fontWeight: "800", color: CORES.texto },
  clienteSelecionado: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#BBF7D0",
    backgroundColor: "#ECFDF5",
    borderRadius: RAIO.md,
    padding: ESPACO.md,
  },
  clienteNome: { fontSize: FONTE.media, fontWeight: "800", color: CORES.texto },
  clienteMeta: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  botaoLimpar: {
    width: 36,
    height: 36,
    borderRadius: RAIO.circulo,
    backgroundColor: "#FEE2E2",
    alignItems: "center",
    justifyContent: "center",
  },
  formasGrid: { flexDirection: "row", flexWrap: "wrap", gap: ESPACO.sm },
  formaBotao: {
    flexGrow: 1,
    minWidth: "46%",
    height: 52,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
    backgroundColor: "#fff",
  },
  formaBotaoAtivo: { borderColor: CORES.primario, backgroundColor: CORES.primarioClaro },
  formaTexto: { color: CORES.textoSecundario, fontWeight: "800" },
  formaTextoAtivo: { color: CORES.primario },
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
  inputMultilinha: { minHeight: 80, textAlignVertical: "top" },
  troco: { color: CORES.sucesso, fontWeight: "800", fontSize: FONTE.media },
  resumo: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: ESPACO.md,
    ...SOMBRA,
  },
  resumoLabel: { color: CORES.textoSecundario, fontSize: FONTE.pequena, fontWeight: "700" },
  resumoValor: { color: CORES.texto, fontSize: FONTE.titulo, fontWeight: "900", marginTop: 2 },
  botaoFinalizar: {
    minWidth: 150,
    height: 52,
    borderRadius: RAIO.md,
    backgroundColor: CORES.sucesso,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
  },
  botaoDesabilitado: { opacity: 0.5 },
  botaoFinalizarTexto: { color: "#fff", fontSize: FONTE.media, fontWeight: "900" },
  scannerContainer: { flex: 1, backgroundColor: "#000" },
  camera: { flex: 1 },
  scannerOverlay: { flex: 1, alignItems: "center", justifyContent: "center", padding: ESPACO.lg },
  fecharScanner: {
    position: "absolute",
    top: 54,
    right: 24,
    width: 44,
    height: 44,
    borderRadius: RAIO.circulo,
    backgroundColor: "rgba(0,0,0,0.45)",
    alignItems: "center",
    justifyContent: "center",
  },
  frameScan: {
    width: "82%",
    height: 180,
    borderWidth: 3,
    borderColor: "#fff",
    borderRadius: RAIO.lg,
    backgroundColor: "rgba(255,255,255,0.08)",
  },
  scannerTexto: { color: "#fff", marginTop: ESPACO.md, fontSize: FONTE.media, fontWeight: "800", textAlign: "center" },
  botaoScanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    marginTop: ESPACO.md,
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
  },
  botaoScannerTexto: { color: "#fff", fontWeight: "800" },
});
