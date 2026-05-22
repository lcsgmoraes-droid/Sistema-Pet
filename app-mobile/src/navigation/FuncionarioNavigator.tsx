import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import { Alert, Text, TouchableOpacity } from "react-native";
import FuncionarioCarrinhoScreen from "../screens/funcionario/FuncionarioCarrinhoScreen";
import FuncionarioConsultaScreen from "../screens/funcionario/FuncionarioConsultaScreen";
import FuncionarioScannerScreen from "../screens/funcionario/FuncionarioScannerScreen";
import { useAuthStore } from "../store/auth.store";
import { CORES } from "../theme";
import { FuncionarioStackParamList } from "../types/funcionarioNavigation";

const Stack = createNativeStackNavigator<FuncionarioStackParamList>();

function HeaderLogoutAction() {
  const { logout } = useAuthStore();

  const confirmarLogout = () => {
    Alert.alert("Sair da conta", "Deseja sair da conta de funcionario?", [
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
      <Text style={{ color: CORES.primario, fontWeight: "800" }}>Sair</Text>
    </TouchableOpacity>
  );
}

export default function FuncionarioNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerRight: HeaderLogoutAction,
        headerTitleStyle: { fontWeight: "800" },
      }}
    >
      <Stack.Screen name="FuncionarioConsulta" component={FuncionarioConsultaScreen} options={{ title: "PDV Funcionario" }} />
      <Stack.Screen name="FuncionarioScanner" component={FuncionarioScannerScreen} options={{ title: "Escanear", headerShown: false }} />
      <Stack.Screen name="FuncionarioCarrinho" component={FuncionarioCarrinhoScreen} options={{ title: "Carrinho PDV" }} />
    </Stack.Navigator>
  );
}
