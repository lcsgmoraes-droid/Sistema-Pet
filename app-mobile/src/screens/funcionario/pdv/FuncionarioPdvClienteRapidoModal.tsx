import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
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

import { CORES, ESPACO, FONTE, RAIO } from "../../../theme";
import type { FuncionarioPdvCliente } from "../../../types";
import { listarOrigensClientePdv } from "../../../services/funcionarioPdv.service";

const ORIGENS_PADRAO = [
  { value: "loja_fisica", label: "Loja Física" },
  { value: "ecommerce", label: "E-commerce" },
  { value: "app", label: "App" },
  { value: "ifood", label: "iFood" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "instagram", label: "Instagram" },
  { value: "indicacao", label: "Indicação" },
];

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
    origem_cliente?: string | null;
    nome?: string | null;
    telefone?: string | null;
    endereco?: string | null;
  }) => Promise<FuncionarioPdvCliente | void>;
}) {
  const [nome, setNome] = useState("");
  const [telefone, setTelefone] = useState("");
  const [endereco, setEndereco] = useState("");
  const [origem, setOrigem] = useState("loja_fisica");
  const [novaOrigem, setNovaOrigem] = useState("");
  const [origens, setOrigens] = useState(ORIGENS_PADRAO);
  const [erroOrigens, setErroOrigens] = useState(false);
  useEffect(() => {
    if (!visible) return;
    let ativo = true;
    setErroOrigens(false);
    listarOrigensClientePdv()
      .then((data) => {
        if (ativo) setOrigens(data);
      })
      .catch(() => {
        if (ativo) setErroOrigens(true);
      });
    return () => {
      ativo = false;
    };
  }, [visible]);
  const origemVazia = origem === "__nova__" && !novaOrigem.trim();

  function limparEFechar() {
    setNome("");
    setTelefone("");
    setEndereco("");
    setOrigem("loja_fisica");
    setNovaOrigem("");
    onClose();
  }

  function fechar() {
    if (!salvando) limparEFechar();
  }

  async function salvar() {
    if (origemVazia) return;
    const criado = await onSave({
      origem_cliente: origem === "__nova__" ? novaOrigem.trim() : origem,
      nome: nome.trim() || null,
      telefone: telefone.trim() || null,
      endereco: endereco.trim() || null,
    });
    if (criado) limparEFechar();
  }

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={fechar}>
      <KeyboardAvoidingView
        style={styles.overlay}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
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

          <ScrollView style={{ flexShrink: 1 }} keyboardShouldPersistTaps="handled">
            <Text style={styles.label}>Origem do cliente</Text>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator
              keyboardShouldPersistTaps="handled"
              style={{ marginTop: ESPACO.xs }}
            >
              {[...origens, { value: "__nova__", label: "+ Nova origem" }].map((item) => (
                <TouchableOpacity
                  key={item.value}
                  disabled={salvando}
                  onPress={() => setOrigem(item.value)}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: origem === item.value }}
                  style={[styles.origem, origem === item.value && styles.origemSelecionada]}
                >
                  <Text
                    style={{
                      color: origem === item.value ? "#fff" : CORES.texto,
                    }}
                  >
                    {item.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            {origem === "__nova__" && (
              <TextInput
                value={novaOrigem}
                onChangeText={setNovaOrigem}
                maxLength={50}
                placeholder="Nome da nova origem"
                accessibilityLabel="Nome da nova origem"
                style={styles.input}
                editable={!salvando}
              />
            )}
            {erroOrigens && (
              <Text style={styles.subtitle}>Não foi possível carregar as origens adicionais.</Text>
            )}
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
          </ScrollView>

          <View style={styles.actions}>
            <TouchableOpacity style={styles.cancel} onPress={fechar} disabled={salvando}>
              <Text style={styles.cancelText}>Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.save, origemVazia && { opacity: 0.5 }]}
              onPress={salvar}
              disabled={salvando || origemVazia}
            >
              {salvando ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Ionicons name="person-add-outline" size={18} color="#fff" />
              )}
              <Text style={styles.saveText}>Adicionar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
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
    maxHeight: "92%",
    backgroundColor: CORES.superficie,
    borderTopLeftRadius: RAIO.lg,
    borderTopRightRadius: RAIO.lg,
    padding: ESPACO.lg,
    paddingBottom: ESPACO.xxl,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: ESPACO.md,
  },
  title: { color: CORES.texto, fontSize: FONTE.titulo, fontWeight: "900" },
  subtitle: {
    color: CORES.textoSecundario,
    fontSize: FONTE.pequena,
    marginTop: 2,
  },
  close: {
    width: 40,
    height: 40,
    borderRadius: RAIO.circulo,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: CORES.fundo,
  },
  label: {
    color: CORES.texto,
    fontSize: FONTE.normal,
    fontWeight: "800",
    marginTop: ESPACO.sm,
  },
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
  origem: {
    padding: ESPACO.sm,
    marginRight: ESPACO.xs,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
  },
  origemSelecionada: {
    backgroundColor: CORES.primario,
    borderColor: CORES.primario,
  },
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
