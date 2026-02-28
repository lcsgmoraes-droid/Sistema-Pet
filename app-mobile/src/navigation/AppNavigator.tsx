import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuthStore } from '../store/auth.store';
import { useTenantStore } from '../store/tenant.store';
import { ActivityIndicator, View } from 'react-native';
import { CORES } from '../theme';
import { usePushNotifications } from '../hooks/usePushNotifications';

// Navegadores
import AuthNavigator from './AuthNavigator';
import MainNavigator from './MainNavigator';

// Tela de seleção de loja
import SelecionarLojaScreen from '../screens/SelecionarLojaScreen';

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  const { isAuthenticated, isLoading: authLoading, loadUser } = useAuthStore();
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
      <NavigationContainer>
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="SelecionarLoja" component={SelecionarLojaScreen} />
        </Stack.Navigator>
      </NavigationContainer>
    );
  }

  // Loja escolhida → fluxo normal (login ou app)
  return (
    <NavigationContainer>
      {isAuthenticated ? <MainNavigator /> : <AuthNavigator />}
    </NavigationContainer>
  );
}

