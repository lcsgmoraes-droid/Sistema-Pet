import { Ionicons } from "@expo/vector-icons";
import React, { useCallback, useState } from "react";
import { ActivityIndicator, Modal, ScrollView, Text, TouchableOpacity, View } from "react-native";

import api from "../../../services/api";
import { CORES, ESPACO } from "../../../theme";
import { beneficiosStyles as styles } from "./BeneficiosStyles";
import { brl, type ExtratoCashback, type SugestaoCashback } from "./BeneficiosUtils";

export function BeneficiosCashbackSection({
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
