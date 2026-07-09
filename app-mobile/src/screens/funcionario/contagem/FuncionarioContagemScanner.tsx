import { Ionicons } from "@expo/vector-icons";
import { CameraView } from "expo-camera";
import { Text, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import { funcionarioContagemStyles as styles } from "./FuncionarioContagemStyles";

export function FuncionarioContagemPermissionRequest({
  requestPermission,
}: {
  requestPermission: () => void | Promise<unknown>;
}) {
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

export function FuncionarioContagemScanner({
  scanAtivo,
  buscandoProduto,
  feedback,
  instrucao,
  onBarcodeScanned,
  onClose,
  onResetScan,
}: {
  scanAtivo: boolean;
  buscandoProduto: boolean;
  feedback?: { tipo: "sucesso" | "erro"; mensagem: string } | null;
  instrucao: string;
  onBarcodeScanned: (event: { data: string }) => void | Promise<void>;
  onClose: () => void;
  onResetScan: () => void;
}) {
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
          <TouchableOpacity style={styles.fecharScanner} onPress={onClose}>
            <Ionicons name="close" size={28} color="#fff" />
          </TouchableOpacity>
          <View style={styles.frameScan} />
          <Text style={styles.scannerTexto} numberOfLines={2}>
            {buscandoProduto ? "Buscando no ERP..." : instrucao}
          </Text>
          {feedback ? (
            <View
              style={[
                styles.scannerFeedback,
                feedback.tipo === "erro" ? styles.scannerFeedbackErro : styles.scannerFeedbackSucesso,
              ]}
            >
              <Ionicons
                name={feedback.tipo === "erro" ? "alert-circle-outline" : "checkmark-circle-outline"}
                size={18}
                color="#fff"
              />
              <Text style={styles.scannerFeedbackTexto} numberOfLines={2}>
                {feedback.mensagem}
              </Text>
            </View>
          ) : null}
          {!scanAtivo && !buscandoProduto && !feedback ? (
            <TouchableOpacity style={styles.botaoScanner} onPress={onResetScan}>
              <Ionicons name="scan-outline" size={18} color="#fff" />
              <Text style={styles.botaoScannerTexto}>Escanear novamente</Text>
            </TouchableOpacity>
          ) : null}
        </View>
      </CameraView>
    </View>
  );
}
