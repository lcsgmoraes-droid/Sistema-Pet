import { Ionicons } from "@expo/vector-icons";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as Location from "expo-location";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  Modal,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import KeyboardSafeScrollView from "../components/KeyboardSafeScrollView";
import {
  extractStoreSlug,
  resolveTenantAssetUrl,
  TenantInfo,
  useTenantStore,
} from "../store/tenant.store";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../theme";

const LOCATION_LOOKUP_TIMEOUT_MS = 6500;
const GEOCODE_LOOKUP_TIMEOUT_MS = 4500;
const LAST_POSITION_MAX_AGE_MS = 10 * 60 * 1000;

function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  message: string,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(message)), timeoutMs);
    promise
      .then(resolve)
      .catch(reject)
      .finally(() => clearTimeout(timer));
  });
}

function StoreLogo({
  store,
  size = 48,
}: {
  store: TenantInfo;
  size?: number;
}) {
  const imageUrl = resolveTenantAssetUrl(store.imagem_url ?? store.logo_url);
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setImageFailed(false);
  }, [imageUrl]);

  return (
    <View
      style={[
        styles.logoBox,
        { width: size, height: size, borderRadius: Math.min(12, size / 4) },
      ]}
    >
      {imageUrl && !imageFailed ? (
        <Image
          source={{ uri: imageUrl }}
          style={{ width: size - 6, height: size - 6 }}
          resizeMode={store.logo_url ? "contain" : "cover"}
          onError={() => setImageFailed(true)}
        />
      ) : (
        <Ionicons
          name="storefront-outline"
          size={Math.round(size * 0.52)}
          color={CORES.primario}
        />
      )}
    </View>
  );
}

export default function SelecionarLojaScreen() {
  const { buscarPorSlug, buscarPorNome, buscarProximas, confirmarTenant } =
    useTenantStore();
  const [termo, setTermo] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [buscandoLocalizacao, setBuscandoLocalizacao] = useState(false);
  const [lojaPrevia, setLojaPrevia] = useState<TenantInfo | null>(null);
  const [lojasEncontradas, setLojasEncontradas] = useState<TenantInfo[]>([]);
  const [tituloResultados, setTituloResultados] = useState("Lojas encontradas");
  const [qrAberto, setQrAberto] = useState(false);
  const [qrLido, setQrLido] = useState(false);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();

  function selecionarResultado(loja: TenantInfo) {
    setLojaPrevia(loja);
    setTermo(loja.slug);
    setLojasEncontradas([]);
  }

  async function buscarLoja(valor: string) {
    const consulta = valor.trim();
    if (!consulta) {
      Alert.alert("Campo obrigatorio", "Digite o nome, codigo ou URL da loja.");
      return;
    }

    setCarregando(true);
    setLojaPrevia(null);
    setLojasEncontradas([]);
    try {
      try {
        const loja = await buscarPorSlug(consulta);
        setLojaPrevia(loja);
        return;
      } catch {
        const lojas = await buscarPorNome(consulta);
        if (lojas.length === 1) {
          setLojaPrevia(lojas[0]);
          return;
        }
        if (lojas.length > 1) {
          setTituloResultados("Lojas encontradas");
          setLojasEncontradas(lojas);
          return;
        }
      }

      Alert.alert(
        "Loja nao encontrada",
        "Verifique o nome, codigo ou URL da loja e tente novamente.",
      );
    } finally {
      setCarregando(false);
    }
  }

  async function buscarPorLocalizacao() {
    setBuscandoLocalizacao(true);
    setLojaPrevia(null);
    setLojasEncontradas([]);

    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (!permission.granted) {
        Alert.alert(
          "Permissao necessaria",
          "Permita o acesso a localizacao para sugerirmos lojas perto de voce.",
        );
        return;
      }

      const posicao =
        (await Location.getLastKnownPositionAsync({
          maxAge: LAST_POSITION_MAX_AGE_MS,
          requiredAccuracy: 5000,
        }).catch(() => null)) ||
        (await withTimeout(
          Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.Low,
          }),
          LOCATION_LOOKUP_TIMEOUT_MS,
          "Tempo excedido ao obter localizacao.",
        ));

      let cidade: string | null = null;
      let uf: string | null = null;
      try {
        const geocode = await withTimeout(
          Location.reverseGeocodeAsync(posicao.coords),
          GEOCODE_LOOKUP_TIMEOUT_MS,
          "Tempo excedido ao identificar cidade.",
        );
        const endereco = geocode[0];
        cidade =
          endereco?.city || endereco?.subregion || endereco?.district || null;
        const region = endereco?.region?.trim() || "";
        uf = region.length === 2 ? region : null;
      } catch {
        // Latitude e longitude continuam suficientes para a busca principal.
      }

      const lojas = await buscarProximas(
        posicao.coords.latitude,
        posicao.coords.longitude,
        cidade,
        uf,
      );
      if (lojas.length === 0) {
        Alert.alert(
          "Nenhuma loja sugerida",
          "Nao encontramos lojas proximas. Use o nome, QR Code ou codigo da loja.",
        );
        return;
      }

      setTituloResultados("Lojas mais proximas");
      setLojasEncontradas(lojas);
    } catch {
      Alert.alert(
        "Erro",
        "Nao foi possivel buscar lojas pela sua localizacao agora.",
      );
    } finally {
      setBuscandoLocalizacao(false);
    }
  }

  async function confirmarLoja() {
    if (!lojaPrevia) return;
    setCarregando(true);
    try {
      await confirmarTenant(lojaPrevia);
    } catch {
      Alert.alert("Erro", "Nao foi possivel vincular a loja. Tente novamente.");
    } finally {
      setCarregando(false);
    }
  }

  async function abrirScanner() {
    if (!cameraPermission?.granted) {
      const result = await requestCameraPermission();
      if (!result.granted) {
        Alert.alert(
          "Permissao necessaria",
          "Permita o acesso a camera para escanear o QR Code da sua loja.",
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
    const slug = extractStoreSlug(data);
    setTermo(slug);
    void buscarLoja(slug);
  }

  return (
    <View style={styles.container}>
      <KeyboardSafeScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.heroArea}>
          <View style={styles.iconeCirculo}>
            <Image
              source={require("../../assets/icon.png")}
              style={styles.iconeLogo}
            />
          </View>
          <Text style={styles.titulo}>Bem-vindo ao CorePet</Text>
          <Text style={styles.subtitulo}>
            Para comecar, selecione a loja que voce deseja acessar.
          </Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.label}>Nome, codigo ou URL da loja</Text>
          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              placeholder="Ex.: Atacadao das Racoes"
              placeholderTextColor={CORES.textoClaro}
              value={termo}
              onChangeText={(value) => {
                setTermo(value);
                setLojaPrevia(null);
                setLojasEncontradas([]);
              }}
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="search"
              onSubmitEditing={() => void buscarLoja(termo)}
            />
            <TouchableOpacity
              style={styles.botaoQr}
              onPress={abrirScanner}
              activeOpacity={0.7}
              accessibilityLabel="Ler QR Code da loja"
            >
              <Ionicons name="qr-code-outline" size={24} color={CORES.primario} />
            </TouchableOpacity>
          </View>

          <Text style={styles.dica}>
            Pesquise pelo nome ou use o codigo e QR Code fornecidos pela loja.
          </Text>

          <TouchableOpacity
            style={[
              styles.botaoLocalizacao,
              buscandoLocalizacao && styles.botaoDesabilitado,
            ]}
            onPress={buscarPorLocalizacao}
            disabled={buscandoLocalizacao}
            activeOpacity={0.8}
          >
            {buscandoLocalizacao ? (
              <ActivityIndicator color={CORES.primario} />
            ) : (
              <>
                <Ionicons
                  name="location-outline"
                  size={18}
                  color={CORES.primario}
                />
                <Text style={styles.botaoLocalizacaoTexto}>
                  Ver lojas mais proximas
                </Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.botaoBuscar,
              carregando && styles.botaoDesabilitado,
            ]}
            onPress={() => void buscarLoja(termo)}
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

        {lojasEncontradas.length > 0 ? (
          <View style={styles.cardResultados}>
            <Text style={styles.resultadosTitulo}>{tituloResultados}</Text>
            {lojasEncontradas.map((loja) => (
              <TouchableOpacity
                key={loja.id}
                style={styles.resultadoItem}
                onPress={() => selecionarResultado(loja)}
                activeOpacity={0.75}
              >
                <StoreLogo store={loja} />
                <View style={styles.resultadoInfo}>
                  <Text style={styles.resultadoNome} numberOfLines={1}>
                    {loja.nome}
                  </Text>
                  <Text style={styles.resultadoEndereco} numberOfLines={2}>
                    {[loja.endereco, loja.numero].filter(Boolean).join(", ")}
                    {loja.bairro ? ` - ${loja.bairro}` : ""}
                    {loja.cidade
                      ? ` - ${loja.cidade}${loja.uf ? `/${loja.uf}` : ""}`
                      : ""}
                  </Text>
                  {typeof loja.distancia_km === "number" ? (
                    <Text style={styles.resultadoDistancia}>
                      {loja.distancia_km.toLocaleString("pt-BR", {
                        maximumFractionDigits: 1,
                      })}{" "}
                      km de distancia
                    </Text>
                  ) : null}
                </View>
                <Ionicons
                  name="chevron-forward"
                  size={18}
                  color={CORES.textoClaro}
                />
              </TouchableOpacity>
            ))}
          </View>
        ) : null}

        {lojaPrevia ? (
          <View style={styles.cardLoja}>
            <StoreLogo store={lojaPrevia} size={76} />
            <Text style={styles.lojaNome}>{lojaPrevia.nome}</Text>
            {lojaPrevia.cidade ? (
              <Text style={styles.lojaCidade}>
                {lojaPrevia.cidade}
                {lojaPrevia.uf ? ` - ${lojaPrevia.uf}` : ""}
              </Text>
            ) : null}
            {lojaPrevia.endereco ? (
              <Text style={styles.lojaEndereco}>
                {[lojaPrevia.endereco, lojaPrevia.numero]
                  .filter(Boolean)
                  .join(", ")}
                {lojaPrevia.bairro ? ` - ${lojaPrevia.bairro}` : ""}
              </Text>
            ) : null}

            <TouchableOpacity
              style={styles.botaoConfirmar}
              onPress={() => void confirmarLoja()}
              activeOpacity={0.8}
            >
              <Ionicons name="checkmark-circle" size={20} color="#fff" />
              <Text style={styles.botaoConfirmarTexto}>Entrar nesta loja</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.botaoCancelar}
              onPress={() => {
                setLojaPrevia(null);
                setTermo("");
              }}
            >
              <Text style={styles.botaoCancelarTexto}>Escolher outra loja</Text>
            </TouchableOpacity>
          </View>
        ) : null}
      </KeyboardSafeScrollView>

      <Modal
        visible={qrAberto}
        animationType="slide"
        onRequestClose={() => setQrAberto(false)}
      >
        <View style={styles.scannerContainer}>
          <CameraView
            style={StyleSheet.absoluteFill}
            facing="back"
            barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
            onBarcodeScanned={onBarcodeScanned}
          />
          <View style={styles.scannerOverlay}>
            <View style={styles.scannerMoldura} />
            <Text style={styles.scannerInstrucao}>
              Aponte para o QR Code da loja
            </Text>
          </View>
          <TouchableOpacity
            style={styles.botaoFecharScanner}
            onPress={() => setQrAberto(false)}
            accessibilityLabel="Fechar leitor"
          >
            <Ionicons name="close-circle" size={44} color="#fff" />
          </TouchableOpacity>
        </View>
      </Modal>
    </View>
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
    paddingTop: 52,
    alignItems: "center",
  },
  heroArea: {
    alignItems: "center",
    marginBottom: ESPACO.xl ?? 32,
  },
  iconeCirculo: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: CORES.superficie,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    ...(SOMBRA ?? {}),
  },
  iconeLogo: {
    width: 74,
    height: 74,
    borderRadius: 20,
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
    backgroundColor: "#ECF8F7",
  },
  dica: {
    fontSize: FONTE.pequena ?? 12,
    color: CORES.textoClaro ?? "#888",
    marginTop: 8,
    marginBottom: 18,
    lineHeight: 17,
  },
  botaoLocalizacao: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderWidth: 1.5,
    borderColor: CORES.primario,
    minHeight: 48,
    borderRadius: RAIO.md ?? 10,
    marginBottom: 10,
    backgroundColor: "#ECF8F7",
    paddingHorizontal: 12,
  },
  botaoLocalizacaoTexto: {
    color: CORES.primario,
    fontSize: FONTE.normal ?? 14,
    fontWeight: "700",
    flexShrink: 1,
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
  cardResultados: {
    width: "100%",
    backgroundColor: "#fff",
    borderRadius: RAIO.lg ?? 16,
    padding: ESPACO.md,
    marginBottom: ESPACO.md,
    ...(SOMBRA ?? {}),
  },
  resultadosTitulo: {
    fontSize: FONTE.normal ?? 14,
    fontWeight: "700",
    color: CORES.texto ?? "#1a1a1a",
    marginBottom: ESPACO.sm,
  },
  resultadoItem: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: CORES.borda ?? "#ddd",
    borderRadius: RAIO.md ?? 10,
    padding: ESPACO.sm,
    marginBottom: ESPACO.xs,
    gap: 10,
  },
  logoBox: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: CORES.borda ?? "#ddd",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
    flexShrink: 0,
  },
  resultadoInfo: {
    flex: 1,
    minWidth: 0,
  },
  resultadoNome: {
    fontSize: FONTE.normal ?? 14,
    fontWeight: "700",
    color: CORES.texto ?? "#1a1a1a",
  },
  resultadoEndereco: {
    fontSize: FONTE.pequena ?? 12,
    color: CORES.textoSecundario ?? "#666",
    marginTop: 2,
    lineHeight: 16,
  },
  resultadoDistancia: {
    fontSize: FONTE.pequena ?? 12,
    color: CORES.primario,
    fontWeight: "700",
    marginTop: 4,
  },
  cardLoja: {
    width: "100%",
    backgroundColor: "#fff",
    borderRadius: RAIO.lg ?? 16,
    padding: ESPACO.lg ?? 24,
    alignItems: "center",
    ...(SOMBRA ?? {}),
  },
  lojaNome: {
    fontSize: FONTE.media ?? 20,
    fontWeight: "700",
    color: CORES.texto ?? "#1a1a1a",
    marginTop: ESPACO.md,
    textAlign: "center",
  },
  lojaCidade: {
    fontSize: FONTE.normal ?? 14,
    color: CORES.textoSecundario ?? "#555",
    marginTop: 4,
  },
  lojaEndereco: {
    fontSize: FONTE.pequena ?? 12,
    color: CORES.textoSecundario ?? "#666",
    textAlign: "center",
    marginTop: 5,
    lineHeight: 17,
  },
  botaoConfirmar: {
    width: "100%",
    height: 50,
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md ?? 10,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginTop: ESPACO.lg,
  },
  botaoConfirmarTexto: {
    color: "#fff",
    fontWeight: "700",
    fontSize: FONTE.media ?? 15,
  },
  botaoCancelar: {
    paddingVertical: 14,
  },
  botaoCancelarTexto: {
    color: CORES.primario,
    fontWeight: "600",
  },
  scannerContainer: {
    flex: 1,
    backgroundColor: "#000",
  },
  scannerOverlay: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    alignItems: "center",
    justifyContent: "center",
  },
  scannerMoldura: {
    width: 250,
    height: 250,
    borderWidth: 3,
    borderColor: "#fff",
    borderRadius: 18,
  },
  scannerInstrucao: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
    marginTop: 24,
    backgroundColor: "rgba(0,0,0,0.55)",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  botaoFecharScanner: {
    position: "absolute",
    top: 54,
    right: 24,
  },
});
