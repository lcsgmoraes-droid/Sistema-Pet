import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { Text, TouchableOpacity, View } from "react-native";
import {
  GestorValoresVenda,
  GestorVendaDetalhe,
  GestorVendasResumo,
} from "../../services/gestor.service";
import { CORES } from "../../theme";
import { formatarMoeda } from "../../utils/format";
import { gestorStyles as styles } from "./GestorDashboardStyles";
import { formatIsoDateBR, formatQuantity } from "./GestorDashboardUtils";

const PAGE_SIZE = 20;
type IconName = keyof typeof Ionicons.glyphMap;

export default function GestorFaturamentoCard({
  vendas,
}: {
  vendas: GestorVendasResumo;
}) {
  const [expanded, setExpanded] = useState(false);
  const [visibleSales, setVisibleSales] = useState(PAGE_SIZE);
  const [expandedSale, setExpandedSale] = useState<number | null>(null);
  const composicao = vendas.composicao;
  const details = composicao?.detalhes ?? [];
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

      <TouchableOpacity
        accessibilityRole="button"
        accessibilityLabel="Detalhes do faturamento"
        accessibilityState={{ expanded }}
        style={styles.revenueToggle}
        onPress={() => setExpanded((value) => !value)}
      >
        <Text style={styles.revenueToggleText}>
          {expanded ? "Ocultar detalhes" : "Ver detalhes"}
        </Text>
        <Ionicons
          name={expanded ? "chevron-up" : "chevron-down"}
          size={19}
          color={CORES.primario}
        />
      </TouchableOpacity>

      {expanded ? (
        <View>
          {composicao ? (
            <>
              <SaleCalculation valores={composicao} />
              <Text style={styles.footnote}>
                O faturamento líquido não desconta custos, taxas de cartão ou
                comissões. A entrega cobrada aparece separadamente.
              </Text>
              <SaleSettlement valores={composicao} />
              <Text style={styles.footnote}>
                Pago das vendas do período considera os pagamentos dessas
                vendas, mesmo que recebidos em outra data. Crediário a receber
                não é recebimento; créditos e benefícios quitam a venda sem
                entrada de dinheiro novo.
              </Text>

              <Text style={styles.revenueSectionTitle}>
                Vendas que compõem o total
              </Text>
              {details.length ? (
                <>
                  <Text style={styles.footnote}>
                    Exibindo {Math.min(visibleSales, details.length)} de{" "}
                    {details.length} vendas. Os totais acima consideram todas
                    elas.
                  </Text>
                  {details.slice(0, visibleSales).map((venda) => (
                    <SaleDetail
                      key={venda.venda_id}
                      venda={venda}
                      expanded={expandedSale === venda.venda_id}
                      onPress={() =>
                        setExpandedSale(
                          expandedSale === venda.venda_id
                            ? null
                            : venda.venda_id,
                        )
                      }
                    />
                  ))}
                  {visibleSales < details.length ? (
                    <TouchableOpacity
                      accessibilityRole="button"
                      style={styles.revenueToggle}
                      onPress={() =>
                        setVisibleSales((value) => value + PAGE_SIZE)
                      }
                    >
                      <Text style={styles.revenueToggleText}>
                        Ver mais vendas
                      </Text>
                    </TouchableOpacity>
                  ) : null}
                </>
              ) : (
                <Text style={styles.unavailable}>
                  Nenhuma venda no período.
                </Text>
              )}
            </>
          ) : (
            <View style={styles.detailRows}>
              <MoneyRow
                label="Faturamento bruto"
                value={vendas.faturamento_bruto}
              />
              <MoneyRow label="Descontos" value={vendas.descontos} />
              <Text style={styles.footnote}>
                Detalhamento indisponível nesta atualização. Este resumo
                anterior pode incluir a entrega no total das vendas.
              </Text>
            </View>
          )}
        </View>
      ) : null}
    </View>
  );
}

function SaleCalculation({ valores }: { valores: GestorValoresVenda }) {
  return (
    <View style={styles.detailRows}>
      <MoneyRow label="Faturamento bruto" value={valores.faturamento_bruto} />
      <MoneyRow label="− Descontos" value={valores.descontos} />
      {valores.devolucoes !== 0 ? (
        <MoneyRow label="− Devoluções" value={valores.devolucoes} />
      ) : null}
      <MoneyRow
        label="= Faturamento líquido"
        value={valores.faturamento_liquido}
      />
      {valores.taxa_entrega !== 0 ? (
        <>
          <MoneyRow label="+ Entrega cobrada" value={valores.taxa_entrega} />
          <MoneyRow label="= Total com entrega" value={valores.total_vendas} />
        </>
      ) : null}
    </View>
  );
}

function SaleSettlement({ valores }: { valores: GestorValoresVenda }) {
  return (
    <View>
      <Text style={styles.revenueSectionTitle}>
        Composição do total das vendas
      </Text>
      <MoneyRow label="Pago das vendas do período" value={valores.valor_pago} />
      <MoneyRow
        label="Créditos e benefícios utilizados"
        value={valores.creditos_utilizados}
      />
      <MoneyRow label="Crediário a receber" value={valores.crediario_receber} />
      <MoneyRow
        label="Aguardando pagamento, sem crediário"
        value={valores.em_aberto}
      />
      <MoneyRow label="= Total das vendas" value={valores.total_vendas} />
    </View>
  );
}

function SaleDetail({
  venda,
  expanded,
  onPress,
}: {
  venda: GestorVendaDetalhe;
  expanded: boolean;
  onPress: () => void;
}) {
  return (
    <View style={styles.revenueSale}>
      <TouchableOpacity
        accessibilityRole="button"
        accessibilityLabel={`Detalhes da venda ${venda.numero_venda}`}
        accessibilityState={{ expanded }}
        style={styles.revenueSaleToggle}
        onPress={onPress}
      >
        <View style={{ flex: 1 }}>
          <Text style={styles.revenueSaleTitle}>
            Venda #{venda.numero_venda}
          </Text>
          <Text style={styles.cardSubtitle}>
            {formatIsoDateBR(venda.data_venda.slice(0, 10))}
          </Text>
        </View>
        <Text style={styles.detailValue}>
          {formatarMoeda(venda.faturamento_liquido)}
        </Text>
        <Ionicons
          name={expanded ? "chevron-up" : "chevron-down"}
          size={17}
          color={CORES.primario}
        />
      </TouchableOpacity>
      {expanded ? (
        <View style={styles.revenueSaleBody}>
          <SaleCalculation valores={venda} />
          <SaleSettlement valores={venda} />
          <Text style={styles.revenueSectionTitle}>
            Pagamentos e formas de quitação
          </Text>
          {venda.devolucoes > 0 ? (
            <Text style={styles.footnote}>
              O histórico abaixo preserva os pagamentos originais. A devolução
              de {formatarMoeda(venda.devolucoes)} já foi abatida na composição
              acima. Pago após os ajustes: {formatarMoeda(venda.valor_pago)}.
            </Text>
          ) : null}
          {venda.pagamentos?.length ? (
            venda.pagamentos.map((pagamento, index) => (
              <View
                key={pagamento.id ?? `pagamento-${index}`}
                style={styles.detailRow}
              >
                <View style={{ flex: 1 }}>
                  <Text style={styles.detailLabel}>
                    {pagamento.forma_pagamento}
                  </Text>
                  <Text style={styles.cardSubtitle}>
                    {pagamento.tipo === "crediario"
                      ? "Crediário contratado"
                      : pagamento.tipo === "beneficio"
                        ? "Crédito ou benefício utilizado"
                        : pagamento.origem === "conta_legada"
                          ? "Recebimento histórico comprovado"
                          : "Pagamento"}
                    {pagamento.data_pagamento
                      ? ` · ${formatIsoDateBR(pagamento.data_pagamento.slice(0, 10))}`
                      : ""}
                  </Text>
                </View>
                <Text style={styles.detailValue}>
                  {formatarMoeda(pagamento.valor)}
                </Text>
              </View>
            ))
          ) : (
            <Text style={styles.footnote}>
              Sem pagamentos registrados nesta venda.
            </Text>
          )}
        </View>
      ) : null}
    </View>
  );
}

function MoneyRow({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{formatarMoeda(value)}</Text>
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
