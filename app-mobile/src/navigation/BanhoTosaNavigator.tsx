import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import HeaderProfileActions from "../components/HeaderProfileActions";
import FuncionarioBanhoTosaScreen from "../screens/funcionario/FuncionarioBanhoTosaScreen";

export type BanhoTosaStackParamList = {
  BanhoTosaOperacao: undefined;
};

const Stack = createNativeStackNavigator<BanhoTosaStackParamList>();

export default function BanhoTosaNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: "#059669" },
        headerTintColor: "#fff",
        headerTitleStyle: { fontWeight: "700" },
        headerRight: () => (
          <HeaderProfileActions logoutContextLabel="banho e tosa" />
        ),
      }}
    >
      <Stack.Screen
        name="BanhoTosaOperacao"
        component={FuncionarioBanhoTosaScreen}
        options={{ title: "Banho & Tosa" }}
      />
    </Stack.Navigator>
  );
}
