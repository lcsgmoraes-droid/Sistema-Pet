import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { avaliarEntrega } from "../../../services/shop.service";
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
  onRated: () => void | Promise<void>;
};

export function OrderCard({
  pedido,
  repetindo,
  onPayNow,
  onRepeat,
  onTrack,
  onRated,
}: OrderCardProps) {
  const [avaliacaoAberta, setAvaliacaoAberta] = useState(false);
  const [nota, setNota] = useState(5);
  const [comentario, setComentario] = useState("");
  const [enviandoAvaliacao, setEnviandoAvaliacao] = useState(false);
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
    ["aprovado", "em_preparo", "pronto", "pago", "criado"].includes(statusKey),
  );
  const podePagarAgora = statusKey === "pendente" && !!pedido.payment_url;
  const canalLabel = getCanalLabel(pedido);

  async function enviarAvaliacao() {
    if (!pedido.venda_id) return;
    setEnviandoAvaliacao(true);
    try {
      await avaliarEntrega(pedido.venda_id, nota, comentario);
      setAvaliacaoAberta(false);
      setComentario("");
      await onRated();
      Alert.alert("Obrigado!", "Sua avaliacao da entrega foi registrada.");
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      Alert.alert(
        "Nao foi possivel avaliar",
        typeof detail === "string" ? detail : "Tente novamente.",
      );
    } finally {
      setEnviandoAvaliacao(false);
    }
  }

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardHeaderInfo}>
          <Text style={styles.pedidoId}>{getPedidoTitulo(pedido)}</Text>
          <Text style={styles.pedidoData}>{formatarDataHora(pedido.created_at)}</Text>
          <View style={styles.canalBadge}>
            <Ionicons name="pricetag-outline" size={11} color="#9A3412" />
            <Text style={styles.canalBadgeText}>{canalLabel}</Text>
          </View>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: cfg.cor }]}>
          <Ionicons name={cfg.icone as any} size={13} color={cfg.corTexto} />
          <Text style={[styles.statusTexto, { color: cfg.corTexto }]}>{cfg.label}</Text>
        </View>
      </View>

      {entregaCfg && (
        <View style={[styles.entregaBadge, { backgroundColor: entregaCfg.cor + "20" }]}>
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
              <Text style={styles.itemQtd}>{safeText(item.quantidade, "0")}x</Text>
            </View>
            <Text style={styles.itemNome} numberOfLines={1}>
              {safeText(item.nome, "Produto")}
            </Text>
          </View>
        ))}
        {itensRestantes > 0 && <Text style={styles.itemMais}>+{itensRestantes} outros itens</Text>}
      </View>

      {temPalavraChave && (
        <View style={styles.palavraChaveBox}>
          <Ionicons name="key" size={16} color={CORES.primario} />
          <View>
            <Text style={styles.palavraChaveLabel}>Fale no caixa para retirar:</Text>
            <Text style={styles.palavraChaveValor}>{palavraChave.toUpperCase()}</Text>
          </View>
        </View>
      )}

      {pedido.avaliacao_entrega ? (
        <View style={styles.avaliacaoResumo}>
          <Text style={styles.avaliacaoEstrelas}>
            {"★".repeat(pedido.avaliacao_entrega.nota)}
            {"☆".repeat(5 - pedido.avaliacao_entrega.nota)}
          </Text>
          <Text style={styles.avaliacaoTexto}>Sua avaliacao da entrega</Text>
        </View>
      ) : null}

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
            <TouchableOpacity style={styles.btnRastrear} onPress={() => onTrack(pedido)}>
              <Ionicons name="navigate" size={14} color="#fff" />
              <Text style={styles.btnRastrearTexto}>Rastrear</Text>
            </TouchableOpacity>
          )}
          {pedido.pode_avaliar_entrega && pedido.venda_id ? (
            <TouchableOpacity style={styles.btnAvaliar} onPress={() => setAvaliacaoAberta(true)}>
              <Ionicons name="star-outline" size={14} color="#fff" />
              <Text style={styles.btnAvaliarTexto}>Avaliar entrega</Text>
            </TouchableOpacity>
          ) : null}
          <TouchableOpacity
            style={[styles.btnRepetir, repetindo && { opacity: 0.6 }]}
            onPress={() => onRepeat(pedido)}
            disabled={repetindo}
          >
            {repetindo ? (
              <ActivityIndicator size="small" color={CORES.primario} />
            ) : (
              <>
                <Ionicons name="refresh-outline" size={14} color={CORES.primario} />
                <Text style={styles.btnRepetirTexto}>Repetir</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      </View>
      <Modal
        visible={avaliacaoAberta}
        transparent
        animationType="fade"
        onRequestClose={() => setAvaliacaoAberta(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitulo}>Como foi sua entrega?</Text>
            <Text style={styles.modalSubtitulo}>Toque nas estrelas para dar uma nota.</Text>
            <View style={styles.estrelasLinha}>
              {[1, 2, 3, 4, 5].map((valor) => (
                <TouchableOpacity
                  key={valor}
                  onPress={() => setNota(valor)}
                  accessibilityLabel={`${valor} estrelas`}
                >
                  <Ionicons
                    name={valor <= nota ? "star" : "star-outline"}
                    size={36}
                    color="#F59E0B"
                  />
                </TouchableOpacity>
              ))}
            </View>
            <TextInput
              style={styles.comentarioInput}
              value={comentario}
              onChangeText={setComentario}
              placeholder="Quer contar mais alguma coisa? (opcional)"
              multiline
              maxLength={1000}
            />
            <View style={styles.modalAcoes}>
              <TouchableOpacity
                style={styles.modalCancelar}
                onPress={() => setAvaliacaoAberta(false)}
                disabled={enviandoAvaliacao}
              >
                <Text style={styles.modalCancelarTexto}>Agora nao</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalEnviar}
                onPress={enviarAvaliacao}
                disabled={enviandoAvaliacao}
              >
                {enviandoAvaliacao ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.modalEnviarTexto}>Enviar</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}
