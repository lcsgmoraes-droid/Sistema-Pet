import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import KeyboardSafeScrollView from "../../../components/KeyboardSafeScrollView";
import { CORES, ESPACO } from "../../../theme";
import { cartStyles as styles } from "./CartStyles";

type CartAddressModalProps = {
  visible: boolean;
  cep: string;
  rua: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  estado: string;
  buscandoCep: boolean;
  onClose: () => void;
  onCepChange: (value: string) => void;
  onRuaChange: (value: string) => void;
  onNumeroChange: (value: string) => void;
  onComplementoChange: (value: string) => void;
  onBairroChange: (value: string) => void;
  onCidadeChange: (value: string) => void;
  onEstadoChange: (value: string) => void;
  onUseAddress: () => void;
};

export function CartAddressModal({
  visible,
  cep,
  rua,
  numero,
  complemento,
  bairro,
  cidade,
  estado,
  buscandoCep,
  onClose,
  onCepChange,
  onRuaChange,
  onNumeroChange,
  onComplementoChange,
  onBairroChange,
  onCidadeChange,
  onEstadoChange,
  onUseAddress,
}: CartAddressModalProps) {
  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        style={{ flex: 1, backgroundColor: CORES.fundo }}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitulo}>Endereço de entrega</Text>
          <TouchableOpacity onPress={onClose}>
            <Ionicons name="close" size={24} color={CORES.texto} />
          </TouchableOpacity>
        </View>

        <KeyboardSafeScrollView contentContainerStyle={styles.modalConteudo}>
          <Text style={styles.modalLabel}>CEP</Text>
          <View style={styles.cepRow}>
            <TextInput
              style={[styles.modalInput, { flex: 1 }]}
              placeholder="00000-000"
              placeholderTextColor={CORES.textoClaro}
              keyboardType="numeric"
              value={cep}
              onChangeText={onCepChange}
              maxLength={9}
            />
            {buscandoCep && (
              <ActivityIndicator
                size="small"
                color={CORES.primario}
                style={{ marginLeft: 8 }}
              />
            )}
          </View>

          <Text style={styles.modalLabel}>Rua / Avenida *</Text>
          <TextInput
            style={styles.modalInput}
            placeholder="Ex: Rua das Flores"
            placeholderTextColor={CORES.textoClaro}
            value={rua}
            onChangeText={onRuaChange}
          />

          <View style={styles.modalRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.modalLabel}>Número</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="123"
                placeholderTextColor={CORES.textoClaro}
                keyboardType="numeric"
                value={numero}
                onChangeText={onNumeroChange}
              />
            </View>
            <View style={{ flex: 2, marginLeft: ESPACO.sm }}>
              <Text style={styles.modalLabel}>Complemento</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="Apto 42"
                placeholderTextColor={CORES.textoClaro}
                value={complemento}
                onChangeText={onComplementoChange}
              />
            </View>
          </View>

          <Text style={styles.modalLabel}>Bairro</Text>
          <TextInput
            style={styles.modalInput}
            placeholder="Bairro"
            placeholderTextColor={CORES.textoClaro}
            value={bairro}
            onChangeText={onBairroChange}
          />

          <View style={styles.modalRow}>
            <View style={{ flex: 2 }}>
              <Text style={styles.modalLabel}>Cidade *</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="São Paulo"
                placeholderTextColor={CORES.textoClaro}
                value={cidade}
                onChangeText={onCidadeChange}
              />
            </View>
            <View style={{ flex: 1, marginLeft: ESPACO.sm }}>
              <Text style={styles.modalLabel}>UF</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="SP"
                placeholderTextColor={CORES.textoClaro}
                autoCapitalize="characters"
                maxLength={2}
                value={estado}
                onChangeText={onEstadoChange}
              />
            </View>
          </View>

          <TouchableOpacity style={styles.modalBotao} onPress={onUseAddress}>
            <Text style={styles.modalBotaoTexto}>Usar este endereço</Text>
          </TouchableOpacity>
        </KeyboardSafeScrollView>
      </KeyboardAvoidingView>
    </Modal>
  );
}
