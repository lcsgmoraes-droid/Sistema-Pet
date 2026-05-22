import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { buscarProdutosFuncionario } from "../../services/funcionario.service";
import { useFuncionarioPdvStore } from "../../store/funcionarioPdv.store";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import { Produto } from "../../types";
import { formatarMoeda } from "../../utils/format";

function precoProduto(produto: Produto): number {
  return Number(produto.promocao_ativa && produto.preco_promocional ? produto.preco_promocional : produto.preco) || 0;
}

export default function FuncionarioConsultaScreen() {
  const navigation = useNavigation<any>();
  const { adicionarProduto, subtotal, totalItens } = useFuncionarioPdvStore();
  const [busca, setBusca] = useState("");
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (texto: string) => {
    const termo = texto.trim();
    if (termo.length === 1) {
      setProdutos([]);
      return;
    }

    setCarregando(true);
    setErro(null);
    try {
      const resultado = await buscarProdutosFuncionario(termo);
      setProdutos(resultado);
    } catch {
      setProdutos([]);
      setErro("Nao foi possivel buscar produtos.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar("");
  }, [carregar]);

  function onBusca(texto: string) {
    setBusca(texto);
    if (texto.length === 0 || texto.length >= 2) {
      carregar(texto);
    }
  }

  function adicionar(item: Produto) {
    const estoque = Number(item.estoque ?? 0);
    if (Number.isFinite(estoque) && estoque <= 0) {
      Alert.alert("Sem estoque", "Produto sem estoque disponivel.");
      return;
    }

    try {
      adicionarProduto(item, 1);
    } catch (error: any) {
      Alert.alert("Estoque", error?.message || "Nao foi possivel adicionar o produto.");
    }
  }

  function renderProduto({ item }: { item: Produto }) {
    const estoque = Number(item.estoque ?? 0);
    const semEstoque = Number.isFinite(estoque) && estoque <= 0;
    const temPromocao = item.promocao_ativa && !!item.preco_promocional;

    return (
      <View style={[styles.card, semEstoque && styles.cardSemEstoque]}>
        <View style={styles.imagemBox}>
          {item.foto_url ? (
            <Image source={{ uri: item.foto_url }} style={styles.imagem} resizeMode="contain" />
          ) : (
            <Ionicons name="image-outline" size={28} color={CORES.textoClaro} />
          )}
        </View>

        <View style={styles.produtoInfo}>
          <Text style={styles.produtoNome} numberOfLines={2}>{item.nome}</Text>
          <View style={styles.metaRow}>
            {item.codigo ? <Text style={styles.metaTexto} numberOfLines={1}>SKU {item.codigo}</Text> : null}
            {item.codigo_barras ? <Text style={styles.metaTexto} numberOfLines={1}>EAN {item.codigo_barras}</Text> : null}
          </View>
          <Text style={[styles.estoqueTexto, semEstoque && styles.estoqueZero]}>
            {semEstoque ? "Sem estoque" : `Estoque: ${Number.isFinite(estoque) ? estoque : "-"}`}
          </Text>
          <View style={styles.precoRow}>
            {temPromocao ? <Text style={styles.precoOriginal}>{formatarMoeda(item.preco)}</Text> : null}
            <Text style={styles.preco}>{formatarMoeda(precoProduto(item))}</Text>
          </View>
        </View>

        <TouchableOpacity
          style={[styles.botaoAdd, semEstoque && styles.botaoAddDisabled]}
          onPress={() => adicionar(item)}
          disabled={semEstoque}
        >
          <Ionicons name="add" size={22} color="#fff" />
        </TouchableOpacity>
      </View>
    );
  }

  const total = totalItens();

  return (
    <View style={styles.container}>
      <View style={styles.topo}>
        <View style={styles.searchBox}>
          <Ionicons name="search-outline" size={18} color={CORES.textoSecundario} />
          <TextInput
            value={busca}
            onChangeText={onBusca}
            placeholder="Nome, codigo, SKU ou barras"
            placeholderTextColor={CORES.textoClaro}
            autoCapitalize="none"
            style={styles.input}
            returnKeyType="search"
            onSubmitEditing={() => carregar(busca)}
          />
        </View>
        <TouchableOpacity style={styles.iconButton} onPress={() => navigation.navigate("FuncionarioScanner")}>
          <Ionicons name="scan-outline" size={22} color="#fff" />
        </TouchableOpacity>
        <TouchableOpacity style={styles.cartButton} onPress={() => navigation.navigate("FuncionarioCarrinho")}>
          <Ionicons name="cart-outline" size={22} color={CORES.primario} />
          {total > 0 ? (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{total > 99 ? "99+" : total}</Text>
            </View>
          ) : null}
        </TouchableOpacity>
      </View>

      <TouchableOpacity style={styles.resumoCarrinho} onPress={() => navigation.navigate("FuncionarioCarrinho")}>
        <View>
          <Text style={styles.resumoLabel}>Carrinho PDV</Text>
          <Text style={styles.resumoValor}>{formatarMoeda(subtotal)}</Text>
        </View>
        <View style={styles.resumoDireita}>
          <Text style={styles.resumoItens}>{total} item(ns)</Text>
          <Ionicons name="chevron-forward" size={20} color={CORES.textoSecundario} />
        </View>
      </TouchableOpacity>

      {erro ? (
        <TouchableOpacity style={styles.erroBox} onPress={() => carregar(busca)}>
          <Text style={styles.erroTexto}>{erro}</Text>
          <Ionicons name="refresh-outline" size={18} color={CORES.erro} />
        </TouchableOpacity>
      ) : null}

      <FlatList
        data={produtos}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderProduto}
        contentContainerStyle={styles.lista}
        ListEmptyComponent={
          carregando ? (
            <ActivityIndicator color={CORES.primario} style={styles.loading} />
          ) : (
            <View style={styles.vazio}>
              <Ionicons name="barcode-outline" size={34} color={CORES.textoClaro} />
              <Text style={styles.vazioTitulo}>Nenhum produto na busca</Text>
              <Text style={styles.vazioTexto}>Use a camera ou digite pelo menos 2 caracteres.</Text>
            </View>
          )
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  topo: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    padding: ESPACO.md,
    backgroundColor: CORES.superficie,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
  },
  searchBox: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    backgroundColor: CORES.fundo,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    paddingHorizontal: ESPACO.md,
    height: 46,
  },
  input: { flex: 1, color: CORES.texto, fontSize: FONTE.normal, minWidth: 0 },
  iconButton: {
    width: 46,
    height: 46,
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: CORES.primario,
  },
  cartButton: {
    width: 46,
    height: 46,
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: CORES.primario,
    backgroundColor: CORES.superficie,
  },
  badge: {
    position: "absolute",
    right: -4,
    top: -4,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    paddingHorizontal: 3,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: CORES.secundario,
  },
  badgeText: { color: "#fff", fontSize: 10, fontWeight: "800" },
  resumoCarrinho: {
    margin: ESPACO.md,
    marginBottom: 0,
    padding: ESPACO.md,
    borderRadius: RAIO.md,
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderColor: CORES.borda,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    ...SOMBRA,
  },
  resumoLabel: { color: CORES.textoSecundario, fontSize: FONTE.pequena, fontWeight: "700" },
  resumoValor: { color: CORES.texto, fontSize: FONTE.grande, fontWeight: "800", marginTop: 2 },
  resumoDireita: { flexDirection: "row", alignItems: "center", gap: ESPACO.xs },
  resumoItens: { color: CORES.textoSecundario, fontSize: FONTE.normal },
  erroBox: {
    marginHorizontal: ESPACO.md,
    marginTop: ESPACO.md,
    padding: ESPACO.md,
    borderRadius: RAIO.md,
    backgroundColor: "#FEF2F2",
    borderWidth: 1,
    borderColor: "#FECACA",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  erroTexto: { color: CORES.erro, fontWeight: "700" },
  lista: { padding: ESPACO.md, gap: ESPACO.sm, paddingBottom: ESPACO.xl },
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.md,
    padding: ESPACO.md,
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
  },
  cardSemEstoque: { opacity: 0.72 },
  imagemBox: {
    width: 58,
    height: 58,
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: CORES.fundo,
    overflow: "hidden",
  },
  imagem: { width: "100%", height: "100%" },
  produtoInfo: { flex: 1, minWidth: 0 },
  produtoNome: { color: CORES.texto, fontSize: FONTE.normal, fontWeight: "800" },
  metaRow: { flexDirection: "row", gap: ESPACO.sm, marginTop: 4 },
  metaTexto: { flexShrink: 1, color: CORES.textoSecundario, fontSize: FONTE.pequena },
  estoqueTexto: { color: CORES.sucesso, fontSize: FONTE.pequena, fontWeight: "700", marginTop: 4 },
  estoqueZero: { color: CORES.erro },
  precoRow: { flexDirection: "row", alignItems: "center", gap: ESPACO.sm, marginTop: 4 },
  precoOriginal: { color: CORES.textoClaro, fontSize: FONTE.pequena, textDecorationLine: "line-through" },
  preco: { color: CORES.primario, fontSize: FONTE.media, fontWeight: "900" },
  botaoAdd: {
    width: 42,
    height: 42,
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: CORES.sucesso,
  },
  botaoAddDisabled: { backgroundColor: CORES.textoClaro },
  loading: { marginTop: ESPACO.xl },
  vazio: { alignItems: "center", paddingTop: ESPACO.xxl, paddingHorizontal: ESPACO.lg },
  vazioTitulo: { color: CORES.texto, fontWeight: "800", marginTop: ESPACO.sm, fontSize: FONTE.media },
  vazioTexto: { color: CORES.textoSecundario, textAlign: "center", marginTop: ESPACO.xs },
});
