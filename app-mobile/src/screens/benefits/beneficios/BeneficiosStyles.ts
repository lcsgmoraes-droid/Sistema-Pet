import { StyleSheet } from "react-native";

import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../../theme";

export const beneficiosStyles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: CORES.fundo },
  conteudo: { padding: ESPACO.md, paddingBottom: ESPACO.xxl },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: ESPACO.xl,
  },

  secao: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginBottom: ESPACO.md,
    ...SOMBRA,
  },
  secaoCashback: {},

  secaoTitulo: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: ESPACO.sm,
    gap: ESPACO.xs,
  },
  secaoTituloTexto: {
    fontSize: FONTE.media,
    fontWeight: "700",
    color: CORES.texto,
    marginLeft: ESPACO.xs,
  },

  // Ranking
  rankingTopo: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: ESPACO.sm,
  },
  rankingBadge: {
    width: 52,
    height: 52,
    borderRadius: RAIO.circulo,
    justifyContent: "center",
    alignItems: "center",
  },
  rankingBadgeTexto: { fontSize: 24, fontWeight: "800", color: "#fff" },
  rankingNivel: {
    fontSize: FONTE.grande,
    fontWeight: "800",
    color: CORES.texto,
  },
  rankingGasto: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
    marginTop: 2,
  },
  vantagens: { marginBottom: ESPACO.sm },
  vantagemItem: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 3,
  },
  vantagemCheckmark: {
    fontSize: FONTE.normal,
    fontWeight: "700",
    marginRight: 6,
  },
  vantagemTexto: {
    flex: 1,
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
  },
  verTodosBotao: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-end",
    paddingVertical: ESPACO.xs,
    marginTop: ESPACO.sm,
    gap: 4,
  },
  verTodosTexto: {
    fontSize: FONTE.pequena,
    color: CORES.primario,
    fontWeight: "600",
  },
  progressoTrilha: {
    height: 8,
    borderRadius: RAIO.circulo,
    backgroundColor: CORES.borda,
    overflow: "hidden",
    marginBottom: ESPACO.xs,
  },
  progressoBarra: { height: 8, borderRadius: RAIO.circulo },
  progressoTexto: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
    marginTop: 2,
  },

  // Carimbos
  carimbosGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginBottom: ESPACO.sm,
  },
  carimbo: {
    width: 30,
    height: 30,
    borderRadius: RAIO.circulo,
    justifyContent: "center",
    alignItems: "center",
  },
  carimboAtivo: { backgroundColor: CORES.pontos },
  carimboVazio: {
    backgroundColor: CORES.borda,
    borderWidth: 1.5,
    borderColor: CORES.textoClaro,
  },
  carimbosProgresso: {
    fontSize: FONTE.normal,
    color: CORES.texto,
    fontWeight: "600",
  },
  carimbosInfo: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
    marginTop: 4,
  },

  // Cashback
  cashbackValor: {
    fontSize: 32,
    fontWeight: "800",
    color: CORES.sucesso,
    marginBottom: 4,
  },
  cashbackInfo: { fontSize: FONTE.pequena, color: CORES.textoSecundario },

  // Modal Extrato Cashback
  extratoOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "flex-end",
  },
  extratoContainer: {
    backgroundColor: CORES.superficie,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: ESPACO.lg,
    maxHeight: "85%",
  },
  extratoHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: ESPACO.md,
  },
  extratoTitulo: {
    fontSize: FONTE.grande,
    fontWeight: "800",
    color: CORES.texto,
  },
  extratoSaldoBox: {
    backgroundColor: CORES.primarioClaro,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    alignItems: "center",
    marginBottom: ESPACO.md,
  },
  extratoSaldoLabel: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
    marginBottom: 4,
  },
  extratoSaldoValor: {
    fontSize: 36,
    fontWeight: "900",
    color: CORES.sucesso,
  },
  extratoSugestao: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: "#FFFBEB",
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
    marginBottom: ESPACO.sm,
    gap: ESPACO.xs,
  },
  extratoSugestaoTexto: {
    flex: 1,
    fontSize: FONTE.pequena,
    color: CORES.texto,
    lineHeight: 18,
  },
  extratoAlertaExpira: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FEF2F2",
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
    marginBottom: ESPACO.sm,
    gap: ESPACO.xs,
  },
  extratoAlertaTexto: {
    fontSize: FONTE.pequena,
    color: CORES.erro,
    fontWeight: "600",
  },
  extratoSubtitulo: {
    fontSize: FONTE.normal,
    fontWeight: "700",
    color: CORES.texto,
    marginBottom: ESPACO.sm,
    marginTop: ESPACO.xs,
  },
  extratoLista: {
    maxHeight: 280,
  },
  extratoItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: ESPACO.sm,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
  },
  extratoItemDesc: {
    fontSize: FONTE.pequena,
    color: CORES.texto,
    flex: 1,
  },
  extratoItemData: {
    fontSize: FONTE.pequena - 1,
    color: CORES.textoSecundario,
    marginTop: 2,
  },
  extratoItemValor: {
    fontSize: FONTE.normal,
    fontWeight: "700",
    marginLeft: ESPACO.sm,
    minWidth: 80,
    textAlign: "right",
  },
  extratoFechar: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    alignItems: "center",
    marginTop: ESPACO.md,
  },
  extratoFecharTexto: {
    color: "#fff",
    fontWeight: "700",
    fontSize: FONTE.normal,
  },

  // Cupons
  cupomCard: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
    marginBottom: ESPACO.sm,
    backgroundColor: CORES.primarioClaro,
  },
  cupomExpirado: { backgroundColor: CORES.fundo, borderStyle: "dashed" },
  cupomTopo: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  cupomCodigo: { flexDirection: "row", alignItems: "center", flex: 1 },
  cupomCodigoTexto: {
    fontSize: FONTE.media,
    fontWeight: "700",
    color: CORES.primario,
    letterSpacing: 1,
  },
  cupomBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: RAIO.circulo,
  },
  cupomBadgeAtivo: { backgroundColor: "#DCFCE7" },
  cupomBadgeExp: { backgroundColor: CORES.borda },
  cupomBadgeTexto: {
    fontSize: FONTE.pequena,
    fontWeight: "600",
    color: CORES.sucesso,
  },
  cupomDesconto: {
    fontSize: FONTE.normal,
    color: CORES.texto,
    fontWeight: "600",
  },
  cupomInfo: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
    marginTop: 2,
  },

  textoExpirado: { color: CORES.textoClaro },
  vazioTexto: {
    fontSize: FONTE.normal,
    color: CORES.textoClaro,
    textAlign: "center",
    paddingVertical: ESPACO.md,
  },

  erroTexto: {
    fontSize: FONTE.media,
    color: CORES.textoSecundario,
    textAlign: "center",
    marginTop: ESPACO.md,
    marginBottom: ESPACO.md,
  },
  btnRetentar: {
    backgroundColor: CORES.primario,
    paddingHorizontal: ESPACO.lg,
    paddingVertical: ESPACO.sm,
    borderRadius: RAIO.md,
  },
  btnRetentarTexto: {
    color: "#fff",
    fontWeight: "700",
    fontSize: FONTE.normal,
  },

  // Próximos Níveis
  secaoTituloExpansivel: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 0,
  },
  proximosSubtitulo: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
    marginTop: ESPACO.xs,
    marginBottom: ESPACO.sm,
  },
  nivelCard: {
    borderLeftWidth: 3,
    borderRadius: RAIO.sm,
    backgroundColor: CORES.fundo,
    padding: ESPACO.sm,
    marginBottom: ESPACO.sm,
  },
  nivelCardTopo: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: ESPACO.xs,
  },
  nivelBadgePequeno: {
    width: 36,
    height: 36,
    borderRadius: RAIO.circulo,
    justifyContent: "center",
    alignItems: "center",
  },
  nivelBadgePequenoTexto: { fontSize: 16, fontWeight: "800", color: "#fff" },
  nivelNome: { fontSize: FONTE.normal, fontWeight: "700" },
  nivelMeta: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
    marginTop: 1,
  },
  vantagemItemFuturo: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 2,
  },
  vantagemCheckmarkFuturo: {
    fontSize: FONTE.pequena,
    fontWeight: "700",
    marginRight: 6,
    marginTop: 1,
  },
  vantagemTextoFuturo: {
    flex: 1,
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
  },
});
