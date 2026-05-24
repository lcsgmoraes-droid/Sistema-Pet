import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import { Alert, Text, TouchableOpacity } from "react-native";
import FuncionarioBalancoScreen from "../screens/funcionario/FuncionarioBalancoScreen";
import FuncionarioHomeScreen from "../screens/funcionario/FuncionarioHomeScreen";
import FuncionarioPdvScreen from "../screens/funcionario/FuncionarioPdvScreen";
import { useAuthStore } from "../store/auth.store";
import { FuncionarioStackParamList } from "../types/funcionarioNavigation";

export type { FuncionarioStackParamList } from "../types/funcionarioNavigation";

const Stack = createNativeStackNavigator<FuncionarioStackParamList>();

function HeaderLogoutAction() {
  const { logout } = useAuthStore();

  const confirmarLogout = () => {
    Alert.alert("Sair da conta", "Deseja sair da conta do funcionario?", [
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

export default function FuncionarioNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: "#059669" },
        headerTintColor: "#fff",
        headerTitleStyle: { fontWeight: "700" },
        headerRight: HeaderLogoutAction,
      }}
    >
      <Stack.Screen
        name="FuncionarioHome"
        component={FuncionarioHomeScreen}
        options={{ title: "Funcionario" }}
      />
      <Stack.Screen
        name="FuncionarioBalanco"
        component={FuncionarioBalancoScreen}
        options={{ title: "Balanco de Estoque" }}
      />
      <Stack.Screen
        name="FuncionarioPdv"
        component={FuncionarioPdvScreen}
        options={{ title: "PDV Rapido" }}
      />
    </Stack.Navigator>
  );
}
