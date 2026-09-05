import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Image, Text, TouchableOpacity, View } from "react-native";
import { FotoProdutoRapido } from "../../../services/funcionarioProdutos.service";
import { CORES } from "../../../theme";
import { novoProdutoStyles as styles } from "./NovoProdutoStyles";

export function ProdutoRapidoFotos({ fotos, ocupado, salvo, adicionar, remover }: {
  fotos: FotoProdutoRapido[];
  ocupado: boolean;
  salvo: boolean;
  adicionar: (origem: "camera" | "galeria") => void;
  remover: (uri: string) => void;
}) {
  return (
    <View style={styles.fotosSection}>
      <Text style={styles.label}>Fotos · opcional ({fotos.length}/5)</Text>
      {!salvo ? <Text style={styles.texto}>A primeira foto será a principal. Você pode tirar a foto agora ou escolher na galeria.</Text> : null}
      <View style={styles.unidades}>
        {fotos.map((foto, index) => (
          <View key={foto.uri} style={styles.fotoCard}>
            <Image source={{ uri: foto.uri }} accessibilityLabel={`Foto ${index + 1} do produto`} style={styles.foto} />
            <Text style={styles.fotoLegenda}>{foto.enviada ? "Enviada" : salvo ? "Envio pendente" : index === 0 ? "Principal" : `Foto ${index + 1}`}</Text>
            {!salvo ? <TouchableOpacity accessibilityLabel={`Remover foto ${index + 1}`} accessibilityRole="button" disabled={ocupado} style={styles.removerFoto} onPress={() => remover(foto.uri)}>
              <Text style={styles.erro}>Remover</Text>
            </TouchableOpacity> : null}
          </View>
        ))}
      </View>
      {!salvo && fotos.length < 5 ? <View style={styles.unidades}>
        <TouchableOpacity accessibilityRole="button" style={styles.botaoFoto} disabled={ocupado} onPress={() => adicionar("camera")}>
          <Ionicons name="camera-outline" size={22} color={CORES.primario} /><Text style={styles.secundarioTexto}>Tirar foto</Text>
        </TouchableOpacity>
        <TouchableOpacity accessibilityRole="button" style={styles.botaoFoto} disabled={ocupado} onPress={() => adicionar("galeria")}>
          <Ionicons name="images-outline" size={22} color={CORES.primario} /><Text style={styles.secundarioTexto}>Galeria</Text>
        </TouchableOpacity>
      </View> : null}
    </View>
  );
}
