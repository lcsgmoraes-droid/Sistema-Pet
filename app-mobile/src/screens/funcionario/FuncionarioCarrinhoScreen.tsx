import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import React from "react";
import { Alert, FlatList, Image, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { FuncionarioPdvItem, useFuncionarioPdvStore } from "../../store/funcionarioPdv.store";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import { formatarMoeda } from "../../utils/format";

export default function FuncionarioCarrinhoScreen() {
  const navigation = useNavigation<any>();
  const { itens, subtotal, atualizarQuantidade, removerProduto, limpar } = useFuncionarioPdvStore();

  function alterarQuantidade(produtoId: number, quantidade: number) {
    try {
      atualizarQuantidade(produtoId, quantidade);
    } catch (error: any) {
      Alert.alert("Estoque", error?.message || "Nao foi possivel alterar a quantidade.");
    }
  }

  function confirmarLimpar() {
    if (itens.length === 0) return;
    Alert.alert("Limpar carrinho", "Deseja remover todos os itens?", [
      { text: "Cancelar", style: "cancel" },
      { text: "Limpar", style: "destructive", onPress: limpar },
    ]);
  }

  function remover(item: FuncionarioPdvItem) {
    Alert.alert("Remover item", `Remover ${item.nome}?`, [
      { text: "Cancelar", style: "cancel" },
      { text: "Remover", style: "destructive", onPress: () => removerProduto(item.produto_id) },
    ]);
  }

  function renderItem({ item }: { item: FuncionarioPdvItem }) {
    return (
      <View style={styles.item}>
        <View style={styles.imagemBox}>
          {item.foto_url ? (
            <Image source={{ uri: item.foto_url }} style={styles.imagem} resizeMode="contain" />
          ) : (
            <Ionicons name="cube-outline" size={26} color={CORES.textoClaro} />
          )}
        </View>

        <View style={styles.info}>
          <Text style={styles.nome} numberOfLines={2}>{item.nome}</Text>
          <Text style={styles.preco}>{formatarMoeda(item.preco_unitario)} / un</Text>
          {item.codigo ? <Text style={styles.codigo} numberOfLines={1}>SKU {item.codigo}</Text> : null}
        </View>

        <View style={styles.controles}>
          <TouchableOpacity
            style={styles.controleBtn}
            onPress={() => {
              if (item.quantidade <= 1) {
                remover(item);
              } else {
                alterarQuantidade(item.produto_id, item.quantidade - 1);
              }
            }}
          >
            <Ionicons name={item.quantidade <= 1 ? "trash-outline" : "remove"} size={18} color={item.quantidade <= 1 ? CORES.erro : CORES.texto} />
          </TouchableOpacity>
          <Text style={styles.qtd}>{item.quantidade}</Text>
          <TouchableOpacity style={styles.controleBtn} onPress={() => alterarQuantidade(item.produto_id, item.quantidade + 1)}>
            <Ionicons name="add" size={18} color={CORES.texto} />
          </TouchableOpacity>
        </View>

        <Text style={styles.subtotalItem} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.75}>
          {formatarMoeda(item.subtotal)}
        </Text>
      </View>
    );
  }

  if (itens.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Ionicons name="cart-outline" size={54} color={CORES.textoClaro} />
        <Text style={styles.emptyTitle}>Carrinho vazio</Text>
        <View style={styles.emptyActions}>
          <TouchableOpacity style={styles.primaryButton} onPress={() => navigation.navigate("FuncionarioConsulta")}>
            <Ionicons name="search-outline" size={18} color="#fff" />
            <Text style={styles.primaryButtonText}>Buscar produto</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.secondaryButton} onPress={() => navigation.navigate("FuncionarioScanner")}>
            <Ionicons name="scan-outline" size={18} color={CORES.primario} />
            <Text style={styles.secondaryButtonText}>Escanear</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={itens}
        keyExtractor={(item) => String(item.produto_id)}
        renderItem={renderItem}
        contentContainerStyle={styles.lista}
        ListHeaderComponent={
          <View style={styles.acoesTopo}>
            <TouchableOpacity style={styles.secondaryButtonInline} onPress={() => navigation.navigate("FuncionarioConsulta")}>
              <Ionicons name="search-outline" size={18} color={CORES.primario} />
              <Text style={styles.secondaryButtonText}>Buscar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.secondaryButtonInline} onPress={() => navigation.navigate("FuncionarioScanner")}>
              <Ionicons name="scan-outline" size={18} color={CORES.primario} />
              <Text style={styles.secondaryButtonText}>Escanear</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.dangerButtonInline} onPress={confirmarLimpar}>
              <Ionicons name="trash-outline" size={18} color={CORES.erro} />
              <Text style={styles.dangerButtonText}>Limpar</Text>
            </TouchableOpacity>
          </View>
        }
      />

      <View style={styles.rodape}>
        <View>
          <Text style={styles.totalLabel}>Total</Text>
          <Text style={styles.totalValor}>{formatarMoeda(subtotal)}</Text>
        </View>
        <Text style={styles.totalItens}>{itens.reduce((acc, item) => acc + item.quantidade, 0)} item(ns)</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  lista: { padding: ESPACO.md, paddingBottom: 118, gap: ESPACO.sm },
  acoesTopo: { flexDirection: "row", alignItems: "center", gap: ESPACO.sm, marginBottom: ESPACO.sm },
  item: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    padding: ESPACO.md,
    borderRadius: RAIO.md,
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderColor: CORES.borda,
  },
  imagemBox: {
    width: 54,
    height: 54,
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: CORES.fundo,
    overflow: "hidden",
  },
  imagem: { width: "100%", height: "100%" },
  info: { flex: 1, minWidth: 0 },
  nome: { color: CORES.texto, fontSize: FONTE.normal, fontWeight: "800" },
  preco: { color: CORES.textoSecundario, fontSize: FONTE.pequena, marginTop: 2 },
  codigo: { color: CORES.textoClaro, fontSize: FONTE.pequena, marginTop: 2 },
  controles: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    overflow: "hidden",
    backgroundColor: CORES.fundo,
  },
  controleBtn: { width: 34, height: 34, alignItems: "center", justifyContent: "center" },
  qtd: { minWidth: 28, textAlign: "center", color: CORES.texto, fontWeight: "800" },
  subtotalItem: { width: 86, color: CORES.texto, fontWeight: "900", textAlign: "right" },
  rodape: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    padding: ESPACO.md,
    paddingBottom: ESPACO.lg,
    backgroundColor: CORES.superficie,
    borderTopWidth: 1,
    borderTopColor: CORES.borda,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    ...SOMBRA,
  },
  totalLabel: { color: CORES.textoSecundario, fontSize: FONTE.pequena, fontWeight: "700" },
  totalValor: { color: CORES.texto, fontSize: FONTE.titulo, fontWeight: "900", marginTop: 2 },
  totalItens: { color: CORES.textoSecundario, fontWeight: "700" },
  emptyContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: ESPACO.xl,
    backgroundColor: CORES.fundo,
  },
  emptyTitle: { color: CORES.texto, fontSize: FONTE.grande, fontWeight: "900", marginTop: ESPACO.md },
  emptyActions: { flexDirection: "row", gap: ESPACO.sm, marginTop: ESPACO.lg },
  primaryButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.xs,
    backgroundColor: CORES.primario,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm + 4,
    borderRadius: RAIO.md,
  },
  primaryButtonText: { color: "#fff", fontWeight: "800" },
  secondaryButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.xs,
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderColor: CORES.primario,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm + 4,
    borderRadius: RAIO.md,
  },
  secondaryButtonInline: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: ESPACO.xs,
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderColor: CORES.primario,
    paddingVertical: ESPACO.sm + 4,
    borderRadius: RAIO.md,
  },
  secondaryButtonText: { color: CORES.primario, fontWeight: "800" },
  dangerButtonInline: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: ESPACO.xs,
    backgroundColor: "#FEF2F2",
    borderWidth: 1,
    borderColor: "#FECACA",
    paddingVertical: ESPACO.sm + 4,
    borderRadius: RAIO.md,
  },
  dangerButtonText: { color: CORES.erro, fontWeight: "800" },
});
