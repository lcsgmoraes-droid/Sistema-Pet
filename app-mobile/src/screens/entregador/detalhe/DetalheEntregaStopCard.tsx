import React from "react";
import { ActivityIndicator, Text, TouchableOpacity, View } from "react-native";

import { detalheEntregaStyles as styles } from "./DetalheEntregaStyles";
import {
  STATUS_BADGE,
  abrirMapa,
  ligar,
  rotaPermiteReordenacao,
  type Parada,
} from "./DetalheEntregaUtils";

export type DetalheEntregaStopCardProps = {
  parada: Parada;
  rotaStatus?: string | null;
  processando: number | null;
  drag?: () => void;
  isActive?: boolean;
  abrirModalOrdem: (parada: Parada) => void;
  abrirModalRecebimento: (paradaId: number) => void;
  abrirDetalhesVenda: (vendaId: number) => void | Promise<void>;
  marcarEntregue: (paradaId: number) => void | Promise<void>;
  marcarNaoEntregue: (paradaId: number) => void;
};

export function DetalheEntregaStopCard({
  parada,
  rotaStatus,
  processando,
  drag,
  isActive,
  abrirModalOrdem,
  abrirModalRecebimento,
  abrirDetalhesVenda,
  marcarEntregue,
  marcarNaoEntregue,
}: DetalheEntregaStopCardProps) {
  const badge = STATUS_BADGE[parada.status] ?? {
    label: parada.status,
    color: "#374151",
    bg: "#f3f4f6",
  };
  const emProcessamento = processando === parada.id;
  const podeReordenar = rotaPermiteReordenacao(rotaStatus);

  return (
    <View
      key={parada.id}
      style={[styles.paradaCard, isActive ? styles.paradaCardAtiva : styles.paradaCardInativa]}
    >
      <View style={styles.paradaHeader}>
        <View style={styles.ordemWrapper}>
          {podeReordenar ? (
            <TouchableOpacity
              style={styles.ordemCircle}
              onPress={() => abrirModalOrdem(parada)}
              activeOpacity={0.85}
            >
              <Text style={styles.ordemText}>{parada.ordem}</Text>
            </TouchableOpacity>
          ) : (
            <View style={styles.ordemCircle}>
              <Text style={styles.ordemText}>{parada.ordem}</Text>
            </View>
          )}
          {podeReordenar ? (
            <Text style={styles.ordemEditHint}>Toque para alterar</Text>
          ) : null}
        </View>
        <View style={styles.paradaInfo}>
          <Text style={styles.paradaCliente} numberOfLines={1}>
            {parada.cliente_nome ?? `Cliente da venda #${parada.venda_id}`}
          </Text>
          <Text style={styles.paradaEndereco} numberOfLines={2}>
            {parada.endereco}
          </Text>
        </View>
        {podeReordenar && drag ? (
          <TouchableOpacity
            style={[styles.btnDrag, isActive && styles.btnDragAtivo]}
            onLongPress={drag}
            delayLongPress={70}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Text style={styles.btnDragText}>?</Text>
          </TouchableOpacity>
        ) : null}
        <View style={[styles.statusBadge, { backgroundColor: badge.bg }]}>
          <Text style={[styles.statusBadgeText, { color: badge.color }]}>
            {badge.label}
          </Text>
        </View>
      </View>

      {!!parada.observacoes && (
        <Text style={styles.observacoes}>?? {parada.observacoes}</Text>
      )}

      <View style={styles.paradaBotoes}>
        <TouchableOpacity
          style={styles.btnMapa}
          onPress={() => abrirMapa(parada.endereco)}
        >
          <Text style={styles.btnMapaText}>?? Navegar</Text>
        </TouchableOpacity>

        {parada.cliente_telefone || parada.cliente_celular ? (
          <TouchableOpacity
            style={styles.btnLigar}
            onPress={() =>
              ligar(parada.cliente_celular ?? parada.cliente_telefone)
            }
          >
            <Text style={styles.btnLigarText}>?? Ligar</Text>
          </TouchableOpacity>
        ) : null}

        <TouchableOpacity
          style={styles.btnRecebimento}
          onPress={() => abrirModalRecebimento(parada.id)}
        >
          <Text style={styles.btnRecebimentoIcon}>??</Text>
          <Text style={styles.btnRecebimentoText}>Receber</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.btnDetalhes}
          onPress={() => abrirDetalhesVenda(parada.venda_id)}
        >
          <Text style={styles.btnDetalhesText}>?? Detalhes</Text>
        </TouchableOpacity>
      </View>

      {parada.status === "pendente" && (
        <View style={styles.paradaAcoes}>
          {emProcessamento ? (
            <ActivityIndicator color="#2563eb" />
          ) : (
            <>
              <TouchableOpacity
                style={styles.btnEntregue}
                onPress={() => marcarEntregue(parada.id)}
              >
                <Text style={styles.btnEntregueText}>? Entregue</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.btnNaoEntregue}
                onPress={() => marcarNaoEntregue(parada.id)}
              >
                <Text style={styles.btnNaoEntregueText}>? NÃ£o entregue</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      )}
    </View>
  );
}
