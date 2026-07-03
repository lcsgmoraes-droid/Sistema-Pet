import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { CORES } from "../../../theme";
import { Pedido } from "../../../types";
import { OrderCard } from "./OrderCard";
import { ordersStyles as styles } from "./OrdersStyles";
import { getPedidoRenderKey } from "./OrdersUtils";

type OrdersContentProps = {
  pedidos: Pedido[];
  carregando: boolean;
  refreshing: boolean;
  repetindo: string | null;
  erroPedidos: string | null;
  onOpenCatalog: () => void;
  onPayNow: (paymentUrl: string) => void;
  onRefresh: () => void;
  onReload: () => void;
  onRepeat: (pedido: Pedido) => void;
  onTrack: (pedido: Pedido) => void;
};

export function OrdersContent({
  pedidos,
  carregando,
  refreshing,
  repetindo,
  erroPedidos,
  onOpenCatalog,
  onPayNow,
  onRefresh,
  onReload,
  onRepeat,
  onTrack,
}: OrdersContentProps) {
  if (carregando) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color={CORES.primario} />
        <Text style={styles.loadingText}>Carregando pedidos...</Text>
      </View>
    );
  }

  return (
    <FlatList
      data={pedidos}
      keyExtractor={(item, index) => getPedidoRenderKey(item, index)}
      renderItem={({ item }) => (
        <OrderCard
          pedido={item}
          repetindo={repetindo === getPedidoRenderKey(item)}
          onPayNow={onPayNow}
          onRepeat={onRepeat}
          onTrack={onTrack}
        />
      )}
      contentContainerStyle={styles.lista}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={CORES.primario}
        />
      }
      ListHeaderComponent={
        pedidos.length > 0 ? (
          <View style={styles.header}>
            <Ionicons name="receipt-outline" size={24} color={CORES.primario} />
            <View>
              <Text style={styles.headerTitulo}>Meus Pedidos</Text>
              <Text style={styles.headerSub}>
                {pedidos.length} {pedidos.length === 1 ? "pedido" : "pedidos"}
              </Text>
            </View>
          </View>
        ) : null
      }
      ListEmptyComponent={
        erroPedidos ? (
          <View style={styles.vazio}>
            <Ionicons name="alert-circle-outline" size={56} color={CORES.erro} />
            <Text style={styles.vazioTitulo}>
              Não foi possível carregar seus pedidos
            </Text>
            <Text style={styles.vazioTexto}>
              Puxe para atualizar ou tente novamente em instantes.
            </Text>
            <TouchableOpacity style={styles.btnComprar} onPress={onReload}>
              <Ionicons name="refresh-outline" size={16} color="#fff" />
              <Text style={styles.btnComprarTexto}>Tentar novamente</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.vazio}>
            <Text style={styles.vazioEmoji}>🛍️</Text>
            <Text style={styles.vazioTitulo}>Nenhum pedido feito</Text>
            <Text style={styles.vazioTexto}>
              Seus pedidos aparecerão aqui assim que você finalizar uma compra.
            </Text>
            <TouchableOpacity
              style={styles.btnComprar}
              onPress={onOpenCatalog}
            >
              <Ionicons name="storefront-outline" size={16} color="#fff" />
              <Text style={styles.btnComprarTexto}>Ver produtos</Text>
            </TouchableOpacity>
          </View>
        )
      }
    />
  );
}
