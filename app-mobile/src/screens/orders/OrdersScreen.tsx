import { useFocusEffect, useNavigation } from "@react-navigation/native";
import React, { useCallback, useEffect, useState } from "react";
import { Alert, Linking } from "react-native";

import { listarPedidos, repetirPedido } from "../../services/shop.service";
import { useCartStore } from "../../store/cart.store";
import { Pedido } from "../../types";
import { OrdersContent } from "./orders/OrdersContent";
import {
  getPedidoItens,
  getPedidoRenderKey,
  getPedidoStatusKey,
  hasOpenFulfillmentOrder,
  PENDING_ORDER_POLL_MS,
} from "./orders/OrdersUtils";

export default function OrdersScreen() {
  const navigation = useNavigation<any>();
  const { carregar: recarregarCarrinho } = useCartStore();
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [repetindo, setRepetindo] = useState<string | null>(null);
  const [erroPedidos, setErroPedidos] = useState<string | null>(null);

  async function handleRepetirPedido(pedido: Pedido) {
    const pedidoKey = getPedidoRenderKey(pedido);
    const totalItens = getPedidoItens(pedido).length;
    setRepetindo(pedidoKey);
    try {
      const adicionados = await repetirPedido(pedido);
      await recarregarCarrinho();
      Alert.alert(
        "🛒 Carrinho atualizado",
        `${adicionados} de ${totalItens} produto(s) foram adicionados ao carrinho.`,
        [
          { text: "Continuar comprando", style: "cancel" },
          {
            text: "Ver carrinho",
            onPress: () => navigation.navigate("Loja", { screen: "Carrinho" }),
          },
        ],
      );
    } catch {
      Alert.alert(
        "Erro",
        "Não foi possível repetir o pedido. Tente novamente.",
      );
    } finally {
      setRepetindo(null);
    }
  }

  const carregar = useCallback(async () => {
    setErroPedidos(null);
    try {
      const lista = await listarPedidos();
      setPedidos(lista);
    } catch {
      setPedidos([]);
      setErroPedidos("Não foi possível carregar seus pedidos agora.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      carregar();
    }, [carregar]),
  );

  useEffect(() => {
    const temPedidoPendente = pedidos.some(
      (pedido) => getPedidoStatusKey(pedido) === "pendente",
    );
    const temRetiradaAberta = pedidos.some(hasOpenFulfillmentOrder);
    if (!temPedidoPendente && !temRetiradaAberta) return;

    const interval = setInterval(carregar, PENDING_ORDER_POLL_MS);
    return () => clearInterval(interval);
  }, [carregar, pedidos]);

  async function onRefresh() {
    setRefreshing(true);
    await carregar();
    setRefreshing(false);
  }

  function handleRastrear(pedido: Pedido) {
    if (!pedido.pedido_id) return;
    navigation.navigate("Rastreio", { pedidoId: pedido.pedido_id });
  }

  async function handlePagarAgora(paymentUrl: string) {
    try {
      await Linking.openURL(paymentUrl);
    } catch {
      Alert.alert("Erro", "Não foi possível abrir o pagamento. Tente novamente.");
    }
  }

  return (
    <OrdersContent
      pedidos={pedidos}
      carregando={carregando}
      refreshing={refreshing}
      repetindo={repetindo}
      erroPedidos={erroPedidos}
      onOpenCatalog={() => navigation.navigate("Loja", { screen: "Catalogo" })}
      onPayNow={handlePagarAgora}
      onRefresh={onRefresh}
      onReload={carregar}
      onRepeat={handleRepetirPedido}
      onTrack={handleRastrear}
    />
  );
}
