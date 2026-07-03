import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Image, Text, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import { formatarMoeda } from "../../../utils/format";
import { cartStyles as styles } from "./CartStyles";

type CartItemCardProps = {
  item: any;
  onDecrease: (item: any) => void;
  onIncrease: (item: any) => void;
};

export function CartItemCard({
  item,
  onDecrease,
  onIncrease,
}: CartItemCardProps) {
  return (
    <View style={styles.item}>
      {item.foto_url ? (
        <Image
          source={{ uri: item.foto_url }}
          style={styles.itemFoto}
          resizeMode="cover"
        />
      ) : (
        <View style={[styles.itemFoto, styles.itemFotoPlaceholder]}>
          <Text style={{ fontSize: 22 }}>🛍️</Text>
        </View>
      )}

      <View style={styles.itemInfo}>
        <Text style={styles.itemNome} numberOfLines={2}>
          {item.nome}
        </Text>
        <Text style={styles.itemPreco}>
          {formatarMoeda(item.preco_unitario)} / un
        </Text>
      </View>

      <View style={styles.itemControles}>
        <TouchableOpacity
          style={styles.controleBtn}
          onPress={() => onDecrease(item)}
        >
          <Ionicons
            name={item.quantidade <= 1 ? "trash-outline" : "remove"}
            size={18}
            color={item.quantidade <= 1 ? CORES.erro : CORES.texto}
          />
        </TouchableOpacity>
        <Text style={styles.qtd}>{item.quantidade}</Text>
        <TouchableOpacity
          style={styles.controleBtn}
          onPress={() => onIncrease(item)}
        >
          <Ionicons name="add" size={18} color={CORES.texto} />
        </TouchableOpacity>
      </View>

      <Text style={styles.itemSubtotal}>{formatarMoeda(item.subtotal)}</Text>
    </View>
  );
}
