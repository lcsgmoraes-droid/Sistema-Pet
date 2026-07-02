import { Ionicons } from "@expo/vector-icons";
import { Image, View } from "react-native";

import { CORES } from "../../../theme";
import { funcionarioPdvStyles as styles } from "./FuncionarioPdvStyles";

export function FuncionarioPdvProductImage({
  uri,
  compacta = false,
}: {
  uri?: string | null;
  compacta?: boolean;
}) {
  return (
    <View style={[styles.produtoImagemWrap, compacta && styles.produtoImagemWrapCompacta]}>
      {uri ? (
        <Image source={{ uri }} style={styles.produtoImagem} resizeMode="cover" />
      ) : (
        <Ionicons name="image-outline" size={compacta ? 18 : 22} color={CORES.textoClaro} />
      )}
    </View>
  );
}
