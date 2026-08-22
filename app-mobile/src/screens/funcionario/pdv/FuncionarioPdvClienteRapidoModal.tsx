import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Modal,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { CORES, ESPACO, FONTE, RAIO } from "../../../theme";
import type { FuncionarioPdvCliente } from "../../../types";

export function FuncionarioPdvClienteRapidoModal({
  visible,
  salvando,
  onClose,
  onSave,
}: {
  visible: boolean;
  salvando: boolean;
  onClose: () => void;
  onSave: (payload: {
    nome?: string | null;
    telefone?: string | null;
    endereco?: string | null;
  }) => Promise<FuncionarioPdvCliente | void>;
}) {
  const [nome, setNome] = useState("");
  const [telefone, setTelefone] = useState("");
  const [endereco, setEndereco] = useState("");

  function limparEFechar() {
    setNome("");
    setTelefone("");
    setEndereco("");
    onClose();
  }

  function fechar() {
    if (!salvando) limparEFechar();
  }

  async function salvar() {
    const criado = await onSave({
      nome: nome.trim() || null,
      telefone: telefone.trim() || null,
      endereco: endereco.trim() || null,
    });
    if (criado) limparEFechar();
  }

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={fechar}>
      <View style={styles.overlay}>
        <View style={styles.card}>
          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <Text style={styles.title}>Adicionar pessoa</Text>
              <Text style={styles.subtitle}>Todos os campos sao opcionais.</Text>
            </View>
            <TouchableOpacity style={styles.close} onPress={fechar} disabled={salvando}>
              <Ionicons name="close" size={22} color={CORES.textoSecundario} />
            </TouchableOpacity>
          </View>

          <Text style={styles.label}>Nome</Text>
          <TextInput
            value={nome}
            onChangeText={setNome}
            placeholder="Nome da pessoa"
            style={styles.input}
            autoCapitalize="words"
          />
          <Text style={styles.label}>Telefone</Text>
          <TextInput
            value={telefone}
            onChangeText={setTelefone}
            placeholder="Telefone ou WhatsApp"
            style={styles.input}
            keyboardType="phone-pad"
          />
          <Text style={styles.label}>Endereco</Text>
          <TextInput
            value={endereco}
            onChangeText={setEndereco}
            placeholder="Rua, numero, bairro, cidade..."
            style={[styles.input, styles.address]}
            multiline
          />

          <View style={styles.actions}>
            <TouchableOpacity style={styles.cancel} onPress={fechar} disabled={salvando}>
              <Text style={styles.cancelText}>Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.save} onPress={salvar} disabled={salvando}>
              {salvando ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Ionicons name="person-add-outline" size={18} color="#fff" />
              )}
              <Text style={styles.saveText}>Adicionar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(15,23,42,0.5)",
  },
  card: {
    backgroundColor: CORES.superficie,
    borderTopLeftRadius: RAIO.lg,
    borderTopRightRadius: RAIO.lg,
    padding: ESPACO.lg,
    paddingBottom: ESPACO.xxl,
  },
  header: { flexDirection: "row", alignItems: "center", marginBottom: ESPACO.md },
  title: { color: CORES.texto, fontSize: FONTE.titulo, fontWeight: "900" },
  subtitle: { color: CORES.textoSecundario, fontSize: FONTE.pequena, marginTop: 2 },
  close: {
    width: 40,
    height: 40,
    borderRadius: RAIO.circulo,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: CORES.fundo,
  },
  label: { color: CORES.texto, fontSize: FONTE.normal, fontWeight: "800", marginTop: ESPACO.sm },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    backgroundColor: "#fff",
    color: CORES.texto,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    marginTop: ESPACO.xs,
  },
  address: { minHeight: 76, textAlignVertical: "top" },
  actions: { flexDirection: "row", gap: ESPACO.sm, marginTop: ESPACO.lg },
  cancel: {
    flex: 1,
    minHeight: 50,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
  },
  cancelText: { color: CORES.textoSecundario, fontWeight: "800" },
  save: {
    flex: 1,
    minHeight: 50,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primario,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.xs,
  },
  saveText: { color: "#fff", fontWeight: "900" },
});
