import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import React, { useCallback, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  RefreshControl,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import {
  GestorContaResumo,
  GestorResumo,
  obterResumoGestor,
} from "../../services/gestor.service";
import { useTenantStore } from "../../store/tenant.store";
import { CORES } from "../../theme";
import { formatarMoeda } from "../../utils/format";
import { gestorStyles as styles } from "./GestorDashboardStyles";
import {
  formatIsoDateBR,
  formatQuantity,
  GESTOR_QUICK_PERIODS,
  GestorPeriod,
  maskBRDate,
  parseBRDate,
  resolveGestorPeriod,
  toLocalIsoDate,
} from "./GestorDashboardUtils";

type IconName = keyof typeof Ionicons.glyphMap;

export default function GestorDashboardScreen() {
  const tenant = useTenantStore((state) => state.tenant);
  const [period, setPeriod] = useState<GestorPeriod>(() =>
    resolveGestorPeriod("hoje"),
  );
  const [summary, setSummary] = useState<GestorResumo | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [customOpen, setCustomOpen] = useState(false);
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const requestId = useRef(0);

  const loadSummary = useCallback(
    async (target: GestorPeriod, showAlert = false) => {
      const currentRequest = ++requestId.current;
      try {
        setError(null);
        const data = await obterResumoGestor(target.start, target.end);
        if (currentRequest === requestId.current) setSummary(data);
      } catch (err: any) {
        if (currentRequest !== requestId.current) return;
        const message =
          err?.response?.data?.detail ||
          "Nao foi possivel atualizar a visao do gestor.";
        setError(message);
        if (showAlert) Alert.alert("Resumo indisponivel", message);
      } finally {
        if (currentRequest === requestId.current) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    },
    [],
  );

  useFocusEffect(
    useCallback(() => {
      void loadSummary(period);
    }, [loadSummary, period]),
  );

  const selectQuickPeriod = (
    key: (typeof GESTOR_QUICK_PERIODS)[number]["key"],
  ) => {
    setLoading(!summary);
    setPeriod(resolveGestorPeriod(key));
  };

  const openCustomPeriod = () => {
    setCustomStart(formatIsoDateBR(period.start));
    setCustomEnd(formatIsoDateBR(period.end));
    setCustomOpen(true);
  };

  const applyCustomPeriod = () => {
    const start = parseBRDate(customStart);
    const end = parseBRDate(customEnd);
    if (!start || !end) {
      Alert.alert(
        "Periodo invalido",
        "Informe as duas datas no formato DD/MM/AAAA.",
      );
      return;
    }
    if (end < start) {
      Alert.alert(
        "Periodo invalido",
        "A data final deve ser igual ou posterior a inicial.",
      );
      return;
    }
    if (end > toLocalIsoDate(new Date())) {
      Alert.alert("Periodo invalido", "A data final nao pode estar no futuro.");
      return;
    }
    const days = Math.round(
      (new Date(`${end}T12:00:00`).getTime() -
        new Date(`${start}T12:00:00`).getTime()) /
        86400000,
    );
    if (days > 366) {
      Alert.alert("Periodo muito longo", "Escolha no maximo 367 dias.");
      return;
    }

    setCustomOpen(false);
    setLoading(!summary);
    setPeriod({
      key: "personalizado",
      label: "Periodo",
      start,
      end,
    });
  };

  if (loading && !summary) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={CORES.primario} size="large" />
        <Text style={styles.loadingText}>Organizando os indicadores...</Text>
      </View>
    );
  }

  return (
    <>
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            colors={[CORES.primario]}
            refreshing={refreshing}
            tintColor={CORES.primario}
            onRefresh={() => {
              setRefreshing(true);
              void loadSummary(period, true);
            }}
          />
        }
      >
        <View style={styles.hero}>
          <Text style={styles.heroEyebrow}>Painel executivo</Text>
          <Text style={styles.heroTitle}>{tenant?.nome || "Sua empresa"}</Text>
          <Text style={styles.heroSubtitle}>
            Os numeros mais importantes, sem tabelas e sem rolagem lateral.
          </Text>
          {summary?.atualizado_em ? (
            <Text style={styles.heroMeta}>
              Atualizado {formatUpdatedAt(summary.atualizado_em)}
            </Text>
          ) : null}
        </View>

        <View style={styles.filterSection}>
          <View style={styles.filterHeader}>
            <Text style={styles.filterTitle}>Periodo das vendas</Text>
            <Text style={styles.periodText}>
              {formatIsoDateBR(period.start)} a {formatIsoDateBR(period.end)}
            </Text>
          </View>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.chipsContent}
          >
            {GESTOR_QUICK_PERIODS.map((item) => {
              const active = period.key === item.key;
              return (
                <TouchableOpacity
                  key={item.key}
                  style={[styles.chip, active && styles.chipActive]}
                  onPress={() => selectQuickPeriod(item.key)}
                >
                  <Text
                    style={[styles.chipText, active && styles.chipTextActive]}
                  >
                    {item.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
            <TouchableOpacity
              style={[
                styles.chip,
                styles.customChip,
                period.key === "personalizado" && styles.chipActive,
              ]}
              onPress={openCustomPeriod}
            >
              <Ionicons
                name="calendar-outline"
                size={16}
                color={period.key === "personalizado" ? "#fff" : CORES.primario}
              />
              <Text
                style={[
                  styles.chipText,
                  period.key === "personalizado" && styles.chipTextActive,
                ]}
              >
                Periodo
              </Text>
            </TouchableOpacity>
          </ScrollView>
        </View>

        {error ? (
          <View style={styles.errorCard}>
            <Text style={styles.errorTitle}>
              Alguns numeros podem estar desatualizados
            </Text>
            <Text style={styles.errorText}>{error}</Text>
            <TouchableOpacity
              style={styles.retryButton}
              onPress={() => void loadSummary(period, true)}
            >
              <Text style={styles.retryText}>Tentar novamente</Text>
            </TouchableOpacity>
          </View>
        ) : null}

        {(summary?.avisos || []).map((warning) => (
          <View key={warning} style={styles.warningCard}>
            <Ionicons name="warning-outline" size={20} color="#B45309" />
            <Text style={styles.warningText}>{warning}</Text>
          </View>
        ))}

        {summary ? <DashboardCards summary={summary} /> : null}
      </ScrollView>

      <CustomPeriodModal
        end={customEnd}
        open={customOpen}
        start={customStart}
        onApply={applyCustomPeriod}
        onChangeEnd={(value) => setCustomEnd(maskBRDate(value))}
        onChangeStart={(value) => setCustomStart(maskBRDate(value))}
        onClose={() => setCustomOpen(false)}
      />
    </>
  );
}

function DashboardCards({ summary }: { summary: GestorResumo }) {
  const {
    vendas,
    fluxo_hoje: fluxo,
    contas_receber,
    contas_pagar,
    dre,
  } = summary;
  return (
    <>
      <Card
        icon="trending-up-outline"
        title="Faturamento"
        subtitle="Vendas do periodo selecionado"
      >
        <Text style={styles.mainMetricLabel}>Faturamento liquido</Text>
        <Text style={styles.mainMetricValue}>
          {formatarMoeda(vendas.faturamento_liquido)}
        </Text>
        <View style={styles.moneyGrid}>
          <MoneyCell label="Bruto" value={vendas.faturamento_bruto} />
          <MoneyCell label="Liquido" value={vendas.faturamento_liquido} />
          <MoneyCell label="Recebido" value={vendas.recebido} />
        </View>
        <View style={styles.metricGrid}>
          <MetricBox
            icon="receipt-outline"
            label="Vendas"
            value={String(vendas.quantidade_vendas)}
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
            label="Ticket medio"
            value={formatarMoeda(vendas.ticket_medio)}
          />
        </View>
        {vendas.descontos > 0 ? (
          <Text style={styles.footnote}>
            Descontos concedidos: {formatarMoeda(vendas.descontos)}
          </Text>
        ) : null}
      </Card>

      <Card
        icon="pulse-outline"
        title="Fluxo de caixa de hoje"
        subtitle="Entradas menos saidas do dia"
      >
        {fluxo.disponivel ? (
          <>
            <View style={styles.balanceGrid}>
              <BalanceBox
                label="Realizado"
                value={fluxo.saldo_realizado}
                projected={false}
              />
              <BalanceBox
                label="Projetado"
                value={fluxo.saldo_projetado}
                projected
              />
            </View>
            <View style={styles.detailRows}>
              <DetailRow
                label="Entradas realizadas"
                value={formatarMoeda(fluxo.entradas_realizadas)}
              />
              <DetailRow
                label="Saidas realizadas"
                value={formatarMoeda(fluxo.saidas_realizadas)}
              />
              <DetailRow
                label="Entradas ainda previstas"
                value={formatarMoeda(fluxo.entradas_previstas)}
              />
              <DetailRow
                label="Saidas ainda previstas"
                value={formatarMoeda(fluxo.saidas_previstas)}
              />
            </View>
          </>
        ) : (
          <Text style={styles.unavailable}>
            Fluxo de caixa temporariamente indisponivel.
          </Text>
        )}
      </Card>

      <Card
        icon="wallet-outline"
        title="Contas"
        subtitle="Compromissos e valores a receber"
      >
        <View style={styles.accountsGrid}>
          <AccountPanel kind="receivable" summary={contas_receber} />
          <AccountPanel kind="payable" summary={contas_pagar} />
        </View>
      </Card>

      <Card
        icon="analytics-outline"
        title="Resultado da DRE"
        subtitle={dre.periodo}
      >
        {dre.disponivel ? (
          <>
            <View style={styles.dreResult}>
              <Text style={styles.dreResultLabel}>Lucro liquido</Text>
              <Text
                style={[
                  styles.dreResultValue,
                  dre.lucro_liquido >= 0 ? styles.positive : styles.negative,
                ]}
              >
                {formatarMoeda(dre.lucro_liquido)}
              </Text>
              <Text style={styles.dreMargin}>
                Margem liquida: {formatQuantity(dre.margem_liquida)}%
              </Text>
            </View>
            <View style={styles.detailRows}>
              <DetailRow
                label="Receita bruta"
                value={formatarMoeda(dre.receita_bruta)}
              />
              <DetailRow
                label="Receita liquida"
                value={formatarMoeda(dre.receita_liquida)}
              />
              <DetailRow label="CMV" value={formatarMoeda(dre.cmv)} />
              <DetailRow
                label="Despesas variaveis"
                value={formatarMoeda(dre.despesas_variaveis)}
              />
              <DetailRow
                label="Despesas operacionais"
                value={formatarMoeda(dre.despesas_operacionais)}
              />
              <DetailRow
                label="Lucro bruto"
                value={formatarMoeda(dre.lucro_bruto)}
              />
            </View>
            <Text style={styles.footnote}>
              {dre.criterio === "periodo_selecionado"
                ? "DRE por competencia no periodo selecionado."
                : "Para filtros curtos, a DRE mostra a competencia do mes ate a data final escolhida."}
            </Text>
          </>
        ) : (
          <Text style={styles.unavailable}>
            DRE temporariamente indisponivel.
          </Text>
        )}
      </Card>
    </>
  );
}

function Card({
  icon,
  title,
  subtitle,
  children,
}: {
  icon: IconName;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardHeaderLeft}>
          <View style={styles.cardIcon}>
            <Ionicons name={icon} size={21} color={CORES.primario} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.cardTitle}>{title}</Text>
            <Text style={styles.cardSubtitle}>{subtitle}</Text>
          </View>
        </View>
      </View>
      {children}
    </View>
  );
}

function MoneyCell({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.moneyCell}>
      <Text style={styles.moneyCellLabel}>{label}</Text>
      <Text
        style={styles.moneyCellValue}
        numberOfLines={1}
        adjustsFontSizeToFit
      >
        {formatarMoeda(value)}
      </Text>
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

function BalanceBox({
  label,
  value,
  projected,
}: {
  label: string;
  value: number;
  projected: boolean;
}) {
  return (
    <View
      style={[
        styles.balanceBox,
        projected ? styles.projectedBox : styles.realizedBox,
      ]}
    >
      <Text style={styles.balanceLabel}>{label}</Text>
      <Text
        style={[
          styles.balanceValue,
          value >= 0 ? styles.positive : styles.negative,
        ]}
        numberOfLines={1}
        adjustsFontSizeToFit
      >
        {formatarMoeda(value)}
      </Text>
    </View>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{value}</Text>
    </View>
  );
}

function AccountPanel({
  kind,
  summary,
}: {
  kind: "receivable" | "payable";
  summary: GestorContaResumo;
}) {
  const receivable = kind === "receivable";
  return (
    <View
      style={[
        styles.accountPanel,
        receivable ? styles.receivablePanel : styles.payablePanel,
      ]}
    >
      <View style={styles.accountTitleRow}>
        <Ionicons
          name={
            receivable ? "arrow-down-circle-outline" : "arrow-up-circle-outline"
          }
          size={20}
          color={receivable ? CORES.sucesso : CORES.erro}
        />
        <Text style={styles.accountTitle}>
          {receivable ? "Contas a receber" : "Contas a pagar"}
        </Text>
      </View>
      <Text style={styles.accountTotal}>
        {formatarMoeda(summary.total_aberto)}
      </Text>
      <Text style={styles.accountCaption}>
        {summary.quantidade_abertas} conta(s) em aberto
      </Text>
      <View style={styles.accountStats}>
        <View style={styles.accountStat}>
          <Text style={styles.accountStatLabel}>Vencido</Text>
          <Text
            style={[
              styles.accountStatValue,
              summary.vencido > 0 && styles.overdue,
            ]}
          >
            {formatarMoeda(summary.vencido)}
          </Text>
        </View>
        <View style={styles.accountStat}>
          <Text style={styles.accountStatLabel}>Vence hoje</Text>
          <Text style={styles.accountStatValue}>
            {formatarMoeda(summary.vence_hoje)}
          </Text>
        </View>
        <View style={styles.accountStat}>
          <Text style={styles.accountStatLabel}>No periodo</Text>
          <Text style={styles.accountStatValue}>
            {formatarMoeda(summary.no_periodo)}
          </Text>
        </View>
      </View>
    </View>
  );
}

function CustomPeriodModal({
  open,
  start,
  end,
  onChangeStart,
  onChangeEnd,
  onClose,
  onApply,
}: {
  open: boolean;
  start: string;
  end: string;
  onChangeStart: (value: string) => void;
  onChangeEnd: (value: string) => void;
  onClose: () => void;
  onApply: () => void;
}) {
  return (
    <Modal
      animationType="slide"
      transparent
      visible={open}
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        style={styles.modalBackdrop}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={styles.modalCard}>
          <Text style={styles.modalTitle}>Escolher periodo</Text>
          <Text style={styles.modalSubtitle}>
            Consulte ate 367 dias de uma vez.
          </Text>
          <Text style={styles.inputLabel}>Data inicial</Text>
          <TextInput
            style={styles.input}
            value={start}
            onChangeText={onChangeStart}
            placeholder="DD/MM/AAAA"
            keyboardType="number-pad"
            maxLength={10}
          />
          <Text style={styles.inputLabel}>Data final</Text>
          <TextInput
            style={styles.input}
            value={end}
            onChangeText={onChangeEnd}
            placeholder="DD/MM/AAAA"
            keyboardType="number-pad"
            maxLength={10}
          />
          <View style={styles.modalActions}>
            <TouchableOpacity
              style={[styles.modalButton, styles.modalCancel]}
              onPress={onClose}
            >
              <Text style={styles.modalCancelText}>Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.modalButton, styles.modalApply]}
              onPress={onApply}
            >
              <Text style={styles.modalApplyText}>Aplicar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

function formatUpdatedAt(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "agora";
  return parsed.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
