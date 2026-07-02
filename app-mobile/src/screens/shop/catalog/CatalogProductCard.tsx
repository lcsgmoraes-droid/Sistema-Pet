import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Image, Text, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import { Produto } from "../../../types";
import { formatarMoeda } from "../../../utils/format";
import { catalogStyles as styles } from "./CatalogStyles";

interface CatalogProductCardProps {
  item: Produto;
  naWishlist: boolean;
  userEmail?: string | null;
  onOpenProduct: (produto: Produto) => void;
  onToggleWishlist: (produtoId: number) => void;
  onAddToCart: (produto: Produto) => void;
  onRegisterAviseme: (produto: Produto) => void;
}

export function CatalogProductCard({
  item,
  naWishlist,
  onOpenProduct,
  onToggleWishlist,
  onAddToCart,
  onRegisterAviseme,
}: CatalogProductCardProps) {
  const estoqueDisponivel = Number(item.estoque ?? 0);
  const semEstoque =
    Number.isFinite(estoqueDisponivel) && estoqueDisponivel <= 0;
  const preco =
    item.promocao_ativa && item.preco_promocional
      ? item.preco_promocional
      : item.preco;
  const temPromocao = item.promocao_ativa && !!item.preco_promocional;

  return (
    <View style={[styles.card, semEstoque && styles.cardIndisponivel]}>
      <TouchableOpacity
        style={styles.cardTopo}
        onPress={() => onOpenProduct(item)}
        activeOpacity={0.85}
      >
        {item.foto_url ? (
          <Image
            source={{ uri: item.foto_url }}
            style={styles.foto}
            resizeMode="contain"
          />
        ) : (
          <View style={[styles.foto, styles.fotoPlaceholder]}>
            <Ionicons name="image-outline" size={34} color={CORES.textoClaro} />
          </View>
        )}

        {temPromocao && !semEstoque && (
          <View style={styles.badgePromocao}>
            <Text style={styles.badgeTexto}>Oferta</Text>
          </View>
        )}

        {semEstoque && (
          <View style={styles.badgeIndisponivel}>
            <Text style={styles.badgeTexto}>Indispon?vel</Text>
          </View>
        )}

        <TouchableOpacity
          style={styles.botaoWishlist}
          onPress={() => onToggleWishlist(item.id)}
        >
          <Ionicons
            name={naWishlist ? "heart" : "heart-outline"}
            size={16}
            color={naWishlist ? "#DC2626" : CORES.primario}
          />
        </TouchableOpacity>
      </TouchableOpacity>

      <View style={styles.cardInfo}>
        <Text style={styles.produtoNome} numberOfLines={2}>
          {item.nome}
        </Text>

        {item.categoria_nome ? (
          <Text style={styles.categoriaTexto}>{item.categoria_nome}</Text>
        ) : null}
        {item.codigo ? (
          <Text style={styles.skuTexto}>SKU: {item.codigo}</Text>
        ) : null}

        <Text style={[styles.estoqueTexto, semEstoque && styles.estoqueZero]}>
          {semEstoque
            ? "Volta em breve"
            : Number.isFinite(estoqueDisponivel) && estoqueDisponivel > 0
              ? `Disponivel: ${estoqueDisponivel}`
              : "Disponivel"}
        </Text>

        <View style={styles.precoRow}>
          {temPromocao && (
            <Text style={styles.precoOriginal}>
              {formatarMoeda(item.preco)}
            </Text>
          )}
          <Text style={[styles.preco, semEstoque && styles.precoIndisponivel]}>
            {formatarMoeda(preco)}
          </Text>
        </View>

        {semEstoque ? (
          <TouchableOpacity
            style={styles.botaoAviseme}
            onPress={() => onRegisterAviseme(item)}
          >
            <Ionicons name="notifications-outline" size={14} color="#D97706" />
            <Text style={styles.botaoAvisemeTexto}>Avise-me quando chegar</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={styles.botaoAdicionar}
            onPress={() => onAddToCart(item)}
          >
            <Ionicons name="add" size={16} color="#fff" />
            <Text style={styles.botaoAdicionarTexto}>Adicionar</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}
