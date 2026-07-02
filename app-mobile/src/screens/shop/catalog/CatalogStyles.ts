import { StyleSheet } from "react-native";

import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../../theme";

export const catalogStyles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },

  buscaRow: {
    flexDirection: "row",

    gap: ESPACO.sm,

    padding: ESPACO.md,

    paddingBottom: ESPACO.sm,

    backgroundColor: CORES.superficie,

    borderBottomWidth: 1,

    borderBottomColor: CORES.borda,
  },

  buscaContainer: {
    flex: 1,

    flexDirection: "row",

    alignItems: "center",

    borderWidth: 1,

    borderColor: CORES.borda,

    borderRadius: RAIO.md,

    paddingHorizontal: ESPACO.sm,

    backgroundColor: CORES.fundo,
  },

  buscaInput: {
    flex: 1,
    fontSize: FONTE.normal,
    color: CORES.texto,
    paddingVertical: 8,
  },

  botaoScanner: {
    width: 42,

    height: 42,

    borderRadius: RAIO.md,

    borderWidth: 1,

    borderColor: CORES.primario,

    justifyContent: "center",

    alignItems: "center",
  },

  botaoFiltroAtivo: {
    backgroundColor: CORES.primario,
  },

  badge: {
    position: "absolute",

    top: -4,

    right: -4,

    backgroundColor: CORES.secundario,

    borderRadius: 10,

    minWidth: 16,

    height: 16,

    justifyContent: "center",

    alignItems: "center",
  },

  badgeNum: { color: "#fff", fontSize: 10, fontWeight: "bold" },

  resumoContainer: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    gap: ESPACO.sm,

    paddingHorizontal: ESPACO.md,

    paddingBottom: ESPACO.sm,

    backgroundColor: CORES.superficie,

    borderBottomWidth: 1,

    borderBottomColor: CORES.borda,
  },

  filtroChip: {
    borderWidth: 1,

    borderColor: CORES.borda,

    borderRadius: 999,

    paddingHorizontal: 12,

    paddingVertical: 8,

    backgroundColor: "#fff",
  },

  filtroChipAtivo: {
    borderColor: "#16A34A",

    backgroundColor: "#F0FDF4",
  },

  filtroChipTexto: {
    fontSize: 12,

    fontWeight: "600",

    color: CORES.textoSecundario,
  },

  filtroChipTextoAtivo: {
    color: "#166534",
  },

  resumoCatalogo: {
    marginTop: ESPACO.xs,

    fontSize: 12,

    color: CORES.textoClaro,
  },

  ordenacaoResumo: {
    fontSize: 12,

    color: CORES.primario,

    fontWeight: "700",
  },

  modalBackdrop: {
    flex: 1,

    justifyContent: "flex-end",

    backgroundColor: "rgba(17, 24, 39, 0.45)",
  },

  modalCard: {
    height: "88%",

    backgroundColor: CORES.superficie,

    borderTopLeftRadius: RAIO.lg,

    borderTopRightRadius: RAIO.lg,

    paddingTop: ESPACO.md,
  },

  modalScroll: {
    flex: 1,
  },

  modalHeader: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "flex-start",

    paddingHorizontal: ESPACO.lg,

    paddingBottom: ESPACO.md,

    borderBottomWidth: 1,

    borderBottomColor: CORES.borda,
  },

  modalTitulo: {
    fontSize: FONTE.grande,

    fontWeight: "800",

    color: CORES.texto,
  },

  modalSubtitulo: {
    marginTop: 2,

    fontSize: FONTE.pequena,

    color: CORES.textoSecundario,
  },

  modalFechar: {
    width: 36,

    height: 36,

    borderRadius: 18,

    backgroundColor: CORES.fundo,

    justifyContent: "center",

    alignItems: "center",
  },

  modalConteudo: {
    padding: ESPACO.lg,

    paddingBottom: ESPACO.md,

    gap: ESPACO.lg,
  },

  filtroSecao: {
    gap: ESPACO.sm,
  },

  filtroSecaoTitulo: {
    fontSize: FONTE.normal,

    fontWeight: "800",

    color: CORES.texto,
  },

  filtroOpcoes: {
    flexDirection: "row",

    flexWrap: "wrap",

    gap: ESPACO.xs,
  },

  marcaBuscaContainer: {
    width: "100%",

    minHeight: 42,

    flexDirection: "row",

    alignItems: "center",

    gap: ESPACO.xs,

    borderWidth: 1,

    borderColor: CORES.borda,

    borderRadius: RAIO.md,

    paddingHorizontal: ESPACO.sm,

    backgroundColor: CORES.fundo,
  },

  marcaBuscaInput: {
    flex: 1,

    minWidth: 0,

    fontSize: FONTE.normal,

    color: CORES.texto,

    paddingVertical: 8,
  },

  marcaSelecionadaTexto: {
    width: "100%",

    fontSize: FONTE.pequena,

    fontWeight: "700",

    color: CORES.primario,
  },

  filtroVazioTexto: {
    width: "100%",

    fontSize: FONTE.pequena,

    color: CORES.textoClaro,
  },

  modalAcoes: {
    flexDirection: "row",

    gap: ESPACO.sm,

    padding: ESPACO.lg,

    paddingTop: ESPACO.md,

    borderTopWidth: 1,

    borderTopColor: CORES.borda,
  },

  botaoLimpar: {
    flex: 1,

    minHeight: 44,

    borderRadius: RAIO.md,

    borderWidth: 1,

    borderColor: CORES.borda,

    justifyContent: "center",

    alignItems: "center",
  },

  botaoLimparTexto: {
    color: CORES.textoSecundario,

    fontWeight: "800",
  },

  botaoAplicar: {
    flex: 1.4,

    minHeight: 44,

    borderRadius: RAIO.md,

    backgroundColor: CORES.primario,

    justifyContent: "center",

    alignItems: "center",
  },

  botaoAplicarTexto: {
    color: "#fff",

    fontWeight: "800",
  },

  lista: { padding: ESPACO.sm, paddingBottom: ESPACO.lg },

  colunaPar: {
    justifyContent: "space-between",
    paddingHorizontal: ESPACO.xs,
    alignItems: "stretch",
  },

  card: {
    width: "48%",
    minHeight: 316,
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    marginBottom: ESPACO.sm,
    overflow: "hidden",
    ...SOMBRA,
  },

  cardIndisponivel: { opacity: 0.86 },
  cardTopo: { position: "relative" },
  foto: { width: "100%", height: 130 },

  fotoPlaceholder: {
    backgroundColor: CORES.primarioClaro,
    justifyContent: "center",
    alignItems: "center",
  },

  badgePromocao: {
    position: "absolute",
    top: 8,
    left: 8,
    backgroundColor: CORES.secundario,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: RAIO.circulo,
  },

  badgeIndisponivel: {
    position: "absolute",
    top: 8,
    left: 8,
    backgroundColor: "#D97706",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: RAIO.circulo,
  },

  badgeTexto: { color: "#fff", fontSize: FONTE.pequena, fontWeight: "bold" },

  botaoWishlist: {
    position: "absolute",
    top: 6,
    right: 6,
    backgroundColor: "#fff",
    borderRadius: 20,
    width: 30,
    height: 30,
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.15,
    shadowRadius: 2,
    elevation: 2,
  },

  cardInfo: { padding: ESPACO.sm, flex: 1 },

  produtoNome: {
    fontSize: FONTE.normal,
    fontWeight: "600",
    color: CORES.texto,
    marginBottom: 2,
    lineHeight: 18,
    minHeight: 36,
  },

  categoriaTexto: { fontSize: 10, color: CORES.textoClaro, marginBottom: 1 },
  skuTexto: { fontSize: 10, color: CORES.textoClaro, marginBottom: 2 },
  estoqueTexto: {
    fontSize: 10,
    color: "#10B981",
    fontWeight: "500",
    marginBottom: 4,
    minHeight: 14,
  },
  estoqueZero: { color: "#D97706" },
  precoRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: ESPACO.sm,
    minHeight: 22,
  },

  precoOriginal: {
    fontSize: FONTE.pequena,
    color: CORES.textoClaro,
    textDecorationLine: "line-through",
  },

  preco: { fontSize: FONTE.normal, fontWeight: "bold", color: CORES.primario },
  precoIndisponivel: { color: CORES.textoClaro },

  botaoAdicionar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: CORES.primario,
    borderRadius: RAIO.sm,
    paddingVertical: 7,
    minHeight: 36,
    marginTop: "auto",
    gap: 4,
  },

  botaoAdicionarTexto: {
    color: "#fff",
    fontSize: FONTE.pequena,
    fontWeight: "600",
  },

  botaoAviseme: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
    borderWidth: 1,
    borderColor: "#D97706",
    borderRadius: RAIO.sm,
    paddingVertical: 7,
    minHeight: 36,
    marginTop: "auto",
  },

  botaoAvisemeTexto: { color: "#D97706", fontSize: 10, fontWeight: "600" },
  loading: { flex: 1, justifyContent: "center", alignItems: "center" },
  vazio: { alignItems: "center", paddingTop: 60, gap: 8 },
  vazioTexto: {
    fontSize: FONTE.grande,
    fontWeight: "600",
    color: CORES.textoSecundario,
  },
  vazioSubtexto: {
    fontSize: FONTE.normal,
    color: CORES.textoClaro,
    textAlign: "center",
  },
});
