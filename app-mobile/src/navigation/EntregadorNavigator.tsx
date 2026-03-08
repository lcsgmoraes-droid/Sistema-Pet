import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import { Alert, Text, TouchableOpacity } from "react-native";
import DetalheEntregaScreen from "../screens/entregador/DetalheEntregaScreen";
import RotasDoEntregadorScreen from "../screens/entregador/RotasDoEntregadorScreen";
import { useAuthStore } from "../store/auth.store";
import { EntregadorStackParamList } from "../types/entregadorNavigation";

export type { EntregadorStackParamList } from "../types/entregadorNavigation";

const Stack = createNativeStackNavigator<EntregadorStackParamList>();

function HeaderLogoutAction() {
  const { logout } = useAuthStore();

  const confirmarLogout = () => {
    Alert.alert("Sair da conta", "Deseja sair da conta de entregador?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Sair",
        style: "destructive",
        onPress: () => {
          logout().catch(() => {
            Alert.alert("Erro", "Nao foi possivel sair agora.");
          });
        },
      },
    ]);
  };

  return (
    <TouchableOpacity onPress={confirmarLogout}>
      <Text style={{ color: "#fff", fontWeight: "600" }}>Sair</Text>
    </TouchableOpacity>
  );
}

// ─── Navigator ────────────────────────────────────────────────────────────────

export default function EntregadorNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: "#1e40af" },
        headerTintColor: "#fff",
        headerTitleStyle: { fontWeight: "700" },
        headerRight: HeaderLogoutAction,
      }}
    >
      <Stack.Screen
        name="MinhasRotas"
        component={RotasDoEntregadorScreen}
        options={{ title: "Minhas Entregas" }}
      />
      <Stack.Screen
        name="DetalheEntrega"
        component={DetalheEntregaScreen}
        options={{ title: "Detalhe da Entrega" }}
      />
    </Stack.Navigator>
  );
}
