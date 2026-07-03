import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { ActivityIndicator, Text, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import { Pedido } from "../../../types";
import { formatarDataHora, formatarMoeda } from "../../../utils/format";
import { ordersStyles as styles } from "./OrdersStyles";
import {
  getCanalLabel,
  getEntregaStatusConfig,
  getPedidoItens,
  getPedidoRenderKey,
  getPedidoStatusKey,
  getPedidoTitulo,
  safeText,
  STATUS_CONFIG,
} from "./OrdersUtils";

type OrderCardProps = {
  pedido: Pedido;
  repetindo: boolean;
  onPayNow: (paymentUrl: string) => void;
  onRepeat: (pedido: Pedido) => void;
  onTrack: (pedido: Pedido) => void;
};

export function OrderCard({
  pedido,
  repetindo,
  onPayNow,
  onRepeat,
  onTrack,
}: OrderCardProps) {
  if (!pedido || typeof pedido !== "object") return null;

  const pedidoKey = getPedidoRenderKey(pedido);
  const itens = getPedidoItens(pedido);
  const itensPreview = itens.slice(0, 3);
  const itensRestantes = Math.max(itens.length - 3, 0);
  const statusKey = getPedidoStatusKey(pedido);
  const statusEntrega = safeText(pedido.status_entrega).trim().toLowerCase();
  const palavraChave = safeText(pedido.palavra_chave_retirada).trim();
  const retiradoPor = safeText(pedido.retirado_por).trim();
  const cfg = STATUS_CONFIG[statusKey] ?? STATUS_CONFIG.desconhecido;
  const temEntrega = Boolean(pedido.tem_entrega);
  const entregaCfg = getEntregaStatusConfig(pedido);
  const temPalavraChave =
    !!palavraChave && statusKey !== "cancelado" && statusEntrega !== "entregue";
  const podeRastrear = Boolean(
    pedido.pedido_id &&
      temEntrega &&
      ["aprovado", "em_preparo", "pronto", "pago", "criado"].includes(
        statusKey,
      ),
  );
  const podePagarAgora = statusKey === "pendente" && !!pedido.payment_url;
  const canalLabel = getCanalLabel(pedido);

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardHeaderInfo}>
          <Text style={styles.pedidoId}>{getPedidoTitulo(pedido)}</Text>
          <Text style={styles.pedidoData}>
            {formatarDataHora(pedido.created_at)}
          </Text>
          <View style={styles.canalBadge}>
            <Ionicons name="pricetag-outline" size={11} color="#9A3412" />
            <Text style={styles.canalBadgeText}>{canalLabel}</Text>
          </View>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: cfg.cor }]}>
          <Ionicons name={cfg.icone as any} size={13} color={cfg.corTexto} />
          <Text style={[styles.statusTexto, { color: cfg.corTexto }]}>
            {cfg.label}
          </Text>
        </View>
      </View>

      {entregaCfg && (
        <View
          style={[
            styles.entregaBadge,
            { backgroundColor: entregaCfg.cor + "20" },
          ]}
        >
          <Text style={[styles.entregaBadgeText, { color: entregaCfg.cor }]}>
            {entregaCfg.label}
          </Text>
        </View>
      )}

      {!temEntrega && statusEntrega === "entregue" && !!retiradoPor && (
        <Text style={styles.retiradoPorTexto}>Retirado por {retiradoPor}</Text>
      )}

      <View style={styles.itensList}>
        {itensPreview.map((item, idx) => (
          <View key={idx} style={styles.itemLinha}>
            <View style={styles.itemQtdBadge}>
              <Text style={styles.itemQtd}>
                {safeText(item.quantidade, "0")}x
              </Text>
            </View>
            <Text style={styles.itemNome} numberOfLines={1}>
              {safeText(item.nome, "Produto")}
            </Text>
          </View>
        ))}
        {itensRestantes > 0 && (
          <Text style={styles.itemMais}>+{itensRestantes} outros itens</Text>
        )}
      </View>

      {temPalavraChave && (
        <View style={styles.palavraChaveBox}>
          <Ionicons name="key" size={16} color={CORES.primario} />
          <View>
            <Text style={styles.palavraChaveLabel}>
              Fale no caixa para retirar:
            </Text>
            <Text style={styles.palavraChaveValor}>
              {palavraChave.toUpperCase()}
            </Text>
          </View>
        </View>
      )}

      <View style={styles.cardRodape}>
        <View>
          <Text style={styles.totalLabel}>Total</Text>
          <Text style={styles.totalValor}>{formatarMoeda(pedido.total)}</Text>
        </View>
        <View style={styles.acoes}>
          {podePagarAgora && (
            <TouchableOpacity
              style={styles.btnPagar}
              onPress={() => pedido.payment_url && onPayNow(pedido.payment_url)}
            >
              <Ionicons name="card-outline" size={14} color="#fff" />
              <Text style={styles.btnPagarTexto}>Pagar agora</Text>
            </TouchableOpacity>
          )}
          {podeRastrear && (
            <TouchableOpacity
              style={styles.btnRastrear}
              onPress={() => onTrack(pedido)}
            >
              <Ionicons name="navigate" size={14} color="#fff" />
              <Text style={styles.btnRastrearTexto}>Rastrear</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity
            style={[styles.btnRepetir, repetindo && { opacity: 0.6 }]}
            onPress={() => onRepeat(pedido)}
            disabled={repetindo}
          >
            {repetindo ? (
              <ActivityIndicator size="small" color={CORES.primario} />
            ) : (
              <>
                <Ionicons
                  name="refresh-outline"
                  size={14}
                  color={CORES.primario}
                />
                <Text style={styles.btnRepetirTexto}>Repetir</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}
