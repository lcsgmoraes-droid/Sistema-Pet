import { Ionicons } from "@expo/vector-icons";
import { useIsFocused } from "@react-navigation/native";
import { CameraView, useCameraPermissions } from "expo-camera";
import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator, Alert, Keyboard, Linking, Modal, StyleSheet,
  Text, TextInput, TouchableOpacity, Vibration, View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import KeyboardSafeScrollView from "../../../components/KeyboardSafeScrollView";
import {
  atualizarCadastroProdutoFuncionario, obterCadastroProdutoFuncionario,
  ProdutoCadastro, ProdutoCadastroPayload,
} from "../../../services/funcionarioProdutos.service";
import { CORES, ESPACO, FONTE, RAIO } from "../../../theme";
import { erroCadastroProduto } from "../../../utils/produtoRapido";

type Props = {
  produtoId: number;
  onClose: () => void;
  onSaved: (produto: ProdutoCadastro) => void;
};

export default function EditarProdutoBalanco({ produtoId, onClose, onSaved }: Props) {
  const isFocused = useIsFocused();
  const [permission, requestPermission] = useCameraPermissions();
  const [original, setOriginal] = useState<ProdutoCadastro | null>(null);
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [ean, setEan] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [tentativa, setTentativa] = useState(0);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [scannerAberto, setScannerAberto] = useState(false);
  const leituraAtiva = useRef(false);
  const salvamentoAtivo = useRef(false);
  const montado = useRef(true);

  useEffect(() => {
    montado.current = true;
    return () => { montado.current = false; };
  }, []);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setErro(null);
    obterCadastroProdutoFuncionario(produtoId).then((dados) => {
      if (!ativo) return;
      setOriginal(dados);
      setNome(dados.nome);
      setDescricao(dados.descricao_curta ?? "");
      setEan(dados.codigo_barras ?? "");
    }).catch((error) => {
      if (ativo) setErro(erroCadastroProduto(error, "Não foi possível carregar o cadastro."));
    }).finally(() => { if (ativo) setCarregando(false); });
    return () => { ativo = false; };
  }, [produtoId, tentativa]);

  useEffect(() => {
    if (!isFocused) {
      leituraAtiva.current = false;
      setScannerAberto(false);
    }
  }, [isFocused]);

  function fecharScanner() {
    leituraAtiva.current = false;
    setScannerAberto(false);
  }

  function fechar() {
    if (salvamentoAtivo.current) return;
    if (scannerAberto) fecharScanner();
    else onClose();
  }

  async function abrirCamera() {
    Keyboard.dismiss();
    try {
      const acesso = permission?.granted ? permission : await requestPermission();
      if (!montado.current) return;
      if (!acesso.granted) {
        Alert.alert("Acesso à câmera", "Permita o acesso à câmera nas configurações ou digite o código de barras.", [
          { text: "Digitar código", style: "cancel" },
          { text: "Abrir configurações", onPress: () => { void Linking.openSettings(); } },
        ]);
        return;
      }
      leituraAtiva.current = true;
      setScannerAberto(true);
    } catch {
      Alert.alert("Câmera indisponível", "Você pode digitar o código de barras no campo EAN.");
    }
  }

  function lerCodigo({ data }: { data: string }) {
    if (!leituraAtiva.current) return;
    leituraAtiva.current = false;
    const codigo = data.trim();
    if (!codigo || codigo.length > 20 || !/^[A-Za-z0-9 ._/-]+$/.test(codigo)) {
      fecharScanner();
      Alert.alert("Código inválido", "Leia o código de barras do produto ou digite o código no campo EAN.");
      return;
    }
    setEan(codigo);
    fecharScanner();
    Vibration.vibrate(80);
  }

  async function salvar() {
    if (!original || salvamentoAtivo.current) return;
    if (!nome.trim()) {
      setErro("Informe o nome do produto.");
      return;
    }
    if (ean.trim() && !/^[A-Za-z0-9 ._/-]{1,20}$/.test(ean.trim())) {
      setErro("Informe um código de barras válido, com até 20 caracteres.");
      return;
    }
    const payload: ProdutoCadastroPayload = {};
    if (nome.trim() !== original.nome) payload.nome = nome.trim();
    if ((descricao.trim() || null) !== original.descricao_curta) payload.descricao_curta = descricao.trim() || null;
    if ((ean.trim() || null) !== original.codigo_barras) payload.codigo_barras = ean.trim() || null;
    if (!Object.keys(payload).length) { onClose(); return; }
    salvamentoAtivo.current = true;
    setSalvando(true);
    setErro(null);
    try {
      const atualizado = await atualizarCadastroProdutoFuncionario(produtoId, payload);
      if (montado.current) onSaved(atualizado);
    } catch (error) {
      if (montado.current) setErro(erroCadastroProduto(error, "Não foi possível salvar. Confira a conexão e tente novamente."));
    } finally {
      salvamentoAtivo.current = false;
      if (montado.current) setSalvando(false);
    }
  }

  return (
    <Modal visible animationType="slide" presentationStyle="fullScreen" onRequestClose={fechar}>
      <SafeAreaView style={styles.container}>
        <View style={styles.cabecalho}>
          <Text style={styles.titulo}>{scannerAberto ? "Ler EAN" : "Editar cadastro"}</Text>
          <TouchableOpacity accessibilityRole="button" accessibilityLabel={scannerAberto ? "Voltar para edição" : "Cancelar edição"}
            onPress={fechar} disabled={salvando} style={styles.fechar}>
            <Ionicons name="close" size={26} color={CORES.texto} />
          </TouchableOpacity>
        </View>
        {scannerAberto && isFocused && permission?.granted ? (
          <View style={styles.scanner}>
            <CameraView style={StyleSheet.absoluteFill} facing="back" onBarcodeScanned={lerCodigo}
              barcodeScannerSettings={{ barcodeTypes: ["ean13", "ean8", "upc_a", "upc_e", "code128", "code39"] }}
              onMountError={() => {
                fecharScanner();
                Alert.alert("Câmera indisponível", "Digite o código no campo EAN ou tente abrir a câmera novamente.");
              }} />
            <View pointerEvents="none" style={styles.overlay}>
              <View style={styles.moldura} />
              <Text style={styles.instrucao}>Aponte para o código de barras do produto.</Text>
              <Text style={styles.instrucao}>O código será preenchido para você conferir e salvar.</Text>
            </View>
          </View>
        ) : carregando ? (
          <View style={styles.centrado}><ActivityIndicator color={CORES.primario} /><Text>Carregando cadastro...</Text></View>
        ) : (
          <KeyboardSafeScrollView contentContainerStyle={styles.conteudo}>
            {original ? (
              <>
                <Text style={styles.ajuda}>SKU {original.codigo || "—"} · As alterações serão salvas no cadastro do ERP.</Text>
                <Text style={styles.label}>Nome do produto</Text>
                <TextInput accessibilityLabel="Nome do produto" value={nome} onChangeText={setNome} maxLength={200}
                  editable={!salvando} style={styles.input} placeholder="Nome / descrição do produto" />
                <Text style={styles.label}>EAN / código de barras</Text>
                <View style={styles.linhaEan}>
                  <TextInput accessibilityLabel="EAN / código de barras" value={ean} onChangeText={setEan} maxLength={20}
                    editable={!salvando} autoCapitalize="none" autoCorrect={false} placeholder="Adicionar ou corrigir código"
                    style={[styles.input, styles.campoEan]} />
                  <TouchableOpacity accessibilityRole="button" accessibilityLabel="Ler EAN com a câmera"
                    style={styles.camera} onPress={abrirCamera} disabled={salvando}>
                    <Ionicons name="camera-outline" size={26} color="#fff" />
                  </TouchableOpacity>
                </View>
                <Text style={styles.ajuda}>Digite o código ou toque na câmera para ler a embalagem.</Text>
                <Text style={styles.label}>Descrição complementar</Text>
                <TextInput accessibilityLabel="Descrição complementar" value={descricao} onChangeText={setDescricao}
                  maxLength={1000} editable={!salvando} multiline placeholder="Opcional"
                  style={[styles.input, styles.multilinha]} />
              </>
            ) : null}
            {erro ? <Text accessibilityRole="alert" style={styles.erro}>{erro}</Text> : null}
            {original ? (
              <TouchableOpacity accessibilityRole="button" style={[styles.salvar, salvando && styles.desabilitado]}
                onPress={salvar} disabled={salvando}>
                {salvando ? <ActivityIndicator color="#fff" /> : <Ionicons name="checkmark-circle-outline" size={22} color="#fff" />}
                <Text style={styles.textoSalvar}>{salvando ? "Salvando..." : "Salvar cadastro"}</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity style={styles.salvar} onPress={() => setTentativa((valor) => valor + 1)}>
                <Text style={styles.textoSalvar}>Tentar novamente</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity accessibilityRole="button" style={styles.cancelar} onPress={fechar} disabled={salvando}>
              <Text style={styles.textoCancelar}>Cancelar</Text>
            </TouchableOpacity>
          </KeyboardSafeScrollView>
        )}
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  cabecalho: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: ESPACO.md },
  titulo: { flex: 1, fontSize: FONTE.titulo, fontWeight: "800", color: CORES.texto },
  fechar: { padding: ESPACO.sm, minWidth: 44, minHeight: 44, alignItems: "center", justifyContent: "center" },
  conteudo: { padding: ESPACO.md, paddingBottom: ESPACO.xxl, gap: ESPACO.sm },
  centrado: { flex: 1, justifyContent: "center", alignItems: "center", gap: ESPACO.md },
  label: { marginTop: ESPACO.sm, fontWeight: "700", fontSize: FONTE.normal, color: CORES.texto },
  ajuda: { color: CORES.textoSecundario, fontSize: FONTE.normal },
  input: { minHeight: 50, borderWidth: 1, borderColor: CORES.borda, borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md, paddingVertical: ESPACO.sm, backgroundColor: "#fff", color: CORES.texto, fontSize: FONTE.normal },
  linhaEan: { flexDirection: "row", gap: ESPACO.sm, alignItems: "center" },
  campoEan: { flex: 1 },
  camera: { width: 52, height: 52, borderRadius: RAIO.md, alignItems: "center", justifyContent: "center", backgroundColor: CORES.primario },
  multilinha: { minHeight: 112, textAlignVertical: "top" },
  salvar: { minHeight: 52, padding: ESPACO.md, marginTop: ESPACO.md, flexDirection: "row", gap: ESPACO.sm,
    alignItems: "center", justifyContent: "center", backgroundColor: CORES.sucesso, borderRadius: RAIO.md },
  textoSalvar: { fontSize: FONTE.media, color: "#fff", fontWeight: "800" },
  cancelar: { minHeight: 48, alignItems: "center", justifyContent: "center" },
  textoCancelar: { color: CORES.textoSecundario, fontSize: FONTE.normal, fontWeight: "700" },
  erro: { color: CORES.erro, fontSize: FONTE.normal, marginTop: ESPACO.sm },
  desabilitado: { opacity: 0.6 },
  scanner: { flex: 1, backgroundColor: "#000" },
  overlay: { flex: 1, alignItems: "center", justifyContent: "center", padding: ESPACO.lg, gap: ESPACO.md, backgroundColor: "rgba(0,0,0,0.25)" },
  moldura: { width: "90%", height: 170, borderWidth: 3, borderColor: "#fff", borderRadius: RAIO.md },
  instrucao: { color: "#fff", textAlign: "center", fontSize: FONTE.media, fontWeight: "700" },
});
