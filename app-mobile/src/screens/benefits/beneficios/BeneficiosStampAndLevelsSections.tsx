import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { Text, TouchableOpacity, View } from "react-native";

import { CORES, ESPACO } from "../../../theme";
import { beneficiosStyles as styles } from "./BeneficiosStyles";
import {
  NIVEL_COR,
  NIVEL_ORDEM,
  NIVEL_PT,
  NIVEL_VANTAGENS,
  THRESHOLD_KEY,
  THRESHOLD_MONTHS_KEY,
  THRESHOLD_PURCHASES_KEY,
  brl,
  type Beneficios,
  type RankingThresholds,
} from "./BeneficiosUtils";

export function BeneficiosStampSection({ carimbos }: { carimbos: Beneficios["carimbos"] }) {
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

export function BeneficiosNextLevelsSection({ ranking }: { ranking: Beneficios["ranking"] }) {
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
