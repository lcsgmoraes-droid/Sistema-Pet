import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Text, View } from "react-native";
import { GestorVendasResumo } from "../../services/gestor.service";
import { CORES } from "../../theme";
import { formatarMoeda } from "../../utils/format";
import { gestorStyles as styles } from "./GestorDashboardStyles";
import { formatIsoDateBR, formatQuantity } from "./GestorDashboardUtils";

type IconName = keyof typeof Ionicons.glyphMap;

export default function GestorFaturamentoCard({
  vendas,
}: {
  vendas: GestorVendasResumo;
}) {
  const composicao = vendas.composicao;
  const title = composicao ? "Faturamento líquido" : "Resumo das vendas";

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardHeaderLeft}>
          <View style={styles.cardIcon}>
            <Ionicons
              name="trending-up-outline"
              size={21}
              color={CORES.primario}
            />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.cardTitle}>{title}</Text>
            <Text style={styles.cardSubtitle}>
              {composicao
                ? `${formatIsoDateBR(composicao.data_inicio)} a ${formatIsoDateBR(composicao.data_fim)} · Toda a empresa`
                : "Vendas do período selecionado"}
            </Text>
          </View>
        </View>
      </View>

      {(composicao?.avisos ?? []).map((warning) => (
        <View key={warning} style={styles.warningCard}>
          <Ionicons name="warning-outline" size={20} color="#B45309" />
          <Text style={styles.warningText}>{warning}</Text>
        </View>
      ))}

      <Text style={styles.mainMetricLabel}>
        {composicao
          ? `Vendas − descontos${composicao.devolucoes ? " − devoluções" : ""}`
          : "Total das vendas (resumo anterior)"}
      </Text>
      <Text style={styles.mainMetricValue}>
        {formatarMoeda(
          composicao?.faturamento_liquido ?? vendas.faturamento_liquido,
        )}
      </Text>
      <View style={styles.metricGrid}>
        <MetricBox
          icon="receipt-outline"
          label="Vendas"
          value={String(composicao?.quantidade ?? vendas.quantidade_vendas)}
        />
        <MetricBox
          icon="cube-outline"
          label="Unidades"
          value={formatQuantity(vendas.unidades_vendidas)}
        />
        <MetricBox
          icon="layers-outline"
          label="Produtos diferentes"
          value={String(vendas.produtos_distintos)}
        />
        <MetricBox
          icon="calculator-outline"
          label="Ticket médio"
          value={formatarMoeda(vendas.ticket_medio)}
        />
      </View>

      {!composicao ? (
        <Text style={styles.footnote}>
          Este resumo anterior pode incluir a entrega no total das vendas.
        </Text>
      ) : composicao.taxa_entrega > 0 ? (
        <Text style={styles.footnote}>
          A entrega cobrada não compõe o faturamento líquido.
        </Text>
      ) : null}
    </View>
  );
}

function MetricBox({
  icon,
  label,
  value,
}: {
  icon: IconName;
  label: string;
  value: string;
}) {
  return (
    <View style={styles.metricBox}>
      <View style={styles.metricBoxTop}>
        <Ionicons name={icon} size={16} color={CORES.primario} />
        <Text style={styles.metricBoxLabel}>{label}</Text>
      </View>
      <Text style={styles.metricBoxValue}>{value}</Text>
    </View>
  );
}
