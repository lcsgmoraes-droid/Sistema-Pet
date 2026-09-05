import { StyleSheet } from "react-native";
import { CORES, ESPACO, FONTE, RAIO } from "../../../theme";

export const novoProdutoStyles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.md, gap: ESPACO.md },
  card: {
    backgroundColor: CORES.superficie, padding: ESPACO.md, gap: ESPACO.md,
    borderRadius: RAIO.md, borderWidth: 1, borderColor: CORES.borda,
  },
  heading: { flexDirection: "row", alignItems: "center", gap: ESPACO.sm },
  titulo: { fontSize: FONTE.titulo, fontWeight: "800", color: CORES.texto, flexShrink: 1 },
  subtitulo: { fontSize: FONTE.grande, fontWeight: "700", color: CORES.texto },
  texto: { fontSize: FONTE.normal, color: CORES.textoSecundario, lineHeight: 21 },
  label: { fontSize: FONTE.normal, fontWeight: "600", color: CORES.texto, marginBottom: -8 },
  input: {
    minHeight: 50, borderWidth: 1, borderColor: CORES.borda, borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.md, paddingVertical: ESPACO.sm, fontSize: FONTE.media,
    color: CORES.texto, backgroundColor: CORES.superficie,
  },
  primario: {
    minHeight: 50, backgroundColor: CORES.primario, borderRadius: RAIO.sm,
    padding: ESPACO.md, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: ESPACO.sm,
  },
  primarioTexto: { color: "#fff", fontSize: FONTE.media, fontWeight: "700", textAlign: "center" },
  secundario: { minHeight: 48, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: CORES.primario, borderRadius: RAIO.sm },
  secundarioTexto: { color: CORES.primario, fontSize: FONTE.normal, fontWeight: "700" },
  desabilitado: { opacity: 0.5 },
  aviso: { padding: ESPACO.md, backgroundColor: CORES.primarioClaro, borderRadius: RAIO.sm },
  avisoTexto: { color: CORES.primarioEscuro, fontSize: FONTE.normal },
  erro: { color: CORES.erro, fontSize: FONTE.normal, lineHeight: 21 },
  unidades: { flexDirection: "row", flexWrap: "wrap", gap: ESPACO.sm },
  unidade: { minHeight: 44, borderWidth: 1, borderColor: CORES.borda, borderRadius: RAIO.sm, padding: ESPACO.sm, justifyContent: "center" },
  unidadeAtiva: { borderColor: CORES.primario, backgroundColor: CORES.primarioClaro },
  unidadeTextoAtivo: { color: CORES.primarioEscuro, fontWeight: "700", fontSize: FONTE.normal },
  preco: { color: CORES.primario, fontSize: FONTE.titulo, fontWeight: "800" },
  descricao: { minHeight: 100, textAlignVertical: "top" },
  fotosSection: { gap: ESPACO.md },
  fotoCard: { width: 112, gap: 4 },
  foto: { width: 112, height: 112, borderRadius: RAIO.sm, backgroundColor: CORES.fundo },
  fotoLegenda: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  removerFoto: { minHeight: 44, justifyContent: "center" },
  botaoFoto: { minHeight: 48, flexDirection: "row", gap: ESPACO.sm, alignItems: "center", padding: ESPACO.sm, borderWidth: 1, borderColor: CORES.borda, borderRadius: RAIO.sm },
});
