import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import HeaderProfileActions from "../components/HeaderProfileActions";
import FuncionarioBalancoScreen from "../screens/funcionario/FuncionarioBalancoScreen";
import FuncionarioContagemScreen from "../screens/funcionario/FuncionarioContagemScreen";
import FuncionarioHomeScreen from "../screens/funcionario/FuncionarioHomeScreen";
import FuncionarioPdvScreen from "../screens/funcionario/FuncionarioPdvScreen";
import { FuncionarioStackParamList } from "../types/funcionarioNavigation";

export type { FuncionarioStackParamList } from "../types/funcionarioNavigation";

const Stack = createNativeStackNavigator<FuncionarioStackParamList>();

export default function FuncionarioNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: "#059669" },
        headerTintColor: "#fff",
        headerTitleStyle: { fontWeight: "700" },
        headerRight: () => <HeaderProfileActions logoutContextLabel="funcionario" />,
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
        name="FuncionarioContagem"
        component={FuncionarioContagemScreen}
        options={{ title: "Contagem" }}
      />
      <Stack.Screen
        name="FuncionarioPdv"
        component={FuncionarioPdvScreen}
        options={{ title: "PDV Rapido" }}
      />
    </Stack.Navigator>
  );
}
