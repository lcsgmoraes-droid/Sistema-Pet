import { Ionicons } from "@expo/vector-icons";
import { CameraView, useCameraPermissions } from "expo-camera";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { TenantInfo, useTenantStore } from "../store/tenant.store";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../theme";

export default function SelecionarLojaScreen() {
  const { buscarPorSlug, confirmarTenant } = useTenantStore();

  const [slug, setSlug] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [lojaPrevia, setLojaPrevia] = useState<TenantInfo | null>(null);
  const [qrAberto, setQrAberto] = useState(false);
  const [qrLido, setQrLido] = useState(false);

  const [cameraPermission, requestCameraPermission] = useCameraPermissions();

  // ─── Buscar loja pelo slug ───────────────────────────────────────────────

  async function buscarLoja(slugDigitado: string) {
    if (!slugDigitado.trim()) {
      Alert.alert("Campo obrigatório", "Digite o código ou URL da sua loja.");
      return;
    }
    setCarregando(true);
    setLojaPrevia(null);
    try {
      // Só consulta, não salva ainda — aguarda confirmação do usuário
      const loja = await buscarPorSlug(slugDigitado);
      setLojaPrevia(loja);
    } catch (err: any) {
      Alert.alert(
        "Loja não encontrada",
        err?.message || "Verifique o código da loja e tente novamente.",
        [{ text: "OK" }],
      );
    } finally {
      setCarregando(false);
    }
  }

  // ─── Confirmar loja já encontrada ───────────────────────────────────────

  async function confirmarLoja() {
    if (!lojaPrevia) return;
    setCarregando(true);
    try {
      // Agora salva no SecureStore e atualiza o store — AppNavigator vai navegar
      await confirmarTenant(lojaPrevia);
    } catch (err: any) {
      Alert.alert("Erro", "Não foi possível vincular a loja. Tente novamente.");
    } finally {
      setCarregando(false);
    }
  }

  // ─── QR Code ─────────────────────────────────────────────────────────────

  async function abrirScanner() {
    if (!cameraPermission?.granted) {
      const result = await requestCameraPermission();
      if (!result.granted) {
        Alert.alert(
          "Permissão necessária",
          "Permita o acesso à câmera para escanear o QR Code da sua loja.",
          [{ text: "OK" }],
        );
        return;
      }
    }
    setQrLido(false);
    setQrAberto(true);
  }

  function onBarcodeScanned({ data }: { data: string }) {
    if (qrLido) return;
    setQrLido(true);
    setQrAberto(false);
    const slugExtraido = data
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\/[^/]+\/?/, "")
      .replace(/^\//, "")
      .split("/")[0]
      .split("?")[0];
    setSlug(slugExtraido);
    buscarLoja(slugExtraido);
  }

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
      >
        {/* Logo / Ícone */}
        <View style={styles.heroArea}>
          <View style={styles.iconeCirculo}>
            <Text style={styles.iconeEmoji}>🐾</Text>
          </View>
          <Text style={styles.titulo}>Bem-vindo!</Text>
          <Text style={styles.subtitulo}>
            Para começar, vincule o app à sua loja petshop.
          </Text>
        </View>

        {/* Card de entrada */}
        <View style={styles.card}>
          <Text style={styles.label}>Código ou URL da loja</Text>
          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              placeholder="ex: atacadao"
              placeholderTextColor={CORES.textoClaro}
              value={slug}
              onChangeText={(t) => {
                setSlug(t);
                setLojaPrevia(null);
              }}
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="search"
              onSubmitEditing={() => buscarLoja(slug)}
            />
            <TouchableOpacity
              style={styles.botaoQr}
              onPress={abrirScanner}
              activeOpacity={0.7}
            >
              <Ionicons
                name="qr-code-outline"
                size={24}
                color={CORES.primario}
              />
            </TouchableOpacity>
          </View>

          <Text style={styles.dica}>
            Peça o código ou QR Code ao responsável da sua loja.
          </Text>

          <TouchableOpacity
            style={[styles.botaoBuscar, carregando && styles.botaoDesabilitado]}
            onPress={() => buscarLoja(slug)}
            disabled={carregando}
            activeOpacity={0.8}
          >
            {carregando ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.botaoBuscarTexto}>Buscar loja</Text>
            )}
          </TouchableOpacity>
        </View>

        {/* Preview da loja encontrada */}
        {lojaPrevia && (
          <View style={styles.cardLoja}>
            {lojaPrevia.logo_url ? (
              <Image
                source={{ uri: lojaPrevia.logo_url }}
                style={styles.lojaLogo}
                resizeMode="contain"
              />
            ) : (
              <View style={styles.lojaLogoPlaceholder}>
                <Text style={{ fontSize: 36 }}>🏪</Text>
              </View>
            )}
            <Text style={styles.lojaNome}>{lojaPrevia.nome}</Text>
            {lojaPrevia.cidade ? (
              <Text style={styles.lojaCidade}>
                {lojaPrevia.cidade}
                {lojaPrevia.uf ? ` — ${lojaPrevia.uf}` : ""}
              </Text>
            ) : null}

            <TouchableOpacity
              style={styles.botaoConfirmar}
              onPress={confirmarLoja}
              activeOpacity={0.8}
            >
              <Ionicons name="checkmark-circle" size={20} color="#fff" />
              <Text style={styles.botaoConfirmarTexto}>Entrar nesta loja</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.botaoCancelar}
              onPress={() => {
                setLojaPrevia(null);
                setSlug("");
              }}
            >
              <Text style={styles.botaoCancelarTexto}>Escolher outra loja</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>

      {/* Modal de Scanner QR */}
      <Modal
        visible={qrAberto}
        animationType="slide"
        onRequestClose={() => setQrAberto(false)}
      >
        <View style={styles.scannerContainer}>
          <CameraView
            style={StyleSheet.absoluteFillObject}
            facing="back"
            barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
            onBarcodeScanned={onBarcodeScanned}
          />
          {/* Overlay com moldura */}
          <View style={styles.scannerOverlay}>
            <View style={styles.scannerMoldura} />
            <Text style={styles.scannerInstrucao}>
              Aponte para o QR Code da loja
            </Text>
          </View>
          <TouchableOpacity
            style={styles.botaoFecharScanner}
            onPress={() => setQrAberto(false)}
          >
            <Ionicons name="close-circle" size={44} color="#fff" />
          </TouchableOpacity>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: CORES.fundo ?? "#F5F5F5",
  },
  scroll: {
    flexGrow: 1,
    padding: ESPACO.md,
    paddingTop: 60,
    alignItems: "center",
  },

  // Hero
  heroArea: {
    alignItems: "center",
    marginBottom: ESPACO.xl ?? 32,
  },
  iconeCirculo: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: CORES.primario,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: ESPACO.md,
    ...(SOMBRA ?? {}),
  },
  iconeEmoji: {
    fontSize: 40,
  },
  titulo: {
    fontSize: FONTE.titulo ?? 26,
    fontWeight: "700",
    color: CORES.texto ?? "#1a1a1a",
    marginBottom: 8,
  },
  subtitulo: {
    fontSize: FONTE.media ?? 15,
    color: CORES.textoSecundario ?? "#555",
    textAlign: "center",
    lineHeight: 22,
    paddingHorizontal: 16,
  },

  // Card de entrada
  card: {
    width: "100%",
    backgroundColor: "#fff",
    borderRadius: RAIO.lg ?? 16,
    padding: ESPACO.lg ?? 24,
    marginBottom: ESPACO.md,
    ...(SOMBRA ?? {}),
  },
  label: {
    fontSize: FONTE.pequena ?? 13,
    fontWeight: "600",
    color: CORES.texto ?? "#1a1a1a",
    marginBottom: 8,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  input: {
    flex: 1,
    height: 50,
    borderWidth: 1.5,
    borderColor: CORES.borda ?? "#ddd",
    borderRadius: RAIO.md ?? 10,
    paddingHorizontal: 14,
    fontSize: FONTE.media ?? 15,
    color: CORES.texto ?? "#1a1a1a",
    backgroundColor: "#FAFAFA",
  },
  botaoQr: {
    width: 50,
    height: 50,
    borderWidth: 1.5,
    borderColor: CORES.primario,
    borderRadius: RAIO.md ?? 10,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EEF2FF",
  },
  dica: {
    fontSize: FONTE.pequena ?? 12,
    color: CORES.textoClaro ?? "#888",
    marginTop: 8,
    marginBottom: 20,
  },
  botaoBuscar: {
    backgroundColor: CORES.primario,
    height: 50,
    borderRadius: RAIO.md ?? 10,
    alignItems: "center",
    justifyContent: "center",
  },
  botaoDesabilitado: {
    opacity: 0.6,
  },
  botaoBuscarTexto: {
    color: "#fff",
    fontSize: FONTE.media ?? 15,
    fontWeight: "700",
  },

  // Card de prévia da loja
  cardLoja: {
    width: "100%",
    backgroundColor: "#fff",
    borderRadius: RAIO.lg ?? 16,
    padding: ESPACO.lg ?? 24,
    alignItems: "center",
    borderWidth: 2,
    borderColor: CORES.primario,
    ...(SOMBRA ?? {}),
  },
  lojaLogo: {
    width: 80,
    height: 80,
    borderRadius: 12,
    marginBottom: 12,
  },
  lojaLogoPlaceholder: {
    width: 80,
    height: 80,
    borderRadius: 12,
    backgroundColor: "#F0F4FF",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  lojaNome: {
    fontSize: FONTE.grande ?? 18,
    fontWeight: "700",
    color: CORES.texto ?? "#1a1a1a",
    textAlign: "center",
    marginBottom: 4,
  },
  lojaCidade: {
    fontSize: FONTE.pequena ?? 13,
    color: CORES.textoSecundario ?? "#555",
    marginBottom: 20,
  },
  botaoConfirmar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: CORES.sucesso ?? "#22C55E",
    height: 50,
    borderRadius: RAIO.md ?? 10,
    paddingHorizontal: 24,
    width: "100%",
    justifyContent: "center",
    marginBottom: 10,
  },
  botaoConfirmarTexto: {
    color: "#fff",
    fontSize: FONTE.media ?? 15,
    fontWeight: "700",
  },
  botaoCancelar: {
    paddingVertical: 8,
  },
  botaoCancelarTexto: {
    color: CORES.textoClaro ?? "#888",
    fontSize: FONTE.pequena ?? 13,
  },

  // Scanner
  scannerContainer: {
    flex: 1,
    backgroundColor: "#000",
  },
  scannerOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
  },
  scannerMoldura: {
    width: 240,
    height: 240,
    borderWidth: 3,
    borderColor: "#fff",
    borderRadius: 16,
    backgroundColor: "transparent",
  },
  scannerInstrucao: {
    marginTop: 24,
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
    textAlign: "center",
    backgroundColor: "rgba(0,0,0,0.5)",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  botaoFecharScanner: {
    position: "absolute",
    top: 50,
    right: 20,
  },
});
