import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, Alert, View } from "react-native";
import { usePushNotifications } from "../hooks/usePushNotifications";
import { registerSessionExpiredHandler } from "../services/sessionExpiration";
import { useAuthStore } from "../store/auth.store";
import { useCartStore } from "../store/cart.store";
import { useTenantStore } from "../store/tenant.store";
import { CORES } from "../theme";

// Navegadores
import EntregadorNavigator from "./EntregadorNavigator";
import FuncionarioNavigator from "./FuncionarioNavigator";
import GestorNavigator from "./GestorNavigator";
import MainNavigator from "./MainNavigator";
import VeterinarioNavigator from "./VeterinarioNavigator";
import {
  flushPendingNavigation,
  navigateWhenReady,
  navigationRef,
} from "./navigationRef";

// Tela de seleção de loja
import SelecionarLojaScreen from "../screens/SelecionarLojaScreen";

const Stack = createNativeStackNavigator();

const appLinking = {
  prefixes: ["corepet://app", "corepet://", "https://corepet.com.br/app"],
  config: {
    screens: {
      AppTabs: {
        screens: {
          Pedidos: {
            screens: {
              ListaPedidos: "pedidos",
              Rastreio: "pedidos/:pedidoId/rastreio",
            },
          },
          Home: {
            screens: {
              Inicio: "inicio",
              Notificacoes: "notificacoes",
            },
          },
          Loja: {
            screens: {
              Catalogo: "produtos",
              DetalhesProduto: "produtos/:produtoId",
            },
          },
        },
      },
      Login: "login",
      Register: "cadastro",
      ForgotPassword: "recuperar-senha",
    },
  },
};

export default function AppNavigator() {
  const {
    isAuthenticated,
    isLoading: authLoading,
    loadUser,
    logout,
    user,
  } = useAuthStore();
  const { tenant, isLoading: tenantLoading, loadTenant } = useTenantStore();
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(
    () =>
      registerSessionExpiredHandler(async () => {
        await logout();
        setSessionExpired(true);
      }),
    [logout],
  );

  useEffect(() => {
    // Carrega tenant e usuário em paralelo
    loadTenant();
    loadUser();
  }, []);

  useEffect(() => {
    if (
      authLoading ||
      tenantLoading ||
      !isAuthenticated ||
      !user?.id ||
      !tenant?.id
    ) {
      return;
    }

    void useCartStore
      .getState()
      .carregar({ userId: user.id, tenantId: tenant.id });
  }, [authLoading, isAuthenticated, tenant?.id, tenantLoading, user?.id]);

  useEffect(() => {
    if (!sessionExpired || authLoading || tenantLoading || !tenant) return;

    navigateWhenReady("Login");
    Alert.alert("Sessao expirada", "Entre novamente para continuar.");
    setSessionExpired(false);
  }, [authLoading, sessionExpired, tenant, tenantLoading]);

  // Configura push notifications automaticamente após login
  usePushNotifications(isAuthenticated);

  // Aguarda os dois carregamentos
  if (authLoading || tenantLoading) {
    return (
      <View
        style={{
          flex: 1,
          justifyContent: "center",
          alignItems: "center",
          backgroundColor: CORES.primario,
        }}
      >
        <ActivityIndicator size="large" color="#fff" />
      </View>
    );
  }

  // Nenhuma loja vinculada → mostra onboarding de seleção
  if (!tenant) {
    return (
      <NavigationContainer linking={appLinking as any}>
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen
            name="SelecionarLoja"
            component={SelecionarLojaScreen}
          />
        </Stack.Navigator>
      </NavigationContainer>
    );
  }

  // Loja escolhida → fluxo normal (login ou app)
  let activeNav: React.ReactNode;
  if (
    isAuthenticated &&
    (user?.is_gestor || user?.perfil_operacional === "gestor")
  ) {
    activeNav = <GestorNavigator />;
  } else if (
    isAuthenticated &&
    (user?.is_veterinario || user?.perfil_operacional === "veterinario")
  ) {
    activeNav = <VeterinarioNavigator />;
  } else if (isAuthenticated && user?.is_entregador) {
    activeNav = <EntregadorNavigator />;
  } else if (
    isAuthenticated &&
    (user?.is_funcionario || user?.perfil_operacional === "funcionario")
  ) {
    activeNav = <FuncionarioNavigator />;
  } else {
    activeNav = <MainNavigator />;
  }

  return (
    <NavigationContainer
      ref={navigationRef}
      linking={appLinking as any}
      onReady={flushPendingNavigation}
    >
      {activeNav}
    </NavigationContainer>
  );
}
