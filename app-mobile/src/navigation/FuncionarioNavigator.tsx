import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import HeaderProfileActions from "../components/HeaderProfileActions";
import FuncionarioBalancoScreen from "../screens/funcionario/FuncionarioBalancoScreen";
import FuncionarioBanhoTosaScreen from "../screens/funcionario/FuncionarioBanhoTosaScreen";
import FuncionarioContagemScreen from "../screens/funcionario/FuncionarioContagemScreen";
import FuncionarioHomeScreen from "../screens/funcionario/FuncionarioHomeScreen";
import FuncionarioGranelScreen from "../screens/funcionario/FuncionarioGranelScreen";
import FuncionarioPdvScreen from "../screens/funcionario/FuncionarioPdvScreen";
import NotificationsScreen from "../screens/notifications/NotificationsScreen";
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
        name="FuncionarioGranel"
        component={FuncionarioGranelScreen}
        options={{ title: "Lancar granel" }}
      />
      <Stack.Screen
        name="FuncionarioPdv"
        component={FuncionarioPdvScreen}
        options={{ title: "PDV Rapido" }}
      />
      <Stack.Screen
        name="FuncionarioBanhoTosa"
        component={FuncionarioBanhoTosaScreen}
        options={{ title: "Banho & Tosa" }}
      />
      <Stack.Screen
        name="FuncionarioNovidades"
        component={NotificationsScreen}
        initialParams={{ somenteNovidades: true }}
        options={{ title: "Novidades" }}
      />
    </Stack.Navigator>
  );
}
