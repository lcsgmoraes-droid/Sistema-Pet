import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

export default function FuncionarioHomeScreen() {
  const navigation = useNavigation<any>();

  return (
    <View style={styles.container}>
      <View style={styles.headerCard}>
        <View style={styles.headerIcone}>
          <Ionicons name="briefcase-outline" size={26} color={CORES.sucesso} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.titulo}>App do funcionario</Text>
          <Text style={styles.subtitulo}>Escolha a operacao que deseja registrar no ERP.</Text>
        </View>
      </View>

      <TouchableOpacity style={styles.acao} onPress={() => navigation.navigate("FuncionarioBalanco")}>
        <View style={[styles.acaoIcone, { backgroundColor: "#DCFCE7" }]}>
          <Ionicons name="barcode-outline" size={24} color={CORES.sucesso} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.acaoTitulo}>Balanco de estoque</Text>
          <Text style={styles.acaoTexto}>Ler codigo, informar saldo final, lote e validade.</Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color={CORES.textoClaro} />
      </TouchableOpacity>

      <TouchableOpacity style={styles.acao} onPress={() => navigation.navigate("FuncionarioContagem")}>
        <View style={[styles.acaoIcone, { backgroundColor: "#FEF3C7" }]}>
          <Ionicons name="clipboard-outline" size={24} color={CORES.aviso} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.acaoTitulo}>Contagem</Text>
          <Text style={styles.acaoTexto}>Bipar produtos, salvar a lista e gerar PDF ou Excel.</Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color={CORES.textoClaro} />
      </TouchableOpacity>

      <TouchableOpacity style={styles.acao} onPress={() => navigation.navigate("FuncionarioPdv")}>
        <View style={[styles.acaoIcone, { backgroundColor: "#DBEAFE" }]}>
          <Ionicons name="cart-outline" size={24} color={CORES.primario} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.acaoTitulo}>Passar venda</Text>
          <Text style={styles.acaoTexto}>Scanner, carrinho, cliente opcional e pagamento simples.</Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color={CORES.textoClaro} />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: CORES.fundo,
    padding: ESPACO.md,
    gap: ESPACO.md,
  },
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
    width: 52,
    height: 52,
    borderRadius: RAIO.md,
    backgroundColor: "#ECFDF5",
    alignItems: "center",
    justifyContent: "center",
    marginRight: ESPACO.md,
  },
  titulo: {
    fontSize: FONTE.titulo,
    fontWeight: "800",
    color: CORES.texto,
  },
  subtitulo: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    marginTop: 2,
  },
  acao: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    ...SOMBRA,
  },
  acaoIcone: {
    width: 48,
    height: 48,
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
    marginRight: ESPACO.md,
  },
  acaoTitulo: {
    fontSize: FONTE.grande,
    fontWeight: "800",
    color: CORES.texto,
  },
  acaoTexto: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    marginTop: 2,
  },
});
