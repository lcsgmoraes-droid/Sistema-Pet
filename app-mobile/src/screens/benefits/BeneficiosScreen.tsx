import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Clipboard,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import api from "../../services/api";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

interface RankingThresholds {
  silver_min_spent: number;
  silver_min_purchases: number;
  gold_min_spent: number;
  gold_min_purchases: number;
  diamond_min_spent: number;
  diamond_min_purchases: number;
  platinum_min_spent: number;
  platinum_min_purchases: number;
}

interface Beneficios {
  cashback: { saldo: number };
  carimbos: {
    total_geral: number;
    carimbos_no_cartao: number;
    meta: number;
    min_purchase_value: number;
  };
  ranking: {
    nivel: string;
    total_spent: number;
    total_purchases: number;
    thresholds: RankingThresholds;
  };
  cupons: {
    id: number;
    code: string;
    coupon_type: string;
    discount_value: number | null;
    discount_percent: number | null;
    valid_until: string | null;
    expirado: boolean;
    min_purchase_value: number | null;
  }[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const NIVEL_ORDEM = ["bronze", "silver", "gold", "diamond", "platinum"];

const NIVEL_PT: Record<string, string> = {
  bronze: "Bronze",
  silver: "Prata",
  gold: "Ouro",
  diamond: "Diamante",
  platinum: "Platina",
};

const NIVEL_COR: Record<string, string> = {
  bronze: "#CD7F32",
  silver: "#9CA3AF",
  gold: "#F59E0B",
  diamond: "#06B6D4",
  platinum: "#8B5CF6",
};

const NIVEL_VANTAGENS: Record<string, string[]> = {
  bronze: [
    "Cashback básico em todas as compras",
    "Participa do Cartão Fidelidade",
    "Cupom de boas-vindas",
  ],
  silver: [
    "Cashback maior",
    "Participa de sorteios mensais",
    "Cupom de aniversário especial",
  ],
  gold: [
    "Cashback alto",
    "Sorteios com prêmios melhores",
    "Brinde mensal na loja",
  ],
  diamond: [
    "Cashback premium",
    "Sorteios exclusivos Diamante",
    "Ofertas antecipadas",
  ],
  platinum: [
    "Cashback máximo",
    "Sorteios exclusivos Platina",
    "Destaque do mês",
    "Atendimento prioritário",
  ],
};

const THRESHOLD_KEY: Record<string, keyof RankingThresholds> = {
  silver: "silver_min_spent",
  gold: "gold_min_spent",
  diamond: "diamond_min_spent",
  platinum: "platinum_min_spent",
};

function brl(valor: number): string {
  return valor.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatarDesconto(item: Beneficios["cupons"][number]): string {
  if (item.discount_percent != null)
    return `${item.discount_percent}% de desconto`;
  if (item.discount_value != null)
    return `R$ ${brl(item.discount_value)} de desconto`;
  return "Desconto especial";
}

function diasRestantes(isoDate: string | null): string | null {
  if (!isoDate) return null;
  const diff = new Date(isoDate).getTime() - Date.now();
  const dias = Math.ceil(diff / (1000 * 60 * 60 * 24));
  if (dias < 0) return "Expirado";
  if (dias === 0) return "Expira hoje!";
  if (dias === 1) return "Expira amanhã";
  return `Expira em ${dias} dias`;
}

// ---------------------------------------------------------------------------
// Sub-componentes
// ---------------------------------------------------------------------------

function SecaoRanking({ ranking }: { ranking: Beneficios["ranking"] }) {
  const { nivel, total_spent, thresholds } = ranking;
  const cor = NIVEL_COR[nivel] ?? CORES.primario;
  const nomeNivel = NIVEL_PT[nivel] ?? nivel;

  const idxAtual = NIVEL_ORDEM.indexOf(nivel);
  const proximoNivel = NIVEL_ORDEM[idxAtual + 1] ?? null;
  const thresholdKey = proximoNivel ? THRESHOLD_KEY[proximoNivel] : null;
  const metaGasto = thresholdKey ? thresholds[thresholdKey] : null;

  const faltam = metaGasto == null ? 0 : Math.max(0, metaGasto - total_spent);
  const progresso = metaGasto ? Math.min(1, total_spent / metaGasto) : 1;

  return (
    <View style={[styles.secao, { borderLeftColor: cor, borderLeftWidth: 4 }]}>
      <View style={styles.rankingTopo}>
        <View style={[styles.rankingBadge, { backgroundColor: cor }]}>
          <Text style={styles.rankingBadgeTexto}>{nomeNivel[0]}</Text>
        </View>
        <View style={{ flex: 1, marginLeft: ESPACO.md }}>
          <Text style={styles.rankingNivel}>{nomeNivel}</Text>
          <Text style={styles.rankingGasto}>
            Total gasto no período: R$ {brl(total_spent)}
          </Text>
        </View>
      </View>

      <View style={styles.vantagens}>
        {(NIVEL_VANTAGENS[nivel] ?? []).map((item, i) => (
          <View key={i} style={styles.vantagemItem}>
            <Text style={[styles.vantagemCheckmark, { color: cor }]}>✓</Text>
            <Text style={styles.vantagemTexto}>{item}</Text>
          </View>
        ))}
      </View>

      {proximoNivel && metaGasto != null ? (
        <View style={{ marginTop: ESPACO.sm }}>
          <View style={styles.progressoTrilha}>
            <View
              style={[
                styles.progressoBarra,
                {
                  width: `${Math.round(progresso * 100)}%` as any,
                  backgroundColor: cor,
                },
              ]}
            />
          </View>
          <Text style={styles.progressoTexto}>
            Faltam{" "}
            <Text style={{ fontWeight: "bold", color: cor }}>
              R$ {brl(faltam)}
            </Text>{" "}
            para {NIVEL_PT[proximoNivel]}
          </Text>
        </View>
      ) : (
        <Text
          style={[styles.progressoTexto, { color: cor, fontWeight: "bold" }]}
        >
          🏆 Você atingiu o nível máximo!
        </Text>
      )}
    </View>
  );
}

function SecaoCarimbos({ carimbos }: { carimbos: Beneficios["carimbos"] }) {
  const { carimbos_no_cartao, meta, min_purchase_value } = carimbos;
  const filled = Math.min(carimbos_no_cartao, meta);
  const stamps = Array.from({ length: meta });

  return (
    <View style={styles.secao}>
      <View style={styles.secaoTitulo}>
        <Ionicons name="star-outline" size={20} color={CORES.pontos} />
        <Text style={styles.secaoTituloTexto}>Cartão Fidelidade</Text>
      </View>

      <View style={styles.carimbosGrid}>
        {stamps.map((_, i) => (
          <View
            key={i}
            style={[
              styles.carimbo,
              i < filled ? styles.carimboAtivo : styles.carimboVazio,
            ]}
          >
            {i < filled && <Ionicons name="paw" size={14} color="#fff" />}
          </View>
        ))}
      </View>

      <Text style={styles.carimbosProgresso}>
        {filled}/{meta} carimbos —{" "}
        {meta - filled === 0
          ? "🎉 Cartão completo!"
          : `faltam ${meta - filled} para ganhar a recompensa`}
      </Text>

      {min_purchase_value > 0 && (
        <Text style={styles.carimbosInfo}>
          Cada compra a partir de R$ {brl(min_purchase_value)} garante 1 carimbo
        </Text>
      )}
    </View>
  );
}

function SecaoCashback({ saldo }: { saldo: number }) {
  return (
    <View style={[styles.secao, styles.secaoCashback]}>
      <View style={styles.secaoTitulo}>
        <Ionicons name="cash-outline" size={20} color={CORES.sucesso} />
        <Text style={styles.secaoTituloTexto}>Saldo de Cashback</Text>
      </View>
      <Text style={styles.cashbackValor}>R$ {brl(saldo)}</Text>
      <Text style={styles.cashbackInfo}>
        Use ao fazer uma compra presencial no PetShop ou no checkout do app
      </Text>
    </View>
  );
}

function SecaoCupons({
  cupons,
  onVerTodos,
}: {
  cupons: Beneficios["cupons"];
  onVerTodos: () => void;
}) {
  const [copiado, setCopiado] = useState<string | null>(null);

  const copiar = (codigo: string) => {
    Clipboard.setString(codigo);
    setCopiado(codigo);
    setTimeout(() => setCopiado(null), 2000);
  };

  const ativos = cupons.filter((c) => !c.expirado);
  const expirados = cupons.filter((c) => c.expirado);
  const todos = [...ativos, ...expirados];

  return (
    <View style={styles.secao}>
      <View style={styles.secaoTitulo}>
        <Ionicons name="ticket-outline" size={20} color={CORES.primario} />
        <Text style={styles.secaoTituloTexto}>
          Cupons de Desconto
          {ativos.length > 0
            ? ` · ${ativos.length} ativo${ativos.length > 1 ? "s" : ""}`
            : ""}
        </Text>
      </View>

      {todos.length === 0 ? (
        <Text style={styles.vazioTexto}>
          Nenhum cupom disponível no momento
        </Text>
      ) : (
        todos.map((item) => {
          const prazo = diasRestantes(item.valid_until);
          return (
            <View
              key={item.id}
              style={[styles.cupomCard, item.expirado && styles.cupomExpirado]}
            >
              <View style={styles.cupomTopo}>
                <TouchableOpacity
                  onPress={() => !item.expirado && copiar(item.code)}
                  activeOpacity={item.expirado ? 1 : 0.7}
                  style={styles.cupomCodigo}
                >
                  <Text
                    style={[
                      styles.cupomCodigoTexto,
                      item.expirado && styles.textoExpirado,
                    ]}
                  >
                    {item.code}
                  </Text>
                  {!item.expirado && (
                    <Ionicons
                      name={
                        copiado === item.code ? "checkmark" : "copy-outline"
                      }
                      size={15}
                      color={
                        copiado === item.code ? CORES.sucesso : CORES.primario
                      }
                      style={{ marginLeft: 6 }}
                    />
                  )}
                </TouchableOpacity>
                <View
                  style={[
                    styles.cupomBadge,
                    item.expirado
                      ? styles.cupomBadgeExp
                      : styles.cupomBadgeAtivo,
                  ]}
                >
                  <Text
                    style={[
                      styles.cupomBadgeTexto,
                      item.expirado && styles.textoExpirado,
                    ]}
                  >
                    {item.expirado ? "Expirado" : "Ativo"}
                  </Text>
                </View>
              </View>

              <Text
                style={[
                  styles.cupomDesconto,
                  item.expirado && styles.textoExpirado,
                ]}
              >
                {formatarDesconto(item)}
              </Text>

              {item.min_purchase_value != null &&
                item.min_purchase_value > 0 && (
                  <Text style={styles.cupomInfo}>
                    Pedido mínimo: R$ {brl(item.min_purchase_value)}
                  </Text>
                )}

              {!!prazo && prazo !== "Expirado" && (
                <Text
                  style={[
                    styles.cupomInfo,
                    prazo === "Expira hoje!" && { color: CORES.erro },
                  ]}
                >
                  {prazo}
                </Text>
              )}
            </View>
          );
        })
      )}
      <Pressable onPress={onVerTodos} style={styles.verTodosBotao}>
        <Text style={styles.verTodosTexto}>Ver todos os cupons</Text>
        <Ionicons name="chevron-forward" size={14} color={CORES.primario} />
      </Pressable>
    </View>
  );
}

function SecaoProximosNiveis({ ranking }: { ranking: Beneficios["ranking"] }) {
  const { nivel, thresholds } = ranking;
  const idxAtual = NIVEL_ORDEM.indexOf(nivel);
  const proximosNiveis = NIVEL_ORDEM.slice(idxAtual + 1);

  if (proximosNiveis.length === 0) return null;

  return (
    <View style={styles.secao}>
      <View style={styles.secaoTitulo}>
        <Ionicons name="trending-up-outline" size={20} color={CORES.primario} />
        <Text style={styles.secaoTituloTexto}>Próximos Níveis</Text>
      </View>
      <Text style={styles.proximosSubtitulo}>
        Veja o que você ganha ao subir de nível
      </Text>
      {proximosNiveis.map((lvl) => {
        const cor = NIVEL_COR[lvl] ?? CORES.primario;
        const key = THRESHOLD_KEY[lvl] as keyof RankingThresholds | undefined;
        const meta = key ? thresholds[key] : null;
        const vantagens = NIVEL_VANTAGENS[lvl] ?? [];
        return (
          <View key={lvl} style={[styles.nivelCard, { borderLeftColor: cor }]}>
            <View style={styles.nivelCardTopo}>
              <View
                style={[styles.nivelBadgePequeno, { backgroundColor: cor }]}
              >
                <Text style={styles.nivelBadgePequenoTexto}>
                  {NIVEL_PT[lvl]?.[0] ?? "?"}
                </Text>
              </View>
              <View style={{ flex: 1, marginLeft: ESPACO.sm }}>
                <Text style={[styles.nivelNome, { color: cor }]}>
                  {NIVEL_PT[lvl]}
                </Text>
                {meta != null && (
                  <Text style={styles.nivelMeta}>
                    A partir de R$ {brl(meta)} em compras no período
                  </Text>
                )}
              </View>
            </View>
            {vantagens.map((v, i) => (
              <View key={i} style={styles.vantagemItemFuturo}>
                <Text style={[styles.vantagemCheckmarkFuturo, { color: cor }]}>
                  ✦
                </Text>
                <Text style={styles.vantagemTextoFuturo}>{v}</Text>
              </View>
            ))}
          </View>
        );
      })}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Tela principal
// ---------------------------------------------------------------------------

export default function BeneficiosScreen() {
  const navigation = useNavigation<any>();
  const [dados, setDados] = useState<Beneficios | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [erro, setErro] = useState(false);

  const carregar = useCallback(async () => {
    try {
      setErro(false);
      const { data } = await api.get<Beneficios>(
        "/ecommerce/auth/meus-beneficios",
      );
      setDados(data);
    } catch {
      setErro(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const onRefresh = () => {
    setRefreshing(true);
    carregar();
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={CORES.primario} />
      </View>
    );
  }

  if (erro || !dados) {
    return (
      <View style={styles.center}>
        <Ionicons name="alert-circle-outline" size={56} color={CORES.erro} />
        <Text style={styles.erroTexto}>
          Não foi possível carregar seus benefícios
        </Text>
        <TouchableOpacity style={styles.btnRetentar} onPress={carregar}>
          <Text style={styles.btnRetentarTexto}>Tentar novamente</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.conteudo}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          colors={[CORES.primario]}
          tintColor={CORES.primario}
        />
      }
    >
      <SecaoRanking ranking={dados.ranking} />
      <SecaoProximosNiveis ranking={dados.ranking} />
      <SecaoCarimbos carimbos={dados.carimbos} />
      <SecaoCashback saldo={dados.cashback.saldo} />
      <SecaoCupons
        cupons={dados.cupons}
        onVerTodos={() => navigation.navigate("MeusCupons")}
      />
    </ScrollView>
  );
}

// ---------------------------------------------------------------------------
// Estilos
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
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
  proximosSubtitulo: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
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
