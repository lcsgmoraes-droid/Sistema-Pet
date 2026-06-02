import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import React, { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { usePushNotifications } from '../hooks/usePushNotifications';
import { useAuthStore } from '../store/auth.store';
import { useTenantStore } from '../store/tenant.store';
import { CORES } from '../theme';

// Navegadores
import AuthNavigator from './AuthNavigator';
import EntregadorNavigator from './EntregadorNavigator';
import FuncionarioNavigator from './FuncionarioNavigator';
import MainNavigator from './MainNavigator';
import VeterinarioNavigator from './VeterinarioNavigator';
import { navigationRef } from './navigationRef';

// Tela de seleção de loja
import SelecionarLojaScreen from '../screens/SelecionarLojaScreen';

const Stack = createNativeStackNavigator();

const appLinking = {
  prefixes: ["corepet://", "https://corepet.com.br/app"],
  config: {
    screens: {
      Pedidos: {
        screens: {
          ListaPedidos: "pedidos",
          Rastreio: "pedidos/:pedidoId/rastreio",
        },
      },
    },
  },
};

export default function AppNavigator() {
  const { isAuthenticated, isLoading: authLoading, loadUser, user } = useAuthStore();
  const { tenant, isLoading: tenantLoading, loadTenant } = useTenantStore();

  // Configura push notifications automaticamente após login
  usePushNotifications(isAuthenticated);

  useEffect(() => {
    // Carrega tenant e usuário em paralelo
    loadTenant();
    loadUser();
  }, []);

  // Aguarda os dois carregamentos
  if (authLoading || tenantLoading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: CORES.primario }}>
        <ActivityIndicator size="large" color="#fff" />
      </View>
    );
  }

  // Nenhuma loja vinculada → mostra onboarding de seleção
  if (!tenant) {
    return (
      <NavigationContainer linking={appLinking as any}>
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="SelecionarLoja" component={SelecionarLojaScreen} />
        </Stack.Navigator>
      </NavigationContainer>
    );
  }

  // Loja escolhida → fluxo normal (login ou app)
  let activeNav: React.ReactNode;
  if (!isAuthenticated) {
    activeNav = <AuthNavigator />;
  } else if (user?.is_veterinario || user?.perfil_operacional === "veterinario") {
    activeNav = <VeterinarioNavigator />;
  } else if (user?.is_entregador) {
    activeNav = <EntregadorNavigator />;
  } else if (user?.is_funcionario || user?.perfil_operacional === "funcionario") {
    activeNav = <FuncionarioNavigator />;
  } else {
    activeNav = <MainNavigator />;
  }

  return (
    <NavigationContainer ref={navigationRef} linking={appLinking as any}>
      {activeNav}
    </NavigationContainer>
  );
}

