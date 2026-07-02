import { Ionicons } from "@expo/vector-icons";
import { Image, Text, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import { funcionarioContagemStyles as styles } from "./FuncionarioContagemStyles";

export function FuncionarioContagemProdutoImagem({
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

export function FuncionarioContagemCheckboxLinha({
  ativo,
  titulo,
  descricao,
  onPress,
}: {
  ativo: boolean;
  titulo: string;
  descricao: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={styles.checkboxLinha} onPress={onPress}>
      <Ionicons
        name={ativo ? "checkbox-outline" : "square-outline"}
        size={24}
        color={ativo ? CORES.sucesso : CORES.textoClaro}
      />
      <View style={{ flex: 1 }}>
        <Text style={styles.checkboxTitulo}>{titulo}</Text>
        <Text style={styles.checkboxDescricao}>{descricao}</Text>
      </View>
    </TouchableOpacity>
  );
}
