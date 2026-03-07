import { createNativeStackNavigator } from '@react-navigation/native-stack';
import React from 'react';
import DetalheEntregaScreen from '../screens/entregador/DetalheEntregaScreen';
import RotasDoEntregadorScreen from '../screens/entregador/RotasDoEntregadorScreen';
import { EntregadorStackParamList } from '../types/entregadorNavigation';

export type { EntregadorStackParamList } from '../types/entregadorNavigation';

const Stack = createNativeStackNavigator<EntregadorStackParamList>();

// ─── Navigator ────────────────────────────────────────────────────────────────

export default function EntregadorNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: '#1e40af' },
        headerTintColor: '#fff',
        headerTitleStyle: { fontWeight: '700' },
      }}
    >
      <Stack.Screen
        name="MinhasRotas"
        component={RotasDoEntregadorScreen}
        options={{ title: 'Minhas Entregas' }}
      />
      <Stack.Screen
        name="DetalheEntrega"
        component={DetalheEntregaScreen}
        options={{ title: 'Detalhe da Entrega' }}
      />
    </Stack.Navigator>
  );
}
