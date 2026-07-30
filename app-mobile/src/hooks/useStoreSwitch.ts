import { Alert } from "react-native";
import { useAuthStore } from "../store/auth.store";
import { useCartStore } from "../store/cart.store";
import { useTenantStore } from "../store/tenant.store";

export function useStoreSwitch() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const logout = useAuthStore((state) => state.logout);
  const itens = useCartStore((state) => state.itens);
  const limparCarrinho = useCartStore((state) => state.limpar);
  const limparCarrinhoLocal = useCartStore((state) => state.limparLocal);
  const limparTenant = useTenantStore((state) => state.limparTenant);

  function requestStoreSwitch() {
    const hasCartItems = itens.length > 0;
    const details = hasCartItems
      ? " Seu carrinho atual sera esvaziado para nao misturar produtos de lojas diferentes."
      : "";

    Alert.alert(
      "Trocar loja",
      `Sua conta e seus pedidos ficam vinculados a loja selecionada.${details} Deseja continuar?`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Trocar",
          style: "destructive",
          onPress: async () => {
            try {
              if (isAuthenticated) {
                await limparCarrinho().catch(() => undefined);
              }
              limparCarrinhoLocal();
              if (isAuthenticated) {
                await logout();
              }
              await limparTenant();
            } catch {
              Alert.alert("Erro", "Nao foi possivel trocar a loja agora.");
            }
          },
        },
      ],
    );
  }

  return requestStoreSwitch;
}
