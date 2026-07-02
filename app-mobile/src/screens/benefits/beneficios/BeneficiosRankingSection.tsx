import React from "react";
import { Text, View } from "react-native";

import { CORES, ESPACO } from "../../../theme";
import { beneficiosStyles as styles } from "./BeneficiosStyles";
import {
  NIVEL_COR,
  NIVEL_ORDEM,
  NIVEL_PT,
  NIVEL_VANTAGENS,
  THRESHOLD_KEY,
  brl,
  type Beneficios,
} from "./BeneficiosUtils";

export function BeneficiosRankingSection({ ranking }: { ranking: Beneficios["ranking"] }) {
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
