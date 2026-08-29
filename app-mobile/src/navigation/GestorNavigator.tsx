import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import HeaderProfileActions from "../components/HeaderProfileActions";
import GestorDashboardScreen from "../screens/gestor/GestorDashboardScreen";
import { CORES } from "../theme";
import { GestorStackParamList } from "../types/gestorNavigation";

const Stack = createNativeStackNavigator<GestorStackParamList>();

export default function GestorNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: CORES.primario },
        headerTintColor: "#fff",
        headerTitleStyle: { fontWeight: "800" },
        headerRight: () => <HeaderProfileActions logoutContextLabel="gestor" />,
      }}
    >
      <Stack.Screen
        name="GestorDashboard"
        component={GestorDashboardScreen}
        options={{ title: "Visao do gestor" }}
      />
    </Stack.Navigator>
  );
}
