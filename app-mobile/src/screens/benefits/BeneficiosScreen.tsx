import { Ionicons } from "@expo/vector-icons";
import * as Clipboard from "expo-clipboard";
import { useNavigation } from "@react-navigation/native";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Modal,
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
  silver_min_months: number;
  gold_min_spent: number;
  gold_min_purchases: number;
  gold_min_months: number;
  diamond_min_spent: number;
  diamond_min_purchases: number;
  diamond_min_months: number;
  platinum_min_spent: number;
  platinum_min_purchases: number;
  platinum_min_months: number;
}

interface ExtratoCashback {
  saldo_atual: number;
  transacoes: {
    id: number;
    amount: number;
    tx_type: string; // 'credit' | 'debit' | 'expired'
    source_type: string;
    description: string | null;
    created_at: string | null;
    expires_at: string | null;
    expired: boolean;
  }[];
}

interface SugestaoCashback {
  saldo_disponivel: number;
  ticket_sugerido: number;
  valor_com_cashback: number;
  economia: number;
  proximo_expirando: {
    amount: number;
    expires_at: string;
    dias_restantes: number;
  } | null;
}

interface Beneficios {
  cashback: { saldo: number };
  carimbos: {
    total_geral: number;
    carimbos_no_cartao: number;
    carimbos_ativos_brutos: number;
    carimbos_comprometidos_total: number;
    carimbos_convertidos: number;
    carimbos_em_debito: number;
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
    id: number | string;
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

const THRESHOLD_PURCHASES_KEY: Record<string, keyof RankingThresholds> = {
  silver: "silver_min_purchases",
  gold: "gold_min_purchases",
  diamond: "diamond_min_purchases",
  platinum: "platinum_min_purchases",
};

const THRESHOLD_MONTHS_KEY: Record<string, keyof RankingThresholds> = {
  silver: "silver_min_months",
  gold: "gold_min_months",
  diamond: "diamond_min_months",
  platinum: "platinum_min_months",
};

function brl(valor: number): string {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function numero(valor: unknown, fallback = 0): number {
  const n = Number(valor);
  return Number.isFinite(n) ? n : fallback;
}

function inteiro(valor: unknown, fallback = 0): number {
  return Math.max(0, Math.trunc(numero(valor, fallback)));
}

function nivelSeguro(nivel: unknown): string {
  const normalizado = String(nivel || "bronze").toLowerCase();
  return NIVEL_ORDEM.includes(normalizado) ? normalizado : "bronze";
}

function normalizarBeneficios(raw: any): Beneficios {
  const thresholds = raw?.ranking?.thresholds || {};
  const cuponsRaw = Array.isArray(raw?.cupons) ? raw.cupons : [];

  return {
    cashback: {
      saldo: numero(raw?.cashback?.saldo),
    },
    carimbos: {
      total_geral: inteiro(raw?.carimbos?.total_geral),
      carimbos_no_cartao: inteiro(raw?.carimbos?.carimbos_no_cartao),
      carimbos_ativos_brutos: inteiro(raw?.carimbos?.carimbos_ativos_brutos),
      carimbos_comprometidos_total: inteiro(
        raw?.carimbos?.carimbos_comprometidos_total,
      ),
      carimbos_convertidos: inteiro(raw?.carimbos?.carimbos_convertidos),
      carimbos_em_debito: inteiro(raw?.carimbos?.carimbos_em_debito),
      meta: Math.max(1, inteiro(raw?.carimbos?.meta, 10)),
      min_purchase_value: numero(raw?.carimbos?.min_purchase_value),
    },
    ranking: {
      nivel: nivelSeguro(raw?.ranking?.nivel),
      total_spent: numero(raw?.ranking?.total_spent),
      total_purchases: inteiro(raw?.ranking?.total_purchases),
      thresholds: {
        silver_min_spent: numero(thresholds.silver_min_spent, 300),
        silver_min_purchases: inteiro(thresholds.silver_min_purchases, 4),
        silver_min_months: inteiro(thresholds.silver_min_months, 2),
        gold_min_spent: numero(thresholds.gold_min_spent, 1000),
        gold_min_purchases: inteiro(thresholds.gold_min_purchases, 10),
        gold_min_months: inteiro(thresholds.gold_min_months, 4),
        diamond_min_spent: numero(thresholds.diamond_min_spent, 3000),
        diamond_min_purchases: inteiro(thresholds.diamond_min_purchases, 20),
        diamond_min_months: inteiro(thresholds.diamond_min_months, 6),
        platinum_min_spent: numero(thresholds.platinum_min_spent, 8000),
        platinum_min_purchases: inteiro(thresholds.platinum_min_purchases, 40),
        platinum_min_months: inteiro(thresholds.platinum_min_months, 10),
      },
    },
    cupons: cuponsRaw
      .map((c: any) => {
        const code = String(c?.code || c?.codigo || "").trim();
        if (!code) return null;
        return {
          id: inteiro(c?.id) || code,
          code,
          coupon_type: String(c?.coupon_type || c?.tipo_desconto || ""),
          discount_value:
            c?.discount_value != null
              ? numero(c.discount_value)
              : c?.valor_desconto != null
                ? numero(c.valor_desconto)
                : null,
          discount_percent:
            c?.discount_percent != null ? numero(c.discount_percent) : null,
          valid_until: c?.valid_until ?? null,
          expirado: Boolean(c?.expirado),
          min_purchase_value:
            c?.min_purchase_value != null
              ? numero(c.min_purchase_value)
              : c?.valor_minimo_pedido != null
                ? numero(c.valor_minimo_pedido)
                : null,
        };
      })
      .filter(Boolean) as Beneficios["cupons"],
  };
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
            Gasto nos últimos 12 meses: R$ {brl(total_spent)}
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
            em gastos nos últimos 12 meses para {NIVEL_PT[proximoNivel]}
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
  const {
    total_geral,
    carimbos_no_cartao,
    carimbos_ativos_brutos,
    carimbos_comprometidos_total,
    carimbos_em_debito,
    meta,
    min_purchase_value,
  } = carimbos;
  const saldoNoCartao = Math.max(carimbos_no_cartao || 0, 0);
  const filled = Math.min(saldoNoCartao, meta);
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

      {carimbos_em_debito > 0 && (
        <Text
          style={[styles.carimbosInfo, { color: CORES.erro, fontWeight: "700" }]}
        >
          Debito fidelidade: {carimbos_em_debito} carimbo(s)
        </Text>
      )}

      <Text style={styles.carimbosInfo}>
        Saldo atual: {total_geral} · Ativos: {carimbos_ativos_brutos} · Comprometidos: {carimbos_comprometidos_total}
      </Text>

      {min_purchase_value > 0 && (
        <Text style={styles.carimbosInfo}>
          Cada compra a partir de R$ {brl(min_purchase_value)} garante 1 carimbo
        </Text>
      )}
    </View>
  );
}

function SecaoCashback({
  saldo,
  customerId,
}: {
  saldo: number;
  customerId?: number;
}) {
  const [modalAberto, setModalAberto] = useState(false);
  const [extrato, setExtrato] = useState<ExtratoCashback | null>(null);
  const [sugestao, setSugestao] = useState<SugestaoCashback | null>(null);
  const [loadingExtrato, setLoadingExtrato] = useState(false);

  const abrirExtrato = useCallback(async () => {
    setModalAberto(true);
    if (extrato) return; // já carregado
    setLoadingExtrato(true);
    try {
      const [extRes, sugRes] = await Promise.all([
        api.get<ExtratoCashback>("/ecommerce/auth/cashback/extrato"),
        api.get<SugestaoCashback>("/ecommerce/auth/cashback/sugestao"),
      ]);
      setExtrato(extRes.data);
      setSugestao(sugRes.data);
    } catch {
      // silencia, modal mostra fallback
    } finally {
      setLoadingExtrato(false);
    }
  }, [extrato]);

  const iconeTransacao = (tx_type: string) => {
    if (tx_type === "credit")
      return { nome: "arrow-down-circle", cor: CORES.sucesso };
    if (tx_type === "expired") return { nome: "time-outline", cor: CORES.erro };
    return { nome: "arrow-up-circle", cor: "#F59E0B" }; // debit
  };

  const labelTransacao = (tx_type: string) => {
    if (tx_type === "credit") return "Entrada";
    if (tx_type === "expired") return "Expirado";
    return "Sa\u00edda";
  };

  return (
    <>
      <TouchableOpacity
        style={[styles.secao, styles.secaoCashback]}
        onPress={abrirExtrato}
        activeOpacity={0.75}
      >
        <View style={styles.secaoTitulo}>
          <Ionicons name="cash-outline" size={20} color={CORES.sucesso} />
          <Text style={styles.secaoTituloTexto}>Saldo de Cashback</Text>
          <Ionicons
            name="chevron-forward"
            size={16}
            color={CORES.textoSecundario}
            style={{ marginLeft: "auto" }}
          />
        </View>
        <Text style={styles.cashbackValor}>R$ {brl(saldo)}</Text>
        <Text style={styles.cashbackInfo}>
          Toque para ver extrato e vantagens
        </Text>
      </TouchableOpacity>

      <Modal
        visible={modalAberto}
        animationType="slide"
        transparent
        onRequestClose={() => setModalAberto(false)}
      >
        <View style={styles.extratoOverlay}>
          <View style={styles.extratoContainer}>
            {/* Cabeçalho */}
            <View style={styles.extratoHeader}>
              <Text style={styles.extratoTitulo}>Cashback</Text>
              <TouchableOpacity onPress={() => setModalAberto(false)}>
                <Ionicons name="close" size={24} color={CORES.texto} />
              </TouchableOpacity>
            </View>

            {/* Saldo */}
            <View style={styles.extratoSaldoBox}>
              <Text style={styles.extratoSaldoLabel}>
                Saldo dispon\u00edvel
              </Text>
              <Text style={styles.extratoSaldoValor}>
                R$ {brl(extrato?.saldo_atual ?? saldo)}
              </Text>
            </View>

            {/* Sugest\u00e3o inteligente */}
            {sugestao && sugestao.economia > 0 && (
              <View style={styles.extratoSugestao}>
                <Ionicons name="bulb-outline" size={18} color="#F59E0B" />
                <Text style={styles.extratoSugestaoTexto}>
                  Numa pr\u00f3xima compra de{" "}
                  <Text style={{ fontWeight: "700" }}>
                    R$ {brl(sugestao.ticket_sugerido)}
                  </Text>
                  , voc\u00ea pagaria apenas{" "}
                  <Text style={{ fontWeight: "700", color: CORES.sucesso }}>
                    R$ {brl(sugestao.valor_com_cashback)}
                  </Text>{" "}
                  usando seu cashback!
                </Text>
              </View>
            )}

            {/* Alerta de expira\u00e7\u00e3o */}
            {sugestao?.proximo_expirando && (
              <View style={styles.extratoAlertaExpira}>
                <Ionicons name="warning-outline" size={16} color={CORES.erro} />
                <Text style={styles.extratoAlertaTexto}>
                  R$ {brl(sugestao.proximo_expirando.amount)} expiram em{" "}
                  {sugestao.proximo_expirando.dias_restantes === 0
                    ? "hoje!"
                    : `${sugestao.proximo_expirando.dias_restantes} dia(s)`}
                </Text>
              </View>
            )}

            {/* Extrato */}
            <Text style={styles.extratoSubtitulo}>Movimenta\u00e7\u00f5es</Text>

            {loadingExtrato ? (
              <ActivityIndicator
                color={CORES.primario}
                style={{ marginVertical: ESPACO.lg }}
              />
            ) : extrato && extrato.transacoes.length > 0 ? (
              <ScrollView
                style={styles.extratoLista}
                showsVerticalScrollIndicator={false}
              >
                {extrato.transacoes.map((tx) => {
                  const icone = iconeTransacao(tx.tx_type);
                  const dataF = tx.created_at
                    ? new Date(tx.created_at).toLocaleDateString("pt-BR")
                    : "";
                  return (
                    <View key={tx.id} style={styles.extratoItem}>
                      <Ionicons
                        name={icone.nome as any}
                        size={22}
                        color={icone.cor}
                        style={{ marginRight: ESPACO.sm }}
                      />
                      <View style={{ flex: 1 }}>
                        <Text style={styles.extratoItemDesc} numberOfLines={2}>
                          {tx.description ?? labelTransacao(tx.tx_type)}
                        </Text>
                        <Text style={styles.extratoItemData}>{dataF}</Text>
                        {tx.expires_at &&
                          tx.tx_type === "credit" &&
                          !tx.expired && (
                            <Text
                              style={[
                                styles.extratoItemData,
                                { color: "#F59E0B" },
                              ]}
                            >
                              Expira:{" "}
                              {new Date(tx.expires_at).toLocaleDateString(
                                "pt-BR",
                              )}
                            </Text>
                          )}
                      </View>
                      <Text
                        style={[
                          styles.extratoItemValor,
                          {
                            color:
                              tx.tx_type === "credit"
                                ? CORES.sucesso
                                : CORES.erro,
                          },
                        ]}
                      >
                        {tx.amount > 0 ? "+" : ""}R$ {brl(Math.abs(tx.amount))}
                      </Text>
                    </View>
                  );
                })}
              </ScrollView>
            ) : (
              <Text style={[styles.vazioTexto, { marginVertical: ESPACO.md }]}>
                Nenhuma movimenta\u00e7\u00e3o ainda
              </Text>
            )}

            <TouchableOpacity
              style={styles.extratoFechar}
              onPress={() => setModalAberto(false)}
            >
              <Text style={styles.extratoFecharTexto}>Fechar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </>
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

  const copiar = async (codigo: string) => {
    await Clipboard.setStringAsync(codigo);
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
  const [aberto, setAberto] = useState(false);

  if (proximosNiveis.length === 0) return null;

  return (
    <View style={styles.secao}>
      <TouchableOpacity
        onPress={() => setAberto(!aberto)}
        style={styles.secaoTituloExpansivel}
        activeOpacity={0.7}
      >
        <View style={[styles.secaoTitulo, { marginBottom: 0 }]}>
          <Ionicons
            name="trending-up-outline"
            size={20}
            color={CORES.primario}
          />
          <Text style={styles.secaoTituloTexto}>Próximos Níveis</Text>
        </View>
        <Ionicons
          name={aberto ? "chevron-up" : "chevron-down"}
          size={18}
          color={CORES.textoSecundario}
        />
      </TouchableOpacity>

      {aberto && (
        <>
          <Text style={styles.proximosSubtitulo}>
            Requisitos medidos nos últimos 12 meses
          </Text>
          {proximosNiveis.map((lvl) => {
            const cor = NIVEL_COR[lvl] ?? CORES.primario;
            const keyGasto = THRESHOLD_KEY[lvl] as
              | keyof RankingThresholds
              | undefined;
            const keyCompras = THRESHOLD_PURCHASES_KEY[lvl] as
              | keyof RankingThresholds
              | undefined;
            const keyMeses = THRESHOLD_MONTHS_KEY[lvl] as
              | keyof RankingThresholds
              | undefined;
            const metaGasto = keyGasto ? thresholds[keyGasto] : null;
            const metaCompras = keyCompras ? thresholds[keyCompras] : null;
            const metaMeses = keyMeses ? thresholds[keyMeses] : null;
            const vantagens = NIVEL_VANTAGENS[lvl] ?? [];
            const requisitos = [
              metaGasto ? `R$ ${brl(metaGasto)} em gastos` : false,
              metaCompras ? `${metaCompras} compras` : false,
              metaMeses ? `${metaMeses} meses ativos` : false,
            ].filter(Boolean) as string[];
            return (
              <View
                key={lvl}
                style={[styles.nivelCard, { borderLeftColor: cor }]}
              >
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
                    {requisitos.length > 0 && (
                      <Text style={styles.nivelMeta}>
                        {requisitos.join(" · ")} nos últimos 12 meses
                      </Text>
                    )}
                  </View>
                </View>
                {vantagens.map((v, i) => (
                  <View key={i} style={styles.vantagemItemFuturo}>
                    <Text
                      style={[styles.vantagemCheckmarkFuturo, { color: cor }]}
                    >
                      ✦
                    </Text>
                    <Text style={styles.vantagemTextoFuturo}>{v}</Text>
                  </View>
                ))}
              </View>
            );
          })}
        </>
      )}
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
      setDados(normalizarBeneficios(data));
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
      <SecaoCarimbos carimbos={dados.carimbos} />
      <SecaoCashback saldo={dados.cashback.saldo} />
      <SecaoCupons
        cupons={dados.cupons}
        onVerTodos={() => navigation.navigate("MeusCupons")}
      />
      <SecaoProximosNiveis ranking={dados.ranking} />
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
