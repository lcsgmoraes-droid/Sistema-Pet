import { useCallback } from 'react';
import { Alert } from 'react-native';
import { useAuthStore } from '../store/auth.store';

export function navigateToLogin(navigation: any) {
  let current = navigation;

  while (current) {
    const state = current.getState?.();
    if (state?.routeNames?.includes('Login')) {
      current.navigate('Login');
      return;
    }
    current = current.getParent?.();
  }

  navigation.navigate('Login');
}

export function useRequireAuth(navigation: any) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return useCallback(
    (action?: () => void, message = 'Entre na sua conta para continuar.') => {
      if (isAuthenticated) {
        action?.();
        return true;
      }

      Alert.alert('Entre na sua conta', message, [
        { text: 'Agora nao', style: 'cancel' },
        { text: 'Entrar', onPress: () => navigateToLogin(navigation) },
      ]);
      return false;
    },
    [isAuthenticated, navigation],
  );
}
